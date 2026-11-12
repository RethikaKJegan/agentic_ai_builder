import {defineConfig} from '@playwright/test';
import path from 'node:path';
process.env['PLAYWRIGHT_BROWSERS_PATH']=path.resolve(import.meta.dirname,'.browser-cache');
process.env['BUILDER_LOGIN_SECRET']='isolated-workflow-presentation-test';
export default defineConfig({testDir:'./e2e',testMatch:'investigation-actions.spec.ts',workers:1,timeout:60000,use:{baseURL:'http://127.0.0.1:3257',headless:true},webServer:{command:'npm run start -- --hostname 127.0.0.1 --port 3257',cwd:import.meta.dirname,url:'http://127.0.0.1:3257',reuseExistingServer:false,env:{BUILDER_LOGIN_SECRET:process.env['BUILDER_LOGIN_SECRET'],BUILDER_ENVIRONMENT:'test',BUILDER_UI_ORIGINS:'http://127.0.0.1:3257'}}});
