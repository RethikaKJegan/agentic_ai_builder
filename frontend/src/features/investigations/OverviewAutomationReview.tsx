"use client";
import {useEffect,useRef,useState} from 'react';
import {api} from '@/api/client';
import {type AutomationRecord} from '@/api/orchestration';
import {type OverviewResult} from '@/api/overview-automation';
import {useBackend} from '@/api/state';
import {ConnectedPlan,actionButton} from './ConnectedPlan';
import {SavedDetails} from './LifecyclePanels';
import {ApiFeedback} from '@/features/workflows/ApiFeedback';
import {InputError} from '@/api/feedback';
import {Link} from '@/lib/navigation';

export function OverviewAutomationReview({value,onChange,compact=false,initialRunId,onRun,onAnswer}:{value:OverviewResult;onChange:(v:OverviewResult)=>void;compact?:boolean;initialRunId?:string|undefined;onRun?:(id:string)=>void;onAnswer?:(answers:Record<string,string>)=>void}) {
  const backend=useBackend();
  const [busy,setBusy]=useState(false);
  const [answers,setAnswers]=useState<Record<string,string>>({});
  const [error,setError]=useState<Error|null>(null);
  const [runId,setRunId]=useState<string>();
  const [agreed,setAgreed]=useState(false);
  const [replacements,setReplacements]=useState<AutomationRecord[]|null>(null);
  const [replacementId,setReplacementId]=useState('');
  const retryKeys=useRef<Record<string,string>>({});
  const pendingControl=useRef<{action:string;key:string}|null>(null);
  const scope=backend.session?.auth.subject;
  const matchingScope=!value.workspace||(value.workspace.workspace_id===scope?.workspace_id&&value.workspace.subject_id===scope?.subject_id);
  useEffect(()=>{setAgreed(false);setReplacements(null);setReplacementId('');retryKeys.current={};pendingControl.current=null;setError(null);},[value.request_key,scope?.workspace_id,scope?.subject_id]);
  useEffect(()=>setRunId(initialRunId),[value.request_key,initialRunId]);
  useEffect(()=>{
    if(value.state!=='planning'||!value.request_key||!matchingScope)return;
    let live=true;
    const timer=setInterval(()=>void api.overviewIntent({operation:'get',request_key:value.request_key}).then(next=>{if(live)onChange(next);}).catch(e=>{if(live)setError(e as Error);}),2000);
    return ()=>{live=false;clearInterval(timer);};
  },[value.state,value.request_key,matchingScope,onChange]);
  useEffect(()=>{
    if(!value.activation||!value.request_key||!matchingScope||busy||(value.schedule_record&&!['active','paused'].includes(value.schedule_record.state)))return;
    let live=true;
    const timer=setInterval(()=>void api.overviewIntent({operation:'get',request_key:value.request_key}).then(next=>{if(live)onChange(next);}).catch(e=>{if(live)setError(e as Error);}),10000);
    return ()=>{live=false;clearInterval(timer);};
  },[value.activation,value.request_key,value.schedule_record,matchingScope,busy,onChange]);
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
  async function editAutomation(){
    setBusy(true);setError(null);
    try{const records=await api.automationRecords();setReplacements(records.items.filter(item=>['active','paused'].includes(item.state)&&item.kind===(value.event_subscription?'subscription':'schedule')&&item.id!==value.activation?.schedule_id));}
    catch(e){setError(e as Error);}finally{setBusy(false);}
  }
  async function replaceAutomation(){
    if(!value.activation||!replacementId)return;
    if(pendingControl.current&&pendingControl.current.action!=='replace:'+replacementId){setError(new InputError('Refresh to confirm the previous control before choosing another replacement.'));return;}
    pendingControl.current??={action:'replace:'+replacementId,key:crypto.randomUUID()};
    setBusy(true);setError(null);
    try{await api.controlAutomation(value.activation.schedule_id,{request_key:pendingControl.current.key,action:'replace',replacement_id:replacementId});setReplacements(null);await refresh();}
    catch(e){setError(e as Error);}finally{setBusy(false);}
  }
  async function retryOccurrence(id:string){
    setBusy(true);setError(null);retryKeys.current[id]??=crypto.randomUUID();
    try{await api.controlAutomation(id,{request_key:retryKeys.current[id],action:'retry'});delete retryKeys.current[id];await refresh();}
    catch(e){setError(e as Error);}finally{setBusy(false);}
  }
  const schedule=value.schedule;
  const event=value.event_subscription;
  const automated=!!(schedule||event);
  return <section aria-label="Overview request review" className="mt-6 min-w-0 space-y-4 rounded-xl border p-4">
    {(!value.composition_id||compact)&&<><div className="flex flex-wrap items-center gap-3"><h2 className="font-semibold">Request review</h2><button className={actionButton} disabled={busy} onClick={()=>void refresh()}>Refresh request</button></div>
    <p className="break-words">{value.intent?.business_goal}</p></>}
    {value.state==='planning'&&<div><p role="status">Generation {value.planning_job?.state}. Your request is saved; no automation is active.</p><button className={actionButton} disabled={busy} onClick={()=>void cancelGeneration()}>Cancel generation</button></div>}
    {!!value.communication_review?.length&&<div aria-label="Email and Calendar review" className="space-y-2 rounded-lg border p-3 text-sm">{value.communication_review.map(line=><p key={line}>{line}</p>)}</div>}
    {!!value.clarifications?.length&&onAnswer&&<form className="space-y-3" aria-label="Communication choices" onSubmit={event=>{event.preventDefault();onAnswer(answers);}}>
      {value.clarifications.map(item=><label key={item.field} className="block space-y-1 text-sm"><span>{item.question}</span>{item.options.length?<select className="block w-full rounded border p-2" required value={answers[item.field]??''} onChange={event=>setAnswers({...answers,[item.field]:event.target.value})}><option value="">Choose an option</option>{item.options.map(option=><option key={option.value} value={option.value}>{option.label}</option>)}</select>:<input className="block w-full rounded border p-2" required type={item.field==='review_time'?'time':item.field==='recipient'?'email':item.field==='review_duration_minutes'?'number':'text'} value={answers[item.field]??''} onChange={event=>setAnswers({...answers,[item.field]:event.target.value})}/>}</label>)}
      {answers['review_timing']==='fixed'&&!value.clarifications.some(item=>item.field==='review_time')&&<label className="block text-sm">Review start time<input className="ml-2 rounded border p-2" type="time" required value={answers['review_time']??''} onChange={event=>setAnswers({...answers,review_time:event.target.value})}/></label>}
      <button className={actionButton} type="submit" disabled={busy}>Continue to review</button>
    </form>}
    {!value.clarifications?.length&&!!value.questions?.length&&(value['business_clarification']===true
      ?<div role="status" className="space-y-2 text-sm text-muted-foreground">{value.questions.map((question,i)=><p key={i}>{question}</p>)}<p>Update the request with the intended business meaning and generate again.</p></div>
      :<p role="status" className="text-sm text-muted-foreground">This saved request has unresolved execution requirements. Generate a new workflow to apply the current planning defaults; no additional answer is requested here.</p>)}
    {Array.isArray(value['limitations'])&&value['limitations'].filter((s):s is string=>typeof s==='string').map((s,i)=><p key={i} role="status" className="text-sm text-muted-foreground">{s}</p>)}
    {!compact&&schedule&&<div className="space-y-2 text-sm">
      <p>Proposed next run: {new Date(schedule.next_due*1000).toLocaleString(undefined,{timeZone:schedule.timezone})} ({schedule.timezone})</p>
      <p>Up to {schedule.max_occurrences} occurrences, through {new Date(schedule.expires_at*1000).toLocaleDateString()}. Missed runs: {schedule.missed_run_policy}; overlapping runs: {schedule.overlap_policy}.</p>
      <p>Requested actions: {value.intent?.side_effects.join(', ').replaceAll('_',' ')||'Read and prepare findings'}.</p>
      <SavedDetails label="Exact sources, destinations and recurring authorization" value={{query:value['query'],relative_dates:value['temporal_pin'],operations:value.operations}}/>
    </div>}
    {!compact&&event&&<div className="space-y-2 text-sm"><p>Business event: {event.source.event_type} from {event.source.source_id} ({event.source.timezone}).</p><p>Up to {event.max_occurrences} occurrences, through {new Date(event.expires_at*1000).toLocaleDateString()}. Only the configured authenticated adapter can deliver events.</p><SavedDetails label="Reviewed event authorization" value={{source:event.source,conditions:event.conditions??[],operations:value.operations}}/></div>}
    <ApiFeedback error={error}/>
    {compact&&value.state==='prepared'&&value.composition_id&&<Link to="/app/workflows/investigate" search={{connected:'1',composition:value.composition_id,overview:value.request_key}} className={actionButton}>Open workflow</Link>}
    {!compact&&value.composition_id&&<ConnectedPlan id={value.composition_id} runId={runId} onRun={id=>{setRunId(id);onRun?.(id);}} scheduled={automated}/>}
    {!compact&&automated&&!value.activation&&<div className="space-y-3">
      <p className="text-sm">Review and approve the workflow above, then authorize its recurring sources, actions and destinations.</p>
      <label className="flex items-start gap-2 text-sm"><input type="checkbox" checked={agreed} onChange={e=>setAgreed(e.currentTarget.checked)}/>I authorize this reviewed {event?'event subscription':'schedule'} and the displayed actions and destinations within its limits.</label>
      <button className={actionButton} disabled={busy||!agreed||!backend.can('workflow.approve')} onClick={()=>void activate()}>{event?'Authorize and start event subscription':'Authorize and start schedule'}</button>
    </div>}
    {!compact&&value.activation&&<div className="space-y-2 text-sm"><p role="status">{event?'Event subscription':'Schedule'} {value.schedule_record?.state??value.activation.state}.{!event&&(!value.schedule_record||value.schedule_record.state==='active')&&<> Next run: {new Date((value.schedule_record?.due??value.activation.due)*1000).toLocaleString(undefined,schedule?{timeZone:schedule.timezone}:undefined)}</>}</p>
      {(!value.schedule_record||value.schedule_record.state==='active')&&<button className={actionButton} disabled={busy} onClick={()=>void control('pause')}>Pause schedule</button>}
      {value.schedule_record?.state==='paused'&&<button className={actionButton} disabled={busy} onClick={()=>void control('resume')}>Resume schedule</button>}
      {(!value.schedule_record||['active','paused'].includes(value.schedule_record.state))&&<button className={actionButton} disabled={busy} onClick={()=>void control('cancel')}>Cancel schedule</button>}
    </div>}
    {!compact&&value.activation&&(!value.schedule_record||['active','paused'].includes(value.schedule_record.state))&&<div className="space-y-2 text-sm"><button className={actionButton} disabled={busy||!backend.can('workflow.approve')} onClick={()=>void editAutomation()}>Edit automation</button>{replacements&&<div className="space-y-2"><p>Prepare and approve an edited proposal, then select its authorized automation here to replace this definition. A paused replacement resumes when selected. Earlier executions stay attached to their reviewed version.</p><label>Reviewed replacement<select className="ml-2 max-w-full rounded border p-2" value={replacementId} disabled={busy} onChange={e=>setReplacementId(e.currentTarget.value)}><option value="">Select a reviewed automation</option>{replacements.map(item=><option key={item.id} value={item.id}>{typeof item['name']==='string'?item['name']:item.id}</option>)}</select></label>{!replacements.length&&<p>No other reviewed automation is available.</p>}<button className={actionButton} disabled={busy||!replacementId||!backend.can('workflow.approve')} onClick={()=>void replaceAutomation()}>Replace reviewed definition</button></div>}</div>}
    {!compact&&!!value.automation_history?.length&&<div className="space-y-2 text-sm"><h3 className="font-semibold">Execution history</h3>{value.automation_history.map(item=><div key={item.id} className="flex flex-wrap items-center gap-2">{item.retry_eligible&&<button className={actionButton} disabled={busy||!backend.can('workflow.execute')} onClick={()=>void retryOccurrence(item.id)}>Retry eligible execution</button>}<span>{new Date(item.due*1000).toLocaleString()} · {item.state}{item.last_error_code?' · '+item.last_error_code:''}</span>{item.run_id&&<button className={actionButton} onClick={()=>{setRunId(item.run_id!);onRun?.(item.run_id!);}}>Inspect execution</button>}</div>)}<p>To edit the objective or trigger, prepare and approve a replacement workflow. Previous executions remain in this history.</p></div>}
  </section>;
}
