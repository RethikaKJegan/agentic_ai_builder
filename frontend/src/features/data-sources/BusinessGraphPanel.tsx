"use client";
import BusinessRuleExecutionPanel from './BusinessRuleExecutionPanel';
import BusinessMonitoringPanel from './BusinessMonitoringPanel';
import BusinessAssociationsPanel from './BusinessAssociationsPanel';
import BusinessPolicyComparisonPanel from './BusinessPolicyComparisonPanel';
import BusinessWarrantyPanel from './BusinessWarrantyPanel';
import BusinessIntelligencePanel from './BusinessIntelligencePanel';
import {useEffect,useRef,useState} from 'react';
import dynamic from 'next/dynamic';
import {api} from '@/api/client';
import type {BusinessGraphPlan,BusinessSourceGraph,BusinessGraphRequest,BusinessVersion} from '@/api/business-ontology';
import {ApiFeedback} from '@/features/workflows/ApiFeedback';
const Canvas=dynamic(()=>import('./BusinessGraphCanvas'),{ssr:false,loading:()=> <p className="text-sm">Loading graph view…</p>});
const button='rounded-lg border px-3 py-2 text-sm disabled:opacity-40';
const field='mt-1 w-full min-w-0 rounded-lg border bg-background p-2 text-sm';
const asError=(e:unknown)=>e instanceof Error?e:new Error('Source graph is unavailable.');
export default function BusinessGraphPanel({snapshot,canManage,refreshToken=0,policyRefreshToken=0}:{snapshot:BusinessVersion;canManage:boolean;refreshToken?:number;policyRefreshToken?:number}){
 const [plan,setPlan]=useState<BusinessGraphPlan>(),[graph,setGraph]=useState<BusinessSourceGraph>(),[error,setError]=useState<Error>();
 const [serial,setSerial]=useState(''),[bindings,setBindings]=useState<BusinessGraphRequest['bindings']>({}),[loading,setLoading]=useState(true),[busy,setBusy]=useState(false),[reload,setReload]=useState(0),[selected,setSelected]=useState('');
 const seq=useRef(0),mounted=useRef(false),key=useRef(''),planHash=useRef('');
 useEffect(()=>{mounted.current=true;let active=true;seq.current++;setPlan(undefined);setError(undefined);setLoading(true);
  void api.businessGraphPlan(snapshot.version_id).then(value=>{if(active){if(planHash.current!==value.plan_hash)key.current='';planHash.current=value.plan_hash;setPlan(value);}}).catch(e=>{if(active)setError(asError(e));}).finally(()=>{if(active)setLoading(false);});
  return()=>{active=false;mounted.current=false;};
 },[snapshot.version_id,refreshToken,reload]);
 useEffect(()=>{setGraph(undefined);setSelected('');setBindings({});setSerial('');setBusy(false);key.current='';},[snapshot.version_id]);
 function changeBindings(mid:string,cid:string){key.current='';setBindings(value=>{const next={...value};if(cid)next[mid]={concept_id:cid,attributes:{}};else delete next[mid];return next;});}
 async function build(){
  if(busy||!plan)return;const current=++seq.current;setBusy(true);setError(undefined);key.current||=crypto.randomUUID();
  try{const value=await api.buildBusinessGraph(snapshot.version_id,{plan_hash:plan.plan_hash,serial,bindings,request_key:key.current});if(mounted.current&&current===seq.current){setGraph(value);setSelected('');setReload(v=>v+1);}}
  catch(e){if(mounted.current&&current===seq.current)setError(asError(e));}
  finally{if(mounted.current&&current===seq.current)setBusy(false);}
 }
 async function inspect(id:string){
  const current=++seq.current;setBusy(true);setError(undefined);
  try{const value=await api.businessSourceGraph(snapshot.version_id,id);if(mounted.current&&current===seq.current){setGraph(value);setSelected('');}}
  catch(e){if(mounted.current&&current===seq.current)setError(asError(e));}
  finally{if(mounted.current&&current===seq.current)setBusy(false);}
 }
 function download(name:string,content:string,type:string){const url=URL.createObjectURL(new Blob([content],{type}));const link=document.createElement('a');link.href=url;link.download=`simpson-${graph?.graph_id}-${name}`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
 const record=graph?.records.find(r=>r.node_id===selected)??graph?.records[0];
 return <section aria-label="Mapped source graph" className="min-w-0 space-y-4 rounded-xl border p-4"><header className="flex flex-wrap items-center justify-between gap-3"><div><h4 className="font-semibold">Engine source graph</h4><p className="mt-1 text-xs text-muted-foreground">Explicit mappings · Separate source records · Serial matches remain candidates</p></div><button className={button} disabled={loading||busy} onClick={()=>setReload(v=>v+1)}>Refresh graph plan</button></header>
  <ApiFeedback error={error} onRetry={()=>setReload(v=>v+1)} retrying={loading||busy}/>
  {loading&&<p role="status" className="text-sm">Loading source mapping plan…</p>}
  {plan&&<>
   {!plan.available&&<p role="status" className="text-sm">{plan.unavailable_reason}</p>}
   {canManage&&<details><summary className="cursor-pointer text-sm font-medium">Configure source mappings ({Object.keys(bindings).length} selected)</summary><p className="mt-2 text-xs text-muted-foreground">Choose record concepts and field meanings explicitly. Mapping and source presence do not verify business policy.</p><div className="mt-3 max-h-96 space-y-3 overflow-auto">{plan.mappings.map(mapping=>{const binding=bindings[mapping.mapping_id];const concept=snapshot.concepts.find(c=>c.id===binding?.concept_id);return <div key={mapping.mapping_id} className="rounded-lg border p-3"><p className="text-sm font-medium">{mapping.label} · {mapping.role==='service'?'db1 service':'db2 quality'}</p><p className="text-xs text-muted-foreground">{mapping.collection}{mapping.available?'':` · ${mapping.reason}`}</p><label className="mt-2 block text-xs">Concept for {mapping.collection}<select className={field} disabled={busy||!mapping.available} value={binding?.concept_id??''} onChange={e=>changeBindings(mapping.mapping_id,e.target.value)}><option value="">Keep as source record only</option>{snapshot.concepts.filter(c=>mapping.modules.includes(c.module_id)).map(c=><option key={c.id} value={c.id}>{c.label} ({c.module_id})</option>)}</select></label>{concept?.properties.map(prop=><label key={prop.name} className="mt-2 block text-xs">{mapping.collection} → {prop.name} · {prop.datatype}{prop.required?' · Required':''}<select className={field} disabled={busy} value={binding?.attributes[prop.name]??''} onChange={e=>{key.current='';setBindings(value=>{const next={...value[mapping.mapping_id]!,attributes:{...value[mapping.mapping_id]!.attributes}};if(e.target.value)next.attributes[prop.name]=e.target.value;else delete next.attributes[prop.name];return {...value,[mapping.mapping_id]:next};});}}><option value="">Unmapped</option>{mapping.fields.map(f=><option key={f.name} value={f.name}>{f.name} ({f.types.join(', ')})</option>)}</select></label>)}</div>;})}</div></details>}
   {canManage&&<form className="flex flex-wrap items-end gap-3" onSubmit={e=>{e.preventDefault();void build();}}><label className="min-w-0 flex-1 text-sm">Exact engine serial<input className={field} value={serial} maxLength={80} required disabled={busy} onChange={e=>{key.current='';setSerial(e.target.value);}} placeholder="Enter one engine serial"/></label><button type="submit" className={button} disabled={loading||busy||!plan.available||!plan.configured||!serial.trim()||!Object.keys(bindings).length}>{busy?'Reading bounded sources…':'Build & save source graph'}</button></form>}
   <p className="text-xs text-muted-foreground">Build reads both databases with up to 20 records per queried collection and a truncation probe. It saves a local graph snapshot; company records are never changed.</p>
   <label className="block text-sm">Saved source graph<select className={field} disabled={busy} value={graph?.graph_id??''} onChange={e=>{if(e.target.value)void inspect(e.target.value);}}><option value="">Choose a saved graph</option>{plan.snapshots.map(g=><option key={g.graph_id} value={g.graph_id}>{g.serial} · {g.records} records · {g.created_at}</option>)}</select></label>
  </>}
  {graph&&<>
   <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">{graph.coverage.map(stage=><div key={stage.stage} className="rounded-lg border p-2"><p className="text-sm font-medium">{stage.records}</p><p className="text-xs text-muted-foreground">{stage.stage.replaceAll('_',' ')}</p></div>)}</div>
   <p className="text-sm">Mapped-instance validation: {graph.validation.status} · {graph.validation.mapped_records} mapped records. Mapping meaning and business policy remain unverified.</p>
   <p className="text-sm text-muted-foreground">Monitoring unavailable: {graph.monitoring.missing.join('; ')}. Warranty evaluation has not run; physical-engine identity remains unresolved.</p>
   <BusinessRuleExecutionPanel key={`execution:${graph.version_id}:${graph.graph_id}`} graph={graph} canManage={canManage} onInspect={setSelected}/>
   <BusinessMonitoringPanel key={`monitoring:${graph.version_id}:${graph.graph_id}`} graph={graph} onInspect={setSelected}/>
   <BusinessAssociationsPanel key={`associations:${graph.version_id}:${graph.graph_id}`} graph={graph} onInspect={setSelected}/>
   <BusinessPolicyComparisonPanel refreshToken={policyRefreshToken} key={`policy:${graph.version_id}:${graph.graph_id}`} graph={graph} onInspect={setSelected}/>
   <BusinessWarrantyPanel key={`warranty:${graph.version_id}:${graph.graph_id}`} graph={graph} onInspect={setSelected}/>
   <BusinessIntelligencePanel key={`intelligence:${graph.version_id}:${graph.graph_id}`} versionId={graph.version_id} graphId={graph.graph_id} onInspect={setSelected}/>
   <Canvas graph={graph} onSelect={setSelected}/>
   <div className="grid gap-4 lg:grid-cols-[220px_1fr]"><div role="group" aria-label="Graph source records" className="max-h-80 space-y-2 overflow-auto">{graph.records.map(node=><button key={node.node_id} className={`block w-full break-words rounded-lg border p-2 text-left text-xs ${record?.node_id===node.node_id?'border-primary bg-primary/5':''}`} onClick={()=>setSelected(node.node_id)}>{node.collection} · {String(node.key['_id']??node.node_id.slice(0,8))}<span className="block text-muted-foreground">{node.role}</span></button>)}</div>{record&&<article aria-label="Graph record detail" className="min-w-0 rounded-lg border p-3"><h5 className="font-semibold">{record.collection}</h5><p className="mt-1 break-all text-xs text-muted-foreground">{record.connection_id} · {record.node_id}</p><dl className="mt-3 space-y-2 text-xs">{record.fields.map(f=><div key={f.name} className="break-words"><dt className="font-medium">{f.name}</dt><dd>{f.state==='value'?String(f.value):f.state.replaceAll('_',' ')}</dd></div>)}</dl><p className="mt-3 break-all text-xs text-muted-foreground">Record SHA-256: {record.record_sha256}</p></article>}</div>
   <details><summary className="cursor-pointer text-sm">Edges and unresolved references ({graph.edges.length} / {graph.unresolved.length})</summary><ul className="mt-2 max-h-64 space-y-2 overflow-auto text-xs">{graph.edges.map((e,i)=><li key={i} className="break-all">{e.source.slice(0,10)} → {e.target.slice(0,10)} · {e.classification} · {e.predicate}</li>)}{graph.unresolved.map((u,i)=><li key={`u${i}`} className="break-words">{u.field} → {u.target_collection}: {u.state}</li>)}</ul></details>
   <details><summary className="cursor-pointer text-sm">Collection outcomes and truncation</summary><ul className="mt-2 space-y-1 text-xs">{graph.outcomes.map(o=><li key={o.collection}>{o.collection}: {o.status.replaceAll('_',' ')} · {o.records}{o.truncated?' · Truncated':''}</li>)}</ul></details>
   <details><summary className="cursor-pointer text-sm">Validation issues ({graph.validation.issues.length+graph.validation.conversion_issues.length})</summary><ul className="mt-2 max-h-64 space-y-2 overflow-auto text-xs">{graph.validation.issues.map((i,n)=><li key={n} className="break-all">{i.message} · {i.focus} · {i.path}</li>)}{graph.validation.conversion_issues.map((i,n)=><li key={`c${n}`}>{i.field} → {i.attribute}: {i.reason}</li>)}</ul></details>
   <div className="flex flex-wrap gap-2"><button className={button} onClick={()=>download('graph.ttl',graph.rdf,'text/turtle')}>Download source RDF</button><button className={button} onClick={()=>download('validation.ttl',graph.shacl_report,'text/turtle')}>Download instance report</button></div>
   <ul className="list-inside list-disc text-xs text-muted-foreground">{graph.warnings.map(w=><li key={w}>{w}</li>)}</ul><p className="break-all text-xs text-muted-foreground">Read began {graph.read_started_at} · Saved {graph.created_at} · {graph.mapping_version}<br/>Source revisions: {JSON.stringify(graph.source_revisions)}</p>
  </>}
 </section>;
}
