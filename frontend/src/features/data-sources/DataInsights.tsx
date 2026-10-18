"use client";
import { connectionDisplayName, displayText } from "@/lib/display-text";

import {useEffect, useMemo, useState} from "react";
import {ArrowUpRight, BarChart3, Database, GitBranch, Layers3, RefreshCw, Sparkles} from "lucide-react";
import {api} from "@/api/client";
import type {DatabaseConnection, DatabaseMetadata} from "@/api/data-sources";
import type {SemanticView} from "@/api/semantic-kg";

const colors=["#2563eb", "#8b5cf6", "#06b6d4", "#f59e0b", "#94a3b8"];
const panel="min-w-0 rounded-2xl border border-border/70 bg-background p-6 shadow-sm";
const control="rounded-xl border bg-background px-4 py-2.5 text-sm disabled:opacity-50";
function fieldKind(types:string[]) {
 if(types.length!==1)return "Mixed / other";
 const type=types[0]!.toLowerCase();
 if(/^(smallint|integer|bigint|int\d*|long|numeric|decimal|real|double.*|float\d*|number)$/.test(type))return "Numeric";
 if(/date|timestamp|^time/.test(type))return "Date & time";
 if(/bool/.test(type))return "Boolean";
 if(/text|string|char/.test(type))return "Text";
 return "Mixed / other";
}

export default function DataInsights({connections}:{connections:DatabaseConnection[]}) {
 const [selected,setSelected]=useState("");
 const [snapshots,setSnapshots]=useState<DatabaseMetadata[]>([]);
 const [graph,setGraph]=useState<SemanticView|null>(null);
 const [loading,setLoading]=useState(true),[refresh,setRefresh]=useState(0);
 const [warnings,setWarnings]=useState<string[]>([]),[updated,setUpdated]=useState<string>();
 const key=JSON.stringify(connections.map(c=>({id:c.connection_id,revision:c.metadata_revision,generation:c.generation,status:c.connection_status,profiling:c.profiling_status})));
 const targets=useMemo(()=>JSON.parse(key) as {id:string;revision:number;status:string}[],[key]);
 useEffect(()=>{
  let active=true;setLoading(true);setWarnings([]);setSnapshots([]);setGraph(null);setUpdated(undefined);
  const readable=targets.filter(c=>c.status!=="disconnected");
  void Promise.all([
   Promise.allSettled(readable.map(c=>api.databaseMetadata(c.id))),
   api.knowledgeGraph().then(value=>({value,error:false})).catch(()=>({value:null,error:true})),
  ]).then(([results,kg])=>{
   if(!active)return;
   const loaded:DatabaseMetadata[]=[],issues:string[]=[];
   results.forEach((result,index)=>{if(result.status==="fulfilled")loaded.push(result.value);else issues.push(`Metadata unavailable for ${connections.find(c=>c.connection_id===readable[index]?.id)?.name??"a connection"}.`);});
   if(kg.error)issues.push("Semantic Intelligence summary is currently unavailable.");
   setSnapshots(loaded);setGraph(kg.value);setWarnings(issues);setUpdated(new Date().toISOString());setLoading(false);
  });
  return()=>{active=false;};
  // Reload by source identity/revision rather than every connection-status poll.
  // eslint-disable-next-line react-hooks/exhaustive-deps
 },[targets,refresh]);
 const effectiveSelection=connections.some(c=>c.connection_id===selected)?selected:"";
 const scoped=snapshots.filter(s=>!effectiveSelection||s.connection.connection_id===effectiveSelection);
 const datasets=scoped.flatMap(s=>(s.snapshot?.datasets??[]).map(d=>({...d,connection:s.connection.name,connection_id:s.connection.connection_id})));
 const fields=datasets.flatMap(d=>d.fields);
 const distribution=["Text","Numeric","Date & time","Boolean","Mixed / other"].map((name,index)=>({name,count:fields.filter(f=>fieldKind(f.types)===name).length,color:colors[index]!}));
 let offset=0;
 const gradient=distribution.map(d=>{const start=offset;offset+=fields.length?d.count/fields.length*100:0;return `${d.color} ${start}% ${offset}%`;}).join(",");
 const datasetIds=new Set(datasets.map(d=>d.dataset_id));
 const relationships=graph?.relationships.filter(e=>datasetIds.has(e.source_dataset_id)&&datasetIds.has(e.target_dataset_id))??[];
 const statuses=["confirmed","inferred","ambiguous","needs_review","rejected"].map((name,index)=>({name,count:relationships.filter(e=>e.status===name).length,color:colors[index]!}));
 const ranked=[...datasets].sort((a,b)=>b.fields.length-a.fields.length).slice(0,6);
 const peak=Math.max(1,...ranked.map(d=>d.fields.length));
 const sampled=datasets.filter(d=>d.discovery_method==="sampled");
 const declared=datasets.filter(d=>d.discovery_method!=="sampled");
 const available=scoped.filter(s=>s.snapshot).length;
 const notices=[...warnings,...scoped.flatMap(s=>s.snapshot?.warnings??[])];
 return <section aria-label="EDA dashboard" className="space-y-5">
  <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-950 via-blue-950 to-indigo-900 p-8 text-white shadow-lg">
   <div className="pointer-events-none absolute -right-20 -top-28 h-80 w-80 rounded-full border-[45px] border-white/5"/>
   <div className="relative flex items-start justify-between gap-8"><div>
    <p className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.2em] text-blue-200"><Sparkles className="h-4 w-4"/>Data, at a glance</p>
    <h2 className="mt-3 text-3xl font-semibold tracking-tight">A clearer picture of your data.</h2>
    <p className="mt-3 max-w-xl text-sm leading-6 text-blue-100/80">Explore the shape of your connected databases, the fields within them, and the relationships that bring them together.</p>
    <span className="mt-5 inline-flex rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs text-blue-100">Metadata overview · No business-row analysis</span>
   </div><BarChart3 className="mt-2 h-16 w-16 shrink-0 text-blue-300/60" strokeWidth={1}/></div>
  </div>
  <div className="flex flex-wrap items-center justify-between gap-3">
   <label className="flex items-center gap-3 text-sm font-medium">Explore<select aria-label="EDA connection" className={`${control} max-w-sm`} value={effectiveSelection} onChange={e=>setSelected(e.target.value)}><option value="">All connections</option>{connections.map(c=><option key={c.connection_id} value={c.connection_id}>{connectionDisplayName(c.name, c.engine)}</option>)}</select></label>
   <div className="flex items-center gap-3"><span className="text-xs text-muted-foreground">{loading?"Refreshing overview…":updated?`Updated ${new Date(updated).toLocaleTimeString()}`:""}</span><button className={`${control} flex items-center gap-2`} disabled={loading} onClick={()=>setRefresh(v=>v+1)}><RefreshCw className={`h-4 w-4 ${loading?"animate-spin":""}`}/>Refresh insights</button></div>
  </div>
  {loading?<div role="status" className="grid grid-cols-4 gap-4" aria-label="Loading EDA overview">{[0,1,2,3].map(i=><div key={i} className="h-28 animate-pulse rounded-2xl border bg-muted/50"/>)}</div>:<>
   {notices.length>0&&<div role="status" className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">{notices.map((w,i)=><p key={i}>{w}</p>)}<p className="mt-1 text-xs">Charts include successfully loaded metadata only.</p></div>}
   <div className="grid grid-cols-4 gap-4">{[
    {label:"Profiled connections",value:available,detail:"Successful metadata snapshots",icon:Database},
    {label:"Discovered datasets",value:datasets.length,detail:`${declared.length} declared · ${sampled.length} sampled`,icon:Layers3},
    {label:"Discovered fields",value:fields.length,detail:"Across the selected datasets",icon:BarChart3},
    {label:"Semantic Intelligence relationships",value:graph?relationships.length:"—",detail:graph?"Links within this selection":"Graph summary unavailable",icon:GitBranch},
   ].map(card=><article key={card.label} className={panel}><div className="flex items-center justify-between gap-2"><p className="text-xs font-medium text-muted-foreground">{displayText(card.label)}</p><card.icon className="h-4 w-4 text-blue-500"/></div><p className="mt-3 text-3xl font-semibold tracking-tight" aria-label={displayText(card.label)}>{card.value}</p><p className="mt-2 text-xs text-muted-foreground">{card.detail}</p></article>)}</div>
   {!datasets.length?<div className={`${panel} py-14 text-center`}><Database className="mx-auto h-9 w-9 text-blue-400"/><h3 className="mt-4 font-semibold">Your data story starts here</h3><p className="mt-2 text-sm text-muted-foreground">{displayText(connections.length?"No successful dataset metadata in this selection yet. Connect and profile a database, then refresh insights.":"Add a database connection to see its discovered structure here.")}</p></div>:<>
    <div className="grid grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] gap-5">
     <article className={panel} aria-label="Field type distribution"><p className="text-xs font-medium uppercase tracking-wider text-blue-600">Structure</p><h3 className="mt-1 text-lg font-semibold">What your fields look like</h3><p className="mt-1 text-xs text-muted-foreground">Field types from the discovered schema</p><div className="mt-7 flex items-center gap-8"><div role="img" aria-label={`Field types: ${distribution.map(d=>`${d.name} ${d.count}`).join(", ")}`} className="relative h-40 w-40 shrink-0 rounded-full" style={{background:fields.length?`conic-gradient(${gradient})`:"#e2e8f0"}}><div className="absolute inset-5 flex flex-col items-center justify-center rounded-full bg-background"><span className="text-3xl font-semibold">{fields.length}</span><span className="text-xs text-muted-foreground">fields</span></div></div><ul className="min-w-0 flex-1 space-y-3">{distribution.map(d=><li key={d.name} className="flex items-center gap-2 text-xs"><span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{background:d.color}}/><span className="flex-1 text-muted-foreground">{displayText(d.name)}</span><span className="font-semibold tabular-nums">{d.count}</span></li>)}</ul></div></article>
     <article className={panel} aria-label="Dataset field counts"><div className="flex items-center justify-between"><div><p className="text-xs font-medium uppercase tracking-wider text-blue-600">Dataset footprint</p><h3 className="mt-1 text-lg font-semibold">Where the detail lives</h3></div><ArrowUpRight className="h-5 w-5 text-muted-foreground"/></div><p className="mt-1 text-xs text-muted-foreground">Largest datasets by discovered field count · Top 6</p><div className="mt-6 space-y-4">{ranked.map((d,i)=><div key={d.dataset_id}><div className="mb-1.5 flex justify-between gap-3 text-xs"><span className="truncate font-medium" title={displayText(`${d.connection} / ${d.name}`)}>{displayText(d.name)}<span className="ml-2 font-normal text-muted-foreground">{d.connection}</span></span><span className="font-semibold tabular-nums">{d.fields.length}</span></div><div className="h-2 rounded-full bg-muted"><div className="h-full rounded-full" style={{width:`${d.fields.length/peak*100}%`,background:colors[i%colors.length]}}/></div></div>)}</div></article>
    </div>
    <div className="grid grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)] gap-5">
     <article className={panel}><p className="text-xs font-medium uppercase tracking-wider text-blue-600">Connected knowledge</p><h3 className="mt-1 text-lg font-semibold">Relationships, with context</h3><p className="mt-1 text-xs text-muted-foreground">Semantic review status from the current Semantic Intelligence</p>{graph?<><div className="mt-6 flex h-4 overflow-hidden rounded-full bg-muted" role="img" aria-label={statuses.map(s=>`${s.name} ${s.count}`).join(", ")}>{statuses.filter(s=>s.count).map(s=><div key={s.name} style={{width:`${s.count/relationships.length*100}%`,background:s.color}}/>)}</div><div className="mt-5 grid grid-cols-3 gap-4">{statuses.map(s=><div key={s.name}><p className="text-xl font-semibold tabular-nums">{s.count}</p><p className="mt-1 flex items-center gap-1.5 text-xs capitalize text-muted-foreground"><span className="h-2 w-2 rounded-full" style={{background:s.color}}/>{displayText(s.name.replaceAll("_"," "))}</p></div>)}</div>{graph.stale&&<p className="mt-4 text-xs text-amber-700">Semantic Intelligence metadata is awaiting a rebuild; these relationship counts are historical.</p>}</>:<p className="mt-6 text-sm text-muted-foreground">Semantic Intelligence summary unavailable. Refresh insights to try again.</p>}</article>
     <article className={`${panel} bg-gradient-to-br from-blue-50/70 to-background`}><p className="text-xs font-medium uppercase tracking-wider text-blue-600">Discovery coverage</p><h3 className="mt-1 text-lg font-semibold">Know what you’re seeing</h3><div className="mt-5 space-y-4">{[{name:"Declared structure",value:declared.length,detail:"Schema definitions, keys and constraints"},{name:"Sampled structure",value:sampled.length,detail:"Observed document fields; coverage may vary"},{name:"Discovery samples",value:sampled.reduce((n,d)=>n+d.sample_count,0),detail:"Documents sampled during metadata profiling, not total rows"}].map(item=><div key={item.name} className="flex items-start justify-between gap-4 border-b pb-3 last:border-0 last:pb-0"><div><p className="text-sm font-medium">{displayText(item.name)}</p><p className="mt-1 max-w-xs text-xs leading-5 text-muted-foreground">{item.detail}</p></div><span className="text-xl font-semibold tabular-nums">{item.value}</span></div>)}</div></article>
    </div>
   </>}
   <p className="px-1 text-xs leading-5 text-muted-foreground">Based on saved metadata and Semantic Intelligence evidence. Refreshes automatically when connection metadata changes. No sales, revenue, total-record counts or record-level quality scores are inferred.</p>
  </>}
 </section>;
}
