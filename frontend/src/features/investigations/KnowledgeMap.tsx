'use client';
import '@xyflow/react/dist/style.css';
import {useEffect,useMemo,useState} from 'react';
import {ReactFlow,ReactFlowProvider,Background,Controls,Handle,Position,MarkerType,useReactFlow,useNodesInitialized,type Node,type NodeProps} from '@xyflow/react';
import dagre from '@dagrejs/dagre';
import {Network,CheckCircle2,BookOpen,Layers,Search,ArrowUpRight,Info,ChevronRight,Loader2} from 'lucide-react';
import {api} from '@/api/client';
import {useBackend} from '@/api/state';
import type {ActionDocument} from '@/api/orchestration';
import type {CompositionView} from '@/api/compositions';
import type {KnowledgeSnapshot} from '@/api/knowledge-map';
import {knowledgeContext} from '@/domain/knowledge-context';
import {pinnedKnowledgeVersion,workflowKnowledge,type KnowledgeConcept} from '@/domain/workflow-knowledge';

const label=(s:string)=>s.replaceAll('_',' ').replace(/([a-z])([A-Z])/g,'$1 $2');
type Card=Node<{label:string;module:string;state:string;group:boolean;count:number},'concept'>;
function ConceptCard({data,selected}:NodeProps<Card>){
 const executed=data.state==='executed';const planned=data.state==='planned';const context=data.state==='context';
 return <div className={`w-[224px] rounded-2xl border p-4 shadow-sm ${selected?'ring-2 ring-primary ring-offset-2':''} ${executed?'border-emerald-600 bg-emerald-100':context?'border-emerald-300 border-dashed bg-emerald-50':planned?'border-blue-500 bg-background':'border-border bg-background'} ${data.group?'border-dashed bg-muted/50':''}`}>
  <Handle type="target" position={Position.Left}/>
  <div className="flex items-start gap-3"><span className={`rounded-lg p-2 ${executed?'bg-emerald-200 text-emerald-800':context?'bg-emerald-100 text-emerald-700':planned?'bg-blue-50 text-blue-700':'bg-muted text-muted-foreground'}`}>{data.group?<Layers size={17}/>:executed?<CheckCircle2 size={17}/>:<BookOpen size={17}/>}</span><div className="min-w-0"><p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">{data.module}</p><p className="mt-1 break-words text-sm font-semibold">{data.label}</p></div></div>
  <p className="mt-3 text-xs text-muted-foreground">{data.group?`${data.count} concepts · click to expand`:executed?'Executed · mapped evidence':context?'Connected context · usage unverified':planned?'Planned · saved reference':'Available · ontology definition'}</p>
  <Handle type="source" position={Position.Right}/>
 </div>;
}
const nodeTypes={concept:ConceptCard};
function FitKnowledgeView({signature}:{signature:string}){
 const {fitView}=useReactFlow();const ready=useNodesInitialized();
 useEffect(()=>{if(!ready)return;const timer=setTimeout(()=>void fitView({padding:.22,maxZoom:1.05,duration:180}),30);return()=>clearTimeout(timer);},[signature,ready,fitView]);
 return null;
}
type Props={doc:ActionDocument;view:CompositionView};
export function KnowledgeMap(props:Props){
 const subject=useBackend(s=>s.session?.auth.subject);
 const key=JSON.stringify([subject?.workspace_id,subject?.subject_id,props.doc.composition_id,props.view.workflow_id,props.view.workflow_version,props.view.run?.run_id]);
 if(!subject||props.doc.scope.workspace!==subject.workspace_id||props.doc.scope.owner!==subject.subject_id||props.doc.action_plan.scope.workspace_id!==subject.workspace_id||props.doc.action_plan.scope.owner_id!==subject.subject_id||props.view.composition_id!==props.doc.composition_id)return <p role="status">Knowledge is unavailable in this workspace.</p>;
 return <ScopedKnowledgeMap key={key} {...props}/>;
}
function ScopedKnowledgeMap({doc,view}:Props){
 const pinned=pinnedKnowledgeVersion(doc,view);
 const [loaded,setLoaded]=useState<{snapshot:KnowledgeSnapshot;historical:boolean;modules:Record<string,string>}|null>(null);
 const [error,setError]=useState(false);const [retry,setRetry]=useState(0);
 const [mode,setMode]=useState<'workflow'|'full'>('workflow');const [step,setStep]=useState('all');const [search,setSearch]=useState('');
 const [selected,setSelected]=useState<string|null>(null);const [expanded,setExpanded]=useState<string[]>([]);const [collapsed,setCollapsed]=useState<string[]>([]);
 const [runNote,setRunNote]=useState('');
 useEffect(()=>{
  let live=true;setLoaded(null);setError(false);
  async function load(){
   const ontology=await api.businessOntology();
   let snapshot:KnowledgeSnapshot;let historical=false;
   if(pinned){
    try{snapshot=await api.knowledgeSnapshot(pinned);historical=true;}
    catch{if(!ontology.current_version_id)throw new Error('No authorized snapshot');snapshot=await api.knowledgeSnapshot(ontology.current_version_id);}
   }else{if(!ontology.current_version_id)throw new Error('No authorized ontology');snapshot=await api.knowledgeSnapshot(ontology.current_version_id);}
   if(pinned&&historical&&snapshot.version_id!==pinned)throw new Error('Snapshot reference mismatch');
   if(live)setLoaded({snapshot,historical,modules:Object.fromEntries(ontology.modules.map(m=>[m.id,m.label]))});
  }
  void load().catch(()=>{if(live)setError(true);});
  return()=>{live=false;};
 },[pinned,retry]);
 useEffect(()=>{
  let live=true;const id=view.run?.run_id;
  if(!id)return;
  void api.runKnowledge(id).then(value=>{if(live)setRunNote(value.projections.length?'Saved run knowledge references are available. Concept highlights require exact step and mapping evidence.':'This run has no saved graph projection.');}).catch(()=>{if(live)setRunNote('Saved run graph references are unavailable. The authorized ontology remains explorable.');});
  return()=>{live=false;};
 },[view.run?.run_id,view.run?.status]);
 const model=useMemo(()=>loaded?workflowKnowledge(loaded.snapshot,doc,view,loaded.historical):null,[loaded,doc,view]);
 const context=useMemo(()=>model?knowledgeContext(model,step):null,[model,step]);
 const graph=useMemo(()=>{
  if(!model||!loaded||!context)return {nodes:[] as Card[],edges:[]};
  const used=(n:KnowledgeConcept)=>n.usage.some(u=>step==='all'||u.step===step);
  const query=search.trim().toLowerCase();
  const modules=[...new Set(model.nodes.map(n=>n.module_id))].sort();
  const visible=model.nodes.filter(n=>(mode==='full'||!model.nodes.some(n=>n.usage.length)?!collapsed.includes(n.module_id):used(n)||context.neighbours.has(n.id)||expanded.includes(n.module_id))&&(!query||`${n.label} ${n.definition}`.toLowerCase().includes(query)));
  const ids=new Set(visible.map(n=>n.id));
  // Layout depends on visible IDs/edges, never runtime status or node selection.
  const layout=new dagre.graphlib.Graph();layout.setGraph({rankdir:'LR',nodesep:38,ranksep:100});layout.setDefaultEdgeLabel(()=>({}));
  visible.forEach(n=>layout.setNode(n.id,{width:224,height:122}));model.edges.forEach(e=>{if(ids.has(e.source)&&ids.has(e.target))layout.setEdge(e.source,e.target);});dagre.layout(layout);
  const nodes:Card[]=visible.map(n=>{const usages=n.usage.filter(u=>step==='all'||u.step===step);return {id:n.id,type:'concept',selected:selected===n.id,position:{x:layout.node(n.id).x,y:layout.node(n.id).y},data:{label:label(n.label),module:loaded.modules[n.module_id]??label(n.module_id),state:usages.some(u=>u.state==='executed')?'executed':context.neighbours.has(n.id)?'context':usages.length?'planned':'available',group:false,count:0}};});
  if(mode==='full'&&!query){let i=0;for(const module of modules){const hidden=model.nodes.filter(n=>n.module_id===module&&!ids.has(n.id));if(hidden.length&&(mode==='full'?collapsed.includes(module):!expanded.includes(module))){nodes.push({id:'module:'+module,type:'concept',position:{x:(i%3)*260-(visible.length?850:0),y:Math.floor(i/3)*155},data:{label:loaded.modules[module]??label(module),module:'More business knowledge',state:'available',group:true,count:hidden.length}});i++;}}}
  return {nodes,edges:model.edges.filter(e=>ids.has(e.source)&&ids.has(e.target)).map(e=>({id:e.id,source:e.source,target:e.target,label:label(e.label||e.predicate),type:'smoothstep',markerEnd:{type:MarkerType.ArrowClosed},style:{stroke:e.steps.some(s=>step==='all'||s===step)?'#2563eb':'#94a3b8'},labelStyle:{fontSize:11},labelBgPadding:[6,4] as [number,number],labelBgBorderRadius:4}))};
 },[model,loaded,context,mode,step,search,selected,expanded,collapsed]);
 if(error)return <div className="rounded-xl border border-dashed p-8"><h3 className="font-semibold">Knowledge map unavailable</h3><p className="mt-2 text-sm text-muted-foreground">No authorized ontology could be loaded for this workspace. Your workflow and reports remain available.</p><button onClick={()=>setRetry(n=>n+1)} className="mt-4 rounded-lg border px-4 py-2 text-sm">Try again</button></div>;
 if(!model||!loaded)return <div role="status" className="flex min-h-96 items-center justify-center gap-3 text-sm text-muted-foreground"><Loader2 className="h-5 w-5 animate-spin"/>Loading your workspace’s knowledge…</div>;
 const concept=model.nodes.find(n=>n.id===selected);
 const associated=model.nodes.filter(n=>n.usage.length).length;
 const executed=model.nodes.filter(n=>n.usage.some(u=>u.state==='executed')).length;
 const related=concept?model.edges.filter(e=>e.source===concept.id||e.target===concept.id):[];
 return <section aria-label="Workflow knowledge map" className="space-y-4">
  <div className="flex flex-wrap items-start justify-between gap-4"><div><p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-primary"><Network size={15}/>Business context</p><h3 className="mt-2 text-xl font-semibold">The knowledge behind this workflow</h3><p className="mt-1 text-sm text-muted-foreground">Explore definitions, their relationships and the evidence this workflow can establish.</p></div><div className="rounded-xl border bg-muted/30 px-4 py-3 text-right"><p className="text-lg font-semibold">{associated}<span className="text-sm font-normal text-muted-foreground"> / {model.nodes.length}</span></p><p className="text-xs text-muted-foreground">concepts associated with the plan</p><p className="mt-1 text-xs text-emerald-700">{executed} with recorded execution evidence</p></div></div>
  <div className="flex flex-wrap items-center gap-3 rounded-xl border bg-background p-3">
   <div className="inline-flex rounded-lg bg-muted p-1"><button aria-pressed={mode==='workflow'} onClick={()=>setMode('workflow')} className={`rounded-md px-3 py-2 text-sm ${mode==='workflow'?'bg-background font-medium shadow-sm':''}`}>This workflow</button><button aria-pressed={mode==='full'} onClick={()=>setMode('full')} className={`rounded-md px-3 py-2 text-sm ${mode==='full'?'bg-background font-medium shadow-sm':''}`}>Full ontology</button></div>
   <select aria-label="Knowledge workflow step" value={step} onChange={e=>{setStep(e.target.value);setSelected(null);}} className="min-w-0 max-w-full rounded-lg border bg-background px-3 py-2 text-sm"><option value="all">All workflow steps</option>{doc.action_plan.actions.map(a=><option key={a.action_id} value={a.action_id}>{label(a.action_id)}</option>)}</select>
   <label className="flex min-w-0 flex-1 items-center gap-2 rounded-lg border px-3 py-2"><Search size={15} className="shrink-0 text-muted-foreground"/><input aria-label="Search ontology concepts" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search concepts…" className="w-full min-w-0 bg-transparent text-sm outline-none"/></label>
   {expanded.length>0&&<button onClick={()=>setExpanded([])} className="text-xs text-primary">Collapse groups</button>}
  </div>
  {mode==='full'&&<div aria-label="Business module groups" className="flex flex-wrap gap-2">{[...new Set(model.nodes.map(n=>n.module_id))].sort().map(id=><button key={id} aria-pressed={!collapsed.includes(id)} onClick={()=>setCollapsed(old=>old.includes(id)?old.filter(x=>x!==id):[...old,id])} className={`rounded-full border px-3 py-1.5 text-xs ${collapsed.includes(id)?'text-muted-foreground':'border-primary/30 bg-primary/5 text-primary'}`}><Layers size={12} className="mr-1 inline"/>{loaded.modules[id]??label(id)} · {model.nodes.filter(n=>n.module_id===id).length}</button>)}</div>}
  <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground"><span>○ Available</span><span className="text-blue-700">◇ Planned</span><span className="flex items-center gap-1 text-emerald-700"><CheckCircle2 size={13}/>Executed with evidence</span><span className="text-emerald-600">◇ Light green: connected context · usage unverified</span><span className="text-amber-700">– – Unavailable associations are listed below</span><span className="ml-auto">Ontology revision {loaded.snapshot.revision} · {loaded.historical?'Saved version':'Current version'}</span></div>
  {!associated&&<p role="status" className="rounded-xl border border-amber-200 bg-amber-50/40 p-4 text-sm">This workflow has no saved concept associations. The full ontology is available below. New workflows record exact mapped source usage; older runs retain their original evidence.</p>}
  <div className="grid min-w-0 overflow-hidden rounded-2xl border lg:grid-cols-[minmax(0,1fr)_320px]">
   <div className="relative h-[570px] min-w-0 bg-canvas max-sm:h-[420px]" aria-label="Ontology graph canvas">
    <ReactFlowProvider><ReactFlow<Card> nodes={graph.nodes} edges={graph.edges} nodeTypes={nodeTypes} fitView minZoom={.08} maxZoom={1.8} nodesDraggable={false} nodesConnectable={false} edgesReconnectable={false} onNodeClick={(_,node)=>{if(node.data.group){setExpanded(old=>[...old,node.id.slice(7)]);setCollapsed(old=>old.filter(id=>id!==node.id.slice(7)));}else setSelected(node.id);}} proOptions={{hideAttribution:true}}><FitKnowledgeView signature={graph.nodes.map(n=>n.id).join('|')}/><Background gap={22} color="#cbd5e1"/><Controls showInteractive={false}/></ReactFlow></ReactFlowProvider>
    {!graph.nodes.length&&<div className="pointer-events-none absolute inset-0 flex items-center justify-center p-8 text-center text-sm text-muted-foreground">No supported concept associations for this selection. Explore the full ontology or choose another step.</div>}
   </div>
   <aside aria-label="Knowledge concept details" className="min-w-0 space-y-5 border-t bg-background p-5 lg:border-l lg:border-t-0">
    {!concept?<><div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary"><BookOpen size={20}/></div><h4 className="font-semibold">Every concept has a story</h4><p className="text-sm leading-relaxed text-muted-foreground">Select a concept to see its business meaning, connected fields and recorded role in this workflow.</p><div className="rounded-xl bg-muted/50 p-4 text-xs leading-relaxed text-muted-foreground">Connecting two concepts in the ontology does not mean this workflow used their relationship.</div></>:<>
     <div><p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{loaded.modules[concept.module_id]??label(concept.module_id)}</p><h4 className="mt-1 text-lg font-semibold">{label(concept.label)}</h4></div>
     <section><h5 className="mb-2 text-xs font-semibold uppercase tracking-wide">Business definition</h5><p className="text-sm leading-relaxed text-muted-foreground">{concept.definition||'No saved definition.'}</p><p className="mt-2 text-xs text-muted-foreground">Definition status: {concept.status}. Business validation is separate from execution usage.</p></section>
     {context?.neighbours.has(concept.id)&&<section className="rounded-xl border border-dashed border-emerald-300 bg-emerald-50 p-3"><h5 className="text-sm font-semibold text-emerald-800">Connected context</h5><p className="mt-2 text-xs text-emerald-800">Directly connected to {Array.from(context.neighbours.get(concept.id)!).map(id=>label(model.nodes.find(n=>n.id===id)!.label)).join(', ')} in this ontology. This connection does not establish that the workflow used this concept or relationship.</p></section>}
     <section><h5 className="mb-2 text-xs font-semibold uppercase tracking-wide">Workflow relevance</h5>{concept.usage.length?concept.usage.filter(u=>step==='all'||u.step===step).map((u,i)=><div key={i} className="mb-2 rounded-lg bg-muted/50 p-3 text-xs"><p className="font-medium">{label(u.step)} · {u.state==='executed'?'Executed':'Planned'}</p><p className="mt-1 text-muted-foreground">{u.reason}</p>{u.reference&&<p className="mt-1 break-all">Evidence: {u.reference}</p>}</div>):<p className="text-sm text-muted-foreground">Available in the ontology. No saved workflow association.</p>}</section>
     <section><h5 className="mb-2 text-xs font-semibold uppercase tracking-wide">Connected data</h5>{concept.mappings.length?concept.mappings.map(m=><div key={m.id} className="mb-2 rounded-lg border p-3 text-xs"><p className="font-medium">{m.collection}</p><p className="mt-1 break-all text-muted-foreground">{m.field_path}</p><p className="mt-1 text-muted-foreground">Saved mapping · {m.source_role}</p></div>):<p className="text-sm text-muted-foreground">No saved source mapping available.</p>}</section>
     <section><h5 className="mb-2 text-xs font-semibold uppercase tracking-wide">Relationships</h5>{related.map(e=>{const other=model.nodes.find(n=>n.id===(e.source===concept.id?e.target:e.source));return other?<button key={e.id} onClick={()=>{setSelected(other.id);setExpanded(old=>[...old,other.module_id]);}} className="mb-2 flex w-full items-center justify-between gap-2 rounded-lg border p-3 text-left text-xs"><span><span className="text-muted-foreground">{e.source===concept.id?'→':'←'} {label(e.label||e.predicate)}</span><span className="mt-1 block font-medium">{label(other.label)}</span></span><ChevronRight size={14}/></button>:null;})}{!related.length&&<p className="text-sm text-muted-foreground">No saved relationships.</p>}</section>
     {!!concept.unknowns.length&&<section><h5 className="mb-2 text-xs font-semibold uppercase tracking-wide">Limitations</h5>{concept.unknowns.map((u,i)=><p key={i} className="mb-2 text-xs text-muted-foreground">{u}</p>)}</section>}
     <details className="text-xs"><summary className="cursor-pointer text-muted-foreground">Technical references</summary><p className="mt-2 break-all">Concept: {concept.id}</p><p className="mt-1 break-all">Ontology: {model.version}</p>{concept.evidence.map((e,i)=><p key={i} className="mt-2 break-words">Source {e.source_id}: {e.quote}</p>)}</details>
    </>}
   </aside>
  </div>
  {(model.limitations.length>0||runNote)&&<div role="status" className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50/40 p-4 text-sm"><Info size={17} className="mt-0.5 shrink-0 text-amber-700"/><div className="space-y-1">{model.limitations.map(s=><p key={s}>{s}</p>)}{runNote&&<p className="text-xs text-muted-foreground">{runNote}</p>}</div></div>}
  {model.sourceFields.filter(f=>step==='all'||f.step===step).map(f=><details key={f.step} className="rounded-xl border p-4 text-sm"><summary className="cursor-pointer font-medium">Source evidence · {label(f.step)}</summary><p className="mt-3 text-xs text-muted-foreground">Source-query references are shown independently of ontology concept usage.</p>{f.queryId&&<p className="mt-2 flex items-center gap-2 break-all text-xs"><ArrowUpRight size={13}/>Query {f.queryId}</p>}<p className="mt-2 break-all text-xs text-muted-foreground">{f.fields.join(', ')||'No explicit field list recorded.'}</p>{f.coverage&&<p className="mt-2 text-xs">{f.coverage['complete_scan']===true?'Complete source scan.':'Source scan completeness unavailable or partial.'} {f.coverage['has_more']===true?'Additional result rows exist.':''}</p>}</details>)}
 </section>;
}
