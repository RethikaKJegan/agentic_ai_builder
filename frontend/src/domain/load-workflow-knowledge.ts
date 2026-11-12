import type {KnowledgeSnapshot} from '@/api/knowledge-map';
import type {BusinessOntologyState} from '@/api/business-ontology';
type Source={businessOntology:()=>Promise<BusinessOntologyState>;knowledgeSnapshot:(id:string)=>Promise<KnowledgeSnapshot>};
export async function loadWorkflowKnowledge(source:Source,pinned:string|undefined,strictPin=false){
  if(pinned){
    // A saved pin is authoritative; module labels are optional decoration.
    const [snapshot,ontology]=await Promise.all([source.knowledgeSnapshot(pinned).catch(error=>{if(strictPin)throw error;return null;}),source.businessOntology().catch(()=>null)]);
    if(snapshot){
      if(snapshot.version_id!==pinned)throw new Error('Snapshot reference mismatch');
      return {snapshot,historical:true,modules:Object.fromEntries(ontology?.modules.map(m=>[m.id,m.label])??[])};
    }
    // Preserve the existing explicitly labeled current-version fallback for other tenants.
    if(!ontology?.current_version_id)throw new Error('No authorized snapshot');
    const current=await source.knowledgeSnapshot(ontology.current_version_id);
    if(current.version_id!==ontology.current_version_id)throw new Error('Snapshot reference mismatch');
    return {snapshot:current,historical:false,modules:Object.fromEntries(ontology.modules.map(m=>[m.id,m.label]))};
  }
  const ontology=await source.businessOntology();
  if(!ontology.current_version_id)throw new Error('No authorized ontology');
  const snapshot=await source.knowledgeSnapshot(ontology.current_version_id);
  if(snapshot.version_id!==ontology.current_version_id)throw new Error('Snapshot reference mismatch');
  return {snapshot,historical:false,modules:Object.fromEntries(ontology.modules.map(m=>[m.id,m.label]))};
}
