import { displayText } from "@/lib/display-text";
import { useMemo, useState } from 'react';
import { ArrowRight, Bot, CheckCircle2, Circle, Layers3, Loader2, RefreshCw } from 'lucide-react';
import { fromCanonical } from '@/api/mapping';
import { projectDiagram } from '@/domain/procurement-communication';
import { workflowDiagram, friendlyLabel, type DiagramModel } from '@/domain/communication-diagram';
import { PROCUREMENT_STAGES, agentTeams, stageActions, stageState, type StageId } from '@/domain/procurement-stages';
import { ApiFeedback } from '@/features/workflows/ApiFeedback';
import { CommunicationDiagram, DiagramLegend } from './CommunicationDiagram';
import { useProjectCommunication } from './useProjectCommunication';

export function ProcurementProjectCommunication({workflowId,version,view='execution'}:{workflowId:string;version:number;view?:'design'|'hierarchy'|'execution'}) {
  const {project,status,error,retry}=useProjectCommunication(workflowId,version);
  const [selected,setSelected]=useState<StageId>('requirements');
  const [chosen,setChosen]=useState('');
  const [teamId,setTeamId]=useState('');
  const actions=project?stageActions(project,selected):[];
  const action=actions.find(a=>a.run.run_id===chosen) ?? actions.at(-1);
  const teams=useMemo(()=>project?agentTeams(project):[],[project]);
  const team=teams.find(t=>t.workflow.workflow_id===teamId) ?? teams[0];
  const model=useMemo<DiagramModel>(()=>{
    if(!project)return {cards:[],connections:[]};
    if(!project.root_workflow.metadata?.['procurement_plan']) return projectDiagram(project);
    const source=view==='hierarchy'?team:action;
    if(!source)return {cards:[],connections:[]};
    const workflow=fromCanonical(source.workflow).workflow;
    const diagram=workflowDiagram(workflow,view==='hierarchy'?[]:source.events,view==='hierarchy'?undefined:source.run?.run_id,view==='hierarchy'?undefined:source.run?.status);
    if(view!=='hierarchy')return diagram;
    const ids=new Set(diagram.cards.filter(c=>['Coordinator','Helper agent','Master agent','Sub-agent'].includes(c.role)).map(c=>c.id));
    return {cards:diagram.cards.filter(c=>ids.has(c.id)),connections:diagram.connections.filter(e=>ids.has(e.source)&&ids.has(e.target))};
  },[project,view,team,action]);
  if(!project)return <div className="flex flex-1 flex-col items-center justify-center gap-3 p-8"><Loader2 className="h-6 w-6 animate-spin text-primary"/><p className="text-sm text-muted-foreground">Loading the project’s recorded stages…</p><ApiFeedback error={error} onRetry={retry}/></div>;
  // Existing non-procurement communication consumers retain their exact graph.
  if(!project.root_workflow.metadata?.['procurement_plan'])return <><DiagramLegend live={false}/><CommunicationDiagram model={model}/></>;
  return <section className="flex min-h-0 flex-1 flex-col bg-muted/20" aria-label="Procurement workspace">
    <div className="flex flex-wrap items-center justify-between gap-3 border-b bg-background px-4 py-2">
      <div><p className="text-[10px] font-semibold uppercase tracking-[.18em] text-muted-foreground">{view==='hierarchy'?'Agent teams':view==='design'?'Process overview':'Live project'}</p><h2 className="mt-1 text-sm font-semibold">{view==='hierarchy'?'One team. Clear responsibilities.':'From requirements to confirmed receipt'}</h2></div>
      <div className="flex items-center gap-3"><span className="rounded-full border bg-background px-3 py-1 text-xs capitalize">{displayText(friendlyLabel(project.phase))}</span><button onClick={retry} className="rounded-lg border p-2 hover:bg-muted" aria-label="Refresh project diagram"><RefreshCw className="h-4 w-4"/></button></div>
    </div>
    <ApiFeedback error={error} onRetry={retry}/>
    {view==='hierarchy'?<>
      <div className="flex shrink-0 flex-wrap gap-2 border-b bg-background px-3 py-2">{teams.map((t,i)=><button key={t.workflow.workflow_id} onClick={()=>setTeamId(t.workflow.workflow_id)} className={`rounded-xl border px-4 py-2 text-left text-xs ${team===t?'border-primary bg-primary/5 text-primary':'hover:bg-muted'}`}><span className="block font-medium">{t.workflow.agents.find(a=>a.hierarchy_role==='master')?.role}</span><span className="mt-1 block text-[10px] text-muted-foreground">Team {i+1} · {t.workflow.agents.filter(a=>a.hierarchy_role==='sub_agent').length} specialists</span></button>)}</div>

      {team?<div className="flex min-h-0 flex-1"><CommunicationDiagram key={team.workflow.workflow_id} model={model}/></div>:<div className="m-6 rounded-2xl border bg-background p-8 text-center"><Bot className="mx-auto mb-3 text-primary"/><p className="font-medium">No master team available in these records yet</p><p className="mt-2 text-sm text-muted-foreground">The configured preview or recorded child workflow will appear here when available. Tool-only actions are not shown as agent teams.</p></div>}
    </>:<div className="flex min-h-0 flex-1 flex-col lg:flex-row">
      <nav className="flex shrink-0 gap-1 overflow-x-auto border-b bg-background p-2 lg:w-64 lg:flex-col lg:min-h-0 lg:overflow-y-auto lg:border-b-0 lg:border-r" aria-label="Procurement stages">{PROCUREMENT_STAGES.map(([id,label],index)=>{
        const grouped=stageActions(project,id);let state=stageState(grouped);if(!grouped.length){if(id==='vendors'&&(status?.record_counts['vendor']??0)>0)state='Contacts recorded';if(id==='comparison'&&status?.recommendations?.length)state='Assessment recorded';if(id==='buyer'&&status?.activity?.some(e=>e.event_kind==='BUYER_RECEIPT_CONFIRMED'))state='Receipt recorded';if(id==='closure'&&status?.orders?.some(p=>p.status==='CLOSED'))state='Closure recorded';}const isSelected=id===selected;
        return <button key={id} onClick={()=>{setSelected(id);setChosen('');}} className={`flex min-w-48 items-start gap-3 rounded-xl border px-3 py-1 text-left transition-colors lg:min-w-0 ${isSelected?'border-primary/30 bg-primary/5':'border-transparent hover:bg-muted'}`}><span className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] ${isSelected?'bg-primary text-white':'bg-muted text-muted-foreground'}`}>{index+1}</span><span className="min-w-0"><span className="block text-xs font-semibold">{displayText(label)}</span><span className="mt-0.5 flex items-center gap-1.5 text-[10px] text-muted-foreground">{state==='Running'?<Loader2 className="h-3 w-3 animate-spin"/>:state==='Recorded'?<CheckCircle2 className="h-3 w-3 text-emerald-600"/>:<Circle className="h-3 w-3"/>}{state}{grouped.length?` · ${grouped.length} actions`:''}</span></span></button>;
      })}</nav>
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <div className="border-b bg-background px-5 py-4"><p className="text-[10px] uppercase tracking-widest text-muted-foreground">Stage {PROCUREMENT_STAGES.findIndex(s=>s[0]===selected)+1} of {PROCUREMENT_STAGES.length}</p><h3 className="mt-1 font-semibold">{PROCUREMENT_STAGES.find(s=>s[0]===selected)?.[1]}</h3><p className="mt-1 text-xs text-muted-foreground">{PROCUREMENT_STAGES.find(s=>s[0]===selected)?.[2]}</p>
          {view!=='design'&&!!actions.length&&<label className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">Recorded action<select aria-label="Recorded stage action" value={action?.run.run_id??''} onChange={e=>setChosen(e.target.value)} className="max-w-full rounded-lg border bg-background px-3 py-2 text-foreground">{actions.map(a=><option key={a.run.run_id} value={a.run.run_id}>{displayText(a.workflow.name)} · {displayText(friendlyLabel(a.run.status))} · {a.run.run_id.slice(-8)}</option>)}</select></label>}
        </div>
        {selected==='comparison'&&!!status?.recommendations?.length&&<div className="border-b bg-background p-5"><h4 className="mb-3 text-xs font-semibold">Backend comparison results</h4><div className="grid gap-2 sm:grid-cols-2">{status.recommendations.map(r=><div key={r.scope_digest} className="rounded-xl border p-3 text-xs"><p className="font-medium">{r.item_ids.join(', ')}</p><p className="mt-1 text-muted-foreground">{displayText(r.reason.replaceAll('_',' '))}{r.amount?` · ${r.amount} ${r.currency}`:''}</p></div>)}</div></div>}
        {view==='design'?<div className="min-h-0 flex-1 overflow-y-auto p-5"><div className="rounded-2xl border bg-background p-6 shadow-sm"><Layers3 className="mb-4 h-7 w-7 text-primary"/><h4 className="font-semibold">{PROCUREMENT_STAGES.find(s=>s[0]===selected)?.[1]}</h4><p className="mt-2 text-sm leading-6 text-muted-foreground">{PROCUREMENT_STAGES.find(s=>s[0]===selected)?.[2]} This stage is a view of the existing procurement coordinator, not an extra executable step.</p><p className="mt-4 rounded-lg bg-muted p-3 text-xs">{actions.length?`${actions.length} backend actions recorded in this stage. Inspect their exact evidence in Execution.`:'No separate action is available for this stage in the returned history. It may be part of a coordinator action; no completion is assumed.'}</p><div className="mt-5 flex items-center gap-2 text-xs text-muted-foreground">Process <ArrowRight className="h-3 w-3"/> Agent team <ArrowRight className="h-3 w-3"/> Recorded evidence</div></div></div>:action?<div className="flex min-h-0 flex-1"><CommunicationDiagram key={action.run.run_id} model={model}/></div>:<div className="flex flex-1 flex-col items-center justify-center p-10 text-center"><Layers3 className="mb-3 h-8 w-8 text-muted-foreground/50"/><p className="text-sm font-medium">No recorded actions in this stage</p><p className="mt-2 max-w-sm text-xs leading-5 text-muted-foreground">It may be waiting for input, not started, or outside the recent history returned by the server. No completion is assumed.</p></div>}
      </div>
    </div>}
    {project.truncated&&<p className="border-t bg-background px-4 py-2 text-xs text-muted-foreground">Recent recorded activity shown. Complete action history remains in Runs.</p>}
  </section>;
}
