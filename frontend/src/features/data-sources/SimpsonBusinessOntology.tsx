"use client";

import { useCallback, useEffect, useRef, useState } from 'react';
import { BookOpen, Database, Layers3, RefreshCw } from 'lucide-react';
import { api } from '@/api/client';
import type { BusinessOntologyState } from '@/api/business-ontology';
import { ApiFeedback } from '@/features/workflows/ApiFeedback';
import BusinessPolicyLibrary from './BusinessPolicyLibrary';
import BusinessGenerationPanel from './BusinessGenerationPanel';
import BusinessDraftDefinitions from './BusinessDraftDefinitions';
import BusinessSourcesPanel from './BusinessSourcesPanel';

const button = 'rounded-lg border px-3 py-2 text-sm font-medium disabled:opacity-40';
const asError = (error:unknown) => error instanceof Error ? error : new Error('Business ontology could not be loaded.');

export default function SimpsonBusinessOntology({canManage}:{canManage:boolean}) {
  const [view,setView]=useState<'definitions'|'sources'>('definitions');
  const [data,setData] = useState<BusinessOntologyState>();
  const [error,setError] = useState<Error>();
  const [loading,setLoading] = useState(true);
  const [busy,setBusy] = useState(false);
  const [layer,setLayer] = useState('all');
  const [moduleId,setModuleId] = useState('engines');
  const [policyRefresh,setPolicyRefresh]=useState(0);
  const [openDraft,setOpenDraft]=useState<{versionId:string;request:number}>();
  const [service,setService] = useState('');
  const [quality,setQuality] = useState('');
  const request = useRef(0);
  const lock = useRef(false);
  const load = useCallback(async () => {
    const current = ++request.current;
    setLoading(true); setError(undefined);
    try { const result = await api.businessOntology(); if(current===request.current)setData(result); }
    catch(e) { if(current===request.current)setError(asError(e)); }
    finally { if(current===request.current)setLoading(false); }
  },[]);
  const cancel = useCallback(()=>{request.current++;},[]);
  useEffect(()=>{void load();return cancel;},[load,cancel]);
  async function initialize() {
    if(lock.current)return;
    lock.current=true; setBusy(true); setError(undefined);
    const current=++request.current;
    try { const result=await api.initializeBusinessOntology({service,quality}); if(current===request.current)setData(result); }
    catch(e) { if(current===request.current)setError(asError(e)); }
    finally { lock.current=false; if(current===request.current)setBusy(false); }
  }
  const modules = data?.modules.filter(m=>layer==='all'||m.layers.includes(layer)) ?? [];
  const selected = modules.find(m=>m.id===moduleId) ?? modules[0];
  const activeLayer = data?.layers.find(l=>l.id===layer);
  return <section aria-label="Business ontology workspace" className="space-y-5">
    <header className="flex flex-wrap items-start justify-between gap-3">
      <div><p className="text-xs font-medium uppercase tracking-widest text-primary">Business knowledge</p>
        <h2 className="mt-2 text-2xl font-semibold">Simpson Business Ontology</h2>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">Explore business meaning across engines, warranty, field service and quality.</p>
      </div>
      <button className={button} disabled={loading||busy} onClick={()=>void load()} aria-label="Refresh business ontology"><RefreshCw className="mr-2 inline h-4 w-4"/>Refresh</button>
    </header>
    <ApiFeedback error={error} onRetry={load}/>
    {loading&&!data&&<p role="status">Loading business ontology…</p>}
    <nav aria-label="Business ontology views" className="flex flex-wrap gap-2"><button className={button} aria-pressed={view==='definitions'} onClick={()=>setView('definitions')}>Business definitions</button><button className={button} aria-pressed={view==='sources'} onClick={()=>setView('sources')}>Databases, changes & records</button></nav>
    {view==='sources'?<BusinessSourcesPanel canManage={canManage}/>:data&&<>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4" aria-label="Business ontology summary">
        {[[data.layers.length,'Layers'],[data.modules.length,'Business modules'],[data.counts.concepts,'Concepts'],[data.counts.rules,'Business rules']].map(([value,label])=><div key={label} className="rounded-xl border bg-background p-4"><p className="text-2xl font-semibold">{value}</p><p className="mt-1 text-sm text-muted-foreground">{label}</p></div>)}
      </div>
      {!data.workspace?<div className="rounded-2xl border bg-background p-5">
        <h3 className="font-semibold">Connect the business foundation</h3>
        <p className="mt-2 text-sm text-muted-foreground">Choose both Simpson sources: service operations in db1 and claims and quality in db2. Creating the workspace saves this foundation; concept generation follows in the next step.</p>
        {canManage?<form className="mt-4 space-y-4" onSubmit={event=>{event.preventDefault();void initialize();}}>
          <div className="grid gap-4 sm:grid-cols-2">{([['Service operations source',service,setService],['Claims and quality source',quality,setQuality]] as const).map(([label,value,setValue])=><label key={label} className="block text-sm font-medium">{label}<select value={value} onChange={e=>setValue(e.target.value)} disabled={busy} required className="mt-2 w-full min-w-0 rounded-lg border bg-background p-2.5"><option value="">Choose a connected database</option>{data.available_sources.map(source=><option key={source.connection_id} value={source.connection_id}>{source.name}</option>)}</select></label>)}</div>
          {data.available_sources.length<2&&<p role="status" className="text-sm text-muted-foreground">Two connected MongoDB sources are required. Add them in Connections.</p>}
          {service&&service===quality&&<p role="status" className="text-sm">Choose a different database for each role.</p>}
          <button type="submit" className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-40" disabled={busy||loading||!service||!quality||service===quality}>{busy?'Creating workspace…':'Create business ontology workspace'}</button>
        </form>:<p className="mt-3 text-sm text-muted-foreground">A workspace manager can connect the two sources and create the foundation.</p>}
      </div>:<div className="rounded-2xl border bg-background p-5">
        <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="font-semibold">{data.generation_status==='draft_available'?'Business draft available':'Foundation ready'}</h3><span className="rounded-full border px-3 py-1 text-xs">Revision {data.workspace.revision}</span></div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">{data.source_bindings.map(source=><div key={source.role} className="min-w-0 rounded-xl border p-3"><p className="text-xs text-muted-foreground">{source.role==='service'?'Service operations':'Claims and quality'}</p><p className="mt-1 break-words text-sm font-medium"><Database className="mr-2 inline h-4 w-4"/>{source.name??'Source unavailable'}</p><p className="mt-1 text-xs text-muted-foreground">{source.status==='metadata_changed'?'Source metadata changed since initialization':source.status==='connected'?'Connected':'Source unavailable'}</p></div>)}</div>
        <p className="mt-4 text-sm text-muted-foreground">{data.generation_status==='draft_available'?'Definitions are saved as versioned drafts. Evidence checks do not establish verified business policy.':'Concept generation has not started. The saved foundation contains the layer and module structure, with no generated concepts or rules yet.'}</p>
      </div>}
      {data.workspace&&<BusinessGenerationPanel data={data} canManage={canManage} moduleId={selected?.id??'engines'} onModule={id=>{setLayer('all');setModuleId(id);}} onData={setData} onOpenDraft={(module,versionId)=>{setLayer('all');setModuleId(module);setOpenDraft(previous=>({versionId,request:(previous?.request??0)+1}));}}/>}
      {data.workspace&&<BusinessPolicyLibrary canManage={canManage} onData={setData} onChanged={()=>setPolicyRefresh(v=>v+1)}/>}
      <div className="grid gap-4 lg:grid-cols-[220px_1fr]">
        <nav aria-label="Business ontology layers" className="space-y-2 rounded-2xl border bg-background p-3">
          <p className="px-2 py-2 text-sm font-semibold"><Layers3 className="mr-2 inline h-4 w-4"/>Ontology layers</p>
          {[{id:'all',label:'All layers'},...data.layers].map(item=><button key={item.id} aria-pressed={layer===item.id} onClick={()=>setLayer(item.id)} className={`w-full rounded-lg px-3 py-2.5 text-left text-sm ${layer===item.id?'bg-primary text-primary-foreground':'hover:bg-muted'}`}>{item.label}</button>)}
        </nav>
        <div className="min-w-0 space-y-4">
          <div><h3 className="font-semibold">{activeLayer?.label??'All business modules'}</h3><p className="mt-1 text-sm text-muted-foreground">{activeLayer?.description??'Twelve connected areas covering the warranty-to-quality lifecycle.'}</p></div>
          <div className="grid gap-4 xl:grid-cols-2">
            <div className="space-y-2" role="group" aria-label="Business ontology modules">{modules.map(module=><button key={module.id} aria-pressed={selected?.id===module.id} onClick={()=>setModuleId(module.id)} className={`flex w-full items-center justify-between gap-3 rounded-xl border p-3 text-left text-sm ${selected?.id===module.id?'border-primary bg-primary/5':'bg-background'}`}><span>{module.label}</span><span className="shrink-0 text-xs text-muted-foreground">{module.concept_count} concepts</span></button>)}</div>
            {selected&&<article aria-label="Selected business module" className="min-w-0 rounded-2xl border bg-background p-5"><BookOpen className="h-6 w-6 text-primary"/><h4 className="mt-3 text-lg font-semibold">{selected.label}</h4><p className="mt-2 text-sm text-muted-foreground">{selected.description}</p><div className="mt-4 flex flex-wrap gap-2">{selected.layers.map(id=><span key={id} className="rounded-full border px-2 py-1 text-xs">{data.layers.find(l=>l.id===id)?.label??id}</span>)}</div><p className="mt-6 text-sm text-muted-foreground">{selected.concept_count?`${selected.concept_count} draft concepts. Inspect the versioned definitions below.`:'No concepts have been generated for this module.'}</p></article>}
          </div>
        </div>
      </div>
      <BusinessDraftDefinitions policyRefreshToken={policyRefresh} openDraft={openDraft} onData={setData} canManage={canManage} data={data} moduleId={selected?.id??'engines'}/>
    </>}
  </section>;
}
