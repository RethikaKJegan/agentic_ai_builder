"use client";
import {useEffect,useRef,useState} from 'react';
import {api} from '@/api/client';
import type {BusinessModuleCoverage,BusinessOntologyState} from '@/api/business-ontology';
import {ApiFeedback} from '@/features/workflows/ApiFeedback';
export default function BusinessModuleCoveragePanel({versionId,canManage,onData}:{versionId:string;canManage:boolean;onData?:((data:BusinessOntologyState)=>void)|undefined}){
 const [coverage,setCoverage]=useState<BusinessModuleCoverage>(),[error,setError]=useState<Error>(),[busy,setBusy]=useState(false),[reload,setReload]=useState(0);
 const mounted=useRef(false),key=useRef('');
 useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;};},[]);
 useEffect(()=>{let active=true;setCoverage(undefined);setError(undefined);void api.businessModuleCoverage(versionId).then(value=>{if(active)setCoverage(value);}).catch(e=>{if(active)setError(e instanceof Error?e:new Error('Module coverage unavailable.'));});return()=>{active=false;};},[versionId,reload]);
 async function add(){if(!coverage||busy)return;setBusy(true);setError(undefined);key.current||=crypto.randomUUID();try{const result=await api.addBusinessReferenceModules({expected_revision:coverage.revision,request_key:key.current});if(mounted.current){key.current='';onData?.(result.state);setReload(v=>v+1);}}catch(e){if(mounted.current)setError(e instanceof Error?e:new Error('Reference import unavailable.'));}finally{if(mounted.current)setBusy(false);}}
 return <section aria-label="Business module coverage" className="space-y-3 rounded-xl border p-4"><h4 className="font-semibold">Module coverage</h4><p className="text-xs text-muted-foreground">Reference drafts use quotations from your supplied blueprint. Existing module definitions are preserved. Draft coverage does not establish policy completeness.</p><ApiFeedback error={error} onRetry={()=>setReload(v=>v+1)}/>
 {!coverage&&!error&&<p role="status" className="text-sm">Loading module coverage…</p>}
 {coverage&&<><p className="text-sm">{coverage.modules.length-coverage.missing_modules.length} of {coverage.modules.length} modules contain drafts.</p><div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">{coverage.modules.map(m=><details key={m.module_id} className="min-w-0 rounded-lg border p-3"><summary className="cursor-pointer text-sm">{m.label} · {m.status==='draft_available'?'Draft available':'Not started'}</summary><p className="mt-2 text-xs">{m.counts['concepts']??0} concepts · {m.counts['relationships']??0} relationships · {m.counts['rules']??0} candidate rules</p><p className="mt-2 text-xs text-muted-foreground">{m.curated_concepts} reference concepts · {m.source_documents} cited source documents</p><ul className="mt-2 list-inside list-disc text-xs">{m.questions.map((q,i)=><li key={i}>{q}</li>)}</ul></details>)}</div>
 {coverage.unavailable_reason&&<p className="text-xs text-muted-foreground">{coverage.unavailable_reason}</p>}
 {canManage&&onData&&<button className="rounded-lg border px-3 py-2 text-sm" disabled={busy||!coverage.import_available} onClick={()=>void add()}>{busy?'Saving reference drafts…':'Add missing reference drafts'}</button>}
 <p className="text-xs text-muted-foreground">This action saves a new local version and makes no model calls. Warranty decisions, root causes and improvement effectiveness remain evidence dependent.</p></>}
 </section>;
}
