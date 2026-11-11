"use client";
import {useEffect,useRef,useState} from 'react';
import {api} from '@/api/client';
import {type OverviewResult} from '@/api/overview-automation';
import {useBackend} from '@/api/state';
import {ConnectedPlan,actionButton} from './ConnectedPlan';
import {SavedDetails} from './LifecyclePanels';
import {ApiFeedback} from '@/features/workflows/ApiFeedback';
import {InputError} from '@/api/feedback';
import {Link} from '@/lib/navigation';

export function OverviewAutomationReview({value,onChange,compact=false,initialRunId,onRun}:{value:OverviewResult;onChange:(v:OverviewResult)=>void;compact?:boolean;initialRunId?:string|undefined;onRun?:(id:string)=>void}) {
  const backend=useBackend();
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState<Error|null>(null);
  const [runId,setRunId]=useState<string>();
  const [agreed,setAgreed]=useState(false);
  const pendingControl=useRef<{action:string;key:string}|null>(null);
  const scope=backend.session?.auth.subject;
  const matchingScope=!value.workspace||(value.workspace.workspace_id===scope?.workspace_id&&value.workspace.subject_id===scope?.subject_id);
  useEffect(()=>{setAgreed(false);pendingControl.current=null;setError(null);},[value.request_key]);
  useEffect(()=>setRunId(initialRunId),[value.request_key,initialRunId]);
  useEffect(()=>{
    if(value.state!=='planning'||!value.request_key||!matchingScope)return;
    let live=true;
    const timer=setInterval(()=>void api.overviewIntent({operation:'get',request_key:value.request_key}).then(next=>{if(live)onChange(next);}).catch(e=>{if(live)setError(e as Error);}),2000);
    return ()=>{live=false;clearInterval(timer);};
  },[value.state,value.request_key,matchingScope,onChange]);
  if(!matchingScope)return null;
  async function refresh(){
    if(!value.request_key)return;
    setBusy(true);setError(null);
    try{onChange(await api.overviewIntent({operation:'get',request_key:value.request_key}));pendingControl.current=null;}
    catch(e){setError(e as Error);}finally{setBusy(false);}
  }
  async function activate(){
    if(!value.request_key||!agreed)return;
    setBusy(true);setError(null);
    try{
      await api.activateOverview(value.request_key);
      onChange(await api.overviewIntent({operation:'get',request_key:value.request_key}));
    }catch(e){setError(e as Error);}finally{setBusy(false);}
  }
  async function cancelGeneration(){
    if(!value.planning_job)return;
    setBusy(true);setError(null);
    try{await api.cancelPlanning(value.planning_job.job_id);onChange(await api.overviewIntent({operation:'get',request_key:value.request_key}));}
    catch(e){setError(e as Error);}finally{setBusy(false);}
  }
  async function control(action:'pause'|'resume'|'cancel'){
    if(!value.activation)return;
    if(pendingControl.current&&pendingControl.current.action!==action){setError(new InputError('Refresh the schedule to confirm the previous control before choosing another action.'));return;}
    pendingControl.current??={action,key:crypto.randomUUID()};
    setBusy(true);setError(null);
    try{
      await api.controlAutomation(value.activation.schedule_id,{request_key:pendingControl.current.key,action});
      onChange(await api.overviewIntent({operation:'get',request_key:value.request_key}));
      pendingControl.current=null;
    }catch(e){setError(e as Error);}finally{setBusy(false);}
  }
  const schedule=value.schedule;
  return <section aria-label="Overview request review" className="mt-6 min-w-0 space-y-4 rounded-xl border p-4">
    {(!value.composition_id||compact)&&<><div className="flex flex-wrap items-center gap-3"><h2 className="font-semibold">Request review</h2><button className={actionButton} disabled={busy} onClick={()=>void refresh()}>Refresh request</button></div>
    <p className="break-words">{value.intent?.business_goal}</p></>}
    {value.state==='planning'&&<div><p role="status">Generation {value.planning_job?.state}. Your request is saved; no automation is active.</p><button className={actionButton} disabled={busy} onClick={()=>void cancelGeneration()}>Cancel generation</button></div>}
    {!!value.questions?.length&&<p role="status" className="text-sm text-muted-foreground">This saved request has unresolved execution requirements. Generate a new workflow to apply the current planning defaults; no additional answer is requested here.</p>}
    {Array.isArray(value['limitations'])&&value['limitations'].filter((s):s is string=>typeof s==='string').map((s,i)=><p key={i} role="status" className="text-sm text-muted-foreground">{s}</p>)}
    {!compact&&schedule&&<div className="space-y-2 text-sm">
      <p>Proposed next run: {new Date(schedule.next_due*1000).toLocaleString(undefined,{timeZone:schedule.timezone})} ({schedule.timezone})</p>
      <p>Up to {schedule.max_occurrences} occurrences, through {new Date(schedule.expires_at*1000).toLocaleDateString()}. Missed runs: {schedule.missed_run_policy}; overlapping runs: {schedule.overlap_policy}.</p>
      <p>Requested actions: {value.intent?.side_effects.join(', ').replaceAll('_',' ')||'Read and prepare findings'}.</p>
      <SavedDetails label="Exact sources, destinations and recurring authorization" value={{query:value['query'],relative_dates:value['temporal_pin'],operations:value.operations}}/>
    </div>}
    <ApiFeedback error={error}/>
    {compact&&value.state==='prepared'&&value.composition_id&&<Link to="/app/workflows/investigate" search={{connected:'1',composition:value.composition_id,overview:value.request_key}} className={actionButton}>Open workflow</Link>}
    {!compact&&value.composition_id&&<ConnectedPlan id={value.composition_id} runId={runId} onRun={id=>{setRunId(id);onRun?.(id);}} scheduled={!!schedule}/>}
    {!compact&&schedule&&!value.activation&&<div className="space-y-3">
      <p className="text-sm">Review and approve the workflow above, then authorize its recurring sources, actions and destinations.</p>
      <label className="flex items-start gap-2 text-sm"><input type="checkbox" checked={agreed} onChange={e=>setAgreed(e.currentTarget.checked)}/>I authorize this reviewed schedule and the displayed actions and destinations within its limits.</label>
      <button className={actionButton} disabled={busy||!agreed||!backend.can('workflow.approve')} onClick={()=>void activate()}>Authorize and start schedule</button>
    </div>}
    {!compact&&value.activation&&<div className="space-y-2 text-sm"><p role="status">Schedule {value.schedule_record?.state??value.activation.state}.{(!value.schedule_record||value.schedule_record.state==='active')&&<> Next run: {new Date((value.schedule_record?.due??value.activation.due)*1000).toLocaleString(undefined,schedule?{timeZone:schedule.timezone}:undefined)}</>}</p>
      {(!value.schedule_record||value.schedule_record.state==='active')&&<button className={actionButton} disabled={busy} onClick={()=>void control('pause')}>Pause schedule</button>}
      {value.schedule_record?.state==='paused'&&<button className={actionButton} disabled={busy} onClick={()=>void control('resume')}>Resume schedule</button>}
      {(!value.schedule_record||['active','paused'].includes(value.schedule_record.state))&&<button className={actionButton} disabled={busy} onClick={()=>void control('cancel')}>Cancel schedule</button>}
    </div>}
  </section>;
}
