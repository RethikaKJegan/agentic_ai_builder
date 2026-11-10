import {defineConfig} from '@playwright/test';
import path from 'node:path';
process.env['PLAYWRIGHT_BROWSERS_PATH']=path.resolve(import.meta.dirname,'.browser-cache');
process.env['BUILDER_LOGIN_SECRET']='isolated-workflow-query-browser-key';
export default defineConfig({testDir:'./e2e',testMatch:'workflow-queries.spec.ts',workers:1,timeout:60000,use:{baseURL:'http://127.0.0.1:3261',headless:true,trace:'retain-on-failure'},webServer:{command:'npm run start -- --hostname 127.0.0.1 --port 3261',cwd:process.env['BUILDER_E2E_FRONTEND_DIR']??'/tmp/unified-query-build/frontend',url:'http://127.0.0.1:3261',reuseExistingServer:false,timeout:60000,env:{BUILDER_LOGIN_SECRET:process.env['BUILDER_LOGIN_SECRET'],BUILDER_ENVIRONMENT:'test',BUILDER_UI_ORIGINS:'http://127.0.0.1:3261'}}});
