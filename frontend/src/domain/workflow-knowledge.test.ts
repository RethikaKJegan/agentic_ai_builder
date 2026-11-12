import {describe,it,expect} from 'vitest';
import {workflowKnowledge,pinnedKnowledgeVersion} from './workflow-knowledge';
import {knowledgeFixture} from '@/test/fixtures/knowledge-map';

describe('Exact workflow knowledge associations',()=>{
 it.each([['simpsons','Complaint'],['subway','Purchase order'],['new-workspace','Laboratory batch']])('uses the same adapter for %s', (tenant,title)=>{
  const {snapshot,doc,view}=knowledgeFixture(tenant,title);const graph=workflowKnowledge(snapshot,doc,view,true);
  expect(graph.nodes[0]!.label).toBe(title);expect(graph.nodes[0]!.usage.map(u=>u.state)).toEqual(['planned','executed']);
  expect(graph.nodes[1]!.usage).toEqual([]);expect(graph.edges[0]!.steps).toEqual([]);
  expect(pinnedKnowledgeVersion(doc,view)).toBe(snapshot.version_id);
 });
 it.each(['failed','skipped','running','pending'])('never labels %s steps executed',state=>{
  const f=knowledgeFixture();f.view.run!.action_instances![f.doc.action_plan.actions[0]!.action_id]!.state=state;
  expect(workflowKnowledge(f.snapshot,f.doc,f.view,true).nodes[0]!.usage.map(u=>u.state)).toEqual(['planned']);
 });
 it('does not equate successful source queries or similar labels with concept usage',()=>{
  const f=knowledgeFixture();f.doc.action_plan.actions[0]!.evidence_references=[];
  f.view.run!.action_instances![f.doc.action_plan.actions[0]!.action_id]!.output={query_id:'query_saved',result:{columns:[{label:'Complaint'}]},coverage:{complete_scan:false,has_more:true}};
  const graph=workflowKnowledge(f.snapshot,f.doc,f.view,true);
  expect(graph.nodes.every(n=>!n.usage.length)).toBe(true);expect(graph.limitations.join(' ')).toContain('Concept association unavailable');
  expect(graph.sourceFields[0]!.coverage).toMatchObject({has_more:true,complete_scan:false});
 });
 it('does not manufacture execution from unverified receipts, unknown mappings or newer definitions',()=>{
  const f=knowledgeFixture();const instance=f.view.run!.action_instances![f.doc.action_plan.actions[0]!.action_id]!;
  instance.verified_receipt=false;
  expect(workflowKnowledge(f.snapshot,f.doc,f.view,true).nodes[0]!.usage.some(u=>u.state==='executed')).toBe(false);
  instance.verified_receipt=true;instance.output={source_evidence:[{record_id:'r',mapping_id:'unknown'}]};
  expect(workflowKnowledge(f.snapshot,f.doc,f.view,true).nodes[0]!.usage.some(u=>u.state==='executed')).toBe(false);
  const graph=workflowKnowledge(f.snapshot,f.doc,knowledgeFixture().view,false);
  expect(graph.nodes[0]!.usage.some(u=>u.state==='executed')).toBe(false);expect(graph.limitations[0]).toContain('Historical ontology version unavailable');
 });
 it('keeps synthetic scenario evidence separate from actual execution usage',()=>{
  const f=knowledgeFixture();f.view.run!.action_instances![f.doc.action_plan.actions[0]!.action_id]!.provenance_type='SYNTHETIC';
  expect(workflowKnowledge(f.snapshot,f.doc,f.view,true).nodes[0]!.usage.map(u=>u.state)).toEqual(['planned']);
 });
 it('supports recorded report consumption without assigning ontology usage to email delivery',()=>{
  const f=knowledgeFixture();const read=f.doc.action_plan.actions[0]!;
  for(const [id,capability] of [['report','content.prepare'],['send','tool.extension_mail_send']])f.doc.action_plan.actions.push({...read,action_id:id!,capability_id:capability!,depends_on:[read.action_id],bindings:[{kind:'output',action_id:read.action_id,path:[],target:['data']}],evidence_references:[]});
  f.view.run!.action_instances!['report']={state:'completed',provenance_type:'INFERRED',input_provenance:[{source_reference:{action_id:read.action_id,path:[]}}]};
  const node=workflowKnowledge(f.snapshot,f.doc,f.view,true).nodes[0]!;
  expect(node.usage.some(u=>u.step==='report'&&u.state==='executed')).toBe(true);expect(node.usage.some(u=>u.step==='send')).toBe(false);
 });
});

describe('Recorded query ontology usage',()=>{
 it('renders exact Subway metric and joined-relationship receipts in the existing map',()=>{
  const f=knowledgeFixture('client-subway','Purchase order');const a=f.doc.action_plan.actions[0]!;
  a.capability_id='tool.subway_query';a.evidence_references=[];
  const mapping={...f.snapshot.knowledge!.source_mappings[0],field_id:'amount',dataset_id:'purchaseorders'};
  const relation={relationship_id:'shared:relation',source:'shared:case',target:'shared:item',source_field_id:'approval',target_field_id:'approval_id'};
  f.doc['binding_context']={validated_context:{ontology_usage:{version_id:f.snapshot.version_id,scope:{workspace_id:'client-subway',owner_id:'owner'},query_kind:'subway',mappings:[mapping],relationships:[relation]},
   subway_query_catalog:{sources:[{label:'finance.purchaseorders',fields:[{field_id:'amount',name:'totalAmount'}]}]}}};
  const instance=f.view.run!.action_instances![a.action_id]!;
  instance.resolved_inputs={query:{fields:[],group_by:[],filters:[],metrics:[{op:'avg',field_id:'amount'}],joins:['shared:relation']}};
  instance.output={query_id:'subway_query_saved',ontology_version:f.snapshot.version_id,coverage:{complete_scan:true},join_checks:[{relationship_id:'shared:relation'}]};
  instance['ontology_usage']=[{version_id:f.snapshot.version_id,concept_id:'shared:case',mapping_id:'mapping:shared',field_id:'amount',query_id:'subway_query_saved',reason:'Verified Subway query used this mapped source field.'}];
  instance['ontology_relationship_usage']=[{...relation,query_id:'subway_query_saved'}];
  const graph=workflowKnowledge(f.snapshot,f.doc,f.view,true);
  expect(graph.nodes[0]!.usage.map(u=>u.state)).toEqual(['planned','executed']);
  expect(graph.sourceFields[0]!.fields).toContain('finance.purchaseorders · totalAmount');
  expect(graph.edges[0]!.steps).toEqual([a.action_id]);
  instance['ontology_relationship_usage']=[{...relation,target:'foreign',query_id:'subway_query_saved'}];
  expect(workflowKnowledge(f.snapshot,f.doc,f.view,true).edges[0]!.steps).toEqual([]);
 });
 function savedQuery(tenant='simpsons'){
  const f=knowledgeFixture(tenant);const a=f.doc.action_plan.actions[0]!;
  a.capability_id='tool.workflow_data_query';a.evidence_references=[];
  f.doc['overview_intent']={};
  f.doc['binding_context']={
   validated_context:{
    ontology_usage:{version_id:f.snapshot.version_id,scope:{workspace_id:tenant,owner_id:'owner'},mappings:[{...f.snapshot.knowledge!.source_mappings[0],field_id:'field_saved'}]},
    data_query_catalog:{datasets:[{name:'Cases',fields:[{field_id:'field_saved',name:'complaint'}]}]},
   },
  };
  const instance=f.view.run!.action_instances![a.action_id]!;
  instance.resolved_inputs={query:{fields:[],group_by:[],filters:[{field_id:'field_saved'}]}};
  instance.output={query_id:'query_saved',result:{rows:[],matched_rows:0}};
  instance['ontology_usage']=[{version_id:f.snapshot.version_id,concept_id:'shared:case',mapping_id:'mapping:shared',field_id:'field_saved',query_id:'query_saved',reason:'Verified query used this mapped source field.'}];
  return f;
 }
 it.each(['simpsons','subway','new-workspace'])('renders real query usage for %s without returned record mappings',tenant=>{
  const f=savedQuery(tenant);expect(pinnedKnowledgeVersion(f.doc,f.view)).toBe(f.snapshot.version_id);
  const graph=workflowKnowledge(f.snapshot,f.doc,f.view,true);
  expect(graph.nodes[0]!.usage.map(u=>u.state)).toEqual(['planned','executed']);
  expect(graph.nodes[0]!.usage.find(u=>u.state==='executed')).toMatchObject({reference:'query_saved',reason:expect.stringContaining('Cases · complaint')});
  expect(graph.nodes[1]!.usage).toEqual([]);expect(graph.edges[0]!.steps).toEqual([]);
 });
 it.each(['wrong_version','foreign_scope','failed','synthetic','unverified','missing_mapping','current_fallback'])('rejects %s query usage',change=>{
  const f=savedQuery();const instance=f.view.run!.action_instances![f.doc.action_plan.actions[0]!.action_id]!;
  const context=f.doc['binding_context'] as {validated_context:{ontology_usage:{version_id:string;scope:{owner_id:string};mappings:unknown[]}}};
  if(change==='wrong_version')context.validated_context.ontology_usage.version_id='other';
  if(change==='foreign_scope')context.validated_context.ontology_usage.scope.owner_id='other';
  if(change==='failed')instance.state='failed';
  if(change==='synthetic')instance.provenance_type='SYNTHETIC';
  if(change==='unverified')instance.verified_receipt=false;
  if(change==='missing_mapping')context.validated_context.ontology_usage.mappings=[];
  expect(workflowKnowledge(f.snapshot,f.doc,f.view,change!=='current_fallback').nodes.every(n=>!n.usage.some(u=>u.state==='executed'))).toBe(true);
 });
 it('supports imported source mappings without a native knowledge envelope',()=>{
  const f=savedQuery();f.snapshot.source_mappings=f.snapshot.knowledge!.source_mappings;f.snapshot.knowledge=null;
  expect(workflowKnowledge(f.snapshot,f.doc,f.view,true).nodes[0]!.usage.some(u=>u.state==='executed')).toBe(true);
 });
 it('shows planned mappings before execution for a reviewed context query',()=>{
  const f=savedQuery();const a=f.doc.action_plan.actions[0]!;f.view.run=null;
  a.bindings=[{kind:'context',key:'reviewed_query',path:[],target:['query']}];
  const context=f.doc['binding_context'] as {validated_context:Record<string,unknown>};context.validated_context['reviewed_query']={fields:['field_saved']};
  expect(workflowKnowledge(f.snapshot,f.doc,f.view,true).nodes[0]!.usage.map(u=>u.state)).toEqual(['planned']);
 });
});
