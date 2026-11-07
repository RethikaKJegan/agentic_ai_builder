import {test,expect} from '@playwright/test';
import {createHmac,randomBytes} from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
const actionPlan=JSON.parse(fs.readFileSync(path.resolve(import.meta.dirname,'../src/test/fixtures/orchestration.json'),'utf8')).document;
const fixture=JSON.parse(fs.readFileSync(path.resolve(import.meta.dirname,'fixtures/investigation.json'),'utf8'));
for(const mobile of [false,true])test(`scenario context, preflight and classified report on ${mobile?'mobile':'desktop'}`,async({page})=>{
 if(mobile)await page.setViewportSize({width:390,height:844});
 const payload=`${Math.floor(Date.now()/1000)+3600}.${randomBytes(24).toString('hex')}`;
 const secret=process.env['BUILDER_LOGIN_SECRET']!;
 await page.context().addCookies([{name:'builder_workspace_access',value:`${payload}.${createHmac('sha256',secret).update(payload).digest('hex')}`,domain:'127.0.0.1',path:'/'}]);
 let submitted:Record<string,unknown>|null=null;let checked:Record<string,unknown>|null=null;
 const checks={inspection:{state:'ready_with_limitations',blocking_requirements:[],optional_limitations:[]},warranty:{state:'needs_input',blocking_requirements:[{fact_id:'assessment_date',reason:'Provide an assessment date.'}],optional_limitations:[]}};
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/backend/**',async route=>{
  const req=route.request();const target=new URL(req.url()).pathname.replace('/api/backend/','');let data:unknown={items:[],total:0,has_more:false,next_cursor:null};
  if(target==='session')data={mode:'local-development',planning_available:true,runtime_available:true,approval_service_available:true,auth:{subject:{subject_id:'local-builder',workspace_id:'local-workspace'},roles:['admin'],permissions:['workflow.view','workflow.plan','workflow.execute','tools.read','runs.view'],scopes:['workspace:read'],decision:'allow'}};
  else if(target.startsWith('workflow-overview'))data={items:[],next_sequence:0,has_more:false};
  else if(target.endsWith('/environments'))data={items:[{dataset_id:'dataset_fixture',cases:[{case_id:'case_fixture',label:'Complete · C123',source_identifiers:{complaint_id:'C123'}}]}]};
  else if(target.endsWith('/preflight')){checked=req.postDataJSON();data={preflight_id:'preflight_fixture',coverage:checks};}
  else if(target==='business-ontology/v1/action-plans'&&req.method()==='POST'){submitted=req.postDataJSON();data=actionPlan;}
  else if(target==='business-ontology/v1/action-plans/'+actionPlan.composition_id)data=actionPlan;
  else if(target==='business-ontology/v1/investigations')data={items:[],jobs:[]};
  else if(target.endsWith('/jobs')&&req.method()==='POST'){submitted=req.postDataJSON().payload;data={job_id:'job_coverage',kind:'plan',state:'queued',created_at:'2026-11-04T10:00:00Z',updated_at:'2026-11-04T10:00:00Z',workflow_id:null,run_id:null,error:null};}
  else if(target.endsWith('/jobs/job_coverage'))data={job_id:'job_coverage',kind:'plan',state:'running',created_at:'2026-11-04T10:00:00Z',updated_at:'2026-11-04T10:00:00Z',workflow_id:null,run_id:null,error:null};
  else if(target.includes('/plans/'))data={...fixture.plan,preflight:{preflight_id:'preflight_fixture',coverage:checks}};
  else if(target.includes('/runs/')){
   const run=structuredClone(fixture.run);run.outputs.end={...run.outputs.end,execution_status:'completed',scenario_context:{dataset_id:'dataset_fixture'},decision_readiness:{inspection:{state:'ready_with_limitations',business_outcomes:{},provenance:'scenario',official_approval:false},warranty:{state:'needs_input',business_outcomes:{},provenance:'scenario',official_approval:false}},missing_information:[{fact_id:'assessment_date',reason:'Provide an assessment date.',impact:'blocking_requested_conclusion'},{fact_id:'symptom_description',reason:'Optional catalogue description unavailable.',impact:'optional_supporting_evidence'}]};data=run;
  }
  await route.fulfill({json:{request_id:'req_coverage_fixture',status:200,data}});
 });
 await page.goto('/app');await page.getByLabel('Process description').fill('Compare complaint C123 with inspection and check warranty readiness.');
 await page.getByText('Workflow options',{exact:true}).click();
 await page.getByLabel('Evidence source').selectOption('dataset_fixture');
 await expect(page.getByText(/Scenario environment: generated supplemental evidence/)).toBeVisible();
 await page.getByLabel('Assessment date').fill('2026-11-04');
 await page.getByRole('button',{name:'Check evidence',exact:true}).click();
 await expect(page.getByText('warranty: needs input',{exact:true})).toBeVisible();
 expect(checked).toMatchObject({evidence_context:{dataset_id:'dataset_fixture',case_id:'case_fixture'},inputs:{assessment_date:'2026-11-04'}});
 await page.screenshot({path:`../.local/coverage-context-${mobile?'mobile':'desktop'}.png`,fullPage:true});
 await page.getByRole('button',{name:'Generate workflow',exact:true}).click();await expect(page).toHaveURL(/connected=1.*composition=/);
 expect(submitted).toMatchObject({business_request:{evidence_context:{dataset_id:'dataset_fixture',case_id:'case_fixture'},inputs:{assessment_date:'2026-11-04'}}});
 await page.goto('/app/workflows/investigate?workflow=investigation_fixture&run=run_fixture');
 await expect(page.getByRole('heading',{name:'Pre-run evidence coverage'})).toBeVisible();
 await page.getByRole('button',{name:'View report',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Decision readiness'})).toBeVisible();
 await expect(page.getByText(/Generated supplemental evidence and original source observations/)).toBeVisible();
 const optional=page.getByRole('heading',{name:'Optional evidence limitations'}).locator('xpath=following-sibling::ul[1]');
 await expect(optional).toContainText('Optional catalogue description unavailable.');await expect(optional).not.toContainText('Provide an assessment date.');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 await page.screenshot({path:`../.local/coverage-report-${mobile?'mobile':'desktop'}.png`,fullPage:true});
 expect(errors).toEqual([]);
});
