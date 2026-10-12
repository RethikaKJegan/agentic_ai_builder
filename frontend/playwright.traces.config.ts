import path from "node:path";
import { defineConfig } from "@playwright/test";
process.env.PLAYWRIGHT_BROWSERS_PATH = path.resolve(import.meta.dirname, ".browser-cache");
export default defineConfig({
  testDir: "./e2e", testMatch: ["workflow-traces.spec.ts", "agent-communication.spec.ts", "dynamic-delegation.spec.ts", "multitask-delegation.spec.ts", "delegated-tools.spec.ts", "prompt-only.spec.ts", "session-recovery.spec.ts"],
  use: { baseURL: "http://127.0.0.1:3211", headless: true },
  webServer: { command: "npm run start -- --hostname 127.0.0.1 --port 3211", url: "http://127.0.0.1:3211", reuseExistingServer: false, timeout: 60000 },
});
