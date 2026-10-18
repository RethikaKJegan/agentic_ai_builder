import path from "node:path";
import { defineConfig } from "@playwright/test";
process.env.PLAYWRIGHT_BROWSERS_PATH = path.resolve(import.meta.dirname, ".browser-cache");
const directory = process.env["GRAPH_FRONTEND_DIR"];
if (!directory) throw new Error("Set GRAPH_FRONTEND_DIR to an isolated verified production build.");
export default defineConfig({
  testDir: "./e2e",
  testMatch: [
    "semantic-kg.spec.ts",
    "data-insights.spec.ts",
    "knowledge-preview.spec.ts",
    "source-selection.spec.ts",
    "database-operations.spec.ts",
    "database-workflow.spec.ts",
    "data-queries.spec.ts",
    "data-query-jobs.spec.ts",
  ],
  workers: 1,
  timeout: 60000,
  use: { baseURL: "http://127.0.0.1:3217", headless: true },
  webServer: {
    command: "npm run start -- --hostname 127.0.0.1 --port 3217",
    cwd: directory,
    url: "http://127.0.0.1:3217",
    reuseExistingServer: false,
    timeout: 60000,
  },
});
