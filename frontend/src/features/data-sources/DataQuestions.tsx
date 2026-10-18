"use client";
import { displayText } from "@/lib/display-text";

import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/api/client";
import type { PlannedQuery, QueryResult, QueryJob } from "@/api/data-queries";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";
import SelectedSources from "./SelectedSources";

const button="rounded-lg border px-4 py-2 text-sm font-medium disabled:opacity-40";
const asError=(value:unknown)=>value instanceof Error?value:new Error("The data question could not be completed.");

function readableExpression(text:string,labels:Record<string,string>) {
  return text.replace(/\bmeta_[a-f0-9]+\b/g,id=>labels[id]??id);
}

export default function DataQuestions({canManage}:{canManage:boolean}) {
  const [status,setStatus]=useState<Awaited<ReturnType<typeof api.dataQueryStatus>>>();
  const [question,setQuestion]=useState("");
  const [planned,setPlanned]=useState<PlannedQuery>();
  const [result,setResult]=useState<QueryResult>();
  const [error,setError]=useState<Error>();
  const [busy,setBusy]=useState<"plan"|"execute">();
  const [job,setJob]=useState<QueryJob>();
  const [recent,setRecent]=useState<QueryJob[]>([]);
  const [pollVersion,setPollVersion]=useState(0);
  const [pollPaused,setPollPaused]=useState(false);
  const [cancelling,setCancelling]=useState(false);
  const [elapsed,setElapsed]=useState(0);
  const submission=useRef<{planId:string,key:string}|undefined>(undefined);
  const interaction=useRef(0);
  const lock=useRef(false);
  const active=useRef(true);
  useEffect(()=>{active.current=true;void api.dataQueryStatus().then(value=>{if(active.current)setStatus(value);}).catch(e=>{if(active.current)setError(asError(e));});return()=>{active.current=false;};},[]);
  const jobsAvailable=!!status?.jobs_available;
  const jobActive=!!job&&!['succeeded','failed','cancelled'].includes(job.state);
  useEffect(()=>{
    if(!jobsAvailable||!canManage)return;
    let alive=true;const version=interaction.current;
    void api.dataQueryJobs().then(value=>{
      if(!alive)return;
      setRecent(value.items);
      const recovered=value.items.find(item=>!['succeeded','failed','cancelled'].includes(item.state))??value.items[0];
      if(recovered&&interaction.current===version){setJob(recovered);setPlanned(recovered.planned_query);setQuestion(recovered.planned_query.question);setResult(undefined);}
    }).catch(e=>{if(alive)setError(asError(e));});
    return()=>{alive=false;};
  },[jobsAvailable,canManage]);
  const jobId=job?.job_id;
  useEffect(()=>{
    if(!jobId||!jobsAvailable)return;
    let alive=true;let timer:ReturnType<typeof setTimeout>;
    setPollPaused(false);
    async function poll(){
      try{
        const value=await api.dataQueryJob(jobId!);
        if(!alive)return;
        setJob(value);setError(undefined);setRecent(items=>[value,...items.filter(item=>item.job_id!==value.job_id)].slice(0,20));
        if(!['succeeded','failed','cancelled'].includes(value.state)){timer=setTimeout(()=>void poll(),1000);return;}
        if(value.state==='failed'){setError(new ApiError({error_code:value.error?.code??'DATA_QUERY_JOB_FAILED',message:value.error?.message??'Query failed without results.',request_id:value.job_id,retryable:false}));return;}
        if(value.state==='succeeded'&&value.result_available){
          const completed=await api.dataQueryJobResult(value.job_id);
          if(alive&&value.result_expires_at&&value.result_expires_at*1000>Date.now())setResult(completed);
        }
      }catch(e){if(alive){setError(asError(e));setPollPaused(true);}}
    }
    void poll();
    return()=>{alive=false;clearTimeout(timer);};
  },[jobId,jobsAvailable,pollVersion]);
  const jobCreated=job?.created_at;
  useEffect(()=>{
    if(jobCreated===undefined)return;
    const update=()=>setElapsed(Math.max(0,Math.floor(Date.now()/1000-jobCreated)));
    update();
    if(!jobActive)return;
    const timer=setInterval(update,1000);return()=>clearInterval(timer);
  },[jobCreated,jobActive]);
  const resultExpiry=job?.result_expires_at;
  useEffect(()=>{
    if(!jobId||!resultExpiry)return;
    const expire=()=>{setResult(undefined);setJob(value=>value?.job_id===jobId?{...value,result_available:false}:value);};
    const remaining=resultExpiry*1000-Date.now();
    if(remaining<=0){expire();return;}
    const timer=setTimeout(expire,remaining);return()=>clearTimeout(timer);
  },[jobId,resultExpiry]);
  async function cancelJob(){
    if(!job||cancelling)return;
    setCancelling(true);
    try{const value=await api.cancelDataQueryJob(job.job_id);if(active.current){setJob(value);setPollVersion(v=>v+1);}}
    catch(e){if(active.current)setError(asError(e));}
    finally{if(active.current)setCancelling(false);}
  }
  function openJob(value:QueryJob){interaction.current++;setJob(value);setPlanned(value.planned_query);setQuestion(value.planned_query.question);setResult(undefined);setError(undefined);setPollVersion(v=>v+1);}
  async function run(execute:boolean) {
    if(lock.current||jobActive)return;
    interaction.current++;lock.current=true;setBusy(execute?"execute":"plan");setError(undefined);setResult(undefined);
    if(!execute){setPlanned(undefined);setJob(undefined);submission.current=undefined;}
    try {
      if(execute&&planned){
        if(jobsAvailable){
          if(submission.current?.planId!==planned.plan_id)submission.current={planId:planned.plan_id,key:crypto.randomUUID()};
          const value=await api.submitDataQueryJob(planned.plan_id,submission.current.key);
          if(active.current){setJob(value);setPollVersion(v=>v+1);submission.current=undefined;}
        }else{const value=await api.executeDataQuestion(planned.plan_id);if(active.current)setResult(value);}
      }
      else {const value=await api.planDataQuestion(question);if(active.current)setPlanned(value);}
    } catch(e) {if(active.current)setError(asError(e));}
    finally {lock.current=false;if(active.current)setBusy(undefined);}
  }
  const plan=planned?.plan;
  const field=(id:string)=>planned?.field_labels[id]??id;
  return <section aria-label="Data questions" className="space-y-5">
    <div><h2 className="text-xl font-semibold">Ask your data</h2><p className="mt-2 max-w-3xl text-sm text-muted-foreground">Ask a specific question, review the proposed calculation, then run a read-only query. Results come from your connected databases.</p></div>
    <p className="rounded-xl border bg-muted/30 p-3 text-xs text-muted-foreground">Supported queries run in your database, checking up to 1,000,000 rows per dataset. Federated aggregates combine database calculations with dimensions and intermediates of up to 5,000 rows each. Other plans use bounded application reads of up to 5,000 rows per dataset. Four datasets and 2 MB transferred apply. {jobsAvailable?`Background jobs have up to ${status?.job_timeout_seconds??180} seconds from submission; complete results are stored encrypted for 15 minutes.`:"Synchronous queries have a 45-second execution window."} Exceeded limits stop without partial totals. Build current relationships first.</p>
    {status&&!status.configured&&<p role="status" className="rounded-xl border p-3 text-sm">The server model is not configured for data questions.</p>}
    {!canManage&&<p role="status" className="text-sm text-muted-foreground">Planning and querying require database management permission.</p>}
    <form onSubmit={e=>{e.preventDefault();void run(false);}} className="space-y-3">
      <label className="block text-sm font-medium">Your data question<textarea value={question} onChange={e=>{interaction.current++;setQuestion(e.target.value);setPlanned(undefined);setResult(undefined);setError(undefined);setJob(undefined);submission.current=undefined;}} maxLength={2000} rows={3} disabled={!!busy||jobActive} placeholder="Count all orders. Or calculate discounted line-item sales by product category, excluding freight." className="mt-2 w-full rounded-xl border bg-background p-3 text-sm"/></label>
      <button className={`${button} bg-primary text-primary-foreground`} disabled={!canManage||!status?.configured||!question.trim()||!!busy||jobActive}>{busy==="plan"?"Planning…":"Create query plan"}</button>
    </form>
    <ApiFeedback error={error}/>
    {planned&&plan&&<article className="space-y-4 rounded-2xl border p-4 md:p-5" aria-label="Query plan">
      <h3 className="font-semibold">{plan.clarification?"More detail needed":"Review query plan"}</h3>
      {plan.clarification?<p role="status" className="text-sm">{plan.clarification}</p>:<>
        <p className="whitespace-pre-wrap text-sm">{plan.explanation}</p>
        {planned.selection_preview && <SelectedSources key={planned.plan_id} preview={planned.selection_preview}/>}
        {planned.physical_plan&&<div aria-label="Execution plan" className="space-y-1 rounded-lg bg-muted/30 p-3 text-xs text-muted-foreground"><p className="font-medium text-foreground">{displayText(planned.physical_plan.strategy==="application"?"Application execution":planned.physical_plan.strategy==="federated"?"Federated execution":"Database execution")} · {planned.physical_plan.strategy}</p><p>{displayText(planned.physical_plan.reason)}</p><p>{planned.physical_plan.operations.join(" → ")}</p><p>Up to {planned.physical_plan.max_source_rows.toLocaleString()} source rows per dataset · {planned.physical_plan.snapshot}</p></div>}
        <div className="space-y-2 break-words text-xs text-muted-foreground">
          <p>Start from: {displayText(planned.dataset_labels[plan.base_dataset_id])}</p>
          {plan.joins.map(j=><p key={j.relationship_id}>Join: {displayText(planned.dataset_labels[j.target_dataset_id])} · target keys must be unique; every source key must match.</p>)}
          {!!plan.fields.length&&<p>Columns: {plan.fields.map(field).join(", ")}</p>}
          {!!plan.group_by.length&&<p>Group by: {plan.group_by.map(field).join(", ")}</p>}
          {plan.metrics.map(m=><p key={m.label}>{displayText(m.label)} = {m.op}({displayText(m.expression?readableExpression(m.expression,planned.field_labels):"rows")})</p>)}
          {plan.filters.map((f,i)=><p key={i}>Filter: {field(f.field_id)} {f.op} {displayText(JSON.stringify(f.value))}</p>)}
          {!!plan.order_by.length&&<p>Sort: {plan.order_by.map(s=>`${field(s.column)} ${s.direction}`).join(", ")}</p>}
          <p>Return up to {plan.limit} rows · graph revision {planned.graph_revision} · plan expires {new Date(planned.expires_at*1000).toLocaleTimeString()}</p>
        </div>
        <details className="rounded-lg border p-3 text-xs"><summary className="cursor-pointer font-medium">Validated logical read plan</summary><p className="mt-2 text-muted-foreground">Structured intent before execution. Actual reads and checks appear with the results.</p><pre className="mt-2 max-h-80 overflow-auto whitespace-pre-wrap break-all">{displayText(JSON.stringify(plan,null,2))}</pre></details>
        <p className="text-xs text-muted-foreground">Planning uses metadata only. Running reads the selected fields; row values and results are not sent to the planning model. {jobsAvailable?"Complete results are encrypted for 15 minutes; job and plan metadata remain for up to 24 hours.":"Results are not saved in query history."}</p>
        <button type="button" className={`${button} bg-primary text-primary-foreground`} disabled={!canManage||!!busy||jobActive} onClick={()=>void run(true)}>{busy==="execute"?"Reading and checking…":"Run read-only query"}</button>
      </>}
    </article>}
    {job&&<article aria-label="Query job" className="space-y-3 rounded-2xl border p-4">
      <h3 className="font-semibold">Query job · {job.state.replaceAll('_',' ')}</h3>
      <p role="status" className="text-sm">{job.progress.stage}</p>
      <p className="text-xs text-muted-foreground">{jobActive?`${elapsed} seconds elapsed · `:""}Attempt {job.attempt} · {job.progress.completed_fragments} completed fragments · {job.progress.transferred_rows.toLocaleString()} intermediate rows transferred</p>
      {jobActive&&<button type="button" className={button} disabled={cancelling||job.state==='cancel_requested'} onClick={()=>void cancelJob()}>{cancelling||job.state==='cancel_requested'?"Stopping…":"Cancel query"}</button>}
      {pollPaused&&<button type="button" className={button} onClick={()=>setPollVersion(v=>v+1)}>Retry job status</button>}
      {job.state==='succeeded'&&!job.result_available&&<p className="text-sm">The temporary result expired. Create a fresh plan to run it again.</p>}
      {job.result_available&&job.result_expires_at&&<p className="text-xs text-muted-foreground">Result expires {new Date(job.result_expires_at*1000).toLocaleTimeString()}.</p>}
    </article>}
    {!!recent.length&&<details className="rounded-lg border p-3"><summary className="cursor-pointer text-sm font-medium">Recent query jobs</summary><div className="mt-3 flex flex-col gap-2">{recent.map(item=><button type="button" key={item.job_id} disabled={!!busy||jobActive} className="rounded-lg border p-3 text-left text-xs disabled:opacity-40" onClick={()=>openJob(item)}>{item.planned_query.question} · {item.state.replaceAll('_',' ')} · {new Date(item.created_at*1000).toLocaleString()}</button>)}</div></details>}
    {result&&<article aria-label="Query results" className="min-w-0 space-y-4 rounded-2xl border p-4 md:p-5">
      <div><h3 className="font-semibold">Query results</h3><p role="status" className="mt-1 text-sm text-muted-foreground">{result.rows.length} of {result.total_result_rows} result rows · {result.matched_rows} source rows after filtering</p></div>
      {result.limited&&<p className="rounded-lg border p-3 text-sm">Showing the requested first {result.rows.length} rows. Aggregates include all matching rows within the execution budget.</p>}
      {result.execution&&<p aria-label="Execution evidence" className="text-xs text-muted-foreground">{result.execution.strategy} · {result.execution.duration_ms.toLocaleString()} ms · {result.execution.transferred_rows.toLocaleString()} rows transferred · {result.execution.transferred_bytes.toLocaleString()} bytes · {result.execution.snapshot}</p>}
      {result.executed_plan&&<details aria-label="Executed logical query" className="rounded-lg border p-3 text-xs"><summary className="cursor-pointer font-medium">Executed logical read plan</summary><p className="mt-2 text-muted-foreground">Server-returned plan used for this completed result. Database strategy, source reads and join checks are reported separately; this is not native SQL or a MongoDB pipeline dump.</p><pre className="mt-2 max-h-80 overflow-auto whitespace-pre-wrap break-all">{displayText(JSON.stringify(result.executed_plan,null,2))}</pre></details>}
      {!!result.execution?.fragments?.length&&<details aria-label="Database fragments" className="rounded-lg border p-3" open><summary className="cursor-pointer text-sm font-medium">Database fragments</summary><div className="mt-3 space-y-3 break-words text-xs text-muted-foreground">{result.execution.fragments.map((fragment,index)=><div key={index}><p className="font-medium text-foreground">{fragment.engine} · {fragment.purpose}</p><p>{fragment.dataset_ids.map(id=>planned?.dataset_labels[id]??id).join(", ")}</p><p>{fragment.source_rows.toLocaleString()} source rows checked · {fragment.transferred_rows.toLocaleString()} intermediate rows transferred · {fragment.transferred_bytes.toLocaleString()} bytes · {fragment.duration_ms.toLocaleString()} ms</p><p>{fragment.snapshot} · {new Date(fragment.started_at).toLocaleString()} → {new Date(fragment.finished_at).toLocaleString()}</p></div>)}</div></details>}
      <div className="max-h-[500px] overflow-auto rounded-lg border"><table className="w-full text-left text-sm"><thead><tr className="border-b bg-muted/40">{result.columns.map(c=><th key={c.key} className="whitespace-nowrap p-3 font-medium">{displayText(c.label)}</th>)}</tr></thead><tbody>{result.rows.map((row,i)=><tr key={i} className="border-b last:border-0">{result.columns.map(c=><td key={c.key} className="max-w-sm break-words p-3">{row[c.key]===null?"NULL":String(row[c.key])}</td>)}</tr>)}</tbody></table></div>
      {!result.rows.length&&<p className="text-sm text-muted-foreground">No rows matched this query.</p>}
      <details className="rounded-lg border p-3" open><summary className="cursor-pointer text-sm font-medium">Sources and checks</summary><div className="mt-3 space-y-2 text-xs text-muted-foreground">{result.sources.map(s=><p key={s.dataset_id}>{displayText(s.label)} · metadata revision {s.metadata_revision} · {s.rows_read} source rows checked · {new Date(s.started_at).toLocaleString()} → {new Date(s.finished_at).toLocaleString()}</p>)}{result.join_checks.map(j=><p key={j.relationship_id}>Join checked: {j.matched_rows}/{j.source_rows} source rows matched; {j.target_rows} target rows with unique, non-null keys.</p>)}{result.warnings.map(w=><p key={w}>{w}</p>)}</div></details>
    </article>}
  </section>;
}
