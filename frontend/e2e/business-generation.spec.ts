import {policyLibrary} from '../src/test/fixtures/business-policy';
import {graphPlan} from '../src/test/fixtures/business-graph';
import {ruleCatalogue} from '../src/test/fixtures/business-rules';
import {businessVersionSchema} from '../src/api/business-ontology';
import {test,expect} from '@playwright/test';
import {createHmac,randomBytes} from 'node:crypto';
import {readFileSync} from 'node:fs';
const catalogue=JSON.parse(readFileSync(new URL('../src/test/fixtures/business-ontology.json',import.meta.url),'utf8'));
for(const mobile of [false,true])test(`business extraction draft ${mobile?'mobile':'desktop'}`,async({page})=>{
 const secret=process.env['BUILDER_LOGIN_SECRET'];test.skip(!secret,'Use an isolated browser-test signing key.');
 const payload=`${Math.floor(Date.now()/1000)+3600}.${randomBytes(24).toString('hex')}`;
 await page.context().addCookies([{name:'builder_workspace_access',value:`${payload}.${createHmac('sha256',secret!).update(payload).digest('hex')}`,domain:'127.0.0.1',path:'/'}]);
 if(mobile)await page.setViewportSize({width:390,height:844});
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 const source={source_id:'doc1',title:'Warranty process evidence',kind:'process',module_ids:['warranty'],text:'Missing coverage information requires review.',sha256:'fixture_hash',origin:'owner_supplied'};
 const base={definition:source.text,layer:'business',module_id:'warranty',status:'draft',evidence:[{source_id:'doc1',quote:source.text}],confidence:.8,unknowns:['Exclusions have not been supplied.']};
 const concept={...base,id:'warranty:engine',label:'Engine',parent_id:null,properties:[]};
 const adjustments=[{rule_id:'warranty:review',original_basis:'policy_statement',basis:'proposed_logic',reason:'cited_source_kind_does_not_support_authority'}];
 const rule={...base,id:'warranty:review',label:'Requires review',inputs:['warranty:engine'],conditions:['Coverage information is missing'],outcome:'Requires review',basis:'proposed_logic',executable:false};
 const workspace={ontology_id:'simpson',title:'Simpson',namespace:'urn:fixture:',revision:1,status:'foundation',created_at:'2026-10-31',sources:{service:'db1',quality:'db2'},source_revisions:{service:1,quality:1}};
 const first={version_id:'v1',revision:1,kind:'foundation',created_at:'2026-10-31',concepts:[],relationships:[],rules:[],sources:[],questions:{}};
 const second={...first,version_id:'v2',revision:2,kind:'draft',concepts:[concept],rules:[rule],sources:[source],questions:{warranty:['What policy exclusions apply?']},extraction:{module_id:'warranty',model:'fixture-model',input_tokens:500,output_tokens:200,classification_adjustments:adjustments}};
 let current={...catalogue,workspace,documents:[source],source_bindings:[{role:'service',connection_id:'db1',name:'Service db1',status:'connected'},{role:'quality',connection_id:'db2',name:'Quality db2',status:'connected'}],versions:[first],current_version_id:'v1',definitions:{concepts:[],relationships:[],rules:[]},questions:{}};
 const oldFailure={job_id:'old_org',module_id:'organization',state:'failed',created_at:'2026-10-30',version_id:null,error:{code:'BUSINESS_EXTRACTION_INVALID',message:'Earlier response failed validation; saved definitions were retained.'},usage:null};
 let job:object|undefined;let polls=0,submissions=0,imports=0,sourceSaves=0,cancels=0;
 await page.route('**/api/backend/**',async route=>{
  const request=route.request(),path=new URL(request.url()).pathname.replace('/api/backend/','');let data:unknown={items:[],configured:true};
  if(path==='business-ontology/v1/warranty-policies')data=policyLibrary();
  else if(path==='session')data={mode:'local-development',auth:{subject:{subject_id:'alice',workspace_id:'one'},roles:['admin'],permissions:['workflow.view','tools.read','tools.assign'],scopes:['workspace:read','workspace:write'],decision:'allow'},planning_available:false,runtime_available:false,approval_service_available:false};
  else if(path==='data-sources')data={configured:true,shared_demo_identity:false,items:[]};
  else if(path==='data-refresh')data={version:1,items:[]};
  else if(path==='business-ontology/v1')data=current;
  else if(path==='business-ontology/v1/jobs'&&request.method()==='POST'){
   expect(request.postDataJSON()).toMatchObject({module_id:'warranty',expected_revision:submissions===0?1:2,request_key:expect.any(String)});submissions++;
   job={job_id:'j1',module_id:'warranty',state:'queued',created_at:'2026-10-31',version_id:null,error:null,usage:null};data=job;
  }else if(path==='business-ontology/v1/jobs'){
   if(job&&submissions===1&&++polls>=2){job={...job,state:'succeeded',version_id:'v2',usage:{classification_adjustments:adjustments}};current={...current,workspace:{...workspace,revision:2,status:'draft'},versions:[first,second],current_version_id:'v2',generation_status:'draft_available',counts:{concepts:1,relationships:0,rules:1},modules:catalogue.modules.map((m:{id:string})=>({...m,concept_count:m.id==='warranty'?1:0})),definitions:{concepts:[concept],relationships:[],rules:[rule]},questions:{warranty:['What policy exclusions apply?']}};}
   data={configured:true,items:job?[job,oldFailure]:[oldFailure]};
  }else if(path==='business-ontology/v1/import-reference'){expect(request.method()).toBe('POST');imports++;data=current;}
  else if(path==='business-ontology/v1/documents'&&request.method()==='POST'){const body=request.postDataJSON();expect(body).toEqual({title:'Extra process evidence',kind:'process',module_ids:['warranty'],text:source.text});const added={...source,...body,source_id:'added'};sourceSaves++;current={...current,documents:[...current.documents,added]};data=added;}
  else if(path==='business-ontology/v1/jobs/j1/cancel'){expect(request.postDataJSON()).toEqual({});cancels++;job={...job,state:'cancelled'};data=job;}
  else if(path.endsWith('/compilation'))data={compilation:null};
  else if(path.endsWith('/rule-catalogue'))data=ruleCatalogue(businessVersionSchema.parse(path.includes('/versions/v1/')?first:second),false);
  else if(path.endsWith('/graph-plan'))data={...graphPlan(path.includes('/versions/v1/')?'v1':'v2'),available:false,unavailable_reason:'Graph mappings are not configured in this fixture.'};
  else if(path==='business-ontology/v1/versions/v1')data=first;
  else if(path==='business-ontology/v1/versions/v2')data=second;
  else if(path==='business-ontology/v1/documents/doc1')data=source;
  await route.fulfill({status:200,json:{request_id:'req_generation_browser',status:200,data}});
 });
 await page.goto('/app/data-intelligence');await page.getByRole('tab',{name:'Business Ontology',exact:true}).click();
 const generation=page.getByRole('region',{name:'Business ontology generation'});
 await generation.getByRole('button',{name:'Import supplied Simpson reference',exact:true}).click();await expect(generation.getByText(/Reference sources ready/)).toBeVisible();
 await page.getByLabel('Module to generate').selectOption('warranty');
 await generation.getByText('Inspect source documents',{exact:true}).click();await generation.getByRole('button',{name:'Warranty process evidence · process',exact:true}).click();await expect(generation.getByText(source.text,{exact:true})).toBeVisible();
 await generation.getByRole('button',{name:'Add source document',exact:true}).click();await generation.getByLabel('Source title',{exact:true}).fill('Extra process evidence');await generation.getByLabel('Source text',{exact:true}).fill(source.text);await generation.getByRole('button',{name:'Save source document',exact:true}).click();await expect(generation.getByText(/Source document saved for/)).toBeVisible();
 await page.getByRole('button',{name:'Generate module draft',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Business draft available'})).toBeVisible();
 await expect(generation.getByText('Draft generated successfully · Revision 2.',{exact:true})).toBeVisible();await expect(generation.getByText(/Source checks completed/)).toBeVisible();await generation.getByRole('button',{name:'View generated draft',exact:true}).click();
 await page.getByRole('group',{name:'Module definitions'}).getByRole('button',{name:/Requires review/}).click();
 await page.getByText('Source classification corrections (1)',{exact:true}).click();await expect(page.getByText('warranty:review: policy statement → proposed logic',{exact:true})).toBeVisible();
 const detail=page.getByRole('article',{name:'Business definition detail'});
 await expect(detail.getByText(/Execution availability is shown in the rule catalogue/)).toBeVisible();await expect(detail.getByRole('blockquote')).toHaveText(source.text);
 await expect(detail.getByText('Exclusions have not been supplied.')).toBeVisible();
 await detail.scrollIntoViewIfNeeded();await page.screenshot({path:`test-results/business-extraction-${mobile?'mobile':'desktop'}.png`,fullPage:true});
 await page.getByLabel('Definition version').selectOption('v1');
 await expect(page.getByText('No generated definitions for this module in this version.')).toBeVisible();
 await generation.getByRole('button',{name:'View generated draft',exact:true}).click();await expect(page.getByLabel('Definition version')).toHaveValue('v2');
 await generation.getByRole('button',{name:'Refresh generation status',exact:true}).click();expect(submissions).toBe(1);
 await generation.getByRole('button',{name:'Generate module draft',exact:true}).click();await expect(generation.getByRole('button',{name:'Cancel generation',exact:true})).toBeVisible();await generation.getByRole('button',{name:'Cancel generation',exact:true}).click();await expect(generation.getByText('Generation cancelled. No draft was applied.',{exact:true})).toBeVisible();
 await generation.getByText('Generation history (2)',{exact:true}).click();await generation.getByText('Earlier failure details',{exact:true}).click();await expect(generation.getByText(/Earlier response failed validation/)).toBeVisible();
 expect(submissions).toBe(2);expect(imports).toBe(1);expect(sourceSaves).toBe(1);expect(cancels).toBe(1);expect(errors).toEqual([]);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
