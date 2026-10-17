import { defineConfig } from "@playwright/test";
import path from "node:path";
process.env.PLAYWRIGHT_BROWSERS_PATH = path.resolve(import.meta.dirname, ".browser-cache");
const directory = process.env["PHASE4_FRONTEND_DIR"];
if (!directory) throw new Error("Set PHASE4_FRONTEND_DIR to the isolated production build.");
export default defineConfig({
  testDir: "./e2e",
  testMatch: [
    "phase4.spec.ts",
    "phase3.spec.ts",
    "phase1.spec.ts",
    "session-recovery.spec.ts",
    "prompt-only.spec.ts",
  ],
  workers: 1,
  use: { baseURL: "http://127.0.0.1:3100", headless: true },
  webServer: [
    {
      command: "../.venv-integrations/bin/python ../scripts/serve_ui_test_api.py",
      url: "http://127.0.0.1:8011/session",
      reuseExistingServer: false,
      timeout: 60000,
      env: {
        BUILDER_ENVIRONMENT: "test",
        BUILDER_DEV_AUTH: "1",
        BUILDER_REAL_CONNECTORS: "0",
        BUILDER_UI_ORIGINS: "http://127.0.0.1:3100,http://localhost:3100",
      },
    },
    {
      command: "npm run start -- --hostname 127.0.0.1 --port 3100",
      cwd: directory,
      url: "http://127.0.0.1:3100",
      reuseExistingServer: false,
      timeout: 60000,
      env: {
        BUILDER_ENVIRONMENT: "test",
        BUILDER_API_URL: "http://127.0.0.1:8011",
        BUILDER_UI_ORIGINS: "http://127.0.0.1:3100,http://localhost:3100",
      },
    },
  ],
});
