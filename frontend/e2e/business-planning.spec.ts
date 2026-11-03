import { test, expect } from '@playwright/test';
import { createHmac, randomBytes } from 'node:crypto';
import { readFileSync } from 'node:fs';

// Browser fixtures never call a provider, execute a workflow or write company data.
const base = JSON.parse(readFileSync(new URL('../../shared/contracts/examples/workflows/support-triage.json', import.meta.url), 'utf8'));
function proposal() {
 const file = process.env['BUILDER_ONTOLOGY_PROPOSAL_FILE'];
 if (file) return JSON.parse(readFileSync(file, 'utf8')).data.workflow;
 return {...base, workflow_id:'ontology_browser_fixture', name:'Verification fixture: warranty workflow',
  nodes:[base.nodes[0], {node_id:'assess',kind:'transform',label:'Assess warranty evidence'}, base.nodes[1]],
  edges:[{edge_id:'to_assess',source:base.nodes[0].node_id,target:'assess'},{edge_id:'to_output',source:'assess',target:base.nodes[1].node_id}],
  metadata:{business_ontology:{retrieval_version:'simpson-business-planning-v1',state:'incorporated',version_id:'fixture_v2',revision:2,definition_sha256:'a'.repeat(64),trace_sha256:'b'.repeat(64),truncated:false,
   references:[{ref:'concept:warranty:eligibility',kind:'concept',label:'Eligibility evidence',definition:'Compare supplied dates and hours with cited coverage conditions.',evidence:[{source_id:'fixture_source',title:'Browser fixture source',source_kind:'process',source_sha256:'c'.repeat(64),quote:'Use dates and hours as assessment evidence.'}]}],
   contributions:[{node_id:'assess',node_name:'Assess warranty evidence',refs:['concept:warranty:eligibility'],application:'Adds source-qualified date and operating-hour assessment to the proposed step.'}]}}};
}
for (const mobile of [false,true]) for (const matched of [true,false]) test(`automatic ontology contribution ${matched?'matched':'no match'} ${mobile?'mobile':'desktop'}`, async ({page}) => {
 const secret=process.env['BUILDER_LOGIN_SECRET'];test.skip(!secret,'Use an isolated browser-test key.');
 const payload=`${Math.floor(Date.now()/1000)+3600}.${randomBytes(24).toString('hex')}`;
 await page.context().addCookies([{name:'builder_workspace_access',value:`${payload}.${createHmac('sha256',secret!).update(payload).digest('hex')}`,domain:'127.0.0.1',path:'/'}]);
 if(mobile)await page.setViewportSize({width:390,height:844});
 const w=proposal();if(!matched)w.metadata.business_ontology={...w.metadata.business_ontology,state:'no_match',references:[],contributions:[]};
 let saved=false,plans=0,saves=0;const errors:string[]=[],unexpected:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/backend/**',async route=>{
  const request=route.request(),path=new URL(request.url()).pathname.replace('/api/backend/','');
  let data:unknown={items:[],total:0,has_more:false,next_cursor:null,next_sequence:0};
  if(path==='session')data={mode:'local-development',planning_available:true,planning_jobs_available:false,runtime_available:false,approval_service_available:false,auth:{subject:{subject_id:'alice',workspace_id:'one'},roles:['admin'],permissions:['workflow.view','workflow.plan','workflow.edit','tools.read','tools.assign'],scopes:['workspace:read','workspace:write'],decision:'allow'}};
  else if(path==='workflows/plan'){plans++;expect(request.postDataJSON().payload.context).toEqual({generation_mode:'hierarchy',delegation_mode:'runtime_v1',execution_input_mode:'automatic'});data={workflow:w};}
  else if(path===`workflows/${w.workflow_id}/versions/1`&&request.method()==='PUT'){saved=true;saves++;expect(request.postDataJSON().payload.workflow.metadata.business_ontology).toEqual(w.metadata.business_ontology);data={workflow:w};}
  else if(path===`workflows/${w.workflow_id}`){if(!saved){await route.fulfill({status:404,json:{request_id:'req_fixture_missing',status:404,data:{error:{error_code:'WORKFLOW_NOT_FOUND',message:'Not saved yet.',request_id:'req_fixture_missing',retryable:false}}}});return;}data={workflow:w};}
  else if(path==='integrations/google/connections')data={configured:false,setup_message:null,callback_uri:null,callback_in_client_file:false,shared_demo_identity:false,capabilities:[],items:[]};
  else if(request.method()!=='GET')unexpected.push(`${request.method()} ${path}`);
  await route.fulfill({status:200,json:{request_id:'req_ontology_browser',status:200,data}});
 });
 await page.goto('/app');await page.getByRole('textbox',{name:'Process description',exact:true}).fill(matched?'Create a Simpson warranty complaint assessment workflow':'Translate French poetry into Spanish');
 await page.getByRole('button',{name:'Generate workflow',exact:true}).click();
 await expect(page).toHaveURL(new RegExp(`/app/workflows/${w.workflow_id}$`));
 await expect(page.getByRole('button',{name:'View ontology evidence',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'View ontology evidence',exact:true}).click();
 const dialog=page.getByRole('dialog');await expect(dialog.getByRole('heading',{name:'How Business Ontology shaped this workflow'})).toBeInViewport();await page.screenshot({path:`test-results/ontology-planning-opening-${matched?'matched':'no-match'}-${mobile?'mobile':'desktop'}.png`});
 if(matched){const c=w.metadata.business_ontology.contributions[0];await expect(dialog.getByRole('heading',{name:c.node_name})).toBeVisible();await expect(dialog.getByRole('heading',{name:'Business knowledge used',exact:true})).toBeVisible();const first=w.metadata.business_ontology.references.find((r:{ref:string})=>r.ref===c.refs[0]);await expect(dialog.getByText(first.definition,{exact:true}).first()).toBeVisible();await expect(dialog.locator('blockquote').first()).not.toBeVisible();await dialog.getByText(/View supporting sources/).first().click();await expect(dialog.getByText(first.evidence[0].quote,{exact:true}).first()).toBeVisible();}
 else await expect(dialog.getByRole('status')).toContainText('no relevant definitions matched');
 const downloading=page.waitForEvent('download');await dialog.getByRole('button',{name:'Download ontology evidence',exact:true}).click();const download=await downloading;expect(JSON.parse(readFileSync((await download.path())!,'utf8'))).toEqual(w.metadata.business_ontology);
 await page.screenshot({path:`test-results/ontology-planning-${matched?'matched':'no-match'}-${mobile?'mobile':'desktop'}.png`});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 expect(plans).toBe(1);expect(saves).toBe(1);expect(unexpected).toEqual([]);expect(errors).toEqual([]);
});
