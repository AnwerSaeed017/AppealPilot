import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end tests: the real web app, built for production, against a mock of the API
 * that serves fixtures built from the API's own schemas (tests/e2e/mock-api).
 *
 *   npm run test:e2e              build, start and test
 *   E2E_DEV=1 npm run test:e2e    test against `next dev`, for quicker local runs
 */
const MOCK_API_PORT = 8765;
const WEB_PORT = 3100;
const dev = process.env.E2E_DEV === "1";

export default defineConfig({
  testDir: "tests/e2e",
  // The mock API holds state, so tests run one at a time and reset it first.
  fullyParallel: false,
  workers: 1,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: `http://127.0.0.1:${WEB_PORT}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] }, grep: /@mobile/ },
  ],
  webServer: [
    {
      command: "node tests/e2e/mock-api/server.mjs",
      url: `http://127.0.0.1:${MOCK_API_PORT}/health/live`,
      env: { MOCK_API_PORT: String(MOCK_API_PORT) },
      reuseExistingServer: !process.env.CI,
    },
    {
      command: dev
        ? `npx next dev -p ${WEB_PORT}`
        : `npx next build && npx next start -p ${WEB_PORT}`,
      url: `http://127.0.0.1:${WEB_PORT}/cases`,
      env: { API_URL: `http://127.0.0.1:${MOCK_API_PORT}` },
      timeout: 240_000,
      reuseExistingServer: !process.env.CI,
    },
  ],
});
