import {defineConfig} from '@playwright/test';
import previous from './playwright.workflow-queries.config';
export default defineConfig({...previous,testMatch:['natural-communication.spec.ts','overview-automation.spec.ts'],outputDir:'/home/raf/agentic-ai-builder/.local/natural-communication-20261112/browser-results',use:{...previous.use,launchOptions:{executablePath:'/home/raf/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome'}}});
