import "server-only";

import { auth } from "@clerk/nextjs/server";

import {
  ApiError,
  PriceTrackerApi,
  type ApiNotification,
  type ApiPriceObservation,
  type ApiWatch
} from "@/lib/api/generated";
import {
  dashboardDtoSchema,
  notificationListDtoSchema,
  preferencesDtoSchema,
  trackedItemDtoSchema
} from "@/lib/api/schemas";
import type {
  CreateTrackedItemInput,
  DashboardDto,
  DataResult,
  NotificationDto,
  PreferencesDto,
  SavePreferencesInput,
  TrackedItemDto,
  UpdateTrackedItemInput
} from "@/lib/api/types";
import {
  demoDashboard,
  demoNotifications,
  demoPreferences,
  getDemoItem
} from "@/lib/demo-data";

const apiBaseUrl = process.env.API_BASE_URL;

export const isDemoMode =
  process.env.NEXT_PUBLIC_DEMO_MODE === "true" || !apiBaseUrl;

export async function getAccessToken() {
  if (!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY || !process.env.CLERK_SECRET_KEY) {
    throw new Error("Clerk is required when demo mode is disabled.");
  }
  const template = process.env.CLERK_JWT_TEMPLATE_NAME?.trim();
  if (!template) {
    throw new Error("CLERK_JWT_TEMPLATE_NAME is required when demo mode is disabled.");
  }
  const session = await auth();
  const token = await session.getToken({ template });
  if (!token) throw new Error("An authenticated Clerk session is required.");
  return token;
}

async function getClient() {
  if (!apiBaseUrl) return null;
  return new PriceTrackerApi(apiBaseUrl, await getAccessToken());
}

function currencyExponent(currency: string) {
  if (currency === "JPY") return 0;
  if (currency === "BHD" || currency === "KWD") return 3;
  return 2;
}

function fromMinor(value: number, currency: string) {
  return value / 10 ** currencyExponent(currency);
}

function toMinor(value: number, currency: string) {
  return Math.round(value * 10 ** currencyExponent(currency));
}

function mapSummary(watch: ApiWatch, history: ApiPriceObservation[]) {
  const currency = watch.product.currency ?? watch.currency;
  const historyNewestFirst = [...history].sort(
    (a, b) => Date.parse(b.observed_at) - Date.parse(a.observed_at)
  );
  const currentMinor =
    watch.product.current_price_minor ?? historyNewestFirst[0]?.price_minor ?? 0;
  const previousMinor = historyNewestFirst[1]?.price_minor ?? null;
  const lowestMinor = historyNewestFirst.length
    ? Math.min(...historyNewestFirst.map((point) => point.price_minor))
    : currentMinor;
  return {
    id: watch.id,
    title: watch.product.title ?? `${watch.product.store === "amazon" ? "Amazon" : "eBay"} item`,
    store: watch.product.store,
    productUrl: watch.product.canonical_url,
    imageUrl: watch.product.image_url,
    currentPrice: fromMinor(currentMinor, currency),
    previousPrice: previousMinor === null ? null : fromMinor(previousMinor, currency),
    targetPrice: fromMinor(watch.target_price_minor, watch.currency),
    lowestPrice: fromMinor(lowestMinor, currency),
    currency,
    status:
      watch.status === "paused"
        ? ("paused" as const)
        : currentMinor > 0 && currentMinor <= watch.target_price_minor
          ? ("target_reached" as const)
          : ("active" as const),
    lastCheckedAt: watch.product.last_checked_at ?? watch.updated_at
  };
}

function mapItem(watch: ApiWatch, history: ApiPriceObservation[]): TrackedItemDto {
  const summary = mapSummary(watch, history);
  return {
    ...summary,
    shippingPrice:
      watch.product.shipping_price_minor === null
        ? null
        : fromMinor(watch.product.shipping_price_minor, summary.currency),
    seller: null,
    priceHistory: [...history]
      .sort((a, b) => Date.parse(a.observed_at) - Date.parse(b.observed_at))
      .map((point) => ({
        capturedAt: point.observed_at,
        price: fromMinor(point.price_minor, point.currency)
      })),
    createdAt: watch.created_at
  };
}

function mapNotification(notification: ApiNotification): NotificationDto {
  const payload = notification.payload;
  const title =
    typeof payload.product_title === "string" ? payload.product_title : "Tracked item";
  const itemId = typeof payload.watch_id === "string" ? payload.watch_id : "unknown";
  const currency = typeof payload.currency === "string" ? payload.currency : "USD";
  const price =
    typeof payload.price_minor === "number"
      ? new Intl.NumberFormat("en-US", {
          style: "currency",
          currency
        }).format(fromMinor(payload.price_minor, currency))
      : "your target";
  return {
    id: notification.id,
    itemId,
    title: `${title} reached your target`,
    body: `The latest observed total is ${price}. Confirm price and availability at the store.`,
    createdAt: notification.created_at,
    readAt: notification.read_at
  };
}

async function withFallback<T>(
  request: (client: PriceTrackerApi) => Promise<T>,
  fallback: () => T
): Promise<DataResult<T>> {
  if (isDemoMode) {
    return { data: fallback(), source: "demo" };
  }

  const client = await getClient();
  if (!client) throw new Error("API_BASE_URL is required when demo mode is disabled.");

  try {
    return { data: await request(client), source: "api" };
  } catch (error) {
    console.error("PriceTracker API read failed", error);
    throw new Error("The live PriceTracker API request failed.", { cause: error });
  }
}

export function getDashboard(): Promise<DataResult<DashboardDto>> {
  return withFallback(
    async (client) => {
      const watches = await client.listWatches();
      const histories = await Promise.all(
        watches.map((watch) => client.getHistory(watch.id, "all"))
      );
      const items = watches.map((watch, index) => mapSummary(watch, histories[index] ?? []));
      const recentDrops = items.filter(
        (item) => item.previousPrice !== null && item.currentPrice < item.previousPrice
      );
      return dashboardDtoSchema.parse({
        trackedCount: items.length,
        activeCount: items.filter((item) => item.status !== "paused").length,
        targetReachedCount: items.filter((item) => item.status === "target_reached").length,
        totalPotentialSavings: recentDrops.reduce(
          (total, item) => total + Math.max((item.previousPrice ?? item.currentPrice) - item.currentPrice, 0),
          0
        ),
        recentDrops,
        items
      });
    },
    () => demoDashboard
  );
}

export function getItem(id: string): Promise<DataResult<TrackedItemDto | null>> {
  return withFallback<TrackedItemDto | null>(
    async (client) => {
      try {
        const [watch, history] = await Promise.all([
          client.getWatch(id),
          client.getHistory(id, "all")
        ]);
        return trackedItemDtoSchema.parse(mapItem(watch, history));
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null;
        throw error;
      }
    },
    () => getDemoItem(id)
  );
}

export function getNotifications(): Promise<DataResult<NotificationDto[]>> {
  return withFallback(
    async (client) =>
      notificationListDtoSchema.parse((await client.getNotifications()).map(mapNotification)),
    () => demoNotifications
  );
}

export function getPreferences(): Promise<DataResult<PreferencesDto>> {
  return withFallback(
    async (client) => {
      const preferences = await client.getPreferences();
      return preferencesDtoSchema.parse({
        emailNotifications: preferences.email_enabled,
        weeklyDigest: false,
        priceDropMinimumPercent: preferences.alert_rearm_percent,
        timezone: "UTC"
      });
    },
    () => demoPreferences
  );
}

export async function createItem(input: CreateTrackedItemInput) {
  if (isDemoMode) return { id: `demo-${Date.now()}` };
  const client = await getClient();
  if (!client) throw new Error("The API is not configured.");
  return client.createWatch({
    url: input.productUrl,
    target_price_minor: toMinor(input.targetPrice, input.currency),
    currency: input.currency,
    notify_initial_below_target: true
  });
}

export async function updateItem(id: string, input: UpdateTrackedItemInput) {
  if (isDemoMode) return getDemoItem(id);
  const client = await getClient();
  if (!client) throw new Error("The API is not configured.");
  const current = await client.getWatch(id);
  const updated = await client.updateWatch(id, {
    target_price_minor:
      input.targetPrice === undefined
        ? undefined
        : toMinor(input.targetPrice, current.currency),
    status: input.status
  });
  return mapItem(updated, await client.getHistory(id, "all"));
}

export async function deleteItem(id: string) {
  if (isDemoMode) return;
  const client = await getClient();
  if (!client) throw new Error("The API is not configured.");
  await client.deleteWatch(id);
}

export async function savePreferences(input: SavePreferencesInput) {
  if (isDemoMode) return { ...demoPreferences, ...input };
  const client = await getClient();
  if (!client) throw new Error("The API is not configured.");
  const saved = await client.savePreferences({
    email_enabled: input.emailNotifications,
    alert_rearm_percent: input.priceDropMinimumPercent
  });
  return preferencesDtoSchema.parse({
    emailNotifications: saved.email_enabled,
    weeklyDigest: false,
    priceDropMinimumPercent: saved.alert_rearm_percent,
    timezone: "UTC"
  });
}
