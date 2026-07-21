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

test("legal pages render publicly", async ({ page }) => {
  await page.goto("/privacy");
  await expect(page.getByRole("heading", { level: 1, name: "Privacy" })).toBeVisible();

  await page.goto("/terms");
  await expect(page.getByRole("heading", { level: 1, name: "Terms of use" })).toBeVisible();
});

test("the dashboard requires authentication", async ({ page }) => {
  await page.goto("/dashboard");

  await page.waitForURL("**/sign-in**");
  await expect(page).toHaveURL(/sign-in/);
});
