import type {
  DashboardDto,
  NotificationDto,
  PreferencesDto,
  TrackedItemDto,
  TrackedItemSummaryDto
} from "@/lib/api/types";

const now = Date.now();
const hoursAgo = (hours: number) => new Date(now - hours * 3_600_000).toISOString();

const demoItems: TrackedItemSummaryDto[] = [
  {
    id: "sony-headphones",
    title: "Sony WH-1000XM5 Wireless Noise Cancelling Headphones",
    store: "amazon",
    productUrl: "https://www.amazon.com/dp/B09XS7JWHH",
    imageUrl: null,
    currentPrice: 328,
    previousPrice: 399.99,
    targetPrice: 315,
    lowestPrice: 298,
    currency: "USD",
    status: "active",
    lastCheckedAt: hoursAgo(1)
  },
  {
    id: "mechanical-keyboard",
    title: "Low Profile Wireless Mechanical Keyboard",
    store: "ebay",
    productUrl: "https://www.ebay.com/itm/126000000001",
    imageUrl: null,
    currentPrice: 84.5,
    previousPrice: 99,
    targetPrice: 85,
    lowestPrice: 79,
    currency: "USD",
    status: "target_reached",
    lastCheckedAt: hoursAgo(3)
  },
  {
    id: "espresso-machine",
    title: "Compact Barista Espresso Machine with Milk Frother",
    store: "amazon",
    productUrl: "https://www.amazon.com/dp/B0DEMO1234",
    imageUrl: null,
    currentPrice: 549,
    previousPrice: 529,
    targetPrice: 475,
    lowestPrice: 499,
    currency: "USD",
    status: "active",
    lastCheckedAt: hoursAgo(5)
  },
  {
    id: "travel-backpack",
    title: "Carry-on Travel Backpack, 40L",
    store: "ebay",
    productUrl: "https://www.ebay.com/itm/126000000002",
    imageUrl: null,
    currentPrice: 64,
    previousPrice: 64,
    targetPrice: 55,
    lowestPrice: 58,
    currency: "USD",
    status: "paused",
    lastCheckedAt: hoursAgo(28)
  }
];

function historyFor(item: TrackedItemSummaryDto) {
  return Array.from({ length: 90 }, (_, index) => {
    const age = 89 - index;
    const wave = Math.sin(index / 7) * item.currentPrice * 0.025;
    const trend = age * item.currentPrice * 0.0014;
    const drop = index > 70 ? -item.currentPrice * 0.035 : 0;
    return {
      capturedAt: new Date(now - age * 86_400_000).toISOString(),
      price: Number(Math.max(item.lowestPrice, item.currentPrice + wave + trend + drop).toFixed(2))
    };
  });
}

export const demoDashboard: DashboardDto = {
  trackedCount: demoItems.length,
  activeCount: demoItems.filter((item) => item.status === "active").length,
  targetReachedCount: demoItems.filter((item) => item.status === "target_reached").length,
  totalPotentialSavings: 139.49,
  recentDrops: demoItems.filter(
    (item) => item.previousPrice !== null && item.currentPrice < item.previousPrice
  ),
  items: demoItems
};

export const demoNotifications: NotificationDto[] = [
  {
    id: "notification-1",
    itemId: "mechanical-keyboard",
    title: "Target reached",
    body: "The mechanical keyboard is now $84.50, below your $85.00 target.",
    createdAt: hoursAgo(3),
    readAt: null
  },
  {
    id: "notification-2",
    itemId: "sony-headphones",
    title: "Price dropped 18%",
    body: "Sony WH-1000XM5 dropped from $399.99 to $328.00.",
    createdAt: hoursAgo(18),
    readAt: hoursAgo(12)
  }
];

export const demoPreferences: PreferencesDto = {
  emailNotifications: true,
  weeklyDigest: false,
  priceDropMinimumPercent: 5,
  timezone: "America/New_York"
};

export function getDemoItem(id: string): TrackedItemDto | null {
  const item = demoItems.find((candidate) => candidate.id === id);
  if (!item) return null;
  return {
    ...item,
    shippingPrice: item.store === "ebay" ? 6.95 : 0,
    seller: item.store === "ebay" ? "Verified seller" : "Amazon",
    priceHistory: historyFor(item),
    createdAt: hoursAgo(24 * 42)
  };
}
