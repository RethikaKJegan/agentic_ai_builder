"use client";
import {useEffect,useRef,useState} from 'react';
import {api} from '@/api/client';
import type {BusinessOntologyState,BusinessVersion} from '@/api/business-ontology';
import BusinessModuleCoveragePanel from './BusinessModuleCoveragePanel';
import BusinessGraphPanel from './BusinessGraphPanel';
import BusinessRulesPanel from './BusinessRulesPanel';
import BusinessCompilationPanel from './BusinessCompilationPanel';
import {ApiFeedback} from '@/features/workflows/ApiFeedback';
export default function BusinessDraftDefinitions({data,moduleId,canManage=false,onData,openDraft,policyRefreshToken=0}:{data:BusinessOntologyState;moduleId:string;canManage?:boolean;onData?:(data:BusinessOntologyState)=>void;openDraft?:{versionId:string;request:number}|undefined;policyRefreshToken?:number}){
 const [versionId,setVersionId]=useState(''),[snapshot,setSnapshot]=useState<BusinessVersion>(),[selected,setSelected]=useState(''),[error,setError]=useState<Error>();
 const [catalogueRefresh,setCatalogueRefresh]=useState(0);
 const container=useRef<HTMLElement>(null);
 useEffect(()=>{if(openDraft){setVersionId(openDraft.versionId);setSelected('');container.current?.scrollIntoView?.({behavior:'smooth',block:'start'});}},[openDraft]);
 const target=versionId||data.current_version_id;
 useEffect(()=>{let active=true;setSnapshot(undefined);setError(undefined);if(target)void api.businessVersion(target).then(result=>{if(active)setSnapshot(result);}).catch(e=>{if(active)setError(e instanceof Error?e:new Error('Version unavailable.'));});return()=>{active=false;};},[target]);
 const items=snapshot?[
  ...snapshot.concepts.map(item=>({...item,kind:'concept' as const})),
  ...snapshot.relationships.map(item=>({...item,kind:'relationship' as const})),
  ...snapshot.rules.map(item=>({...item,kind:'rule' as const})),
 ].filter(item=>item.module_id===moduleId):[];
 const current=items.find(item=>item.id===selected)??items[0];
 const label=(id:string)=>snapshot?.concepts.find(c=>c.id===id)?.label??id;
 return <section ref={container} aria-label="Generated business definitions" className="space-y-4 rounded-2xl border bg-background p-5">
  <div className="flex flex-wrap items-center justify-between gap-3"><h3 className="font-semibold">Versioned module definitions</h3><label className="text-sm">Definition version<select className="ml-2 max-w-full rounded-lg border bg-background p-2" value={versionId} onChange={e=>{setVersionId(e.target.value);setSelected('');}}><option value="">Latest saved version</option>{data.versions.map(v=><option key={v.version_id} value={v.version_id}>Revision {v.revision} · {v.kind}</option>)}</select></label></div>
  <ApiFeedback error={error}/>
  {!target?<p className="text-sm text-muted-foreground">Create the foundation and generate a module to inspect definitions here.</p>:!snapshot&&!error?<p role="status" className="text-sm">Loading saved definitions…</p>:snapshot&&<>
   <p className="text-xs text-muted-foreground">Revision {snapshot.revision} · {snapshot.kind==='draft'?'Saved draft; business meaning and policy are not verified.':'Foundation structure; no generated definitions.'}</p>
   {snapshot.reference_import&&<p className="text-xs text-muted-foreground">Curated blueprint reference · {snapshot.reference_import.added_modules.length} modules added · No model generation performed by this import</p>}
   {snapshot.extraction&&<p className="text-xs text-muted-foreground">Model: {snapshot.extraction.model} · {snapshot.extraction.input_tokens??'Unknown'} input / {snapshot.extraction.output_tokens??'Unknown'} output tokens</p>}
   {(snapshot.extraction?.classification_adjustments?.length??0)>0&&<details className="rounded-lg border p-3"><summary className="cursor-pointer text-sm">Source classification corrections ({snapshot.extraction!.classification_adjustments!.length})</summary><p className="mt-2 text-xs text-muted-foreground">The cited source kinds did not support policy/code authority. These rules remain proposed logic, with their original citations unchanged.</p><ul className="mt-2 space-y-1 text-xs">{snapshot.extraction!.classification_adjustments!.map(a=><li key={a.rule_id} className="break-words">{a.rule_id}: {a.original_basis.replaceAll('_',' ')} → proposed logic</li>)}</ul></details>}
   <BusinessModuleCoveragePanel key={`coverage:${snapshot.version_id}`} versionId={snapshot.version_id} canManage={canManage} onData={onData?next=>{setVersionId('');setSelected('');onData(next);}:undefined}/>
   <BusinessCompilationPanel key={`compilation:${snapshot.version_id}`} versionId={snapshot.version_id} revision={snapshot.revision} kind={snapshot.kind} canManage={canManage} onCompiled={()=>setCatalogueRefresh(value=>value+1)}/>
   <BusinessRulesPanel key={`rules:${snapshot.version_id}`} snapshot={snapshot} moduleId={moduleId} refreshToken={catalogueRefresh}/>
   {data.workspace?.ontology_id!=='subway'&&<BusinessGraphPanel policyRefreshToken={policyRefreshToken} key={`graph:${snapshot.version_id}`} snapshot={snapshot} canManage={canManage} refreshToken={catalogueRefresh}/>}
   {!items.length?<p className="text-sm text-muted-foreground">No generated definitions for this module in this version.</p>:<div className="grid gap-4 lg:grid-cols-[minmax(180px,260px)_1fr]">
    <div role="group" aria-label="Module definitions" className="max-h-96 space-y-2 overflow-auto">{items.map(item=><button key={item.id} aria-pressed={current?.id===item.id} onClick={()=>setSelected(item.id)} className={`block w-full rounded-lg border p-3 text-left text-sm ${current?.id===item.id?'border-primary bg-primary/5':''}`}><span className="block text-xs text-muted-foreground">{item.kind}</span>{item.label}</button>)}</div>
    {current&&<article aria-label="Business definition detail" className="min-w-0 space-y-4 rounded-xl border p-4"><div><h4 className="font-semibold">{current.label}</h4><p className="mt-2 whitespace-pre-wrap text-sm">{current.definition}</p><p className="mt-2 text-xs text-muted-foreground">{current.layer} · Draft · {current.source_basis?'Curated blueprint reference':'Extraction confidence '+Math.round(current.confidence*100)+'%'} (not business approval)</p></div>
     {current.kind==='concept'&&<><p className="text-sm">Parent: {current.parent_id?label(current.parent_id):'Not specified'}</p>{current.properties.length>0&&<ul className="space-y-2">{current.properties.map(p=><li key={p.name} className="break-words text-sm"><strong>{p.name}</strong> · {p.datatype} · {p.required?'Required':'Optional'}<p className="text-muted-foreground">{p.description}</p></li>)}</ul>}</>}
     {current.kind==='relationship'&&<p className="break-words text-sm">{label(current.source)} → {current.predicate} → {label(current.target)}</p>}
     {current.kind==='rule'&&<div className="space-y-2 text-sm"><p>Rule definition · {current.basis.replaceAll('_',' ')} · Execution availability is shown in the rule catalogue</p><ul className="list-inside list-disc">{current.conditions.map((condition,i)=><li key={i}>{condition}</li>)}</ul><p>Outcome: {current.outcome}</p><p>Inputs: {current.inputs.map(label).join(', ')||'Not specified'}</p></div>}
     <div><h5 className="text-sm font-semibold">Supporting evidence</h5>{current.evidence.map((e,i)=>{const source=snapshot.sources.find(s=>s.source_id===e.source_id);return <div key={i} className="mt-2 rounded-lg border p-3"><p className="text-xs text-muted-foreground">{source?.title??e.source_id} · {source?.kind.replaceAll('_',' ')}</p><blockquote className="mt-2 whitespace-pre-wrap break-words text-sm">{e.quote}</blockquote>{source&&<details className="mt-2"><summary className="cursor-pointer text-xs">Read source and provenance</summary><p className="mt-2 break-all text-xs text-muted-foreground">SHA-256: {source.sha256}</p><p className="mt-1 break-all text-xs text-muted-foreground">{typeof source.origin==='string'?source.origin:JSON.stringify(source.origin)}</p><pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap break-words text-xs">{source.text}</pre></details>}</div>;})}</div>
     {current.unknowns.length>0&&<div><h5 className="text-sm font-semibold">Unresolved information</h5><ul className="mt-2 list-inside list-disc text-sm">{current.unknowns.map((u,i)=><li key={i}>{u}</li>)}</ul></div>}
    </article>}
   </div>}
   {(snapshot.questions[moduleId]?.length??0)>0&&<div><h4 className="text-sm font-semibold">Module questions</h4><ul className="mt-2 list-inside list-disc text-sm text-muted-foreground">{snapshot.questions[moduleId]?.map((q,i)=><li key={i}>{q}</li>)}</ul></div>}
  </>}
 </section>;
}
