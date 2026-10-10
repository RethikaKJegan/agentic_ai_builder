import { defineConfig } from "@playwright/test";
process.env.PLAYWRIGHT_BROWSERS_PATH = ".browser-cache";
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  use: { baseURL: "http://127.0.0.1:3100", headless: true },
  webServer: [{
    command: "../.venv-integrations/bin/python ../scripts/serve_ui_test_api.py",
    url: "http://127.0.0.1:8011/session",
    reuseExistingServer: false,
    timeout: 60000,
  }, {
    command: "npm run start -- --hostname 127.0.0.1 --port 3100",
    url: "http://127.0.0.1:3100",
    reuseExistingServer: false,
    timeout: 60000,
    env: { BUILDER_API_URL: "http://127.0.0.1:8011" },
  }],
});
