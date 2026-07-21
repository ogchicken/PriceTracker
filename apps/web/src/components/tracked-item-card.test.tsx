import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TrackedItemCard } from "@/components/tracked-item-card";
import type { TrackedItemSummaryDto } from "@/lib/api/types";

const item: TrackedItemSummaryDto = {
  id: "keyboard",
  title: "Wireless mechanical keyboard",
  store: "ebay",
  productUrl: "https://www.ebay.com/itm/example",
  imageUrl: null,
  currentPrice: 84.5,
  previousPrice: 99,
  targetPrice: 85,
  lowestPrice: 79,
  currency: "USD",
  status: "target_reached",
  lastCheckedAt: new Date().toISOString()
};

describe("TrackedItemCard", () => {
  it("presents price and target status with a details link", () => {
    render(<TrackedItemCard item={item} />);

    expect(screen.getByText(item.title)).toBeInTheDocument();
    expect(screen.getByText("Target reached")).toBeInTheDocument();
    expect(screen.getByText("$84.50")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /view details/i })).toHaveAttribute(
      "href",
      "/items/keyboard"
    );
  });
});
