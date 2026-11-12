import {defineConfig} from '@playwright/test';
import previous from './playwright.workflow-queries.config';
export default defineConfig({...previous,testMatch:['subway-intelligence.spec.ts','knowledge-map.spec.ts','workflow-queries.spec.ts']});
