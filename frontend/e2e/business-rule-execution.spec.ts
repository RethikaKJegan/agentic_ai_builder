import {test,expect} from '@playwright/test';
import {createHmac,randomBytes} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {executionCatalogue,executionEvidence,executionResult} from '../src/test/fixtures/business-rule-execution';
import {graphPlan,sourceGraph} from '../src/test/fixtures/business-graph';
import {ruleSnapshot,ruleCatalogue} from '../src/test/fixtures/business-rules';
import {policyLibrary} from '../src/test/fixtures/business-policy';
import {intelligenceCatalogue,moduleCoverage} from '../src/test/fixtures/business-intelligence';
import type {BusinessRuleEvidence} from '../src/api/business-ontology';
const fixture=JSON.parse(readFileSync(new URL('../src/test/fixtures/business-ontology.json',import.meta.url),'utf8'));
for(const mobile of [false,true])test(`three executable business rules ${mobile?'mobile':'desktop'}`,async({page})=>{
 const secret=process.env['BUILDER_LOGIN_SECRET'];test.skip(!secret,'An isolated test signing key is required.');
 const payload=`${Math.floor(Date.now()/1000)+3600}.${randomBytes(24).toString('hex')}`;
 await page.context().addCookies([{name:'builder_workspace_access',value:`${payload}.${createHmac('sha256',secret!).update(payload).digest('hex')}`,domain:'127.0.0.1',path:'/'}]);
 if(mobile)await page.setViewportSize({width:390,height:844});
 const version=ruleSnapshot(),graph=sourceGraph();graph.records.push({...graph.records[0]!,node_id:'change1',collection:'internalcutins',key:{_id:'cutin1'},fields:[]});
 const current={...fixture,workspace:{ontology_id:'simpson',title:'Simpson',namespace:'urn:fixture:',revision:2,status:'draft',created_at:'2026-10-31',sources:{service:'db1',quality:'db2'},source_revisions:{service:1,quality:1}},source_bindings:[],documents:version.sources,versions:[version],current_version_id:'v2',generation_status:'draft_available',counts:{concepts:1,relationships:0,rules:1},definitions:{concepts:version.concepts,relationships:[],rules:version.rules},questions:version.questions};
 const cat=executionCatalogue(),saved:BusinessRuleEvidence[]=[],errors:string[]=[],unexpected:string[]=[];let saves=0,runs=0,sourceSaves=0;
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/api/backend/**',async route=>{
  const req=route.request(),path=new URL(req.url()).pathname.replace('/api/backend/','');let data:unknown={items:[],configured:true};
  if(path==='session')data={mode:'local-development',auth:{subject:{subject_id:'alice',workspace_id:'one'},roles:['admin'],permissions:['workflow.view','tools.read','tools.assign'],scopes:['workspace:read','workspace:write'],decision:'allow'},planning_available:false,runtime_available:false,approval_service_available:false};
  else if(path==='data-sources')data={configured:true,shared_demo_identity:false,items:[]};
  else if(['workflows','tools','workflow-overview','business-ontology/v1/jobs'].includes(path))data={items:[]};
  else if(path==='data-refresh')data={version:1,items:[]};
  else if(path==='business-ontology/v1')data=current;
  else if(path==='business-ontology/v1/versions/v2')data=version;
  else if(path==='business-ontology/v1/warranty-policies')data=policyLibrary(false);
  else if(path.endsWith('/module-coverage'))data=moduleCoverage();
  else if(path.endsWith('/compilation'))data={compilation:null};
  else if(path.endsWith('/rule-catalogue'))data=ruleCatalogue(version,false);
  else if(path.endsWith('/graph-plan'))data={...graphPlan(),snapshots:[{graph_id:'g1',created_at:'2026-10-31',serial:'SER-1',records:3,version_id:'v2'}]};
  else if(path.endsWith('/graphs/g1'))data=graph;
  else if(path.endsWith('/intelligence'))data=intelligenceCatalogue();
  else if(path.endsWith('/rule-execution'))data={...cat,evidence:saved.map(({evidence_id,rule_id,graph_id,subject_node_id,change_node_id,revision,created_at,sha256,source_id})=>({evidence_id,rule_id,graph_id,subject_node_id,change_node_id,revision,created_at,sha256,source_id}))};
  else if(path==='business-ontology/v1/documents/execution_source')data=executionEvidence().source;
  else if(path==='business-ontology/v1/documents'&&req.method()==='POST'){
   const body=req.postDataJSON();expect(body).toEqual({title:'Additional inspection evidence',kind:'evidence',module_ids:['failure'],text:'A source document supplied for the current engine investigation.'});sourceSaves++;const source={...executionEvidence().source,...body,source_id:'additional_source'};cat.sources.push(source);data=source;
  }
  else if(path.endsWith('/rule-evidence')){
   const body=req.postDataJSON(),doc=executionEvidence(body.rule_id);expect(body).toEqual({request_key:expect.any(String),expected_revision:0,rule_id:doc.rule_id,subject_node_id:doc.subject_node_id,change_node_id:doc.change_node_id,source_id:doc.source_id,facts:doc.facts});saves++;saved.push(doc);data=doc;
  }
  else if(path.startsWith('business-ontology/v1/rule-evidence/'))data=saved.find(e=>path.endsWith('/'+e.evidence_id));
  else if(path.endsWith('/rules/execute')){
   const body=req.postDataJSON(),doc=executionEvidence(body.rule_id);expect(body).toEqual({rule_id:doc.rule_id,subject_node_id:doc.subject_node_id,change_node_id:doc.change_node_id,evidence_id:saved.some(e=>e.evidence_id===body.evidence_id)?doc.evidence_id:null});runs++;data=executionResult(body.rule_id,!!body.evidence_id);
  }
  else unexpected.push(`${req.method()} ${path}`);
  await route.fulfill({status:200,json:{request_id:'req_rule_browser',status:200,data}});
 });
 await page.goto('/app/data-intelligence');await page.getByRole('tab',{name:'Business Ontology',exact:true}).click();
 const graphPanel=page.getByRole('region',{name:'Mapped source graph'});await graphPanel.getByLabel('Saved source graph').selectOption('g1');
 const runner=graphPanel.getByRole('region',{name:'Execute business rules'});
 await expect(runner.getByLabel('Executable rule').locator('option')).toHaveCount(3);expect(runs).toBe(0);
 for(const rule of cat.rules){
  const doc=executionEvidence(rule.rule_id);await runner.getByLabel('Executable rule').selectOption(rule.rule_id);
  if(doc.subject_node_id)await runner.getByLabel('Rule subject',{exact:true}).selectOption(doc.subject_node_id);
  if(doc.change_node_id)await runner.getByLabel('Rule change record').selectOption(doc.change_node_id);
  await runner.getByRole('button',{name:'Run selected business rule',exact:true}).click();
  await expect(runner.getByText('Rule executed · insufficient evidence',{exact:true})).toBeVisible();
  await runner.getByRole('button',{name:'Record source-cited rule inputs',exact:true}).click();
  const editor=runner.getByRole('region',{name:'Rule evidence editor'});await editor.getByLabel('Rule input source',{exact:true}).selectOption('execution_source');await editor.getByRole('button',{name:'Read rule input source',exact:true}).click();await expect(editor.getByText(doc.source.text,{exact:true})).toBeVisible();
  for(const spec of rule.fact_specs){
   const cell=doc.facts[spec.field_id]!;await editor.getByText(`${spec.label} · Unknown`,{exact:true}).click();
   const input=editor.getByLabel(spec.label,{exact:true});if(spec.kind==='choice')await input.selectOption(String(cell.value));else await input.fill(String(cell.value));
   await editor.getByLabel(`Quotation for ${spec.label}`,{exact:true}).fill(cell.quote!);
  }
  await editor.getByRole('button',{name:'Save rule evidence revision',exact:true}).click();await expect(runner.getByLabel('Saved rule evidence')).toHaveValue(doc.evidence_id);
  await runner.getByRole('button',{name:'Run selected business rule',exact:true}).click();
  const result=runner.getByRole('region',{name:'Business rule execution result'});await expect(result.getByText(`Rule executed · ${executionResult(rule.rule_id).outcome.replaceAll('_',' ')}`,{exact:true})).toBeVisible();
  const downloadEvent=page.waitForEvent('download');await result.getByRole('button',{name:'Download rule execution result',exact:true}).click();const download=await downloadEvent;const report=JSON.parse(readFileSync((await download.path())!,'utf8'));expect(report).toMatchObject({rule_id:rule.rule_id,rules_executed:true,independently_verified:false,model_calls:0,company_queries:0,source_writes:0,evidence_id:doc.evidence_id});expect(report.facts).toEqual(doc.facts);
  if(rule.module_id==='monitoring'){expect(report.calculations).toMatchObject({failed_engine_percentage:'5.000000',first_failures_per_1000_engine_hours:'0.500000'});await expect(result.getByText('0.500000',{exact:true})).toBeVisible();}
  await runner.scrollIntoViewIfNeeded();await page.screenshot({path:`test-results/business-rule-${rule.module_id}-${mobile?'mobile':'desktop'}.png`});
  await runner.getByLabel('Saved rule evidence').selectOption('');await expect(runner.getByRole('region',{name:'Business rule execution result'})).toHaveCount(0);await runner.getByLabel('Saved rule evidence').selectOption(doc.evidence_id);await runner.getByRole('button',{name:'Inspect saved rule evidence',exact:true}).click();await expect(runner.getByText('Saved rule evidence · Revision 1',{exact:true})).toBeVisible();
  const evidenceDownload=page.waitForEvent('download');await runner.getByRole('button',{name:'Download rule evidence',exact:true}).click();expect((await evidenceDownload).suggestedFilename()).toContain('rule-evidence');
 }
 await runner.getByLabel('Executable rule').selectOption(cat.rules[0]!.rule_id);await runner.getByLabel('Rule subject',{exact:true}).selectOption('node1');await runner.getByRole('button',{name:'Record source-cited rule inputs',exact:true}).click();const editor=runner.getByRole('region',{name:'Rule evidence editor'});await editor.getByRole('button',{name:'Add rule evidence source',exact:true}).click();await editor.getByLabel('Rule evidence source title').fill('Additional inspection evidence');await editor.getByLabel('Rule evidence source text').fill('A source document supplied for the current engine investigation.');await editor.getByRole('button',{name:'Save rule evidence source',exact:true}).click();await expect(editor.getByLabel('Rule input source').locator('option[value="additional_source"]')).toHaveCount(1);
 expect(saves).toBe(3);expect(runs).toBe(6);expect(sourceSaves).toBe(1);expect(errors).toEqual([]);expect(unexpected).toEqual([]);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
