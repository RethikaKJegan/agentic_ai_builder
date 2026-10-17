import path from "node:path";
import { defineConfig } from "@playwright/test";
process.env.PLAYWRIGHT_BROWSERS_PATH = path.resolve(import.meta.dirname, ".browser-cache");
const directory = process.env["RELATIONSHIPS_FRONTEND_DIR"];
if (!directory) throw new Error("Set RELATIONSHIPS_FRONTEND_DIR to an isolated production build.");
export default defineConfig({
  testDir: "./e2e", testMatch: "data-relationships.spec.ts", workers: 1,
  use: {baseURL:"http://127.0.0.1:3216",headless:true},
  webServer:{command:"npm run start -- --hostname 127.0.0.1 --port 3216",cwd:directory,url:"http://127.0.0.1:3216",reuseExistingServer:false,timeout:60000},
});
