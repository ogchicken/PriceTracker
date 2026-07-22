import "server-only";

import { z } from "zod";

export const pricePointDtoSchema = z.object({
  capturedAt: z.string().datetime({ offset: true }),
  price: z.number().nonnegative()
});

export const trackedItemSummaryDtoSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1).max(500),
  store: z.enum(["amazon", "ebay"]),
  productUrl: z.string().url(),
  imageUrl: z.string().url().nullable(),
  currentPrice: z.number().nonnegative(),
  previousPrice: z.number().nonnegative().nullable(),
  targetPrice: z.number().positive(),
  lowestPrice: z.number().nonnegative(),
  currency: z.string().length(3),
  status: z.enum(["active", "paused", "target_reached"]),
  lastCheckedAt: z.string().datetime({ offset: true })
});

export const trackedItemDtoSchema = trackedItemSummaryDtoSchema.extend({
  shippingPrice: z.number().nonnegative().nullable(),
  seller: z.string().max(300).nullable(),
  notifyBackInStock: z.boolean(),
  priceHistory: z.array(pricePointDtoSchema).max(10_000),
  createdAt: z.string().datetime({ offset: true })
});

export const dashboardDtoSchema = z.object({
  trackedCount: z.number().int().nonnegative(),
  activeCount: z.number().int().nonnegative(),
  targetReachedCount: z.number().int().nonnegative(),
  totalPotentialSavings: z.number().nonnegative(),
  recentDrops: z.array(trackedItemSummaryDtoSchema),
  items: z.array(trackedItemSummaryDtoSchema)
});

export const notificationDtoSchema = z.object({
  id: z.string().min(1),
  itemId: z.string().min(1),
  title: z.string().min(1).max(200),
  body: z.string().min(1).max(2_000),
  createdAt: z.string().datetime({ offset: true }),
  readAt: z.string().datetime({ offset: true }).nullable()
});

export const notificationListDtoSchema = z.array(notificationDtoSchema);

export const preferencesDtoSchema = z.object({
  emailNotifications: z.boolean(),
  weeklyDigest: z.boolean(),
  priceDropMinimumPercent: z.number().min(0).max(100),
  timezone: z.string().min(1).max(100)
});
