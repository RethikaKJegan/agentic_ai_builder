import {test,expect} from '@playwright/test';
import {createHmac,randomBytes} from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {compositionViewSchema} from '../src/api/compositions';
import {dynamicView} from './fixtures/dynamic-investigation';
for(const mobile of [false,true])for(const clarify of [false,true])test(`no-ID workflow prompt, account, ${clarify?'clarification':'coverage'} and refresh ${mobile?'mobile':'desktop'}`,async({page})=>{
 if(mobile)await page.setViewportSize({width:390,height:844});
 const payload=`${Math.floor(Date.now()/1000)+3600}.${randomBytes(24).toString('hex')}`;
 await page.context().addCookies([{name:'builder_workspace_access',value:`${payload}.${createHmac('sha256',process.env['BUILDER_LOGIN_SECRET']!).update(payload).digest('hex')}`,domain:'127.0.0.1',path:'/'}]);
 const doc=JSON.parse(fs.readFileSync(path.resolve(import.meta.dirname,'../src/test/fixtures/orchestration.json'),'utf8')).document;
 const goal='Find complaints with 0–100 operating hours, calculate statistics, create a spreadsheet and email me.';
 doc.action_plan.goal=goal;doc.interaction_mode='goal';
 const view=compositionViewSchema.parse({...dynamicView('completed'),composition_id:doc.composition_id,workflow_id:'cw_'+doc.composition_id.replace('composition_',''),objective:goal});
 const saved={state:'completed',verified_receipt:true,output:{query_id:'dqj_persisted',coverage:{complete_scan:true,aggregate_complete:true,returned_rows:1,total_result_rows:1,has_more:false},result:{matched_rows:603,executed_at:'2026-11-09T12:00:00Z',warnings:['Separate sources have independent read times.'],columns:[{key:'count',label:'Matching complaints'}],rows:[{count:603}]}}};
 view.run={...view.run!,action_instances:{read:saved}} as typeof view.run;
 const question='Define the complaint operating-hours field and unit before querying.';
 if(clarify){
  view.run!.status='blocked';view.run!.error_code='ACTION_INPUT_REQUIRED';
  view.tasks[0]!.state='needs_input';view.tasks[0]!.result={classification:'query_clarification',state:'needs_input',summary:'This query needs a business definition before it can run.',missing_information:[question],records:[],rule_results:[],tool_receipts:[]};
  view.recovery={eligible:false,can_clarify:true,reason:question};
  view.run!.action_instances={read:{state:'needs_input',resolved_inputs:{query:{clarification:question}}}};
 }
 let submitted:Record<string,unknown>|undefined;
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/backend/**',async route=>{
  const req=route.request();const target=new URL(req.url()).pathname.replace('/api/backend/','');let data:unknown={items:[],total:0,has_more:false,next_cursor:null};
  if(target==='session')data={mode:'local-development',planning_available:true,runtime_available:true,approval_service_available:true,dynamic_composition_available:true,auth:{subject:{subject_id:'alice',workspace_id:'one'},roles:['admin'],permissions:['workflow.view','workflow.plan','tools.read','runs.view'],scopes:['workspace:read'],decision:'allow'}};
  else if(target.startsWith('workflow-overview'))data={items:[],next_sequence:0,has_more:false};
  else if(target==='integrations/google/connections')data={configured:true,setup_message:null,callback_uri:null,callback_in_client_file:false,shared_demo_identity:false,capabilities:[],items:[{connection_id:doc.google_connection_id,account_email:'owner@example.com',status:'connected',granted_scopes:[],revision:1,created_at:'2026-11-09T12:00:00Z',updated_at:'2026-11-09T12:00:00Z',last_verified_at:null,last_error_code:null,capabilities:{}}]};
  else if(target==='business-ontology/v1/action-plans'&&req.method()==='POST'){submitted=req.postDataJSON();data=doc;}
  else if(target==='business-ontology/v1/action-plans/'+doc.composition_id)data=doc;
  else if(target.endsWith('/compositions/'+doc.composition_id+'/view'))data=view;
  await route.fulfill({json:{request_id:'query_browser',status:200,data}});
 });
 await page.goto('/app');await page.getByLabel('Process description').fill(goal);
 await page.getByLabel('Workflow Google account').selectOption(doc.google_connection_id);
 await page.getByRole('button',{name:'Generate workflow',exact:true}).click();
 await expect(page).toHaveURL(/connected=1.*composition=/);
 expect(submitted).toMatchObject({objective:goal,google_connection_id:doc.google_connection_id,automatic_inputs:true,user_values:{}});
 await expect(page.getByLabel('Workflow Google account')).toHaveValue(doc.google_connection_id);
 if(clarify){
  await expect(page.getByRole('heading',{name:'Clarification needed',exact:true})).toBeVisible();
  await expect(page.getByText(question,{exact:true})).toBeVisible();
  await expect(page.getByText(/Reconcile the external action/)).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Generate clarified workflow'})).toBeDisabled();
  await page.reload();await expect(page.getByText(question,{exact:true})).toBeVisible();
  await page.getByLabel('Business definition').fill('Use the numeric recorded meter reading in hours.');
  await page.getByRole('button',{name:'Generate clarified workflow'}).click();
  await expect.poll(()=>submitted?.['objective']).toContain('Business definition supplied by the user: Use the numeric recorded meter reading in hours.');
  expect(submitted?.['google_connection_id']).toBe(doc.google_connection_id);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  expect(errors).toEqual([]);return;
 }
 await page.getByRole('tab',{name:'report',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Verified query results',exact:true})).toBeVisible();
 await expect(page.getByText('603 matching records. Showing 1 of 1 result rows.')).toBeVisible();
 await expect(page.getByText(/Statistics cover all matching records/)).toBeVisible();
 await page.reload();await page.getByRole('tab',{name:'report',exact:true}).click();
 await expect(page.getByRole('cell',{name:'603',exact:true})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 expect(errors).toEqual([]);
});
