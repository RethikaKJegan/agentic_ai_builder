import {defineConfig} from '@playwright/test';
import previous from './playwright.workflow-queries.config';
export default defineConfig({...previous,testMatch:/(overview-automation|workflow-queries)\.spec\.ts/});
