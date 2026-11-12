import {test,expect} from '@playwright/test';
import {createHmac,randomBytes} from 'node:crypto';
import {knowledgeFixture} from '../src/test/fixtures/knowledge-map';

// UI compatibility uses explicitly synthetic persisted API responses. Actual
// Overview/Registry/OpenAI transport/CrewAI/query execution is covered in Python.
for(const autonomous of [false,true])for(const mobile of [false,true])test(`Subway Overview ${autonomous?'autonomous input resume':'query results and exact knowledge'} ${mobile?'mobile':'desktop'}`,async({page})=>{
 if(mobile)await page.setViewportSize({width:390,height:844});
 const payload=`${Math.floor(Date.now()/1000)+3600}.${randomBytes(24).toString('hex')}`;
 await page.context().addCookies([{name:'builder_workspace_access',value:`${payload}.${createHmac('sha256',process.env['BUILDER_LOGIN_SECRET']!).update(payload).digest('hex')}`,domain:'127.0.0.1',path:'/'}]);
 const f=knowledgeFixture('client-subway','Purchase order');const a=f.doc.action_plan.actions[0]!;
 f.doc.scope.owner='subway-client';f.doc.action_plan.scope.owner_id='subway-client';
 Object.assign(f.snapshot.knowledge!.source_mappings[0]!,{source_role:'finance',collection:'purchaseorders',field_path:'totalAmount'});
 const goal='Count purchase orders and calculate their average order value.';
 f.doc.action_plan.goal=goal;f.doc.google_connection_id=null;f.doc.interaction_mode='goal';a.capability_id='tool.subway_query';a.evidence_references=[];
 f.doc['overview_intent']={};f.doc['binding_context']={validated_context:{ontology_usage:{version_id:f.snapshot.version_id,scope:{workspace_id:'client-subway',owner_id:'subway-client'},query_kind:'subway',mappings:[{...f.snapshot.knowledge!.source_mappings[0],field_id:'amount',dataset_id:'purchaseorders'}],relationships:[]},subway_query_catalog:{sources:[{label:'finance.purchaseorders',fields:[{field_id:'amount',name:'totalAmount'}]}]}}};
 const instance=f.view.run!.action_instances![a.action_id]!;
 instance.resolved_inputs={query:{fields:[],metrics:[{label:'average',op:'avg',field_id:'amount'}],group_by:[],filters:[],joins:[]}};
 instance.output={query_id:'subway_synthetic_browser_query',ontology_version:f.snapshot.version_id,scope:{workspace_id:'client-subway',owner_id:'subway-client'},columns:[{id:'average',label:'Average order value'}],rows:[{average:'25.51'}],coverage:{complete_scan:true,aggregate_complete:true,matched_records:50,total_result_rows:1,returned_rows:1,has_more:false},sources:[{read_at:'2026-11-11T10:00:00Z'}],join_checks:[]};
 instance['ontology_usage']=[{version_id:f.snapshot.version_id,concept_id:'shared:case',mapping_id:'mapping:shared',field_id:'amount',query_id:'subway_synthetic_browser_query',reason:'Verified Subway query used this mapped source field.'}];
 if(autonomous){
  f.doc.action_plan.revision=2;
  Object.assign(f.view.run!,{status:'running',action_plan:f.doc.action_plan,adaptive:{objective:goal,status:'waiting_for_input',revision:2,turns:4,assessment:null,pending_wait:{wait_id:'subway_business_wait',requests:[{key:'threshold',schema:{type:'number',minimum:0},reason:'Choose the analytical threshold for this investigation.'}]},decisions:[{decision:'request_input',rationale:'Company threshold is unavailable; use an explicit analytical choice.',revision:2}],revisions:[]}});
 }
 const errors:string[]=[];const mutations:string[]=[];let submitted:Record<string,unknown>|undefined;
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/backend/**',async route=>{
  const req=route.request(),path=new URL(req.url()).pathname.replace('/api/backend/','');let data:unknown={items:[],total:0,has_more:false,next_cursor:null};
  if(req.method()!=='GET')mutations.push(path);
  if(autonomous&&path===`runs/${f.view.run!.run_id}/input`&&req.method()==='POST'){
   expect(req.postDataJSON()).toEqual({wait_id:'subway_business_wait',values:{threshold:125}});
   const state=f.view.run! as typeof f.view.run & {adaptive:{status:string;pending_wait:unknown}};
   state.adaptive.status='completed';state.adaptive.pending_wait=null;state.status='completed';
   data={run:{...state,workflow_id:f.view.workflow_id,workflow_version:1}};
  }
  else if(path==='session')data={mode:'client-isolated',planning_jobs_available:true,overview_routing_available:true,planning_available:true,runtime_available:true,approval_service_available:true,dynamic_composition_available:true,auth:{subject:{workspace_id:'client-subway',subject_id:'subway-client'},roles:['admin'],permissions:['workflow.view','workflow.plan','workflow.execute','tools.read','runs.view'],scopes:['workspace:read'],decision:'allow'}};
  else if(path.startsWith('workflow-overview'))data={items:[],next_sequence:0,has_more:false};
  else if(path==='integrations/google/connections')data={configured:true,setup_message:null,callback_uri:null,callback_in_client_file:false,shared_demo_identity:false,capabilities:[],items:[]};
  else if(path==='planning-jobs'&&req.method()==='POST'){submitted=req.postDataJSON();data={job_id:'plan_subway_fixture',state:'queued',result:null};}
  else if(path==='planning-jobs/plan_subway_fixture')data={job_id:'plan_subway_fixture',state:'succeeded',result:{request_id:'subway_browser',status:200,data:{version:'overview-intent-v1',state:'prepared',request_key:submitted?.['idempotency_key'],workspace:{workspace_id:'client-subway',subject_id:'subway-client'},intent:{intent_type:'population',business_goal:goal,side_effects:[]},composition_id:f.doc.composition_id,schedule:null}}};
  else if(path==='business-ontology/v1/action-plans/'+f.doc.composition_id)data=f.doc;
  else if(path.endsWith('/compositions/'+f.doc.composition_id+'/view'))data=f.view;
  else if(path==='business-ontology/v1/action-plans'&&req.method()==='POST')data={version:'overview-intent-v1',state:'prepared',request_key:submitted?.['idempotency_key'],workspace:{workspace_id:'client-subway',subject_id:'subway-client'},composition_id:f.doc.composition_id,intent:{intent_type:'population',business_goal:goal,side_effects:[]},schedule:null};
  else if(path==='business-ontology/v1')data=f.ontology;
  else if(path.startsWith('business-ontology/v1/automation'))data={items:[],has_more:false,next_cursor:null,jobs:[],health:{}};
  else if(path===`business-ontology/v1/versions/${f.snapshot.version_id}/knowledge`)data=f.snapshot;
  else if(path.endsWith('/knowledge')&&path.startsWith('runs/'))data={projections:[],qualification:'Synthetic browser fixture only.'};
  await route.fulfill({status:path==='planning-jobs'&&req.method()==='POST'?202:200,json:{request_id:'subway_browser',status:path==='planning-jobs'&&req.method()==='POST'?202:200,data}});
 });
 await page.goto('/app');await page.getByLabel('Process description').fill(goal);
 await page.getByRole('button',{name:'Generate workflow',exact:true}).click();
 await expect(page).toHaveURL(/connected=1.*composition=/);
 if(autonomous){
  await expect(page.getByRole('region',{name:'Autonomous investigation progress'})).toBeVisible();
  await expect(page.getByRole('status').filter({hasText:'Waiting for business input'})).toContainText('Plan revision 2');
  await page.getByLabel('Choose the analytical threshold for this investigation.').fill('125');
  await page.getByRole('button',{name:'Save input and resume'}).click();
  await expect(page.getByRole('status').filter({hasText:'Objective satisfied'})).toBeVisible();
 }
 expect(submitted).toMatchObject({operation:'plan_workflow',payload:{objective:goal}});
 await page.getByRole('tab',{name:'Reports',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Verified query results',exact:true})).toBeVisible();
 await expect(page.getByRole('cell',{name:'25.51',exact:true})).toBeVisible();
 await page.getByRole('tab',{name:'Knowledge Map',exact:true}).click();
 await expect(page.getByText('1 with recorded execution evidence',{exact:true})).toBeVisible();
 const node=page.locator('.react-flow__node').filter({hasText:'Purchase order'}).filter({hasText:'Executed · mapped evidence'});
 await node.click();await expect(page.getByLabel('Knowledge concept details').getByText(/finance.purchaseorders · totalAmount/)).toBeVisible();
 await page.reload();await page.getByRole('tab',{name:'Reports',exact:true}).click();
 await expect(page.getByRole('cell',{name:'25.51',exact:true})).toBeVisible();
 expect(mutations.every(path=>['planning-jobs','business-ontology/v1/action-plans',...(autonomous?[`runs/${f.view.run!.run_id}/input`]:[])].includes(path))).toBe(true);
 expect(errors).toEqual([]);
});
