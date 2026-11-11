import {knowledgeSnapshotSchema} from '@/api/knowledge-map';
import {businessOntologySchema} from '@/api/business-ontology';
import {actionDocumentSchema} from '@/api/orchestration';
import {compositionViewSchema} from '@/api/compositions';
import fixture from './orchestration.json' with {type:'json'};
import {dynamicView} from '../../../e2e/fixtures/dynamic-investigation';

export function knowledgeFixture(tenant='simpsons',title='Complaint'){
 const concept=(id:string,name:string)=>({id,label:name,definition:`${tenant} business definition for ${name}.`,layer:'domain',module_id:'operations',status:'draft' as const,evidence:[],confidence:.8,unknowns:[],parent_id:null,properties:[]});
 const snapshot=knowledgeSnapshotSchema.parse({version_id:tenant+'_v1',revision:1,concepts:[concept('shared:case',title),concept('shared:item','Related '+title)],relationships:[{...concept('shared:relation','Concerns'),source:'shared:case',target:'shared:item',predicate:'concerns'}],rules:[],knowledge:{source_mappings:[{id:'mapping:shared',concept_id:'shared:case',source_role:'service',collection:tenant+'_records',field_path:'complaint',attribute:'description'}]}});
 const ontology=businessOntologySchema.parse({api_version:1,workspace:{ontology_id:tenant,title:tenant,namespace:tenant,revision:1,status:'draft',created_at:'2026-11-11',sources:{},source_revisions:{}},layers:[],modules:[{id:'operations',label:'Operations',description:'Business operations',layers:[],concept_count:2}],available_sources:[],source_bindings:[],versions:[{version_id:snapshot.version_id,revision:1,created_at:'2026-11-11',kind:'draft'}],counts:{concepts:2,relationships:1,rules:0},generation_status:'draft_available',current_version_id:snapshot.version_id});
 const doc=actionDocumentSchema.parse(structuredClone(fixture.document));doc.scope={workspace:tenant,owner:'owner'};doc.action_plan.scope={workspace_id:tenant,owner_id:'owner',client_id:tenant};doc.action_plan.actions=doc.action_plan.actions.slice(0,1);doc.action_plan.actions[0]!.evidence_references=['shared:case'];doc['contracts']={};doc['overview_intent']={knowledge:{version_id:snapshot.version_id}};
 const view=compositionViewSchema.parse({
  ...dynamicView(),composition_id:doc.composition_id,workflow_id:'workflow_shared',workflow_version:1,knowledge:{},
  run:{...dynamicView('completed').run,run_id:'run_shared',action_instances:{
   [doc.action_plan.actions[0]!.action_id]:{state:'completed',verified_receipt:true,output:{
    source_evidence:[{record_id:'record_saved',values:{'mapping:shared':{value:'observed'}}}],
    query_id:'query_shared',coverage:{complete_scan:true,has_more:false},
   }},
  }},
 });
 return {snapshot,ontology,doc,view};
}
