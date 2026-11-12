import {defineConfig} from '@playwright/test';
import previous from './playwright.knowledge-map.config';
export default defineConfig({...previous,testMatch:['subway-workflow-layout.spec.ts','knowledge-map.spec.ts'],outputDir:'/home/raf/agentic-ai-builder/.local/subway-report-layout-20261112/browser-results',use:{...previous.use,launchOptions:{executablePath:'/home/raf/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome'}}});
