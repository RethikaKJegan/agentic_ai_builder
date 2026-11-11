import {defineConfig} from '@playwright/test';
import previous from './playwright.workflow-queries.config';
export default defineConfig({...previous,testMatch:'knowledge-map.spec.ts',webServer:{...previous.webServer as object,cwd:process.env['BUILDER_E2E_FRONTEND_DIR']??'/dev/shm/praxi-knowledge-map-20261111/frontend'}});
