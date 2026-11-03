"use client";
import {useEffect,useRef,useState} from 'react';
import {api} from '@/api/client';
import type {BusinessRuleCatalogue,BusinessCompetencyResult,BusinessVersion} from '@/api/business-ontology';
import {ApiFeedback} from '@/features/workflows/ApiFeedback';

const button='rounded-lg border px-3 py-2 text-sm disabled:opacity-40';
const field='mt-1 w-full min-w-0 rounded-lg border bg-background p-2 text-sm';
const basisLabels:Record<string,string>={policy_statement:'Policy statement (unverified)',descriptive_implementation:'Describes code behavior',proposed_logic:'Proposed logic'};
const asError=(e:unknown)=>e instanceof Error?e:new Error('The rule catalogue is unavailable.');
export default function BusinessRulesPanel({snapshot,moduleId,refreshToken=0}:{snapshot:BusinessVersion;moduleId:string;refreshToken?:number}){
 const [data,setData]=useState<BusinessRuleCatalogue>(),[error,setError]=useState<Error>(),[queryError,setQueryError]=useState<Error>();
 const [loading,setLoading]=useState(true),[busy,setBusy]=useState(false),[reload,setReload]=useState(0);
 const [search,setSearch]=useState(''),[moduleFilter,setModuleFilter]=useState('all'),[basis,setBasis]=useState('all'),[selectedRule,setSelectedRule]=useState('');
 const [queryId,setQueryId]=useState('rule_inputs'),[focus,setFocus]=useState(''),[result,setResult]=useState<BusinessCompetencyResult>();
 const mounted=useRef(false),sequence=useRef(0);
 useEffect(()=>{
  mounted.current=true;let active=true;sequence.current++;setData(undefined);setResult(undefined);setError(undefined);setQueryError(undefined);setLoading(true);setBusy(false);
  void api.businessRuleCatalogue(snapshot.version_id).then(value=>{if(active)setData(value);}).catch(e=>{if(active)setError(asError(e));}).finally(()=>{if(active)setLoading(false);});
  return()=>{active=false;mounted.current=false;};
 },[snapshot.version_id,refreshToken,reload]);

 const rules=data?.rules.filter(rule=>(moduleFilter==='all'||rule.module_id===moduleFilter)&&(basis==='all'||rule.basis===basis)&&`${rule.label} ${rule.definition} ${rule.id} ${rule.conditions.join(' ')} ${rule.outcome}`.toLowerCase().includes(search.toLowerCase()))??[];
 const current=rules.find(rule=>rule.id===selectedRule)??rules[0];
 const question=data?.queries.find(query=>query.query_id===queryId);
 const focusOptions=question?.focus_kind==='rule'?snapshot.rules:question?.focus_kind==='concept'?snapshot.concepts:[...snapshot.concepts,...snapshot.relationships,...snapshot.rules];
 function clear(){sequence.current++;setResult(undefined);setQueryError(undefined);setBusy(false);}
 async function run(offset=0){
  if(busy||!question?.available)return;
  const request=++sequence.current;setBusy(true);setQueryError(undefined);setResult(undefined);
  try{const value=await api.runBusinessCompetency(snapshot.version_id,{query_id:queryId,focus_id:focus||null,limit:20,offset});if(mounted.current&&request===sequence.current)setResult(value);}
  catch(e){if(mounted.current&&request===sequence.current)setQueryError(asError(e));}
  finally{if(mounted.current&&request===sequence.current)setBusy(false);}
 }
 return <section aria-label="Business rules and competency questions" className="min-w-0 space-y-5 rounded-xl border p-4">
  <header className="flex flex-wrap items-center justify-between gap-3"><div><h4 className="font-semibold">Rule catalogue & competency questions</h4><p className="mt-1 text-xs text-muted-foreground">Revision {snapshot.revision} · Supported reference rules have implemented evidence checks. Choose a saved source graph below to run them.</p></div><button className={button} disabled={loading||busy} onClick={()=>setReload(value=>value+1)}>Refresh rule catalogue</button></header>
  <ApiFeedback error={error} onRetry={()=>setReload(value=>value+1)} retrying={loading}/>
  {loading&&<p role="status" className="text-sm">Loading saved rule catalogue…</p>}
  {data&&<>
   <div className="grid gap-3 sm:grid-cols-3"><label className="text-xs">Search candidate rules<input className={field} value={search} onChange={e=>setSearch(e.target.value)} placeholder="Name, condition or outcome"/></label><label className="text-xs">Rule module<select className={field} value={moduleFilter} onChange={e=>setModuleFilter(e.target.value)}><option value="all">All modules</option>{[...new Set([moduleId,...snapshot.concepts.map(c=>c.module_id),...data.rules.map(r=>r.module_id)])].sort().map(id=><option key={id} value={id}>{id}</option>)}</select></label><label className="text-xs">Evidence basis<select className={field} value={basis} onChange={e=>setBasis(e.target.value)}><option value="all">All evidence bases</option>{Object.entries(basisLabels).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label></div>
   <p className="text-xs text-muted-foreground">{rules.length} matching candidates · {data.rules.length} in this version</p>
   {!rules.length?<p className="text-sm text-muted-foreground">No saved candidate rules match these filters.</p>:<div className="grid gap-4 lg:grid-cols-[minmax(180px,240px)_1fr]"><div role="group" aria-label="Candidate rules" className="max-h-80 space-y-2 overflow-auto">{rules.map(rule=><button key={rule.id} className={`block w-full rounded-lg border p-3 text-left text-sm ${current?.id===rule.id?'border-primary bg-primary/5':''}`} aria-pressed={current?.id===rule.id} onClick={()=>setSelectedRule(rule.id)}>{rule.label}<span className="mt-1 block text-xs text-muted-foreground">{rule.basis_label}</span></button>)}</div>
    {current&&<article aria-label="Candidate rule detail" className="min-w-0 space-y-3 rounded-lg border p-4"><h5 className="font-semibold">{current.label}</h5><p className="text-xs text-muted-foreground">{current.basis_label} · {current.execution?.available?'Implemented evidence check available':'No matching handler'}</p><p className="text-sm">{current.definition}</p><div className="text-sm"><p className="font-medium">Recorded conditions</p><ul className="mt-1 list-inside list-disc">{current.conditions.map((value,index)=><li key={index}>{value}</li>)}</ul><p className="mt-2">Outcome: {current.outcome}</p></div>
     <details><summary className="cursor-pointer text-sm">Required input definitions</summary><p className="mt-2 text-xs text-muted-foreground">These are declared rule inputs and direct attributes. Company-data availability has not been checked.</p>{current.input_definitions.length?current.input_definitions.map(input=><div key={input.id} className="mt-2 text-sm"><strong>{input.label}</strong>{input.properties.length?<ul className="mt-1 space-y-1">{input.properties.map(prop=><li key={prop.name} className="break-words">{prop.name} · {prop.datatype} · {prop.required?'Required':'Optional'}<p className="text-xs text-muted-foreground">{prop.description}</p></li>)}</ul>:<p className="text-xs text-muted-foreground">No direct attributes declared.</p>}</div>):<p className="mt-2 text-sm">No inputs declared.</p>}</details>
     <details><summary className="cursor-pointer text-sm">Rule evidence ({current.evidence.length})</summary>{current.evidence.map((source,index)=><div key={index} className="mt-2 rounded-lg border p-3 text-sm"><p className="font-medium">{source.title} · {source.kind.replaceAll('_',' ')}</p><blockquote className="mt-2 whitespace-pre-wrap break-words">{source.quote}</blockquote><p className="mt-2 break-all text-xs text-muted-foreground">SHA-256: {source.sha256}</p></div>)}</details>
     {(current.unknowns.length>0||current.module_questions.length>0)&&<details><summary className="cursor-pointer text-sm">Unresolved rule information</summary><ul className="mt-2 list-inside list-disc text-sm">{[...current.unknowns,...current.module_questions].map((value,index)=><li key={index}>{value}</li>)}</ul></details>}
    </article>}
   </div>}
   <section aria-label="Definition competency queries" className="min-w-0 space-y-3 border-t pt-4"><h5 className="font-semibold">Query saved definitions</h5><p className="text-sm text-muted-foreground">These queries inspect the compiled ontology. They do not query company records or classify a warranty complaint.</p>
    <div className="grid gap-3 sm:grid-cols-2"><label className="text-xs">Definition question<select className={field} value={queryId} onChange={e=>{clear();setQueryId(e.target.value);setFocus('');}}>{data.queries.map(query=><option key={query.query_id} value={query.query_id}>{query.label}</option>)}</select></label><label className="text-xs">Definition focus<select className={field} value={focus} onChange={e=>{clear();setFocus(e.target.value);}}><option value="">All matching definitions</option>{focusOptions.map(item=><option key={item.id} value={item.id}>{item.label}</option>)}</select></label></div>
    <p className="text-sm text-muted-foreground">{question?.description}</p>{question&&!question.available&&<p role="status" className="text-sm">{question.unavailable_reason}</p>}
    <button className={button} disabled={busy||!question?.available} onClick={()=>void run()}>{busy?'Running definition query…':'Run definition query'}</button>
    <ApiFeedback error={queryError} onRetry={()=>setReload(value=>value+1)} retrying={loading||busy}/>
    {result&&<div aria-label="Definition query result" className="min-w-0 space-y-3"><p className="text-sm font-medium">{result.rows.length?`${result.rows.length} ${result.rows.length===1?'row':'rows'} · Revision ${result.revision}`:'No matching definitions in this saved version.'}</p>
     {result.rows.length>0&&<div className="max-h-96 overflow-auto rounded-lg border"><table className="w-full text-left text-xs"><thead className="bg-muted"><tr>{result.columns.map(column=><th key={column} className="p-2 font-medium">{column.replaceAll('_',' ')}</th>)}</tr></thead><tbody>{result.rows.map((row,index)=><tr key={index} className="border-t">{result.columns.map(column=>{const cell=row[column];return <td key={column} className="min-w-32 max-w-72 break-words p-2 align-top">{cell?<><span>{cell.label??cell.value}</span>{cell.label&&<p className="mt-1 break-all text-muted-foreground">{cell.entity_id}</p>}</>:<span className="text-muted-foreground">Not specified</span>}</td>;})}</tr>)}</tbody></table></div>}
     <div className="flex flex-wrap gap-2"><button className={button} disabled={busy||result.offset===0} onClick={()=>void run(Math.max(0,result.offset-result.limit))}>Previous results</button><button className={button} disabled={busy||!result.has_more} onClick={()=>void run(result.next_offset??0)}>Next results</button></div>
     <details><summary className="cursor-pointer text-xs">Query provenance</summary><p className="mt-2 break-all text-xs">{result.query_version} · {result.provenance.compiler_version}<br/>Input SHA-256: {result.provenance.input_sha256}<br/>Ontology SHA-256: {result.provenance.ontology_sha256}<br/>Query SHA-256: {result.provenance.query_sha256}</p></details>
    </div>}
   </section>
   <details className="border-t pt-4"><summary className="cursor-pointer text-sm font-medium">Business questions needing mapped company data ({data.business_questions.length})</summary><p className="mt-2 text-sm text-muted-foreground">These questions cannot be answered from definition structure alone. Each still requires the following data and evidence.</p><div className="mt-3 max-h-96 space-y-3 overflow-auto">{data.business_questions.map(item=><article key={item.id} className="rounded-lg border p-3 text-sm"><p className="text-xs text-muted-foreground">{item.department} · Requires instance mapping</p><h6 className="mt-1 font-medium">{item.question}</h6><ul className="mt-2 list-inside list-disc text-muted-foreground">{item.prerequisites.map((value,index)=><li key={index}>{value}</li>)}</ul></article>)}</div><p className="mt-2 break-all text-xs text-muted-foreground">{data.question_source.title} · {data.question_source.section} · SHA-256 {data.question_source.sha256}</p></details>
  </>}
 </section>;
}
