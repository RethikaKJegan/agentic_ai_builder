"use client";
import {useEffect,useState} from 'react';
import {api} from '@/api/client';
import {type OverviewResult} from '@/api/overview-automation';
import {useBackend} from '@/api/state';
import {InputError} from '@/api/feedback';
import {ApiFeedback} from '@/features/workflows/ApiFeedback';
import {OverviewAutomationReview} from './OverviewAutomationReview';

export function OverviewWorkflowReview({requestKey,compositionId,runId,onRun}:{requestKey:string;compositionId:string;runId?:string|undefined;onRun:(id:string)=>void}) {
  const scope=useBackend().session?.auth.subject;
  const workspace=scope?.workspace_id;const owner=scope?.subject_id;
  const [value,setValue]=useState<OverviewResult|null>(null);
  const [error,setError]=useState<Error|null>(null);
  const [attempt,setAttempt]=useState(0);
  useEffect(()=>{
    let live=true;setValue(null);setError(null);
    if(workspace&&owner)void api.overviewIntent({operation:'get',request_key:requestKey}).then(next=>{
      if(!live)return;
      if(next.request_key!==requestKey||next.composition_id!==compositionId||next.state!=='prepared'
        ||next.workspace?.workspace_id!==workspace||next.workspace?.subject_id!==owner) {
        setError(new InputError('This saved request does not match the workflow and current workspace. Open the workflow from its original account.'));return;
      }
      setValue(next);
    }).catch(e=>{if(live)setError(e instanceof Error?e:new InputError('Could not load the saved workflow review.'));});
    return ()=>{live=false;};
  },[requestKey,compositionId,workspace,owner,attempt]);
  return <>
    <ApiFeedback error={error}/>
    {error&&<button className="rounded-lg border px-3 py-2 text-sm" onClick={()=>setAttempt(n=>n+1)}>Retry loading workflow</button>}
    {!value&&!error&&<p role="status">Loading workflow details…</p>}
    {value&&<OverviewAutomationReview value={value} onChange={setValue} initialRunId={runId} onRun={onRun}/>}
  </>;
}
