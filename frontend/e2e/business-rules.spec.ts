import {policyLibrary} from '../src/test/fixtures/business-policy';
import {graphPlan} from '../src/test/fixtures/business-graph';
import {test,expect} from '@playwright/test';
import {createHmac,randomBytes} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {ruleSnapshot,ruleCatalogue,ruleQueryResult} from '../src/test/fixtures/business-rules';
import {businessVersionSchema} from '../src/api/business-ontology';
const catalogue=JSON.parse(readFileSync(new URL('../src/test/fixtures/business-ontology.json',import.meta.url),'utf8'));
for(const mobile of [false,true])test(`rules and definition competency ${mobile?'mobile':'desktop'}`,async({page})=>{
 const secret=process.env['BUILDER_LOGIN_SECRET'];test.skip(!secret,'Use an isolated browser-test signing key.');
 const payload=`${Math.floor(Date.now()/1000)+3600}.${randomBytes(24).toString('hex')}`;
 await page.context().addCookies([{name:'builder_workspace_access',value:`${payload}.${createHmac('sha256',secret!).update(payload).digest('hex')}`,domain:'127.0.0.1',path:'/'}]);
 if(mobile)await page.setViewportSize({width:390,height:844});
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 const second=ruleSnapshot();const first=businessVersionSchema.parse({...second,version_id:'v1',revision:1,kind:'foundation',concepts:[],rules:[],sources:[],questions:{}});
 const workspace={ontology_id:'simpson',title:'Simpson',namespace:'urn:fixture:',revision:2,status:'draft',created_at:'2026-10-31',sources:{service:'db1',quality:'db2'},source_revisions:{service:1,quality:1}};
 const current={...catalogue,workspace,modules:catalogue.modules.map((m:{id:string})=>({...m,concept_count:m.id==='warranty'?1:0})),source_bindings:[],documents:second.sources,versions:[first,second],current_version_id:'v2',generation_status:'draft_available',counts:{concepts:1,relationships:0,rules:1},definitions:{concepts:second.concepts,relationships:[],rules:second.rules},questions:second.questions};
 const compiled={version_id:'v2',compiler_version:'simpson-owl-shacl-v1',input_sha256:'fixture_input_hash',compiled_at:'2026-10-31',report:{status:'passed',compiler_version:'simpson-owl-shacl-v1',version_id:'v2',revision:2,checks:{snapshot:'passed',rdf_syntax:'passed',shapes_meta_shacl:'passed',definition_shacl:'passed'},definition_conforms:true,instance_validation:'not_run',owl_reasoning:'not_run',business_policy_verified:false,counts:{concepts:1},issues:[],warnings:[]},artifacts:[]};
 let hasCompilation=false,queryCalls=0,compileCalls=0,legacyWrites=0;
 await page.route('**/api/backend/**',async route=>{
  const request=route.request(),path=new URL(request.url()).pathname.replace('/api/backend/','');let data:unknown={items:[],configured:true};
  if(path==='business-ontology/v1/warranty-policies')data=policyLibrary();
  else if(path==='session')data={mode:'local-development',auth:{subject:{subject_id:'alice',workspace_id:'one'},roles:['admin'],permissions:['workflow.view','tools.read','tools.assign'],scopes:['workspace:read','workspace:write'],decision:'allow'},planning_available:false,runtime_available:false,approval_service_available:false};
  else if(path==='data-sources')data={configured:true,shared_demo_identity:false,items:[]};
  else if(path==='data-refresh')data={version:1,items:[]};
  else if(path==='business-ontology/v1')data=current;
  else if(path.endsWith('/graph-plan'))data={...graphPlan(path.includes('/versions/v1/')?'v1':'v2'),available:false,unavailable_reason:'Graph mappings are not configured in this fixture.'};
  else if(path==='business-ontology/v1/versions/v1')data=first;
  else if(path==='business-ontology/v1/versions/v2')data=second;
  else if(path.endsWith('/compilation')){
   if(request.method()==='POST'){hasCompilation=true;compileCalls++;}
   data={compilation:path.includes('/v2/')&&hasCompilation?compiled:null};
  }else if(path.endsWith('/rule-catalogue'))data=ruleCatalogue(path.includes('/versions/v1/')?first:second,path.includes('/v2/')&&hasCompilation);
  else if(path.endsWith('/competency-queries/run')){
   const body=request.postDataJSON();expect(body).toMatchObject({query_id:'rule_inputs',focus_id:'warranty:review',limit:20});queryCalls++;
   const result=ruleQueryResult();data={...result,focus_id:body.focus_id,offset:body.offset,rows:body.offset===0?Array.from({length:20},()=>result.rows[0]):result.rows,has_more:body.offset===0,next_offset:body.offset===0?20:null};
  }
  if(path.startsWith('ontology/')&&request.method()!=='GET')legacyWrites++;
  await route.fulfill({status:200,json:{request_id:'req_rules_browser',status:200,data}});
 });
 await page.goto('/app/data-intelligence');await page.getByRole('tab',{name:'Business Ontology',exact:true}).click();
 await page.getByLabel('Module to generate').selectOption('warranty');
 const panel=page.getByRole('region',{name:'Business rules and competency questions'});
 await expect(panel.getByRole('button',{name:'Run definition query'})).toBeDisabled();expect(queryCalls).toBe(0);
 await page.getByRole('button',{name:'Compile & validate version'}).click();
 await expect(panel.getByRole('button',{name:'Run definition query'})).toBeEnabled();expect(queryCalls).toBe(0);
 const detail=panel.getByRole('article',{name:'Candidate rule detail'});
 await detail.getByText('Rule evidence (1)').click();await expect(detail.getByRole('blockquote')).toHaveText(second.sources[0]!.text);
 await detail.getByText('Required input definitions').click();await expect(detail.getByText(/hours · integer · Required/)).toBeVisible();
 await panel.getByLabel('Definition focus').selectOption('warranty:review');await panel.getByRole('button',{name:'Run definition query'}).click();
 await expect(panel.getByText('20 rows · Revision 2')).toBeVisible();await panel.getByRole('button',{name:'Next results'}).click();await expect(panel.getByText('1 row · Revision 2')).toBeVisible();
 await panel.scrollIntoViewIfNeeded();await page.screenshot({path:`test-results/business-rules-${mobile?'mobile':'desktop'}.png`,fullPage:true});
 await panel.getByRole('region',{name:'Definition competency queries'}).scrollIntoViewIfNeeded();await page.screenshot({path:`test-results/business-rule-query-${mobile?'mobile':'desktop'}.png`,fullPage:true});
 await panel.getByLabel('Definition question').selectOption('rule_evidence');await expect(panel.getByLabel('Definition query result')).toHaveCount(0);expect(queryCalls).toBe(2);
 await panel.getByText(/Business questions needing mapped company data/).click();await expect(panel.getByText('Mapped failure dates and versioned policy/exclusions.')).toBeVisible();
 await page.getByLabel('Definition version').selectOption('v1');await expect(panel.getByText('No saved candidate rules match these filters.')).toBeVisible();await expect(panel.getByRole('button',{name:'Run definition query'})).toBeDisabled();
 expect(compileCalls).toBe(1);expect(legacyWrites).toBe(0);expect(errors).toEqual([]);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
