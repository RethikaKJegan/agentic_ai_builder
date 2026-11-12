import {test,expect} from '@playwright/test';
import {createHmac,randomBytes} from 'node:crypto';
import {knowledgeFixture} from '../src/test/fixtures/knowledge-map';
for(const mobile of [false,true])test(`Subway long parallel workflow ${mobile?'mobile':'desktop'}`,async({page})=>{
 await page.setViewportSize(mobile?{width:390,height:844}:{width:1440,height:1000});
 const payload=`${Math.floor(Date.now()/1000)+3600}.${randomBytes(24).toString('hex')}`;
 await page.context().addCookies([{name:'builder_workspace_access',value:`${payload}.${createHmac('sha256',process.env['BUILDER_LOGIN_SECRET']!).update(payload).digest('hex')}`,domain:'127.0.0.1',path:'/'}]);
 const f=knowledgeFixture('client-subway','Purchase order');
 const template=f.view.tasks[0]!;
 f.view.tasks=Array.from({length:12},(_,i)=>({...template,id:`prepare_business_step_${i}`,label:`Business step ${i}. `+'Full evidence instructions. '.repeat(90),depends_on:i<3?[]:i===3?['prepare_business_step_0','prepare_business_step_1','prepare_business_step_2']:[`prepare_business_step_${i-1}`],approval_gate:null}));
 const errors:string[]=[];const writes:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/backend/**',async route=>{
  const req=route.request();const path=new URL(req.url()).pathname.replace('/api/backend/','');let data:unknown={items:[],total:0,has_more:false,next_cursor:null};
  if(req.method()!=='GET')writes.push(path);
  if(path==='session')data={mode:'local-development',planning_available:true,runtime_available:true,approval_service_available:true,dynamic_composition_available:true,auth:{subject:{subject_id:'owner',workspace_id:'client-subway'},roles:['admin','approver'],permissions:['workflow.view','workflow.edit','workflow.plan','workflow.execute','workflow.validate','workflow.approve','tools.read','runs.view'],scopes:['workspace:read','workspace:write'],decision:'allow'}};
  else if(path.startsWith('workflow-overview'))data={items:[],next_sequence:0,has_more:false};
  else if(path==='integrations/google/connections')data={configured:true,setup_message:null,callback_uri:null,callback_in_client_file:false,shared_demo_identity:false,capabilities:[],items:[]};
  else if(path==='business-ontology/v1/action-plans/'+f.doc.composition_id)data=f.doc;
  else if(path.endsWith('/compositions/'+f.doc.composition_id+'/view'))data=f.view;
  await route.fulfill({json:{request_id:'layout_browser',status:200,data}});
 });
 await page.goto('/app/workflows/investigate?connected=1&composition='+f.doc.composition_id);
 const cards=page.locator('.react-flow__node');await expect(cards).toHaveCount(13);
 await expect(page.getByText('Drag to explore · Select a step for details')).toBeVisible();
 await expect.poll(()=>page.locator('.react-flow__viewport').evaluate(el=>Number(el.getAttribute('style')?.match(/scale\(([^)]+)/)?.[1]??0))).toBeGreaterThanOrEqual(.55);
 const boxes=await cards.evaluateAll(nodes=>nodes.map(n=>{const r=n.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height,text:n.textContent??''}}));
 for(let i=0;i<boxes.length;i++){
  expect(boxes[i]!.text.length).toBeLessThan(230);
  for(let j=i+1;j<boxes.length;j++){
   const a=boxes[i]!,b=boxes[j]!;expect(a.x+a.w<=b.x+.5||b.x+b.w<=a.x+.5||a.y+a.h<=b.y+.5||b.y+b.h<=a.y+.5).toBe(true);
  }
 }
 await page.screenshot({path:`/home/raf/agentic-ai-builder/.local/subway-report-layout-20261112/layout-${mobile?'mobile':'desktop'}.png`,fullPage:true});
 await page.locator('.react-flow__node[data-id="prepare_business_step_1"]').click();
 await expect(page.locator('body')).toContainText('Full evidence instructions.');
 await page.keyboard.press('Escape');
 expect(writes).toEqual([]);expect(errors).toEqual([]);
});
