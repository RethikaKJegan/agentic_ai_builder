import {test,expect} from '@playwright/test';
import {createHmac,randomBytes} from 'node:crypto';
for(const tenant of ['client-subway','simpsons'])for(const mobile of [false,true])test(`natural communication ${tenant} ${mobile?'mobile':'desktop'}`,async({page})=>{
 await page.setViewportSize(mobile?{width:390,height:844}:{width:1440,height:1000});
 const p=`${Math.floor(Date.now()/1000)+3600}.${randomBytes(24).toString('hex')}`;
 await page.context().addCookies([{name:'builder_workspace_access',value:p+'.'+createHmac('sha256',process.env['BUILDER_LOGIN_SECRET']!).update(p).digest('hex'),domain:'127.0.0.1',path:'/'}]);
 const goal='Every day at 10:20 PM India time, investigate exceptions, prepare an email report and a calendar event for 30 minutes.';
 let current:Record<string,unknown>|undefined;const submissions:Record<string,unknown>[]=[],errors:string[]=[];let activates=0;
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/backend/**',async route=>{
  const req=route.request(),path=new URL(req.url()).pathname.replace('/api/backend/','');let data:unknown={items:[],total:0,has_more:false,next_cursor:null};
  if(path==='session')data={mode:'local-development',planning_available:true,planning_jobs_available:false,runtime_available:true,overview_routing_available:true,dynamic_composition_available:true,approval_service_available:true,auth:{subject:{workspace_id:tenant,subject_id:'owner'},roles:['admin','approver'],permissions:['workflow.plan','workflow.view','workflow.execute','workflow.approve','tools.read'],scopes:[],decision:'allow'}};
  else if(path.startsWith('workflow-overview'))data={items:[],next_sequence:0,has_more:false};
  else if(path==='integrations/google/connections')data={configured:true,setup_message:null,callback_uri:null,callback_in_client_file:false,shared_demo_identity:false,capabilities:[],items:[]};
  else if(path==='business-ontology/v1/action-plans'&&req.method()==='POST'){
   const b=req.postDataJSON();if(b.operation==='activate')activates++;
   if(b.operation==='prepare'){
    submissions.push(b);current={version:'overview-intent-v1',state:submissions.length===1?'clarification':'prepared',request_key:b.request_key,workspace:{workspace_id:tenant,subject_id:'owner'},intent:{intent_type:'recurring',business_goal:goal,side_effects:['email_send','calendar_write']},questions:[],clarifications:submissions.length===1?[{field:'email_delivery',question:'Should I email the report or prepare a draft?',options:[{value:'send',label:'Email it to me'},{value:'draft',label:'Prepare a draft'}]},{field:'review_timing',question:'When should the reading session start?',options:[{value:'after_ready',label:'After the report is ready'},{value:'fixed',label:'At a fixed time'}]}]:[],communication_review:submissions.length===1?[]:['Connected account: owner@example.com','Report recipient: owner@example.com','Review calendar: Primary calendar','Reading session: 30 minutes, starting 5 minutes after the report is ready.']};
   }data=current;
  }
  await route.fulfill({json:{request_id:'natural_browser',status:200,data}});
 });
 await page.goto('/app');await page.getByLabel('Process description').fill(goal);await page.getByRole('button',{name:'Generate workflow',exact:true}).click();
 await page.getByLabel('Should I email the report or prepare a draft?').selectOption('send');
 await page.getByLabel('When should the reading session start?').selectOption('after_ready');await page.getByRole('button',{name:'Continue to review'}).click();
 await expect(page.getByLabel('Email and Calendar review')).toContainText('5 minutes after the report is ready');
 expect(submissions).toHaveLength(2);expect(submissions[1]?.['objective']).toBe(goal);expect(submissions[1]?.['user_values']).toMatchObject({email_delivery:'send',review_timing:'after_ready'});
 expect(submissions[0]?.['request_key']).not.toBe(submissions[1]?.['request_key']);expect(activates).toBe(0);expect(errors).toEqual([]);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 await page.screenshot({path:`/home/raf/agentic-ai-builder/.local/natural-communication-20261112/review-${tenant}-${mobile?'mobile':'desktop'}.png`,fullPage:true});
});
