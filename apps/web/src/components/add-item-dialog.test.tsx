import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AddItemDialog, getMarketplaceSupport } from "@/components/add-item-dialog";

const mocks = vi.hoisted(() => ({
  createItem: vi.fn(),
  refresh: vi.fn()
}));

vi.mock("@/app/(app)/actions", () => ({
  createTrackedItemAction: mocks.createItem
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: mocks.refresh })
}));

describe("AddItemDialog", () => {
  beforeEach(() => {
    mocks.createItem.mockReset();
    mocks.refresh.mockReset();
    mocks.createItem.mockResolvedValue({
      ok: true,
      message: "Item added.",
      id: "item-1"
    });
  });

  it("identifies supported marketplace URLs", () => {
    expect(getMarketplaceSupport("https://www.amazon.com/dp/example")).toBe("amazon");
    expect(getMarketplaceSupport("https://www.ebay.com/itm/example")).toBe("ebay");
    expect(getMarketplaceSupport("https://example.com/product")).toBeNull();
  });

  it("shows honest feedback for unsupported links", async () => {
    const user = userEvent.setup();
    render(<AddItemDialog defaultOpen />);

    await user.type(screen.getByLabelText("Product URL"), "https://example.com/product");
    await user.type(screen.getByLabelText("Target price"), "80");
    await user.click(screen.getByRole("button", { name: "Start tracking" }));

    expect(
      await screen.findByText("This store is not supported yet. Use an Amazon or eBay product link.")
    ).toBeInTheDocument();
    expect(mocks.createItem).not.toHaveBeenCalled();
  });

  it("submits a supported item and refreshes the workspace", async () => {
    const user = userEvent.setup();
    render(<AddItemDialog defaultOpen />);

    await user.type(
      screen.getByLabelText("Product URL"),
      "https://www.amazon.com/dp/B09XS7JWHH"
    );
    await user.type(screen.getByLabelText("Target price"), "315.50");
    await user.click(screen.getByRole("button", { name: "Start tracking" }));

    await waitFor(() =>
      expect(mocks.createItem).toHaveBeenCalledWith({
        productUrl: "https://www.amazon.com/dp/B09XS7JWHH",
        targetPrice: 315.5,
        currency: "USD"
      })
    );
    expect(mocks.refresh).toHaveBeenCalled();
  });
});
