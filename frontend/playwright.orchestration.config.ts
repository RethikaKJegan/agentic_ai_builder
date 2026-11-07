import { defineConfig } from "@playwright/test";
import path from "node:path";
process.env["PLAYWRIGHT_BROWSERS_PATH"] = path.resolve(import.meta.dirname, ".browser-cache");
process.env["BUILDER_LOGIN_SECRET"] = "isolated-orchestration-browser-only";
const root = path.resolve(import.meta.dirname, "..");
export default defineConfig({
  testDir: "./e2e",
  testMatch: "connected-orchestration.spec.ts",
  workers: 1,
  timeout: 240000,
  expect: { timeout: 15000 },
  use: { baseURL: "http://127.0.0.1:3247", headless: true, trace: "retain-on-failure" },
  webServer: [
    {
      command: `${root}/.venv-integrations/bin/python -B ${root}/scripts/serve_orchestration_ui_test_api.py`,
      cwd: root,
      url: "http://127.0.0.1:8028/session",
      timeout: 60000,
      reuseExistingServer: false,
      env: { BUILDER_ENVIRONMENT: "test" },
    },
    {
      command: "npm run start -- --hostname 127.0.0.1 --port 3247",
      cwd: process.env["BUILDER_E2E_FRONTEND_DIR"] ?? path.resolve(root, ".local/frontend-phase4-stage"),
      url: "http://127.0.0.1:3247",
      timeout: 60000,
      reuseExistingServer: false,
      env: {
        BUILDER_ENVIRONMENT: "test",
        BUILDER_API_URL: "http://127.0.0.1:8028",
        BUILDER_LOGIN_SECRET: process.env["BUILDER_LOGIN_SECRET"],
        BUILDER_UI_ORIGINS: "http://127.0.0.1:3247",
      },
    },
  ],
});
