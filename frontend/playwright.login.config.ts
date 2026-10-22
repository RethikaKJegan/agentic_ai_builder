import { defineConfig } from "@playwright/test";
import { scryptSync } from "node:crypto";
import path from "node:path";
process.env.PLAYWRIGHT_BROWSERS_PATH = path.resolve(import.meta.dirname, ".browser-cache");
const directory = process.env["BUILDER_LOGIN_TEST_DIR"];
if (!directory) throw new Error("Set BUILDER_LOGIN_TEST_DIR to an isolated production build.");
const salt = "b".repeat(32);
export default defineConfig({
  testDir: "./e2e", testMatch: "workspace-login.spec.ts", workers: 1, timeout: 60000,
  use: { baseURL: "http://127.0.0.1:3100", headless: true, trace: "retain-on-failure" },
  webServer: [{
    command: "../.venv-integrations/bin/python ../scripts/serve_ui_test_api.py",
    url: "http://127.0.0.1:8011/session", reuseExistingServer: false, timeout: 60000,
    env: { BUILDER_ENVIRONMENT: "test", BUILDER_DEV_AUTH: "1", BUILDER_REAL_CONNECTORS: "0", BUILDER_TEST_FRESH_DATABASE: "1", BUILDER_TEST_OPERATOR_REVIEW: "1",
      BUILDER_TEST_DATABASE_DIR: path.resolve(import.meta.dirname, "../.local/workspace-login/browser-db"),
      BUILDER_UI_ORIGINS: "http://127.0.0.1:3100,http://localhost:3100" },
  }, {
    command: "npm run start -- --hostname 127.0.0.1 --port 3100", cwd: directory,
    url: "http://127.0.0.1:3100", reuseExistingServer: false, timeout: 60000,
    env: { BUILDER_ENVIRONMENT: "test", BUILDER_API_URL: "http://127.0.0.1:8011", BUILDER_UI_ORIGINS: "http://127.0.0.1:3100,http://localhost:3100",
      BUILDER_LOGIN_SECRET: "isolated-browser-fixture-secret-with-more-than-32-characters",
      BUILDER_LOGIN_PASSWORD_HASH: `${salt}:${scryptSync("12345678", salt, 64).toString("hex")}` },
  }],
});
