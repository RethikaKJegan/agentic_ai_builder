import path from 'node:path';
import {test,expect,type Page} from '@playwright/test';
import {createHmac,randomBytes} from 'node:crypto';
import {knowledgeFixture} from '../src/test/fixtures/knowledge-map';
async function fixture(page:Page,tenant='client-simpsons'){
 const payload=`${Math.floor(Date.now()/1000)+3600}.${randomBytes(24).toString('hex')}`;
 await page.context().addCookies([{name:'builder_workspace_access',value:`${payload}.${createHmac('sha256',process.env['BUILDER_LOGIN_SECRET']!).update(payload).digest('hex')}`,domain:'127.0.0.1',path:'/'}]);
 const f=knowledgeFixture(tenant,tenant==='client-subway'?'Purchase order':'Complaint');f.view.master=null;let reads=0;
 await page.route('**/api/backend/**',async route=>{
 const path=new URL(route.request().url()).pathname.replace('/api/backend/','');let data:unknown={items:[],total:0,has_more:false,next_cursor:null};
 if(path==='session')data={mode:'local-development',planning_available:true,runtime_available:true,approval_service_available:true,dynamic_composition_available:true,auth:{subject:{subject_id:'owner',workspace_id:tenant},roles:['admin','approver'],permissions:['workflow.view','workflow.edit','workflow.plan','workflow.execute','workflow.validate','workflow.approve','tools.read','runs.view'],scopes:['workspace:read','workspace:write'],decision:'allow'}};
 else if(path==='data-sources')data={configured:true,shared_demo_identity:false,items:[]};
 else if(path.startsWith('workflow-overview'))data={items:[],next_sequence:0,has_more:false};
 else if(path==='integrations/google/connections')data={configured:true,setup_message:null,callback_uri:null,callback_in_client_file:false,shared_demo_identity:false,capabilities:[],items:[]};
 else if(path==='business-ontology/v1/action-plans/'+f.doc.composition_id)data=f.doc;
 else if(path.endsWith('/compositions/'+f.doc.composition_id+'/view')){reads++;if(reads>1)await new Promise(resolve=>setTimeout(resolve,900));data=f.view;}
 else if(path==='business-ontology/v1')data=f.ontology;
 else if(path===`business-ontology/v1/versions/${f.snapshot.version_id}/knowledge`)data=f.snapshot;
 await route.fulfill({json:{request_id:'ui_acceptance',status:200,data}});
 });return f;
}
for(const mobile of [false,true])test(`graph remains mounted during details and refresh ${mobile?'mobile':'desktop'}`,async({page})=>{
 await page.setViewportSize(mobile?{width:390,height:844}:{width:1440,height:900});const f=await fixture(page);
 await page.goto('/app/workflows/investigate?connected=1&composition='+f.doc.composition_id);
 const canvas=page.getByLabel('Dynamic investigation workflow canvas');await expect(canvas.locator('.react-flow__node')).toHaveCount(5);
 await page.locator('.react-flow__controls-zoomin').click();await page.waitForTimeout(250);
 const before=await canvas.locator('.react-flow__viewport').getAttribute('style');
 await canvas.locator('.react-flow__node').filter({hasText:'Goal coordinator'}).click();
 await expect(page.getByRole('heading',{name:'Goal coordinator',exact:true})).toBeVisible();await page.keyboard.press('Escape');
 await expect(canvas.locator('.react-flow__viewport')).toHaveAttribute('style',before!);
 await page.getByRole('button',{name:'Refresh plan',exact:true}).click();
 await page.waitForTimeout(150);await expect(canvas).toBeVisible({timeout:200});
 await expect(canvas.locator('.react-flow__viewport')).toHaveAttribute('style',before!);
});

for(const tenant of ['client-simpsons','client-subway'])for(const mobile of [false,true])test(`compact overview and complete ontology ${tenant} ${mobile?'mobile':'desktop'}`,async({page})=>{
 await page.setViewportSize(mobile?{width:390,height:844}:{width:1440,height:900});const f=await fixture(page,tenant);const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/app');await expect(page.getByLabel('Process description')).toBeVisible();await expect(page.getByRole('button',{name:'Generate workflow',exact:true})).toBeVisible();
 await expect(page.getByText('Workflow options',{exact:true})).toHaveCount(0);await expect(page.getByLabel('Overview request review')).toHaveCount(0);
 const card=await page.getByRole('region',{name:'Workflow prompt'}).boundingBox();const main=await page.locator('main').boundingBox();expect(card!.width).toBeGreaterThan(main!.width-64);
 expect(await page.getByLabel('Process description').getAttribute('placeholder')).toBeNull();expect(await page.getByText('Recent workflows',{exact:true}).count()).toBe(0);expect(await page.getByText('Business investigations',{exact:true}).count()).toBe(0);
 if(!mobile){const box=await page.getByRole('button',{name:'Generate workflow',exact:true}).boundingBox();expect(box!.y+box!.height).toBeLessThan(900);}
 await page.screenshot({path:`${path.resolve(import.meta.dirname,'../../.local/ui-ux-release-20261113')}/overview-${tenant}-${mobile?'mobile':'desktop'}.png`,fullPage:true});
 await page.goto('/app/data-intelligence');await page.getByRole('tab',{name:'Ontology',exact:true}).click();await expect(page.getByRole('tab',{name:'Questions',exact:true})).toHaveCount(0);await expect(page.getByRole('tab',{name:'Operations',exact:true})).toHaveCount(0);
 await expect(page.getByRole('heading',{name:tenant,exact:true})).toBeVisible();await page.getByLabel('Search complete ontology').fill(tenant==='client-subway'?'Purchase order':'Complaint');
 const node=page.getByLabel('Complete ontology graph').locator('.react-flow__node').filter({hasText:tenant==='client-subway'?'Purchase order':'Complaint'}).first();await node.click();await expect(page.getByLabel('Client ontology concept details').getByRole('heading',{name:tenant==='client-subway'?'Purchase order':'Complaint',exact:true})).toBeVisible();
 await page.screenshot({path:`${path.resolve(import.meta.dirname,'../../.local/ui-ux-release-20261113')}/ontology-${tenant}-${mobile?'mobile':'desktop'}.png`,fullPage:true});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);expect(errors).toEqual([]);
});

for(const mobile of [false,true])test(`business area overview remains readable with many groups ${mobile?'mobile':'desktop'}`,async({page})=>{
 await page.setViewportSize(mobile?{width:390,height:844}:{width:1440,height:900});const f=await fixture(page);
 const concept=f.snapshot.concepts[0]!;f.snapshot.concepts=[];f.snapshot.relationships=[];f.ontology.modules=[];
 for(let i=0;i<9;i++){const area='area_'+i;f.ontology.modules.push({id:area,label:'Business area '+i,description:'Saved business area',layers:[],concept_count:3});for(let j=0;j<3;j++)f.snapshot.concepts.push({...concept,id:`concept_${i}_${j}`,label:`Saved concept ${i}.${j}`,module_id:area});}
 await page.goto('/app/data-intelligence');await page.getByRole('tab',{name:'Ontology',exact:true}).click();const canvas=page.getByLabel('Complete ontology graph');const first=canvas.locator('.react-flow__node').first();await expect(canvas.locator('.react-flow__node')).toHaveCount(9);await expect(first).toBeVisible();await page.waitForTimeout(300);expect((await first.boundingBox())!.width).toBeGreaterThan(120);
 await first.click();await expect(canvas.locator('.react-flow__node')).toHaveCount(3);await expect(canvas.locator('.react-flow__node').first()).toContainText('Saved concept');expect((await canvas.locator('.react-flow__node').first().boundingBox())!.width).toBeGreaterThan(120);
 await page.screenshot({path:`${path.resolve(import.meta.dirname,'../../.local/ui-ux-release-20261113')}/group-overview-${mobile?'mobile':'desktop'}.png`,fullPage:true});
});
