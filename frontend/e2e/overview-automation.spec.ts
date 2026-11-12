import {test,expect} from '@playwright/test';
import {createHmac,randomBytes} from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {dynamicView} from './fixtures/dynamic-investigation';

for(const event of [false,true])for(const mobile of [false,true])test(`existing Overview ${event?'event':'recurring'} review, consent and refresh ${mobile?'mobile':'desktop'}`,async({page})=>{
  if(mobile)await page.setViewportSize({width:390,height:844});
  const payload=`${Math.floor(Date.now()/1000)+3600}.${randomBytes(24).toString('hex')}`;
  await page.context().addCookies([{name:'builder_workspace_access',value:`${payload}.${createHmac('sha256',process.env['BUILDER_LOGIN_SECRET']!).update(payload).digest('hex')}`,domain:'127.0.0.1',path:'/'}]);
  const doc=JSON.parse(fs.readFileSync(path.resolve(import.meta.dirname,'../src/test/fixtures/orchestration.json'),'utf8')).document;
  const goal='Daily complaint report at 6 PM India time, email me.';doc.action_plan.goal=goal;doc.interaction_mode='goal';
  const view={...dynamicView('completed'),composition_id:doc.composition_id,workflow_id:'cw_'+doc.composition_id.replace('composition_',''),objective:goal,workflow_status:'approved',run:null};
  const proposal:Record<string,unknown>={version:'overview-intent-v1',state:'prepared',request_key:'',workspace:{workspace_id:'one',subject_id:'alice'},intent:{intent_type:'recurring',business_goal:'Daily complaint summary',side_effects:['email_send']},composition_id:doc.composition_id,schedule:{cron:'0 18 * * *',timezone:'Asia/Kolkata',next_due:1794313800,expires_at:1800000000,max_occurrences:90,missed_run_policy:'coalesce',overlap_policy:'forbid'},operations:{extension_mail_send:{properties:{to:{const:'owner@example.com'}}}}};
  if(event){proposal['schedule']=null;proposal['event_subscription']={source:{provider:'fixture',source_id:'synthetic-finance',event_type:'invoice.created',timezone:'Asia/Kolkata'},expires_at:1800000000,max_occurrences:90};}
  let activated=0;let preparations=0;let cancelled=false;const keys:string[]=[];let submitted:Record<string,unknown>|undefined;const errors:string[]=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/api/backend/**',async route=>{
    const req=route.request(),target=new URL(req.url()).pathname.replace('/api/backend/','');let data:unknown={items:[],total:0,has_more:false,next_cursor:null};
    if(target==='session')data={mode:'local-development',planning_available:true,planning_jobs_available:true,runtime_available:true,approval_service_available:true,dynamic_composition_available:true,overview_routing_available:true,auth:{subject:{subject_id:'alice',workspace_id:'one'},roles:['admin'],permissions:['workflow.view','workflow.plan','workflow.edit','workflow.validate','workflow.approve','workflow.execute','tools.read','runs.view'],scopes:['workspace:read'],decision:'allow'}};
    else if(target.startsWith('workflow-overview'))data={items:[],next_sequence:0,has_more:false};
    else if(target==='integrations/google/connections')data={configured:true,setup_message:null,callback_uri:null,callback_in_client_file:false,shared_demo_identity:false,capabilities:[],items:[{connection_id:doc.google_connection_id,account_email:'owner@example.com',status:'connected',granted_scopes:[],revision:1,created_at:'2026-11-10T12:00:00Z',updated_at:'2026-11-10T12:00:00Z',last_verified_at:null,last_error_code:null,capabilities:{}}]};
    else if(target==='planning-jobs'&&req.method()==='POST'){
      const envelope=req.postDataJSON();const body=envelope.payload.context.praxi_overview_request_v1;
      preparations++;keys.push(body.request_key);submitted={...body,overview:true};proposal['request_key']=body.request_key;data={job_id:'plan_overview_'+preparations,state:'queued',result:null};
    }else if(target.startsWith('planning-jobs/plan_overview_')){
      const id=target.slice('planning-jobs/'.length);
      if(req.method()==='DELETE')cancelled=true;
      data=id==='plan_overview_1'?{job_id:id,state:cancelled?'cancelled':'running',result:null}:{job_id:id,state:'succeeded',result:{request_id:'overview_browser',status:200,data:proposal}};
    }
    else if(target==='business-ontology/v1/action-plans'&&req.method()==='POST'){
      const body=req.postDataJSON();expect(body.overview).toBe(true);
      if(body.operation==='prepare'){submitted=body;proposal['request_key']=body.request_key;data=proposal;}
      else if(body.operation==='activate'){
        activated++;const activation={state:'active',schedule_id:'auto_reviewed',authorization_id:'auto_consent',due:1794313800};proposal['activation']=activation;proposal['schedule_record']={id:'auto_reviewed',state:'active',due:1794313800};proposal['automation_history']=[{id:'occ_fixture',state:'failed',due:1794313800,run_id:'run_fixture',last_error_code:'SOURCE_FRESHNESS_UNVERIFIED'}];data=activation;
      }else data=proposal;
    }else if(target==='business-ontology/v1/action-plans/'+doc.composition_id)data=doc;
    else if(target.endsWith('/compositions/'+doc.composition_id+'/view'))data=view;
    await route.fulfill({json:{request_id:'overview_browser',status:200,data}});
  });
  await page.goto('/app');await page.getByLabel('Process description').fill(goal);
  await page.getByLabel('Workflow Google account').selectOption(doc.google_connection_id);
  await page.getByRole('button',{name:'Generate workflow',exact:true}).click();
  await page.getByRole('button',{name:'Cancel generation',exact:true}).click();
  await expect(page.getByRole('button',{name:'Retry generation',exact:true})).toBeEnabled();
  expect(activated).toBe(0);await expect(page.getByLabel('Process description')).toHaveValue(goal);
  await page.getByRole('button',{name:'Retry generation',exact:true}).click();
  await expect(page.getByRole('region',{name:'Overview request review',exact:true})).toBeVisible();
  expect(keys).toHaveLength(2);expect(keys[0]).not.toBe(keys[1]);
  await expect(page).toHaveURL(/\/app\/workflows\/(?:investigate|editor)\?.*overview=/);
  expect(submitted).toMatchObject({objective:goal,google_connection_id:doc.google_connection_id,overview:true});
  expect(activated).toBe(0);expect(await page.getByLabel('Process description').count()).toBe(0);
  const activate=page.getByRole('button',{name:event?'Authorize and start event subscription':'Authorize and start schedule'});await expect(activate).toBeDisabled();
  await page.getByRole('checkbox').check();await activate.click();
  await expect(page.getByText(event?/Event subscription active\./:/Schedule active\. Next run:/)).toBeVisible();expect(activated).toBe(1);await expect(page.getByText(/failed · SOURCE_FRESHNESS_UNVERIFIED/)).toBeVisible();
  await page.reload();await expect(page.getByText(event?/Event subscription active\./:/Schedule active\. Next run:/)).toBeVisible();expect(activated).toBe(1);
  await page.goto('/app');await expect(page.getByLabel('Process description')).toBeVisible();
  await expect(page.getByRole('link',{name:'Open workflow',exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Authorize and start schedule'})).toHaveCount(0);
  await expect(page).toHaveURL(/\/app$/);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  expect(errors).toEqual([]);
});

for(const mobile of [false,true])test(`Overview queued generation cancel and same-prompt retry ${mobile?'mobile':'desktop'}`,async({page})=>{
  if(mobile)await page.setViewportSize({width:390,height:844});
  const token=`${Math.floor(Date.now()/1000)+3600}.${randomBytes(24).toString('hex')}`;
  await page.context().addCookies([{name:'builder_workspace_access',value:`${token}.${createHmac('sha256',process.env['BUILDER_LOGIN_SECRET']!).update(token).digest('hex')}`,domain:'127.0.0.1',path:'/'}]);
  const subject={workspace_id:'one',subject_id:'alice'};
  const submitted:string[]=[];let cancelled=false;
  const question={version:'overview-intent-v1',state:'clarification',request_key:'',workspace:subject,questions:['Which approved report should be updated?']};
  await page.route('**/api/backend/**',async route=>{
    const request=route.request(),target=new URL(request.url()).pathname.replace('/api/backend/','');
    let data:unknown={items:[],total:0,has_more:false,next_cursor:null};
    if(target==='session')data={mode:'local-development',planning_available:true,planning_jobs_available:true,runtime_available:true,approval_service_available:true,dynamic_composition_available:true,overview_routing_available:true,auth:{subject,roles:['admin'],permissions:['workflow.view','workflow.plan','workflow.edit','workflow.validate','workflow.approve','workflow.execute','tools.read','runs.view'],scopes:['workspace:read'],decision:'allow'}};
    else if(target.startsWith('workflow-overview'))data={items:[],next_sequence:0,has_more:false};
    else if(target==='integrations/google/connections')data={configured:false,items:[],setup_message:null};
    else if(target==='planning-jobs'&&request.method()==='POST'){
      const body=request.postDataJSON();expect(body.payload.context.praxi_overview_request_v1.objective).toBe('Daily report at 6 PM India time.');
      submitted.push(body.idempotency_key);question.request_key=body.idempotency_key;
      data=submitted.length===1?{job_id:'plan_first',state:'queued',result:null}:{job_id:'plan_second',state:'succeeded',result:{request_id:'req_second',status:200,data:question}};
    }else if(target==='planning-jobs/plan_first'){
      if(request.method()==='DELETE')cancelled=true;
      data={job_id:'plan_first',state:cancelled?'cancelled':'queued',result:null};
    }else if(target==='business-ontology/v1/action-plans'){
      const body=request.postDataJSON();expect(body.operation).toBe('get');data=question;
    }
    await route.fulfill({json:{request_id:'req_queue_browser',status:200,data}});
  });
  await page.goto('/app');await page.getByLabel('Process description').fill('Daily report at 6 PM India time.');
  await page.getByRole('button',{name:'Generate workflow',exact:true}).click();
  await page.getByRole('button',{name:'Cancel generation',exact:true}).click();
  await expect(page.getByRole('button',{name:'Retry generation',exact:true})).toBeEnabled();
  expect(cancelled).toBe(true);expect(submitted).toHaveLength(1);
  await page.getByRole('button',{name:'Retry generation',exact:true}).click();
  await expect(page.getByText(/no additional answer is requested here/)).toBeVisible();
  expect(submitted).toHaveLength(2);expect(submitted[0]).not.toBe(submitted[1]);
  await page.reload();await expect(page.getByText(/no additional answer is requested here/)).toBeVisible();
  await expect(page.getByRole('button',{name:'Authorize and start schedule'})).toHaveCount(0);
});

for(const mobile of [false,true])test(`Overview uncertain queue submission preserves retry identity ${mobile?'mobile':'desktop'}`,async({page})=>{
  if(mobile)await page.setViewportSize({width:390,height:844});
  const token=`${Math.floor(Date.now()/1000)+3600}.${randomBytes(24).toString('hex')}`;
  await page.context().addCookies([{name:'builder_workspace_access',value:`${token}.${createHmac('sha256',process.env['BUILDER_LOGIN_SECRET']!).update(token).digest('hex')}`,domain:'127.0.0.1',path:'/'}]);
  const subject={workspace_id:'one',subject_id:'alice'};const submitted:string[]=[];
  await page.route('**/api/backend/**',async route=>{
    const request=route.request(),target=new URL(request.url()).pathname.replace('/api/backend/','');let data:unknown={items:[],total:0,has_more:false,next_cursor:null};
    if(target==='session')data={mode:'local-development',planning_available:true,planning_jobs_available:true,runtime_available:true,approval_service_available:true,dynamic_composition_available:true,overview_routing_available:true,auth:{subject,roles:['admin'],permissions:['workflow.view','workflow.plan','workflow.edit','workflow.validate','workflow.approve','workflow.execute','tools.read','runs.view'],scopes:['workspace:read'],decision:'allow'}};
    else if(target.startsWith('workflow-overview'))data={items:[],next_sequence:0,has_more:false};
    else if(target==='integrations/google/connections')data={configured:false,items:[],setup_message:null};
    else if(target==='planning-jobs'&&request.method()==='POST'){
      const body=request.postDataJSON();submitted.push(body.idempotency_key);
      if(submitted.length===1){await route.abort('timedout');return;}
      data=submitted.length===2
        ?{job_id:'plan_failed',state:'failed',result:{request_id:'req_failed',status:504,data:{error:{error_code:'PLANNER_PROVIDER_TIMEOUT',message:'Generation timed out.',request_id:'req_failed',retryable:true}}}}
        :{job_id:'plan_recovered',state:'succeeded',result:{request_id:'req_recovered',status:200,data:{version:'overview-intent-v1',state:'clarification',request_key:body.idempotency_key,workspace:subject,questions:['Which timezone should this schedule use?']}}};
    }
    await route.fulfill({json:{request_id:'req_retry_browser',status:200,data}});
  });
  await page.goto('/app');await page.getByLabel('Process description').fill('Prepare my daily business summary.');
  await page.getByRole('button',{name:'Generate workflow',exact:true}).click();
  await expect(page.getByRole('button',{name:'Retry generation',exact:true})).toBeEnabled();
  await page.getByRole('button',{name:'Retry generation',exact:true}).click();
  await expect(page.getByText('Generation timed out.',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Retry generation',exact:true}).click();
  await expect(page.getByText(/no additional answer is requested here/)).toBeVisible();
  expect(submitted).toHaveLength(3);expect(submitted[0]).toBe(submitted[1]);expect(submitted[1]).not.toBe(submitted[2]);
});

for(const mobile of [false,true])for(const kind of ['population','one_time','restored_pending','blocked'])test(`Overview opens workflow details ${kind} ${mobile?'mobile':'desktop'}`,async({page})=>{
  if(mobile)await page.setViewportSize({width:390,height:844});
  const token=`${Math.floor(Date.now()/1000)+3600}.${randomBytes(24).toString('hex')}`;
  await page.context().addCookies([{name:'builder_workspace_access',value:`${token}.${createHmac('sha256',process.env['BUILDER_LOGIN_SECRET']!).update(token).digest('hex')}`,domain:'127.0.0.1',path:'/'}]);
  const doc=JSON.parse(fs.readFileSync(path.resolve(import.meta.dirname,'../src/test/fixtures/orchestration.json'),'utf8')).document;
  const goal='Count tickets by status and email me the average hmr.';doc.action_plan.goal=goal;doc.interaction_mode='goal';
  const subject={workspace_id:'one',subject_id:'alice'};
  const proposal={version:'overview-intent-v1',state:'prepared',workspace:subject,request_key:'restored_request',composition_id:doc.composition_id,intent:{intent_type:kind==='population'?'population':'one_time',business_goal:goal,side_effects:kind==='population'?[]:['email_send']},schedule:null};
  const view={...dynamicView('completed'),composition_id:doc.composition_id,workflow_id:'cw_'+doc.composition_id.replace('composition_',''),objective:goal,workflow_status:null,run:null};
  if(kind==='blocked'){doc.state='blocked';doc.overview_intent={question_free:true,blocked_requirements:[{requirement:'UNRESOLVED_REQUEST'}]};Object.assign(proposal,{blocked:true,questions:[],limitations:['No verified destination is available.']});Object.assign(view,{state:'blocked',gaps:[{description:'No verified destination is available.'}]});}
  let prepared=0,reads=0;const unexpected:string[]=[];const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  if(kind==='restored_pending')await page.addInitScript(()=>localStorage.setItem('praxi-overview-review-v1:one:alice','restored_request'));
  await page.route('**/api/backend/**',async route=>{
    const req=route.request(),target=new URL(req.url()).pathname.replace('/api/backend/','');let data:unknown={items:[],total:0,has_more:false,next_cursor:null};
    if(target==='session')data={mode:'local-development',planning_available:true,planning_jobs_available:false,runtime_available:true,approval_service_available:true,dynamic_composition_available:true,overview_routing_available:true,auth:{subject,roles:['admin'],permissions:['workflow.view','workflow.plan','workflow.edit','workflow.validate','workflow.approve','workflow.execute','tools.read','runs.view'],scopes:['workspace:read'],decision:'allow'}};
    else if(target.startsWith('workflow-overview'))data={items:[],next_sequence:0,has_more:false};
    else if(target==='integrations/google/connections')data={configured:true,setup_message:null,callback_uri:null,callback_in_client_file:false,shared_demo_identity:false,capabilities:[],items:[{connection_id:doc.google_connection_id,account_email:'owner@example.com',status:'connected',granted_scopes:[],revision:1,created_at:'2026-11-10T12:00:00Z',updated_at:'2026-11-10T12:00:00Z',last_verified_at:null,last_error_code:null,capabilities:{}}]};
    else if(target==='business-ontology/v1/action-plans'&&req.method()==='POST'){
      const body=req.postDataJSON();
      if(body.operation==='prepare'){prepared++;proposal.request_key=body.request_key;data=proposal;}
      else if(body.operation==='get'){
        reads++;data=kind==='restored_pending'&&reads===1?{...proposal,state:'planning',composition_id:undefined,planning_job:{job_id:'plan_restored',state:'running'}}:proposal;
      }else{unexpected.push(body.operation);}
    }else if(target==='business-ontology/v1/action-plans/'+doc.composition_id)data=doc;
    else if(target.endsWith('/compositions/'+doc.composition_id+'/view'))data=view;
    else if(!['GET','HEAD','OPTIONS'].includes(req.method()))unexpected.push(target);
    await route.fulfill({json:{request_id:'navigation_browser',status:200,data}});
  });
  await page.goto('/app');
  if(kind!=='restored_pending'){
    await page.getByLabel('Process description').fill(goal);
    await page.getByLabel('Workflow Google account').selectOption(doc.google_connection_id);
    await page.getByRole('button',{name:'Generate workflow',exact:true}).click();
  }
  await expect(page).toHaveURL(/\/app\/workflows\/(?:investigate|editor)\?.*composition=.*overview=/);
  await expect(page.getByRole('region',{name:'Overview request review',exact:true})).toBeVisible();
  await expect(page.getByRole('tab',{name:'Steps',exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Details',exact:true})).toBeVisible();
  await expect(page.getByLabel('Process description')).toHaveCount(0);
  await page.reload();await expect(page.getByRole('tab',{name:'Steps',exact:true})).toBeVisible();
  if(kind==='blocked'){await expect(page.getByText('Workflow draft blocked',{exact:true})).toBeVisible();await expect(page.getByRole('button',{name:'Run',exact:true})).toBeDisabled();await expect(page.getByRole('textbox')).toHaveCount(0);}
  expect(prepared).toBe(kind==='restored_pending'?0:1);expect(unexpected).toEqual([]);expect(errors).toEqual([]);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
