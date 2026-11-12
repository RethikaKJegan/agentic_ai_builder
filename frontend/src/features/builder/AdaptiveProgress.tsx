"use client";
import { useState } from 'react';
import { api, type RunRecord } from '@/api/client';
import {type z} from 'zod';
import {adaptiveRunSchema} from '@/api/adaptive';

export function AdaptiveProgress({run,onUpdated,compact=false}:{run:Pick<RunRecord,'run_id'> & {adaptive?:z.infer<typeof adaptiveRunSchema>|undefined};onUpdated:()=>void;compact?:boolean}) {
  const [values,setValues]=useState<Record<string,string>>({});
  const [error,setError]=useState('');
  const [busy,setBusy]=useState(false);
  const adaptive=run.adaptive;
  if(!adaptive)return null;
  const assessment=adaptive.assessment;
  const wait=adaptive.pending_wait;
  async function submit() {
    if(!wait)return;
    setBusy(true);setError('');
    try {
      const supplied:Record<string,unknown>={};
      for(const request of wait.requests) {
        const raw=values[request.key]??'';
        const type=request.schema['type'];
        if(raw==='')throw new Error('Provide every requested business value.');
        supplied[request.key]=type==='boolean'?raw==='true':type==='integer'||type==='number'?Number(raw):raw;
        if(typeof supplied[request.key]==='number'&&!Number.isFinite(supplied[request.key]))throw new Error('Enter a valid number.');
      }
      await api.adaptiveInput(run.run_id,wait.wait_id,supplied);onUpdated();
    } catch(caught) {setError(caught instanceof Error?caught.message:'Business input could not be saved.');}
    finally {setBusy(false);}
  }
  return <section aria-label="Autonomous investigation progress" className="max-h-96 shrink-0 space-y-3 overflow-auto border-b p-3 text-sm">
    {!compact&&<><p className="font-medium">{adaptive.objective}</p>
    <p role="status">{adaptive.status==='waiting_for_input'?'Waiting for business input':adaptive.status==='completed'?'Objective satisfied':adaptive.status==='blocked'?'Investigation blocked':'Evaluating evidence and continuing'} · Plan revision {adaptive.revision}</p>
    {adaptive.decisions.at(-1)&&<p className="text-muted-foreground">{adaptive.decisions.at(-1)!.rationale}</p>}
    {assessment&&<>
      <ul className="space-y-1">{assessment.requirements.map(requirement=><li key={requirement.id}>{requirement.description}: {requirement.status}</li>)}</ul>
      {!!assessment.findings.length&&<details><summary>Verified source observations</summary><ul>{assessment.findings.map((finding,index)=><li key={index}>{JSON.stringify(finding.value)} · {finding.evidence_id} · {finding.classification}</li>)}</ul></details>}
      {!!assessment.calculations?.length&&<details><summary>Verified arithmetic</summary><ul>{assessment.calculations.map(calculation=><li key={calculation.id}>{calculation.id}: {calculation.result} ({calculation.operation}). Units and scope follow the cited source evidence.</li>)}</ul></details>}
      {assessment.gaps.map(gap=><p key={gap.id}>{gap.blocking?'Blocking gap: ':'Limitation: '}{gap.description}</p>)}
      {assessment.source_limitations.map((limitation,index)=><p key={index}>{limitation}</p>)}
      <details><summary>Assessment and supporting evidence</summary><pre className="overflow-auto whitespace-pre-wrap break-words text-xs">{JSON.stringify(assessment,null,2)}</pre></details>
    </>}
    {adaptive.deterministic_limitations?.map((limitation,index)=><p key={index} role="status">{limitation.code}: {typeof limitation.details==='string'?limitation.details:'Source evidence requires review.'}</p>)}
    {adaptive.blocker&&<p role="alert">{adaptive.blocker}</p>}</>}
    {wait&&<form onSubmit={event=>{event.preventDefault();void submit();}} className="space-y-3">
      {wait.requests.map(request=><label className="block space-y-1" key={request.key}><span>{request.reason}</span>{request.schema['type']==='boolean'?<select className="block rounded border bg-background p-2" required value={values[request.key]??''} onChange={event=>setValues({...values,[request.key]:event.target.value})}><option value="">Choose</option><option value="true">Yes</option><option value="false">No</option></select>:<input required className="block w-full rounded border bg-background p-2" type={['number','integer'].includes(String(request.schema['type']))?'number':'text'} step={request.schema['type']==='integer'?1:'any'} value={values[request.key]??''} onChange={event=>setValues({...values,[request.key]:event.target.value})}/>}</label>)}
      <button disabled={busy} className="rounded border px-3 py-2" type="submit">{busy?'Saving…':'Save input and resume'}</button>
      {error&&<p role="alert">{error}</p>}
    </form>}
  </section>;
}
