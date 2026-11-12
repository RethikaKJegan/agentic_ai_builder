import type {WorkflowKnowledge} from './workflow-knowledge';

// Context is a visual overlay. Never add it to recorded execution usage.
export function knowledgeContext(model:WorkflowKnowledge,step:string){
 const executed=new Set(model.nodes.filter(n=>n.usage.some(u=>u.state==='executed'&&(step==='all'||u.step===step))).map(n=>n.id));
 const ids=new Set(model.nodes.map(n=>n.id));
 const neighbours=new Map<string,Set<string>>();
 for(const edge of model.edges){
  for(const [anchor,other] of [[edge.source,edge.target],[edge.target,edge.source]] as const){
   if(!executed.has(anchor)||executed.has(other)||!ids.has(other))continue;
   const anchors=neighbours.get(other)??new Set<string>();anchors.add(anchor);neighbours.set(other,anchors);
  }
 }
 return {executed,neighbours};
}
