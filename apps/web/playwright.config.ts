import { defineConfig, devices } from "@playwright/test";

const port = Number(process.env.E2E_PORT ?? 3000);

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    // Full Chromium in new-headless mode; the separate headless shell binary
    // is blocked by some endpoint-protection tools.
    channel: "chromium",
    trace: "on-first-retry"
  },
  webServer: {
    command: `npm run dev -- --port ${port}`,
    url: `http://127.0.0.1:${port}`,
    reuseExistingServer: !process.env.CI,
    env: {
      // Placeholder Clerk keys: enough for public pages and the signed-out
      // redirect; no real Clerk account is contacted by these tests. The keys
      // must be pk_live_/sk_live_ shaped — dev-instance (pk_test_) keys make
      // clerkMiddleware redirect document requests to a Frontend API handshake
      // that does not exist for a placeholder domain.
      NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY:
        process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ?? "pk_live_Y2xlcmsuZXhhbXBsZS5jb20k",
      CLERK_SECRET_KEY: process.env.CLERK_SECRET_KEY ?? "sk_live_ci_placeholder",
      CLERK_JWT_TEMPLATE_NAME: "pricetracker-api",
      API_BASE_URL: process.env.API_BASE_URL ?? "http://127.0.0.1:8000"
    }
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile-chrome", use: { ...devices["Pixel 7"] } }
  ]
});
