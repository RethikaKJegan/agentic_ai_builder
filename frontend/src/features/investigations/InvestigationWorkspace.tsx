'use client';
import {useEffect,useRef,useState} from 'react';
import {useRouter,useSearchParams} from 'next/navigation';
import {ArrowLeft,BookOpen,FileText,GitBranch,Loader2,Play,RefreshCw,Square} from 'lucide-react';
import {api} from '@/api/client';
import {InputError} from '@/api/feedback';
import {useBackend} from '@/api/state';
import {canResumeInvestigation,nodeLabel,stateLabels,type InvestigationPlan,type InvestigationRun,type InvestigationJob} from '@/api/investigations';
import {ApiFeedback} from '@/features/workflows/ApiFeedback';
import {InvestigationCanvas} from './InvestigationCanvas';
import {getReport,InvestigationReportView,InvestigationEvidence,InvestigationNodePanel} from './InvestigationPanels';
import {Link} from '@/lib/navigation';
import DynamicInvestigationWorkspace from './DynamicInvestigationWorkspace';

export default function InvestigationWorkspace() {
 const search=useSearchParams();
 return search.has('composition')||search.get('dynamic')==='1'?<DynamicInvestigationWorkspace/>:<LegacyInvestigationWorkspace/>;
}
function LegacyInvestigationWorkspace() {
 const search=useSearchParams();const router=useRouter();const workflowId=search.get('workflow');const runId=search.get('run');const jobId=search.get('job');
 const [plan,setPlan]=useState<InvestigationPlan|null>(null);const [run,setRun]=useState<InvestigationRun|null>(null);const [job,setJob]=useState<InvestigationJob|null>(null);
 const [error,setError]=useState<Error|null>(null);const [attempt,setAttempt]=useState(0);const [busy,setBusy]=useState(false);const [view,setView]=useState<'canvas'|'steps'|'report'>('canvas');
 const [selected,setSelected]=useState<string|null>(null);const [evidence,setEvidence]=useState(false);const [identifier,setIdentifier]=useState('');const [identifierType,setIdentifierType]=useState('complaint_id');const [notes,setNotes]=useState('');const [ack,setAck]=useState(false);
 const keys=useRef<Record<string,string>>({});const locked=useRef(false);const canRun=useBackend(s=>s.can('workflow.execute'));const status=useBackend(s=>s.status);
 const key=(slot:string)=>keys.current[slot]??(keys.current[slot]=crypto.randomUUID());
 function location(w:string|null,r:string|null,j:string|null) {const q=new URLSearchParams();if(w)q.set('workflow',w);if(r)q.set('run',r);if(j)q.set('job',j);router.replace('/app/workflows/investigate?'+q.toString());}
 useEffect(()=>{
  let active=true;let timer:ReturnType<typeof setTimeout>|undefined;
  if(status!=='connected')return;
  const refresh=async()=>{
   try {
    let currentJob:InvestigationJob|null=null;
    if(jobId){currentJob=await api.investigationJob(jobId);if(!active)return;setJob(currentJob);if(currentJob.state==='failed')setError(new InputError(currentJob.error?.message??'Investigation job failed. Inspect the saved run before retrying.'));}
    const w=workflowId??currentJob?.workflow_id??null;const r=runId??currentJob?.run_id??null;
    if(w){const p=await api.investigationPlan(w);if(!active)return;setPlan(p);}
    let currentRun:InvestigationRun|null=null;
    if(r){currentRun=await api.investigationRun(r);if(!active)return;setRun(currentRun);}
    if(active&&((!workflowId&&w)||(!runId&&r))){location(w,r,jobId);return;}
    if(active&&((currentJob&&['queued','running'].includes(currentJob.state))||currentRun?.status==='running'))timer=setTimeout(()=>void refresh(),1500);
   } catch(caught){if(active){setError(caught instanceof Error?caught:new Error('Could not refresh the investigation.'));setRun(null);}}
  };
  void refresh();return()=>{active=false;if(timer)clearTimeout(timer);};
 // URL identifiers are the persisted recovery authority; polling never submits work.
 // eslint-disable-next-line react-hooks/exhaustive-deps
 },[workflowId,runId,jobId,attempt,status]);
 async function action(work:()=>Promise<void>) {if(locked.current)return;locked.current=true;setBusy(true);setError(null);try{await work();}catch(caught){setError(caught instanceof Error?caught:new Error('The action could not be confirmed. Refresh its saved state before retrying.'));}finally{locked.current=false;setBusy(false);}}
 async function execute(resume=false,restart=false) {
  if(!plan)return;
  await action(async()=>{let current=restart?null:run;
   if(!current){current=await api.createInvestigationRun(plan.workflow_id,key(restart?'new-run:'+run?.run_id:'create-run'));setRun(current);}
   const job=await api.submitInvestigation(resume?'resume':'execute',{run_id:current.run_id},key((resume?'resume:':'execute:')+current.run_id+':'+current.updated_at));
   setJob(job);location(plan.workflow_id,current.run_id,job.job_id);setAttempt(n=>n+1);
  });
 }
 const working=busy||!!job&&['queued','running'].includes(job.state)||run?.status==='running';const report=getReport(run);
 const pending=run?.pending_inputs[0];
 const completed=Object.values(run?.node_states??{}).filter(s=>s==='succeeded').length;
 const skipped=Object.values(run?.node_states??{}).filter(s=>s==='skipped').length;
 return <div className="flex h-full min-h-0 flex-col bg-background">
  <header className="shrink-0 border-b border-border p-4 md:px-6"><div className="flex flex-wrap items-center gap-3"><Link to="/app/workflows" className="rounded-lg border p-2" aria-label="Back to workflows"><ArrowLeft className="h-4 w-4"/></Link><div className="min-w-0 flex-1"><h1 className="font-display text-lg font-semibold">Business investigation</h1><p className="text-xs text-muted-foreground">{plan?`${plan.graph.nodes.length} steps · ${run?stateLabels[run.status]??run.status:'Ready to run'}`:'Building your workflow'}</p></div>{plan&&<div className="flex flex-wrap gap-2"><button className="inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm" onClick={()=>setEvidence(true)}><BookOpen className="h-4 w-4"/>Ontology evidence</button><button disabled={!report} className="inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm disabled:opacity-40" onClick={()=>setView('report')}><FileText className="h-4 w-4"/>View report</button>{(!run||run.status==='queued')&&<button disabled={working||!canRun} onClick={()=>void execute()} className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-40"><Play className="h-4 w-4"/>Run investigation</button>}{(run?.status==='failed'&&canResumeInvestigation(plan,run)||job?.state==='failed'&&run?.status==='running')&&<button disabled={busy||!canRun} onClick={()=>void execute(true)} className="rounded-lg border px-3 py-2 text-sm disabled:opacity-40">Resume eligible work</button>}{run?.status==='failed'&&!canResumeInvestigation(plan,run)&&<button disabled={busy||!canRun} onClick={()=>void execute(false,true)} className="rounded-lg border px-3 py-2 text-sm disabled:opacity-40">Start new run</button>}{run&&['running','queued','waiting_for_input'].includes(run.status)&&<button disabled={busy||!canRun} onClick={()=>void action(async()=>{setRun(await api.cancelInvestigation(run.run_id));setAttempt(n=>n+1);})} className="inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm"><Square className="h-3 w-3"/>Cancel run</button>}</div>}</div>
  {plan&&<p className="mt-3 max-w-5xl text-sm leading-relaxed text-muted-foreground">{plan.objective}</p>}
  {plan&&<div className="mt-4 flex flex-wrap items-center gap-2"><div className="inline-flex rounded-lg border p-0.5">{(['canvas','steps','report'] as const).map(v=><button key={v} disabled={v==='report'&&!report} onClick={()=>setView(v)} className={`rounded-md px-3 py-1.5 text-xs capitalize disabled:opacity-35 ${view===v?'bg-muted font-medium':'text-muted-foreground'}`}>{v==='canvas'?'Workflow':v}</button>)}</div>{run&&<p role="status" className="ml-2 text-xs text-muted-foreground">{completed} of {plan.graph.nodes.length} steps completed{skipped?` · ${skipped} skipped`:null}{working?' · Updating live':''}</p>}<button className="ml-auto inline-flex items-center gap-1 text-xs text-muted-foreground" onClick={()=>{setError(null);setAttempt(n=>n+1);}}><RefreshCw className="h-3 w-3"/>Refresh status</button></div>}
  <ApiFeedback error={error} onRetry={()=>{setError(null);setAttempt(n=>n+1);}}/>
  </header>
  {plan?.preflight&&<section className="shrink-0 border-b bg-muted/20 p-4 md:px-6"><h2 className="text-sm font-medium">Pre-run evidence coverage</h2><div className="mt-2 flex flex-wrap gap-3 text-xs">{Object.entries(plan.preflight.coverage).filter(([task])=>task!=='complaints'||Object.keys(plan.preflight!.coverage).length===1).map(([task,result])=><span key={task}>{task}: {result.state.replaceAll('_',' ')}</span>)}</div>{Object.values(plan.preflight.coverage).some(result=>result.state==='needs_input')&&<p className="mt-2 text-xs text-muted-foreground">Provide an assessment date or select a policy under Workflow options → Investigation context on the prompt screen. Comparison can proceed while a dependent assessment needs inputs.</p>}</section>}
  {pending&&<section className="shrink-0 border-b border-warning/30 bg-warning/5 p-4 md:px-6"><h2 className="text-sm font-medium">Additional information required</h2><p className="mt-1 text-sm text-muted-foreground">{pending.reason}</p><form onSubmit={e=>{e.preventDefault();void action(async()=>{
   const body=pending.node_id==='anchor'?{request_key:key('input:'+identifier),identifiers:{[identifierType]:identifier.trim()}}:{request_key:key('ack:'+notes),acknowledge_gaps:ack,notes};
   const updated=await api.investigationInput(run!.run_id,body);setRun(updated);
   const j=await api.submitInvestigation('resume',{run_id:updated.run_id},key('continue:'+updated.updated_at));setJob(j);location(plan!.workflow_id,updated.run_id,j.job_id);setAttempt(n=>n+1);
  });}} className="mt-3 flex flex-wrap items-center gap-3">{pending.node_id==='anchor'?<><select aria-label="Identifier type" value={identifierType} onChange={e=>setIdentifierType(e.target.value)} className="rounded-lg border bg-background p-2 text-sm"><option value="complaint_id">Complaint ID</option><option value="serial">Engine serial</option></select><input aria-label="Complaint or engine identifier" value={identifier} onChange={e=>setIdentifier(e.target.value)} placeholder="Enter the exact identifier" className="min-w-0 flex-1 rounded-lg border bg-background p-2 text-sm" required/></>:<><label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={ack} onChange={e=>setAck(e.target.checked)} required/>Finalize the report with its unresolved evidence gaps</label><input aria-label="Additional notes" value={notes} onChange={e=>setNotes(e.target.value)} maxLength={2000} placeholder="Optional notes (remain unverified)" className="rounded-lg border bg-background p-2 text-sm"/></>}<button disabled={busy||!canRun} className="rounded-lg bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-40">Continue investigation</button></form></section>}
  <main className="min-h-0 flex-1 overflow-auto">{!plan?<div className="mx-auto flex max-w-lg flex-col items-center gap-4 px-6 py-20 text-center">{!error&&<Loader2 className="h-7 w-7 animate-spin text-primary"/>}<h2 className="font-display text-xl">{job?.state==='queued'?'Workflow queued':job?.state==='failed'?'Workflow generation could not complete':error?'Investigation unavailable':'Building your workflow'}</h2><p className="text-sm text-muted-foreground">{job?.state==='running'?'The planner is selecting relevant business knowledge and building a validated workflow. You can reload this page without submitting it again.':job?.state==='queued'?'Waiting for the workflow worker. Generation will start automatically.':'Open a saved investigation or generate one from the overview.'}</p><Link to="/app" className="text-sm text-primary">Back to prompt</Link></div>:view==='report'&&report?<div className="mx-auto max-w-4xl p-5 md:p-8"><InvestigationReportView report={report} plan={plan}/></div>:view==='steps'?<div className="mx-auto max-w-3xl space-y-2 p-5">{plan.graph.nodes.map(n=><button key={n.id} onClick={()=>setSelected(n.id)} className="flex w-full items-center justify-between gap-4 rounded-xl border bg-background p-4 text-left"><span className="flex items-center gap-3"><GitBranch className="h-4 w-4 text-primary"/><span className="text-sm font-medium">{nodeLabel(n)}</span></span><span className="text-xs text-muted-foreground">{stateLabels[run?.node_states[n.id]??'pending']}</span></button>)}</div>:<InvestigationCanvas plan={plan} run={run} selected={selected} onSelect={setSelected}/>}</main>
  {plan&&<><InvestigationEvidence plan={plan} open={evidence} onClose={()=>setEvidence(false)}/><InvestigationNodePanel plan={plan} run={run} id={selected} onClose={()=>setSelected(null)}/></>}
 </div>;
}
