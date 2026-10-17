import { defineConfig } from '@playwright/test';
import path from 'node:path';
process.env.PLAYWRIGHT_BROWSERS_PATH = path.resolve(import.meta.dirname, '.browser-cache');
const verificationFrontend = process.env['PHASE1_FRONTEND_DIR'];
if (!verificationFrontend) throw new Error('Build an isolated frontend and set PHASE1_FRONTEND_DIR.');
export default defineConfig({
  testDir: './e2e', testMatch: ['phase1.spec.ts', 'session-recovery.spec.ts', 'prompt-only.spec.ts'], workers: 1,
  use: { baseURL: 'http://127.0.0.1:3100', headless: true },
  webServer: [{
    command: '../.venv-integrations/bin/python ../scripts/serve_ui_test_api.py',
    url: 'http://127.0.0.1:8011/session', reuseExistingServer: false, timeout: 60000,
    env: { BUILDER_ENVIRONMENT: 'test', BUILDER_DEV_AUTH: '1', BUILDER_UI_ORIGINS: 'http://127.0.0.1:3100,http://localhost:3100' },
  }, {
    command: 'npm run start -- --hostname 127.0.0.1 --port 3100', cwd: verificationFrontend,
    url: 'http://127.0.0.1:3100', reuseExistingServer: false, timeout: 60000,
    env: { BUILDER_ENVIRONMENT: 'test', BUILDER_API_URL: 'http://127.0.0.1:8011', BUILDER_UI_ORIGINS: 'http://127.0.0.1:3100,http://localhost:3100' },
  }],
});
