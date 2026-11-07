import {test,expect,type Page} from '@playwright/test';
import {createHmac,randomBytes} from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {dynamicView} from './fixtures/dynamic-investigation';
const base=JSON.parse(fs.readFileSync(path.resolve(import.meta.dirname,'../../shared/contracts/examples/workflows/support-triage.json'),'utf8'));
async function setup(page:Page,scenario:'normal'|'missing'|'failed'|'planning_failed'|'approval'|'uncertain'='normal'){
 const payload=`${Math.floor(Date.now()/1000)+3600}.${randomBytes(24).toString('hex')}`;
 await page.context().addCookies([{name:'builder_workspace_access',value:`${payload}.${createHmac('sha256',process.env['BUILDER_LOGIN_SECRET']!).update(payload).digest('hex')}`,domain:'127.0.0.1',path:'/'}]);
 let stage:Parameters<typeof dynamicView>[0]=scenario==='missing'?'needs_input':(scenario==='failed'||scenario==='uncertain')?'failed':'draft';let run=false,compose=0,execute=0,recover=0,decisions=0;
 await page.route('**/api/backend/**',async route=>{
  const req=route.request();const url=new URL(req.url());const target=url.pathname.replace('/api/backend/','');let data:unknown={items:[],total:0,has_more:false,next_cursor:null};
  const snapshot=()=>{const v=dynamicView(stage);if(scenario==='uncertain'&&v.run){v.run.status='blocked';v.run.error_code='UNKNOWN_INVOCATION_RESULT';v.recovery={eligible:false,reason:'Verify provider evidence before considering any recovery.'};}if(scenario==='approval'&&run&&decisions===0){v.run={...dynamicView('completed').run!,status:'paused_for_approval',approvals:[{approval_id:'approval_action',workflow_id:v.workflow_id,workflow_version:1,status:'pending',allowed_decisions:['approved','rejected']}],actions:[{node_id:'action_task_5',label:'Create message draft',state:'pending',inputs:{to:'fixture@example.test',subject:'Inspection',body:'Review the evidence.'},receipt:{}}]} as typeof v.run;}return v;};
  if(target==='session')data={mode:'local-development',planning_available:true,runtime_available:true,approval_service_available:true,dynamic_composition_available:true,auth:{subject:{subject_id:'local-builder',workspace_id:'local-workspace'},roles:['admin','approver'],permissions:['workflow.view','workflow.edit','workflow.plan','workflow.validate','workflow.approve','workflow.execute','tools.read','runs.view'],scopes:['workspace:read'],decision:'allow'}};
  else if(target.startsWith('workflow-overview'))data={items:[],next_sequence:0,has_more:false};
  else if(target==='business-ontology/v1/investigations')data={items:[],jobs:[]};
  else if(target==='business-ontology/v1/investigations/jobs'&&req.method()==='POST'){
   const body=req.postDataJSON();if(body.kind==='compose')compose++;else if(body.kind==='recover'){recover++;stage='completed';}
   data={job_id:body.kind==='compose'?'job_dynamic':'job_recover',kind:body.kind,state:'queued',workflow_id:null,run_id:body.kind==='recover'?'run_dynamic':null,created_at:'2026-11-04T12:00:00Z',updated_at:'2026-11-04T12:00:00Z',error:null};
  }else if(target.includes('/jobs/job_'))data={job_id:'job_dynamic',kind:target.endsWith('job_recover')?'recover':'compose',state:scenario==='planning_failed'?'failed':'succeeded',workflow_id:scenario==='planning_failed'?null:'cw_ui_fixture',composition_id:scenario==='planning_failed'?undefined:'composition_ui_fixture',run_id:recover?'run_dynamic':null,created_at:'2026-11-04T12:00:00Z',updated_at:'2026-11-04T12:00:00Z',error:scenario==='planning_failed'?{code:'CAPABILITY_SELECTION_INVALID',message:'The configured model could not produce a supported plan.'}:null};
  else if(target.endsWith('/compositions/composition_ui_fixture/view'))data=snapshot();
  else if(target==='workflows/cw_ui_fixture/validate'||target==='workflows/cw_ui_fixture/approve'){
   stage=target.endsWith('validate')?'validated':'approved';data={workflow:{...base,workflow_id:'cw_ui_fixture',inputs:[],status:stage}};
  }else if(target==='workflows/cw_ui_fixture/execute'){
   execute++;run=true;stage='completed';data={run:{run_id:'run_dynamic',workflow_id:'cw_ui_fixture',workflow_version:1,status:scenario==='approval'?'paused_for_approval':'completed',approvals:[]}};
  }else if(target==='approvals/approval_action/decision'){
   decisions++;stage='completed';data={approval_id:'approval_action',workflow_id:'cw_ui_fixture',workflow_version:1,status:'approved',allowed_decisions:[]};
  }else if(target==='integrations/google/connections')data={configured:false,setup_message:null,callback_uri:null,callback_in_client_file:false,shared_demo_identity:false,capabilities:[],items:[]};
  await route.fulfill({json:{request_id:'req_dynamic_ui',status:200,data}});
 });
 return {calls:()=>({compose,execute,recover,decisions})};
}
for(const mobile of [false,true])test(`saved workflow, dependencies, approval, report and drawers on ${mobile?'mobile':'desktop'}`,async({page})=>{
 if(mobile)await page.setViewportSize({width:390,height:844});const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));const mock=await setup(page);
 await page.goto('/app/workflows/investigate?composition=composition_ui_fixture');
 await expect(page.locator('.react-flow__node')).toHaveCount(5);
 await expect(page.getByRole('button',{name:'Run investigation',exact:true})).toHaveCount(0);
 await page.getByRole('button',{name:'Agents & tools',exact:true}).click();await expect(page.getByRole('heading',{name:'Agents and tools'})).toBeVisible();await page.getByRole('dialog').getByRole('button',{name:'Close'}).click();
 await page.getByRole('button',{name:'Ontology evidence',exact:true}).click();await expect(page.getByText('Engine',{exact:true})).toBeVisible();await expect(page.getByText(/saved_private_hash/)).not.toBeVisible();await page.getByText('Technical details',{exact:true}).click();await expect(page.getByText(/saved_private_hash/)).toBeVisible();await page.getByRole('dialog').getByRole('button',{name:'Close'}).click();
 await page.getByRole('button',{name:'Validate workflow',exact:true}).click();await expect(page.getByRole('button',{name:'Approve workflow',exact:true})).toBeVisible();await page.getByRole('button',{name:'Approve workflow',exact:true}).click();await page.getByRole('button',{name:'Run investigation',exact:true}).click();
 await expect(page).toHaveURL(/run=run_dynamic/);await expect(page.getByRole('button',{name:'View report',exact:true})).toBeEnabled();
 await page.getByRole('button',{name:'View report',exact:true}).click();await expect(page.getByRole('heading',{name:'Investigation completed',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Memory & recovery',exact:true}).click();await page.getByText('Scoped working memory',{exact:true}).click();await expect(page.getByText(/completed_tasks/)).toBeVisible();await page.getByRole('dialog').getByRole('button',{name:'Close'}).click();
 await page.getByRole('button',{name:'Workflow details',exact:true}).click();await expect(page.getByLabel('Business request',{exact:true})).toHaveValue('Compare complaint C123 with its linked inspection and prepare a source-backed report.');await expect(page.getByLabel('Workflow Google account',{exact:true})).toBeVisible();await page.getByRole('dialog').getByRole('button',{name:'Close'}).click();
 if(!mobile){const start=await page.getByRole('button',{name:'Start new run',exact:true}).boundingBox();const refresh=await page.getByRole('button',{name:'Refresh status',exact:true}).boundingBox();expect(Math.abs(start!.y-refresh!.y)).toBeLessThan(8);}
 await page.reload();await expect(page.getByRole('button',{name:'View report',exact:true})).toBeEnabled();expect(mock.calls()).toEqual({compose:0,execute:1,recover:0,decisions:0});expect(errors).toEqual([]);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 await page.screenshot({path:`test-results/dynamic-investigation-${mobile?'mobile':'desktop'}.png`,fullPage:true});
});
test('required inputs block execution and expose request editing',async({page})=>{
 await setup(page,'missing');await page.goto('/app/workflows/investigate?composition=composition_ui_fixture');await expect(page.getByText('Resolve setup requirements before running')).toBeVisible();await expect(page.getByRole('button',{name:'Run investigation',exact:true})).toHaveCount(0);await page.getByRole('button',{name:'Workflow details',exact:true}).click();await expect(page.getByLabel('Business request',{exact:true})).toBeVisible();
});
test('recovery submits one explicit job and never creates another run',async({page})=>{
 const mock=await setup(page,'failed');await page.goto('/app/workflows/investigate?composition=composition_ui_fixture&run=run_dynamic');await page.getByRole('button',{name:'Resume eligible work',exact:true}).click();await expect(page.getByRole('button',{name:'View report',exact:true})).toBeEnabled();expect(mock.calls().recover).toBe(1);expect(mock.calls().execute).toBe(0);
});
test('failed generation stays failed without an automatic model retry',async({page})=>{
 const mock=await setup(page,'planning_failed');await page.goto('/app/workflows/investigate?job=job_dynamic');await expect(page.getByText('The configured model could not produce a supported plan.')).toBeVisible();expect(mock.calls().compose).toBe(0);expect(mock.calls().execute).toBe(0);
});
test('external action approval remains a separate explicit decision',async({page})=>{
 const mock=await setup(page,'approval');await page.goto('/app/workflows/investigate?composition=composition_ui_fixture');await page.getByRole('button',{name:'Validate workflow',exact:true}).click();await page.getByRole('button',{name:'Approve workflow',exact:true}).click();await page.getByRole('button',{name:'Run investigation',exact:true}).click();await expect(page.getByText('External action approval required')).toBeVisible();expect(mock.calls().decisions).toBe(0);await page.getByText('Prepared action details',{exact:true}).click();await expect(page.getByText(/fixture@example.test/)).toBeVisible();await page.getByRole('button',{name:'Approve action',exact:true}).click();await expect(page.getByText('External action approval required')).toHaveCount(0);expect(mock.calls().decisions).toBe(1);
});

for(const mobile of [false,true])test(`pinned graph and reconciliation survive refresh on ${mobile?'mobile':'desktop'}`,async({page})=>{
 if(mobile)await page.setViewportSize({width:390,height:844});
 await setup(page,'uncertain');
 await page.route('**/api/backend/runs/run_dynamic/knowledge',route=>route.fulfill({json:{request_id:'phase3_graph',status:200,data:{projections:[{pin:{graph_id:'account_fixture',source_key:'fixture',revision:2,sha256:'fixture_hash'},current:false,reason:'Source freshness requires review.',nodes:[{node_id:'a',kind:'concept',label:'Inspection',status:'confirmed'},{node_id:'b',kind:'concept',label:'Complaint',status:'confirmed'}],edges:[{edge_id:'e',source:'a',target:'b',predicate:'investigates',status:'inferred'}]}],qualification:'Historical evidence only.'}}}));
 await page.route('**/api/backend/runs/run_dynamic/recovery',route=>route.fulfill({json:{request_id:'phase3_recovery',status:200,data:{run_id:'run_dynamic',status:'blocked',required_action:'operator_reconciliation',automatic_replay_allowed:false,uncertain_invocations:[{node_id:'send',effect_reference:'run_dynamic:send',required_action:'verify_provider'}],completed_checkpoints:[],consumed_usage:{},guidance:'Verify the provider before any retry.'}}}));
 await page.goto('/app/workflows/investigate?composition=composition_ui_fixture&run=run_dynamic');
 await page.getByRole('button',{name:'Ontology evidence',exact:true}).click();
 await expect(page.getByText('investigates',{exact:true})).toBeVisible();await expect(page.getByText(/Historical evidence — review freshness/)).toBeVisible();
 await page.getByRole('dialog').getByRole('button',{name:'Close'}).click();
 await page.reload();await page.getByRole('button',{name:'Memory & recovery',exact:true}).click();
 await expect(page.getByText('Provider outcome requires reconciliation')).toBeVisible();
 await expect(page.getByText(/run_dynamic:send/)).toBeVisible();
 await expect(page.getByRole('button',{name:'Resume eligible work',exact:true})).toHaveCount(0);
 await expect(page.getByRole('region',{name:'Recovery and reconciliation'}).getByRole('button')).toHaveCount(0);
 if(mobile)await expect.poll(async()=> (await page.getByRole('dialog').boundingBox())?.x??999).toBeLessThan(1);
 await page.screenshot({path:`test-results/phase3-evidence-${mobile?'mobile':'desktop'}.png`,fullPage:true,animations:'disabled'});
});
