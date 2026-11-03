"use client";

import {useEffect,useRef,useState} from 'react';
import {api} from '@/api/client';
import type {BusinessCompilation} from '@/api/business-ontology';
import {ApiFeedback} from '@/features/workflows/ApiFeedback';

const button='rounded-lg border px-3 py-2 text-sm disabled:opacity-40';
const artifactLabels:Record<string,string>={
 'ontology.ttl':'Ontology (Turtle)', 'ontology.rdf':'Ontology (RDF/XML)',
 'instance-shapes.ttl':'Instance shapes', 'definition-shapes.ttl':'Definition shapes',
 'validation-report.ttl':'SHACL report', 'validation-report.json':'Validation report (JSON)',
};
const checkLabels:Record<string,string>={snapshot:'Draft structure',rdf_syntax:'RDF syntax',shapes_meta_shacl:'Shape definitions',definition_shacl:'Ontology constraints'};
const asError=(e:unknown)=>e instanceof Error?e:new Error('Compilation is unavailable.');
export default function BusinessCompilationPanel({versionId,revision,kind,canManage,onCompiled}:{versionId:string;revision:number;kind:'foundation'|'draft';canManage:boolean;onCompiled?:()=>void}){
 const [compilation,setCompilation]=useState<BusinessCompilation>(null),[loading,setLoading]=useState(true),[busy,setBusy]=useState(false),[error,setError]=useState<Error>();
 const mounted=useRef(false),locked=useRef(false);
 const current=useRef(0);
 useEffect(()=>{
  mounted.current=true;const request=++current.current;
  setCompilation(null);setError(undefined);setLoading(true);
  void api.businessCompilation(versionId).then(result=>{if(mounted.current&&request===current.current)setCompilation(result.compilation);}).catch(e=>{if(mounted.current&&request===current.current)setError(asError(e));}).finally(()=>{if(mounted.current&&request===current.current)setLoading(false);});
  return()=>{mounted.current=false;};
 },[versionId]);
 async function load(){
  const request=++current.current;setLoading(true);setError(undefined);
  try{const result=await api.businessCompilation(versionId);if(mounted.current&&request===current.current)setCompilation(result.compilation);}
  catch(e){if(mounted.current&&request===current.current)setError(asError(e));}
  finally{if(mounted.current&&request===current.current)setLoading(false);}
 }
 async function compile(){
  if(locked.current)return;locked.current=true;setBusy(true);setError(undefined);const request=++current.current;
  try{const result=await api.compileBusinessVersion(versionId);if(mounted.current&&request===current.current){setCompilation(result.compilation);onCompiled?.();}}
  catch(e){if(mounted.current&&request===current.current)setError(asError(e));}
  finally{locked.current=false;if(mounted.current&&request===current.current)setBusy(false);}
 }
 function download(artifact:NonNullable<BusinessCompilation>['artifacts'][number]){
  const url=URL.createObjectURL(new Blob([artifact.content],{type:artifact.media_type}));
  const link=document.createElement('a');link.href=url;link.download=`simpson-revision-${revision}-${artifact.name}`;
  document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
 }
 const report=compilation?.report;
 return <section aria-label="Ontology compilation" className="min-w-0 space-y-3 rounded-xl border bg-muted/20 p-4">
  <div className="flex flex-wrap items-center justify-between gap-3"><h4 className="font-semibold">Ontology validation & exports</h4>
   {canManage&&kind==='draft'&&!compilation&&<button className={button} disabled={loading||busy} onClick={()=>void compile()}>{busy?'Compiling version…':'Compile & validate version'}</button>}
  </div>
  <ApiFeedback error={error} onRetry={load} retrying={loading||busy}/>
  {loading&&<p role="status" className="text-sm">Loading saved validation…</p>}
  {!loading&&!compilation&&!error&&<p className="text-sm text-muted-foreground">{kind==='foundation'?'Generate a module draft before compiling this version.':canManage?'This version has not been compiled. Compile it to create RDF/OWL and SHACL exports.':'This version has not been compiled. A workspace manager can compile it.'}</p>}
  {compilation&&report&&<>
   <p role="status" className="text-sm font-medium">{report.status==='passed'?'Definition validation passed':'Definition validation failed'} · Revision {report.revision}</p>
   <p className="text-sm text-muted-foreground">This compilation validates definitions only. Business policy remains unverified. Check the rule catalogue for execution availability, then select a saved source graph to run supported rules.</p>
   <dl className="grid gap-2 text-xs sm:grid-cols-2">{Object.entries(report.checks).map(([name,result])=><div key={name} className="flex gap-2"><dt>{checkLabels[name]??name.replaceAll('_',' ')}</dt><dd className="font-medium">{result}</dd></div>)}</dl>
   {report.issues.length>0&&<ul aria-label="Validation issues" className="space-y-2 text-sm">{report.issues.map((issue,index)=><li key={index} className="break-words"><strong>{issue.message}</strong><p className="break-all text-xs text-muted-foreground">{issue.focus} {issue.path}</p></li>)}</ul>}
   <details><summary className="cursor-pointer text-sm">Unresolved information and mapping limits ({report.warnings.length})</summary>{report.warnings.length?<ul className="mt-2 max-h-64 space-y-2 overflow-auto text-sm">{report.warnings.map((warning,index)=><li key={index} className="break-words"><span className="text-xs text-muted-foreground">{warning.focus} · </span>{warning.message}</li>)}</ul>:<p className="mt-2 text-sm text-muted-foreground">No mapping warnings were recorded. Policy completeness has not been established.</p>}</details>
   <div role="group" aria-label="Ontology downloads" className="flex flex-wrap gap-2">{compilation.artifacts.map(artifact=><button key={artifact.name} className={button} onClick={()=>download(artifact)}>Download {artifactLabels[artifact.name]??artifact.name}</button>)}</div>
   <details><summary className="cursor-pointer text-xs text-muted-foreground">Compilation provenance and file hashes</summary><p className="mt-2 break-all text-xs">{compilation.compiler_version} · {compilation.compiled_at}<br/>Input SHA-256: {compilation.input_sha256}</p><ul className="mt-2 space-y-1 text-xs">{compilation.artifacts.map(artifact=><li key={artifact.name} className="break-all">{artifact.name}: {artifact.sha256}</li>)}</ul></details>
  </>}
 </section>;
}
