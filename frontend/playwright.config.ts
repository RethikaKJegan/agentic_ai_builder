import { defineConfig } from "@playwright/test";
import path from "node:path";
process.env.PLAYWRIGHT_BROWSERS_PATH = path.resolve(import.meta.dirname, ".browser-cache");
const directory = process.env["BUILDER_E2E_FRONTEND_DIR"] ?? import.meta.dirname;
const repository = path.resolve(import.meta.dirname, "..");
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 60000,
  use: { baseURL: "http://127.0.0.1:3100", headless: true, trace: "retain-on-failure" },
  webServer: [{
    command: `${repository}/.venv-integrations/bin/python ${repository}/scripts/serve_ui_test_api.py`,
    cwd: repository,
    url: "http://127.0.0.1:8011/session",
    reuseExistingServer: false,
    timeout: 60000,
    env: { BUILDER_ENVIRONMENT: "test", BUILDER_DEV_AUTH: "1", BUILDER_REAL_CONNECTORS: "0", BUILDER_TEST_FRESH_DATABASE: "1", BUILDER_TEST_OPERATOR_REVIEW: "1",
      BUILDER_TEST_DATABASE_DIR: process.env["BUILDER_E2E_DATABASE_DIR"] ?? path.join(repository, ".local/browser-phase7"),
      BUILDER_UI_ORIGINS: "http://127.0.0.1:3100,http://localhost:3100" },
  }, {
    command: "npm run start -- --hostname 127.0.0.1 --port 3100",
    cwd: directory,
    url: "http://127.0.0.1:3100",
    reuseExistingServer: false,
    timeout: 60000,
    env: { BUILDER_ENVIRONMENT: "test", BUILDER_API_URL: "http://127.0.0.1:8011",
      BUILDER_UI_ORIGINS: "http://127.0.0.1:3100,http://localhost:3100" },
  }],
});
