import {policyLibrary} from '../src/test/fixtures/business-policy';
import {test,expect} from '@playwright/test';
import {createHmac,randomBytes} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {moduleCoverage,intelligenceCatalogue,intelligenceReport} from '../src/test/fixtures/business-intelligence';
import {graphPlan,sourceGraph} from '../src/test/fixtures/business-graph';
import {ruleSnapshot,ruleCatalogue} from '../src/test/fixtures/business-rules';
import {businessVersionSchema} from '../src/api/business-ontology';
const catalogue=JSON.parse(readFileSync(new URL('../src/test/fixtures/business-ontology.json',import.meta.url),'utf8'));
for(const mobile of [false,true])test(`reference module preservation ${mobile?'mobile':'desktop'}`,async({page})=>{
 const secret=process.env['BUILDER_LOGIN_SECRET'];test.skip(!secret,'Use an isolated browser-test signing key.');
 const payload=`${Math.floor(Date.now()/1000)+3600}.${randomBytes(24).toString('hex')}`;
 await page.context().addCookies([{name:'builder_workspace_access',value:`${payload}.${createHmac('sha256',secret!).update(payload).digest('hex')}`,domain:'127.0.0.1',path:'/'}]);if(mobile)await page.setViewportSize({width:390,height:844});
 const second=ruleSnapshot(),third=businessVersionSchema.parse({...second,version_id:'v3',revision:3,concepts:[...second.concepts,{...second.concepts[0],id:'inspection:joint_inspection',module_id:'inspection',label:'Joint inspection reference',source_basis:'curated_supplied_blueprint_draft'}],reference_import:{kit_version:'simpson-reference-modules-v1',source_basis:'curated_supplied_blueprint_drafts',added_modules:['inspection'],bundle_sha256:'fixture'}}),first=businessVersionSchema.parse({...second,version_id:'v1',revision:1,kind:'foundation',concepts:[],rules:[],sources:[],questions:{}});
 const current={...catalogue,workspace:{ontology_id:'simpson',title:'Simpson',namespace:'urn:fixture:',revision:2,status:'draft',created_at:'2026-10-31',sources:{service:'db1',quality:'db2'},source_revisions:{service:1,quality:1}},source_bindings:[],documents:second.sources,versions:[first,second],current_version_id:'v2',generation_status:'draft_available',counts:{concepts:1,relationships:0,rules:1},definitions:{concepts:second.concepts,relationships:[],rules:second.rules},questions:second.questions};
 let imports=0,modelCalls=0,builds=0,reads=0,reports=0,legacyWrites=0,stored=false;const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/backend/**',async route=>{
  const request=route.request(),path=new URL(request.url()).pathname.replace('/api/backend/','');let data:unknown={items:[],configured:true};
  if(path==='business-ontology/v1/warranty-policies')data=policyLibrary();
  else if(path==='session')data={mode:'local-development',auth:{subject:{subject_id:'alice',workspace_id:'one'},roles:['admin'],permissions:['workflow.view','tools.read','tools.assign'],scopes:['workspace:read','workspace:write'],decision:'allow'},planning_available:false,runtime_available:false,approval_service_available:false};
  else if(path==='data-sources')data={configured:true,shared_demo_identity:false,items:[]};else if(path==='data-refresh')data={version:1,items:[]};
  else if(path==='business-ontology/v1')data=current;else if(path==='business-ontology/v1/versions/v1')data=first;else if(path==='business-ontology/v1/versions/v2')data=second;
  else if(path==='business-ontology/v1/reference-modules'){expect(request.postDataJSON()).toMatchObject({expected_revision:2,request_key:expect.any(String)});imports++;stored=true;current.workspace.revision=3;current.current_version_id='v3';current.versions.push(third);current.definitions.concepts=third.concepts;current.counts.concepts=third.concepts.length;current.modules=current.modules.map((m:{id:string})=>({...m,concept_count:third.concepts.filter(c=>c.module_id===m.id).length}));data={version_id:'v3',state:current};}
  else if(path==='business-ontology/v1/versions/v3')data=third;
  else if(path.endsWith('/module-coverage')){const c=moduleCoverage();if(path.includes('/v3/')){c.version_id='v3';c.revision=3;c.missing_modules=[];c.modules[1]!.status='draft_available';c.modules[1]!.counts={concepts:1};c.modules[1]!.curated_concepts=1;c.import_available=false;c.unavailable_reason='All modules already contain drafts.';}else if(stored){c.import_available=false;c.unavailable_reason='Choose the latest saved version.';}data=c;}
  else if(path.endsWith('/intelligence/run')){expect(request.postDataJSON()).toMatchObject({question_id:expect.stringMatching(/^(service_path|claim_fields)$/),limit:20,offset:expect.any(Number)});reports++;data=intelligenceReport(request.postDataJSON().question_id,request.postDataJSON().offset);}
  else if(path.endsWith('/intelligence'))data=intelligenceCatalogue();
  else if(path.endsWith('/compilation'))data={compilation:null};else if(path.endsWith('/rule-catalogue'))data=ruleCatalogue(path.includes('/versions/v1/')?first:second,false);
  else if(path.endsWith('/graph-plan')){const plan=graphPlan(path.includes('/versions/v1/')?'v1':'v2');data={...plan,available:!path.includes('/versions/v1/'),snapshots:stored&&path.includes('/versions/v2/')?[{graph_id:'g1',created_at:'2026-10-31',serial:'SER-1',records:2,version_id:'v2'}]:[]};}
  else if(path.endsWith('/graphs')&&request.method()==='POST'){expect(request.postDataJSON()).toMatchObject({serial:'SER-1',plan_hash:'fixture_plan',bindings:{tickets:{concept_id:'warranty:engine',attributes:{hours:'hmr'}}}});builds++;stored=true;data=sourceGraph();}
  else if(path.endsWith('/graphs/g1')){reads++;data=sourceGraph();}
  if(path.endsWith('/jobs')&&request.method()==='POST')modelCalls++;
  if(path.startsWith('ontology/')&&request.method()!=='GET')legacyWrites++;
  await route.fulfill({status:200,json:{request_id:'req_graph_browser',status:200,data}});
 });
 await page.goto('/app/data-intelligence');await page.getByRole('tab',{name:'Business Ontology',exact:true}).click();
 const coverage=page.getByRole('region',{name:'Business module coverage'});await expect(coverage.getByText('1 of 2 modules contain drafts.')).toBeVisible();expect(imports).toBe(0);
 await coverage.getByRole('button',{name:'Add missing reference drafts'}).click();await expect(coverage.getByText('2 of 2 modules contain drafts.')).toBeVisible();await expect(page.getByText(/Curated blueprint reference · 1 modules added/)).toBeVisible();
 await page.getByRole('group',{name:'Business ontology modules'}).getByRole('button',{name:/Investigation and inspection/}).click();await expect(page.getByRole('button',{name:'concept Joint inspection reference'})).toBeVisible();await expect(page.getByRole('article',{name:'Business definition detail'}).getByText(/Curated blueprint reference/)).toBeVisible();
 await coverage.screenshot({path:`test-results/business-coverage-${mobile?'mobile':'desktop'}.png`});await page.getByRole('article',{name:'Business definition detail'}).screenshot({path:`test-results/business-reference-detail-${mobile?'mobile':'desktop'}.png`});
 await page.getByLabel('Definition version').selectOption('v2');await expect(coverage.getByText('Choose the latest saved version.')).toBeVisible();await expect(coverage.getByRole('button',{name:'Add missing reference drafts'})).toBeDisabled();await expect(page.getByRole('button',{name:'concept Joint inspection reference'})).toHaveCount(0);
 await page.screenshot({path:`test-results/business-reference-${mobile?'mobile':'desktop'}.png`,fullPage:true});expect(imports).toBe(1);expect(modelCalls).toBe(0);expect(builds).toBe(0);expect(reads).toBe(0);expect(reports).toBe(0);expect(legacyWrites).toBe(0);expect(errors).toEqual([]);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
