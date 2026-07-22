"use server";

import { auth } from "@clerk/nextjs/server";
import { revalidatePath } from "next/cache";
import { z } from "zod";

import {
  createItem,
  deleteItem,
  savePreferences,
  updateItem
} from "@/lib/api/server";
import { marketplaceForUrl } from "@/lib/store-url";

export interface ActionResult {
  ok: boolean;
  message: string;
  id?: string;
  fieldErrors?: Record<string, string[] | undefined>;
}

const supportedProductUrl = z
  .url("Enter a complete product URL, including https://.")
  .refine(
    (value) => marketplaceForUrl(value) !== null,
    "Only supported regional Amazon and eBay product links are currently accepted."
  );

const createItemSchema = z.object({
  productUrl: supportedProductUrl,
  targetPrice: z.coerce.number().positive("Target price must be greater than zero.").max(1_000_000),
  currency: z
    .string()
    .trim()
    .length(3, "Use a three-letter currency code.")
    .transform((value) => value.toUpperCase()),
  notifyBackInStock: z.boolean().optional()
});

const updateItemSchema = z.object({
  id: z.string().min(1),
  targetPrice: z.coerce.number().positive().max(1_000_000).optional(),
  status: z.enum(["active", "paused"]).optional(),
  notifyBackInStock: z.boolean().optional()
});

const preferencesSchema = z.object({
  emailNotifications: z.boolean(),
  weeklyDigest: z.boolean(),
  priceDropMinimumPercent: z.coerce.number().min(0).max(100)
});

async function requireAuthenticatedUser() {
  const { userId } = await auth();
  if (!userId) throw new Error("You must be signed in to make this change.");
  return userId;
}

export async function createTrackedItemAction(input: unknown): Promise<ActionResult> {
  const parsed = createItemSchema.safeParse(input);
  if (!parsed.success) {
    return {
      ok: false,
      message: "Check the highlighted fields.",
      fieldErrors: parsed.error.flatten().fieldErrors
    };
  }

  try {
    await requireAuthenticatedUser();
    const item = await createItem(parsed.data);
    revalidatePath("/dashboard");
    return {
      ok: true,
      message: "Item added. Price tracking has started.",
      id: item?.id
    };
  } catch (error) {
    return {
      ok: false,
      message: error instanceof Error ? error.message : "Unable to add this item."
    };
  }
}

export async function updateTrackedItemAction(input: unknown): Promise<ActionResult> {
  const parsed = updateItemSchema.safeParse(input);
  if (!parsed.success) {
    return { ok: false, message: "Enter a valid target price." };
  }
  try {
    await requireAuthenticatedUser();
    await updateItem(parsed.data.id, {
      targetPrice: parsed.data.targetPrice,
      status: parsed.data.status,
      notifyBackInStock: parsed.data.notifyBackInStock
    });
    revalidatePath(`/items/${parsed.data.id}`);
    revalidatePath("/dashboard");
    return {
      ok: true,
      message: "Tracking settings updated."
    };
  } catch (error) {
    return {
      ok: false,
      message: error instanceof Error ? error.message : "Unable to update this item."
    };
  }
}

export async function deleteTrackedItemAction(id: string): Promise<ActionResult> {
  try {
    await requireAuthenticatedUser();
    await deleteItem(id);
    revalidatePath("/dashboard");
    return {
      ok: true,
      message: "Item removed from your tracker."
    };
  } catch (error) {
    return {
      ok: false,
      message: error instanceof Error ? error.message : "Unable to delete this item."
    };
  }
}

export async function savePreferencesAction(input: unknown): Promise<ActionResult> {
  const parsed = preferencesSchema.safeParse(input);
  if (!parsed.success) {
    return { ok: false, message: "Check your notification settings." };
  }
  try {
    await requireAuthenticatedUser();
    await savePreferences(parsed.data);
    revalidatePath("/settings");
    return {
      ok: true,
      message: "Preferences saved."
    };
  } catch (error) {
    return {
      ok: false,
      message: error instanceof Error ? error.message : "Unable to save preferences."
    };
  }
}
