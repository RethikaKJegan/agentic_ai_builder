import { test,expect } from '@playwright/test';
import fs from 'node:fs';import path from 'node:path';
for(const mobile of [false,true])test(`workflow pages expose totals and navigate on ${mobile?'mobile':'desktop'}`,async({page})=>{
 if(mobile)await page.setViewportSize({width:390,height:844});
 const document=JSON.parse(fs.readFileSync(path.resolve(import.meta.dirname,'../../shared/contracts/examples/workflows/support-triage.json'),'utf8'));
 await page.route('**/api/backend/**',async route=>{
  const url=new URL(route.request().url());const name=url.pathname.replace('/api/backend/','');const later=!!url.searchParams.get('cursor');
  const ids=later?['page_0050']:['page_0000','page_0001'];
  let data:unknown={items:[],total:0,has_more:false,next_cursor:null};
  if(name==='session')data={mode:'local-development',planning_available:false,runtime_available:true,approval_service_available:true,auth:{subject:{subject_id:'operator',workspace_id:'local-workspace'},roles:['admin'],permissions:['workflow.view'],scopes:[],decision:'allow'}};
  else if(name==='workflows')data={items:ids.map(id=>({...document,workflow_id:id,name:id,status:'draft'})),total:51,has_more:!later,next_cursor:later?null:'page_0001'};
  else if(name==='workflow-overview')data={items:ids.map(id=>({workflow_id:id,name:id,draft_version:1,published_version:null,release_id:null,activation_state:null,active_run_count:0,latest_run_id:null,latest_run_status:null,pending_approval_count:0,updated_at:'2026-10-17T00:00:00Z'})),next_sequence:0,has_more:!later,next_cursor:later?null:'page_0001',total:51};
  await route.fulfill({json:{request_id:'req_pages',status:200,data}});
 });
 await page.goto('/app/workflows');await expect(page.getByText('page_0000',{exact:true})).toBeVisible();
 await expect(page.getByText(/2 of 51 server workflows/)).toBeVisible();
 await page.getByRole('button',{name:'Next workflows',exact:true}).click();
 await expect(page.getByText('page_0050',{exact:true})).toBeVisible();await expect(page.getByText('page_0000',{exact:true})).toHaveCount(0);
 await expect(page.getByRole('button',{name:'Next workflows',exact:true})).toBeDisabled();
 await page.getByRole('button',{name:'First workflows',exact:true}).click();await expect(page.getByText('page_0000',{exact:true})).toBeVisible();
});
