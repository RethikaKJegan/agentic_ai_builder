import path from "node:path";
import { defineConfig } from "@playwright/test";
process.env.PLAYWRIGHT_BROWSERS_PATH = path.resolve(import.meta.dirname, ".browser-cache");
export default defineConfig({
  testDir: "./e2e",
  testMatch: "slack-gmail.spec.ts",
  use: { baseURL: "http://127.0.0.1:3210", headless: true },
  webServer: {
    command: "npm run start -- --hostname 127.0.0.1 --port 3210",
    url: "http://127.0.0.1:3210",
    reuseExistingServer: false,
    timeout: 60000,
  },
});
