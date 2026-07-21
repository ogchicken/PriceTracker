import { expect, test } from "@playwright/test";

test("public landing page explains the product honestly", async ({ page }) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", { level: 1, name: "Buy when the price feels right." })
  ).toBeVisible();
  await expect(page.getByText("Amazon", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("eBay", { exact: true }).first()).toBeVisible();
  await expect(page.getByRole("link", { name: "Privacy" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Terms" })).toBeVisible();
});

test("demo dashboard renders without Clerk or a live API", async ({ page }) => {
  await page.goto("/dashboard");

  await expect(page.getByRole("heading", { level: 1, name: "Good prices start here." })).toBeVisible();
  await expect(page.getByText("Sample workspace")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Your tracked items" })).toBeVisible();
  await expect(
    page.getByRole("heading", {
      name: "Sony WH-1000XM5 Wireless Noise Cancelling Headphones"
    })
  ).toBeVisible();
});

test("a tracked item exposes history and controls", async ({ page }) => {
  await page.goto("/items/sony-headphones");

  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "Sony WH-1000XM5 Wireless Noise Cancelling Headphones"
    })
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Price history" })).toBeVisible();
  await expect(page.getByRole("tab", { name: "30D" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Tracking controls" })).toBeVisible();
});
