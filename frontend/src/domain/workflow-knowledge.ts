import type {KnowledgeSnapshot} from '@/api/knowledge-map';
import type {ActionDocument} from '@/api/orchestration';
import type {CompositionView} from '@/api/compositions';

export const asObject=(v:unknown):Record<string,unknown>=>v!==null&&typeof v==='object'&&!Array.isArray(v)?v as Record<string,unknown>:{};
const list=(v:unknown):unknown[]=>Array.isArray(v)?v:[];
const strings=(v:unknown)=>list(v).filter((x):x is string=>typeof x==='string');
export type KnowledgeUsage={step:string;state:'planned'|'executed';reason:string;reference?:string};
export type KnowledgeConcept=KnowledgeSnapshot['concepts'][number]&{usage:KnowledgeUsage[];mappings:NonNullable<KnowledgeSnapshot['knowledge']>['source_mappings']};
export type WorkflowKnowledge={version:string;nodes:KnowledgeConcept[];edges:(KnowledgeSnapshot['relationships'][number]&{steps:string[]})[];limitations:string[];sourceFields:{step:string;fields:string[];queryId?:string;coverage?:Record<string,unknown>}[]};

export function pinnedKnowledgeVersion(doc:ActionDocument,view:CompositionView):string|undefined {
  const overview=asObject(doc['overview_intent']);const knowledge=asObject(overview['knowledge']);
  const pins=asObject(view.knowledge['pins']);const packageContext=asObject(doc['client_package_context']);
  const usage=asObject(asObject(asObject(doc['binding_context'])['validated_context'])['ontology_usage']);
  const candidates=[usage['version_id'],knowledge['version_id'],pins['version_id'],pins['ontology_version'],packageContext['ontology_version']];
  return candidates.find((x):x is string=>typeof x==='string'&&x.length>0);
}

export function workflowKnowledge(snapshot:KnowledgeSnapshot,doc:ActionDocument,view:CompositionView,historical:boolean):WorkflowKnowledge {
  const snapshotMappings=snapshot.source_mappings??snapshot.knowledge?.source_mappings??[];
  const nodes=snapshot.concepts.map(c=>({...c,usage:[] as KnowledgeUsage[],mappings:snapshotMappings.filter(m=>m.concept_id===c.id)}));
  const byId=new Map(nodes.map(c=>[c.id,c]));const edges=snapshot.relationships.map(e=>({...e,steps:[] as string[]}));
  const mappings=new Map(snapshotMappings.map(m=>[m.id,m]));
  const context=asObject(doc['binding_context']);const evidence=asObject(context['evidence']);const contracts=asObject(doc['contracts']);
  const sourceFields:WorkflowKnowledge['sourceFields']=[];
  const validated=asObject(context['validated_context']);
  const pin=asObject(validated['ontology_usage']);const pinScope=asObject(pin['scope']);
  const pinned=historical&&pin['version_id']===snapshot.version_id&&pinScope['workspace_id']===doc.scope.workspace&&pinScope['owner_id']===doc.scope.owner;
  const pinnedMappings=list(pin['mappings']).map(asObject).filter(m=>typeof m['id']==='string'&&mappings.get(m['id'])?.concept_id===m['concept_id']);
  const catalog=asObject(validated['data_query_catalog']);
  const fieldLabels=new Map(list(catalog['datasets']).flatMap(raw=>{const d=asObject(raw);return list(d['fields']).flatMap(rawField=>{const f=asObject(rawField);return typeof f['field_id']==='string'&&typeof f['name']==='string'?[[f['field_id'],`${String(d['name']??'Dataset')} · ${f['name']}`] as const]:[];});}));
  const add=(id:string,usage:KnowledgeUsage)=>{
    const node=byId.get(id);if(node&&!node.usage.some(u=>u.step===usage.step&&u.state===usage.state))node.usage.push(usage);
  };
  for(const action of doc.action_plan.actions){
    const contract=asObject(contracts[action.capability_id]);
    const references=[...strings(contract['required_ontology']),...strings(action.evidence_references)];
    for(const ref of references){
      const saved=asObject(evidence[ref]);
      const id=byId.has(ref)?ref:ref.startsWith('concept:')&&byId.has(ref.slice(8))?ref.slice(8):saved['kind']==='concept'&&typeof saved['id']==='string'?saved['id']:mappings.get(ref)?.concept_id;
      if(id)add(id,{step:action.action_id,state:'planned',reason:'Explicit concept or mapping reference in the saved plan.'});
      const edge=edges.find(e=>e.id===ref||'relationship:'+e.id===ref);if(edge)edge.steps.push(action.action_id);
    }
    const instance=view.run?.action_instances?.[action.action_id];const output=asObject(instance?.output);
    let query=asObject(asObject(instance?.resolved_inputs)['query']);
    if(!Object.keys(query).length){
      const binding=action.bindings.find(b=>Array.isArray(b['target'])&&b['target'].length===1&&b['target'][0]==='query');
      if(binding){
        const sections:Record<string,string>={context:'validated_context',literal:'user_values',evidence:'evidence',configuration:'configuration'};
        const section=sections[String(binding['kind'])];
        let value:unknown=section?asObject(context[section])[String(binding['key'])]:asObject(view.run?.action_instances?.[String(binding['action_id'])]?.output);
        for(const part of list(binding['path']))value=asObject(value)[String(part)];
        query=asObject(value);
      }
    }
    const fields=[...strings(query['fields']),...strings(query['group_by']),...list(query['filters']).flatMap(f=>typeof asObject(f)['field_id']==='string'?[String(asObject(f)['field_id'])]:[])];
    const operands=list(query['metrics']).flatMap(m=>String(asObject(m)['expression']??'').match(/[A-Za-z_][A-Za-z0-9_]*/g)??[]).filter(id=>fieldLabels.has(id));
    fields.push(...operands);
    if(pinned&&action.capability_id==='tool.workflow_data_query')for(const mapping of pinnedMappings){if(fields.includes(String(mapping['field_id'])))add(String(mapping['concept_id']),{step:action.action_id,state:'planned',reason:'The query references this exact saved concept-to-source field mapping.'});}
    if(fields.length||typeof output['query_id']==='string')sourceFields.push({step:action.action_id,fields:[...new Set(fields)].map(id=>fieldLabels.get(id)??id),...(typeof output['query_id']==='string'?{queryId:output['query_id']} :{}),...(output['coverage']?{coverage:asObject(output['coverage'])}:{})});
    if(pinned&&instance?.state==='completed'&&instance.provenance_type!=='SYNTHETIC'){
      for(const raw of list(instance['ontology_usage'])){
        const usage=asObject(raw);const mapping=pinnedMappings.find(m=>m['id']===usage['mapping_id']&&m['concept_id']===usage['concept_id']);
        if(usage['version_id']!==snapshot.version_id||!mapping)continue;
        if(action.capability_id!=='content.prepare'&&instance.verified_receipt!==true)continue;
        if(action.capability_id==='content.prepare'&&(!action.depends_on.includes(String(usage['upstream_action_id']))||!list(instance.input_provenance).some(p=>asObject(asObject(p)['source_reference'])['action_id']===usage['upstream_action_id'])))continue;
        const field=typeof usage['field_id']==='string'?fieldLabels.get(usage['field_id'])??usage['field_id']:undefined;
        add(String(usage['concept_id']),{step:action.action_id,state:'executed',reason:`${String(usage['reason'])}${field?' Field: '+field+'.':''}`,reference:String(usage['query_id']??usage['record_id']??usage['upstream_action_id'])});
      }
    }
    // A successful query alone proves no concept association. Require an exact
    // source-evidence mapping on a verified completed reader in the saved version.
    if(!historical||instance?.state!=='completed'||instance.verified_receipt!==true||instance.provenance_type==='SYNTHETIC')continue;
    for(const raw of [...list(output['records']),...list(output['source_evidence']).flatMap(raw=>{const packet=asObject(raw);return Array.isArray(packet['records'])?packet['records']:[raw];})]){
      const record=asObject(raw);if(typeof record['record_id']!=='string')continue;
      const refs=[...Object.keys(asObject(record['values'])),...strings(record['mapping_ids'])];
      if(typeof record['mapping_id']==='string')refs.push(record['mapping_id']);
      for(const ref of refs){const mapping=mappings.get(ref);if(mapping)add(mapping.concept_id,{step:action.action_id,state:'executed',reason:'Verified source receipt contains this exact saved concept mapping.',reference:typeof output['query_id']==='string'?output['query_id']:String(record['record_id'])});}
    }
  }
  // Content steps can consume verified upstream evidence, without implying that
  // email/Calendar/Sheets tools queried the same concepts or ontology links.
  for(let pass=0;pass<doc.action_plan.actions.length;pass++)for(const action of doc.action_plan.actions){
    if(action.capability_id!=='content.prepare')continue;
    const instance=view.run?.action_instances?.[action.action_id];
    const consumed=action.bindings.filter(b=>['output','generated','receipt'].includes(String(b['kind']))&&typeof b['action_id']==='string'&&action.depends_on.includes(String(b['action_id']))).map(b=>String(b['action_id']));
    for(const node of nodes)for(const dep of consumed){
      const usages=node.usage.filter(u=>u.step===dep);
      if(usages.length)add(node.id,{step:action.action_id,state:'planned',reason:'The saved content step consumes an associated upstream output.'});
      if(historical&&instance?.state==='completed'&&instance.provenance_type!=='SYNTHETIC'&&usages.some(u=>u.state==='executed')&&list(instance.input_provenance).some(p=>asObject(asObject(p)['source_reference'])['action_id']===dep))add(node.id,{step:action.action_id,state:'executed',reason:'Recorded input provenance supports consumption of the mapped upstream evidence.'});
    }
  }
  const limitations:string[]=[];
  if(!historical)limitations.push('Current ontology shown. Historical ontology version unavailable.');
  if(!nodes.some(n=>n.usage.length))limitations.push('Usage history unavailable.');
  if(sourceFields.length&&!nodes.some(n=>n.usage.some(u=>u.state==='executed')))limitations.push('Concept association unavailable. Source-query references do not establish concept usage.');
  if(!snapshotMappings.length)limitations.push('This ontology version has no saved concept-to-source mappings.');
  return {version:snapshot.version_id,nodes,edges,limitations,sourceFields};
}
