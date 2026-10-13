import { defineConfig } from "../frontend/node_modules/@playwright/test/index.mjs";
import path from "node:path";
const root = path.resolve(import.meta.dirname, "..");
const ui = process.env["BUILDER_EXTENSION_TEST_UI"];
if (!ui) throw new Error("Set BUILDER_EXTENSION_TEST_UI to an isolated production UI copy.");
process.env["PLAYWRIGHT_BROWSERS_PATH"] = path.join(root, "frontend/.browser-cache");
export default defineConfig({
  testDir: "./tests/browser", workers: 1,
  outputDir: path.join(root, ".local/connector-extension/browser-results"),
  use: { baseURL: "http://127.0.0.1:3313", headless: true },
  webServer: [
    { command: ".venv-integrations/bin/python -m connector_extension.tests.serve_browser_api", cwd: root,
      url: "http://127.0.0.1:8013/session", reuseExistingServer: false, timeout: 60000,
      env: { BUILDER_EXTENSION_UI_ORIGINS: "http://127.0.0.1:3313" } },
    { command: "npm run start -- --hostname 127.0.0.1 --port 3313", cwd: ui,
      url: "http://127.0.0.1:3313", reuseExistingServer: false, timeout: 60000,
      env: { BUILDER_API_URL: "http://127.0.0.1:8013" } },
  ],
});
