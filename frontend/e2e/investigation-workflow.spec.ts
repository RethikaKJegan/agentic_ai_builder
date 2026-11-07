import {test,expect,type Page} from '@playwright/test';
import {createHmac,randomBytes} from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
const fixture=JSON.parse(fs.readFileSync(path.resolve(import.meta.dirname,'fixtures/investigation.json'),'utf8'));
async function setup(page:Page,scenario:'normal'|'waiting'|'failed'='normal') {
 const payload=`${Math.floor(Date.now()/1000)+3600}.${randomBytes(24).toString('hex')}`;const secret=process.env['BUILDER_LOGIN_SECRET']!;
 await page.context().addCookies([{name:'builder_workspace_access',value:`${payload}.${createHmac('sha256',secret).update(payload).digest('hex')}`,domain:'127.0.0.1',path:'/'}]);
 let planCalls=0,executeCalls=0,planPolls=0,runPolls=0,inputCalls=0;let started=false;
 await page.route('**/api/backend/**',async route=>{
  const req=route.request();const target=new URL(req.url()).pathname.replace('/api/backend/','');let data:unknown={items:[],total:0,has_more:false,next_cursor:null};
  const job=(kind:string,state:string)=>({job_id:kind==='plan'?'job_plan':'job_execute',kind,state,created_at:'2026-11-03T10:00:00Z',updated_at:'2026-11-03T10:00:00Z',workflow_id:state==='succeeded'?fixture.plan.workflow_id:null,run_id:kind==='plan'?null:fixture.run.run_id,error:state==='failed'?{code:'INVESTIGATION_GRAPH_REJECTED',message:'The proposed workflow did not pass validation.'}:null});
  if(target==='session')data={mode:'local-development',planning_available:true,runtime_available:true,approval_service_available:true,auth:{subject:{subject_id:'local-builder',workspace_id:'local-workspace'},roles:['admin'],permissions:['workflow.view','workflow.plan','workflow.execute','tools.read','runs.view'],scopes:['workspace:read'],decision:'allow'}};
  else if(target.startsWith('workflow-overview'))data={items:[],next_sequence:0,has_more:false};
  else if(target==='business-ontology/v1/investigations')data={items:[],jobs:[]};
  else if(target==='business-ontology/v1/investigations/jobs'&&req.method()==='POST') {
   const body=req.postDataJSON();if(body.kind==='plan'){planCalls++;data=job('plan','queued');}else{executeCalls++;started=true;data=job(body.kind,'queued');}
  }else if(target.endsWith('/jobs/job_plan')){planPolls++;data=job('plan',scenario==='failed'?'failed':planPolls<2?'running':'succeeded');}
  else if(target.endsWith('/jobs/job_execute'))data=job('execute',runPolls>=1?'succeeded':'running');
  else if(target.includes('/plans/')) {
   if(target.endsWith('/runs'))data={...fixture.run,status:'queued',outputs:{},node_states:Object.fromEntries(fixture.plan.graph.nodes.map((n:{id:string})=>[n.id,'pending']))};
   else data=fixture.plan;
  }else if(target.includes('/runs/run_fixture/input')){inputCalls++;data={...fixture.run,status:'queued'};}
  else if(target.includes('/runs/run_fixture/cancel'))data={...fixture.run,status:'canceled'};
  else if(target.includes('/runs/run_fixture')){
   runPolls++;
   if(scenario==='waiting'&&!inputCalls)data={...fixture.run,status:'waiting_for_input',outputs:{},pending_inputs:[{node_id:'anchor',requested:['complaint_id or serial'],reason:'A concrete source identifier is required.'}],node_states:{start:'succeeded',anchor:'waiting_for_input'}};
   else data=started||new URL(page.url()).searchParams.has('run')?fixture.run:{...fixture.run,status:'queued',outputs:{}};
  }
  await route.fulfill({json:{request_id:'req_investigation_test',status:200,data}});
 });
 return {calls:()=>({planCalls,executeCalls,inputCalls})};
}
for(const mobile of [false,true])test(`prompt, branching canvas, execution and evidence on ${mobile?'mobile':'desktop'}`,async({page})=>{
 if(mobile)await page.setViewportSize({width:390,height:844});
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));const mock=await setup(page);
 await page.goto('/app');await page.getByLabel('Process description').fill('Investigate complaint C123, compare its linked inspection and check warranty readiness.');
 // Archived read-only plans remain inspectable/runable; the current Overview
 // action-plan generator is exercised by connected-orchestration.spec.ts.
 const planned=await page.evaluate(async()=>{const response=await fetch('/api/backend/business-ontology/v1/investigations/jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind:'plan',request_key:crypto.randomUUID(),payload:{objective:'Investigate complaint C123, compare its linked inspection and check warranty readiness.'}})});return {status:response.status};});
 expect(planned.status).toBe(200);
 await page.goto('/app/workflows/investigate?job=job_plan');
 await expect(page).toHaveURL(/workflows\/investigate\?.*job=job_plan/);
 await expect(page.getByRole('button',{name:'Run investigation',exact:true})).toBeVisible({timeout:15000});
 await expect(page.locator('.react-flow__node')).toHaveCount(18);
 await expect(page.locator('.react-flow__edge-text').getByText('Unknown',{exact:true}).first()).toBeVisible();
 await page.getByRole('button',{name:'Ontology evidence'}).click();
 await expect(page.getByRole('heading',{name:'Business knowledge used'})).toBeVisible();
 await expect(page.getByText(/Knowledge hash:/)).not.toBeVisible();
 await page.getByText('Technical details',{exact:true}).click();await expect(page.getByText(/Knowledge hash:/)).toBeVisible();
 await page.getByRole('dialog').getByRole('button',{name:'Close'}).click();
 await page.getByRole('button',{name:'Run investigation',exact:true}).click();
 await expect(page.getByRole('button',{name:'View report',exact:true})).toBeEnabled({timeout:15000});
 await page.getByRole('button',{name:/^steps$/i}).click();
 await page.getByRole('button',{name:'Retrieve complaint Completed'}).click();
 await expect(page.getByText('Found: 1 source record(s).')).toBeVisible();
 await page.getByRole('dialog').getByRole('button',{name:'Close'}).click();
 await page.getByRole('button',{name:'View report',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Investigation completed — additional evidence required'})).toBeVisible();
 await expect(page.getByText(/policy applicable — missing/)).toBeVisible();
 await page.getByRole('button',{name:'Source 1',exact:true}).click();await expect(page.getByRole('heading',{name:'Supporting source'})).toBeVisible();
 await page.getByRole('dialog').getByRole('button',{name:'Close'}).click();
 await page.reload();await expect(page.getByRole('button',{name:'View report',exact:true})).toBeEnabled();
 expect(mock.calls()).toEqual({planCalls:1,executeCalls:1,inputCalls:0});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 await page.screenshot({path:`../.local/investigation-ui-${mobile?'mobile':'desktop'}.png`,fullPage:true});
 expect(errors).toEqual([]);
});
test('missing identifier accepts typed input and resumes the saved run',async({page})=>{
 const mock=await setup(page,'waiting');await page.goto('/app/workflows/investigate?workflow=investigation_fixture&run=run_fixture');
 await page.getByLabel('Complaint or engine identifier').fill('C123');await page.getByRole('button',{name:'Continue investigation'}).click();
 await expect(page.getByRole('button',{name:'View report',exact:true})).toBeEnabled({timeout:15000});
 expect(mock.calls()).toEqual({planCalls:0,executeCalls:1,inputCalls:1});
});
test('failed generation shows its real error and never renders a fake graph',async({page})=>{
 await setup(page,'failed');await page.goto('/app/workflows/investigate?job=job_plan');
 await expect(page.getByText('The proposed workflow did not pass validation.')).toBeVisible();
 await expect(page.locator('.react-flow__node')).toHaveCount(0);
});
