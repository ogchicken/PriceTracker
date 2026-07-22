export type Store = "amazon" | "ebay";
export type TrackingStatus = "active" | "paused" | "target_reached";

export interface PricePointDto {
  capturedAt: string;
  price: number;
}

export interface TrackedItemSummaryDto {
  id: string;
  title: string;
  store: Store;
  productUrl: string;
  imageUrl: string | null;
  currentPrice: number;
  previousPrice: number | null;
  targetPrice: number;
  lowestPrice: number;
  currency: string;
  status: TrackingStatus;
  lastCheckedAt: string;
}

export interface TrackedItemDto extends TrackedItemSummaryDto {
  shippingPrice: number | null;
  seller: string | null;
  notifyBackInStock: boolean;
  priceHistory: PricePointDto[];
  createdAt: string;
}

export interface DashboardDto {
  trackedCount: number;
  activeCount: number;
  targetReachedCount: number;
  totalPotentialSavings: number;
  recentDrops: TrackedItemSummaryDto[];
  items: TrackedItemSummaryDto[];
}

export interface NotificationDto {
  id: string;
  itemId: string;
  title: string;
  body: string;
  createdAt: string;
  readAt: string | null;
}

export interface PreferencesDto {
  emailNotifications: boolean;
  weeklyDigest: boolean;
  priceDropMinimumPercent: number;
  timezone: string;
}

export interface CreateTrackedItemInput {
  productUrl: string;
  targetPrice: number;
  currency: string;
  notifyBackInStock?: boolean;
}

export interface UpdateTrackedItemInput {
  targetPrice?: number;
  status?: "active" | "paused";
  notifyBackInStock?: boolean;
}

export interface SavePreferencesInput {
  emailNotifications: boolean;
  weeklyDigest: boolean;
  priceDropMinimumPercent: number;
}
