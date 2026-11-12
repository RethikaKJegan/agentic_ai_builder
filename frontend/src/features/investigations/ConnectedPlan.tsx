"use client";
import { useEffect, useState } from "react";
import { AutomationPanel } from "./DurableAutomation";
import {KnowledgeMap} from "./KnowledgeMap";
import {Sheet,SheetContent,SheetHeader,SheetTitle,SheetDescription} from "@/components/ui/sheet";
import {Dialog,DialogContent,DialogHeader,DialogTitle,DialogDescription} from "@/components/ui/dialog";
import {Info,Play,CheckCircle2,RefreshCw,Settings2,Network} from "lucide-react";
import { QueryClarification } from './QueryClarification';
import { QueryEvidence } from "./QueryEvidence";
import {AdaptiveProgress} from "@/features/builder/AdaptiveProgress";
import { api } from "@/api/client";
import { GoogleAccountSelect } from "@/features/workflows/GoogleWorkflowConnection";
import { useBackend } from "@/api/state";
import { type ActionDocument, receiptLinks } from "@/api/orchestration";
import { type CompositionView } from "@/api/compositions";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";
import { SavedDetails, Outcome } from "./LifecyclePanels";
import { CompositionCanvas } from './CompositionCanvas';
import { CompositionInspector, CompositionReport } from './CompositionPanels';
import { useOrchestrationCommand } from "./useOrchestrationCommand";

export const actionButton = "rounded-lg border px-3 py-2 text-sm disabled:opacity-40";
export function ConnectedPlan(props:{id:string;runId?:string|undefined;onRun?:((id:string)=>void)|undefined;adaptive?:boolean;scheduled?:boolean}) {
  const subject=useBackend(s=>s.session?.auth.subject);
  return <ScopedConnectedPlan key={JSON.stringify([subject?.workspace_id,subject?.subject_id,props.id,props.runId])} {...props}/>;
}
function ScopedConnectedPlan({
  id,
  runId,
  onRun,
  adaptive = false,
  scheduled = false,
}: {
  id: string;
  runId?: string | undefined;
    onRun?: ((id: string) => void) | undefined;
  adaptive?: boolean;
  scheduled?: boolean;
}) {
  const backend = useBackend();
  const command = useOrchestrationCommand();
  const [doc, setDoc] = useState<ActionDocument | null>(null);
  const [view, setView] = useState<CompositionView | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [refresh, setRefresh] = useState(0);
  const [stale, setStale] = useState(true);
  const [tab,setTab]=useState<'workflow'|'steps'|'report'|'knowledge'|'background'>('workflow');
  const [panel,setPanel]=useState<string|null>(null);
  const [reviewRun,setReviewRun]=useState(false);
  const [details,setDetails]=useState(false);
  const scope = backend.session
    ? backend.session.auth.subject.workspace_id + ":" + backend.session.auth.subject.subject_id
    : "";
  useEffect(() => {
    let live = true;
    let timer: ReturnType<typeof setTimeout>;
    setDoc(null);
    setView(null);
    setStale(true);
    async function read() {
      try {
        const [d, v] = await Promise.all([api.actionPlan(id), api.compositionView(id, runId)]);
        if (!live) return;
        if (d.composition_id!==id || v.composition_id!==id || (runId&&v.run?.run_id!==runId) || d.scope.workspace + ":" + d.scope.owner !== scope || d.action_plan.scope.workspace_id+":"+d.action_plan.scope.owner_id!==scope)
          throw new Error("Plan is outside the selected workspace.");
        setDoc(v.run?.action_plan ? {...d,action_plan:v.run.action_plan} : d);
        setView(v);
        setError(null);
        setStale(false);
        timer = setTimeout(() => void read(), 3000);
      } catch (e) {
        if (live) {
          setError(e as Error);
          setStale(true);
          timer=setTimeout(()=>void read(),3000);
        }
      }
    }
    if (scope) void read();
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [id, runId, refresh, scope]);
  const update = () => setRefresh((n) => n + 1);
  async function prepareReview() {
    await command.act('prepare-review:'+id,{composition_id:id},async body=>{
      const key=String(body['request_key']);
      const current=await api.compositionView(id);
      let ref={workflow_id:current.workflow_id,workflow_version:current.workflow_version??1};
      if(!current.workflow_status){
        const workflow=await api.compositionWorkflow(id);
        ref={workflow_id:workflow.workflow_id,workflow_version:workflow.version};
        await api.request('save_workflow_version',{...ref,base_version:0,workflow},key+'_save');
      }
      if(!current.workflow_status||current.workflow_status==='draft')await api.request('validate_workflow',ref,key+'_validate');
      update();
    });
  }
  async function startReviewed() {
    if(!view)return;
    await command.act('review-run:'+id,{workflow_id:view.workflow_id,workflow_version:view.workflow_version??1},async body=>{
      const current=await api.compositionView(id);
      const ref={workflow_id:current.workflow_id,workflow_version:current.workflow_version??1};
      if(ref.workflow_id!==view.workflow_id||ref.workflow_version!==(view.workflow_version??1))throw new Error('The workflow version changed. Refresh and review again.');
      if(current.workflow_status==='validated')await api.request('approve_workflow',{...ref,action:'approve'},String(body['request_key'])+'_approve');
      else if(!['approved','published'].includes(current.workflow_status??''))throw new Error('Validate this workflow before running it.');
      if(!scheduled&&!adaptive){const result=await api.request('execute_workflow',{...ref,inputs:{}},String(body['request_key'])+'_execute');onRun?.(result.run.run_id);}
      setReviewRun(false);update();
    });
  }
  const disabled = command.busy || stale || command.unknown || view?.state==='blocked';
  const needsQueryDefinition=!!view?.recovery.can_clarify&&view.tasks.some(t=>t.result?.classification==='query_clarification');
  return (
    <section aria-label="Connected action plan" className="min-w-0 space-y-4 rounded-xl border p-4">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b pb-4">
        <div className="min-w-0"><p className="mb-1 text-xs font-medium uppercase tracking-widest text-muted-foreground">Workflow workspace</p><h1 className="text-xl font-semibold">{view?.display_name??'Investigation workflow'}</h1><p className="mt-1 text-xs text-muted-foreground">{view?.run?.status?.replaceAll('_',' ')??view?.workflow_status??'Preparing'}{doc&&` · Plan revision ${doc.action_plan.revision}`}</p></div>
        <div className="flex flex-wrap items-center gap-2">
          <button className={actionButton} disabled={!view} onClick={()=>setDetails(true)}><Info size={14} className="mr-2 inline"/>Details</button>
          <button className={actionButton} disabled={disabled||!view||!backend.can('workflow.edit')||!backend.can('workflow.validate')||!!view.workflow_status&&view.workflow_status!=='draft'} onClick={()=>void prepareReview()}><CheckCircle2 size={14} className="mr-2 inline"/>Validate</button>
          <button className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 disabled:opacity-40" disabled={disabled||!view||!!view.run||!['validated','approved','published'].includes(view.workflow_status??'')||!backend.can('workflow.execute')||!backend.session?.runtime_available||view.workflow_status==='validated'&&!backend.can('workflow.approve')} onClick={()=>setReviewRun(true)}><Play size={14}/>Run</button>
          <button className={actionButton} aria-label="Refresh plan" disabled={command.busy} onClick={update}><RefreshCw size={14}/></button>
        </div>
      </div>
      <ApiFeedback error={error ?? command.error} />
      {view?.state==='blocked'&&<div role="status" className="rounded-lg border border-warning/50 p-3 text-sm"><p className="font-medium">Workflow draft blocked</p><p>This workflow is saved, but unresolved execution requirements prevent approval or execution. No follow-up answer is requested and no action has been performed.</p>{view.gaps.map((gap,i)=>typeof gap['description']==='string'?<p key={i} className="mt-2">{gap['description']}</p>:null)}</div>}
      {command.unknown && (
        <p role="alert">
          Command outcome is unconfirmed. Refresh the saved state before continuing. Do not submit a
          replacement write.
        </p>
      )}
      {command.unknown && (
        <button className={actionButton} disabled={command.busy} onClick={command.retry}>
          Retry identical command
        </button>
      )}
      {!doc || !view ? (
        <p role="status">
          {error ? "Plan unavailable. Refresh to read saved state." : "Loading persisted plan…"}
        </p>
      ) : (
        <>
          <div role="tablist" aria-label="Investigation views" className="flex max-w-full gap-1 overflow-x-auto border-b pb-1">
            {(['workflow','steps','report','knowledge','background'] as const).map(value=><button key={value} role="tab" aria-label={value==='report'?'Reports':value==='knowledge'?'Knowledge Map':value[0]!.toUpperCase()+value.slice(1)} aria-selected={tab===value} disabled={value==='report'&&!view.run&&!view.tasks.some(t=>t.result)} onClick={()=>setTab(value)} className={`shrink-0 rounded-lg px-4 py-2.5 text-sm disabled:opacity-40 ${tab===value?'bg-primary/10 font-semibold text-primary':'text-muted-foreground hover:bg-muted'}`}>{value==='report'?'Reports':value==='knowledge'?'Knowledge Map':value[0]!.toUpperCase()+value.slice(1)}</button>)}
          </div>
          {tab==='knowledge'&&<KnowledgeMap doc={doc} view={view}/>}
          {tab==='background'&&<section className="space-y-4" aria-label="Workflow background"><div><h3 className="font-semibold">Behind the workflow</h3><p className="mt-1 text-sm text-muted-foreground">Inspect the agents, tools and saved execution details supporting this workflow.</p></div><div className="grid gap-3 sm:grid-cols-2"><button className="rounded-xl border p-5 text-left hover:bg-muted/30" onClick={()=>setPanel('agents')}><Network className="mb-3 h-5 w-5 text-primary"/><p className="text-sm font-medium">Agents and tools</p><p className="mt-1 text-xs text-muted-foreground">Task assignments and connected capabilities</p></button><button className="rounded-xl border p-5 text-left hover:bg-muted/30" onClick={()=>setPanel('memory')}><Settings2 className="mb-3 h-5 w-5 text-primary"/><p className="text-sm font-medium">Memory and recovery</p><p className="mt-1 text-xs text-muted-foreground">Saved context, failures and recovery history</p></button></div><SavedDetails label="Execution diagnostics" value={{run:view.run,planning:view.planning}}/><AutomationPanel workflowId={view.workflow_id}/></section>}
          <Sheet open={details} onOpenChange={setDetails}><SheetContent className="w-full overflow-y-auto sm:max-w-xl"><SheetHeader><SheetTitle>Workflow details</SheetTitle><SheetDescription>Saved request, account and execution settings.</SheetDescription></SheetHeader><div className="mt-6 space-y-5"><section><h3 className="text-sm font-semibold">Your request</h3><p className="mt-2 whitespace-pre-wrap text-sm text-muted-foreground">{doc.action_plan.goal}</p></section><GoogleAccountSelect value={doc.google_connection_id??''} onChange={()=>{}} disabled/><SavedDetails label="Completion criteria and missing inputs" value={{completion_criteria:doc.action_plan.completion_criteria,missing_inputs:doc.action_plan.missing_inputs}}/><SavedDetails label="Schedule and request context" value={{overview:doc['overview_intent'],request:view.request_context}}/><SavedDetails label="Workflow references" value={{workflow_id:view.workflow_id,version:view.workflow_version,plan_revision:doc.action_plan.revision,run_id:view.run?.run_id}}/></div></SheetContent></Sheet>
          <Dialog open={reviewRun} onOpenChange={setReviewRun}><DialogContent><DialogHeader><DialogTitle>{view.workflow_status==='validated'?'Review and run workflow':'Run workflow'}</DialogTitle><DialogDescription>{scheduled?'Approve this workflow for the separately reviewed schedule. Scheduling authorization remains below.':adaptive?'Approve this workflow for the existing orchestration controller.':'Start the saved workflow using its connected account and configured actions. External writes still require their exact-payload approvals.'}</DialogDescription></DialogHeader><p className="text-sm">{doc.action_plan.goal}</p><p className="text-xs text-muted-foreground">Workflow version {view.workflow_version??1} · {doc.action_plan.actions.length} steps</p><button className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-40" disabled={disabled} onClick={()=>void startReviewed()}>{scheduled||adaptive?'Approve workflow':'Confirm and run'}</button></DialogContent></Dialog>
          <div className="flex flex-wrap gap-2">
            {!adaptive &&
              view.run &&
              ["running", "queued", "paused_for_approval"].includes(view.run.status) && (
                <button
                  className={actionButton}
                  disabled={disabled || !backend.can("workflow.execute")}
                  onClick={() =>
                    void command.act("cancel:" + view.run!.run_id, {}, async () => {
                      await api.cancelComposition(id, view.run!.run_id);
                      update();
                    })
                  }
                >
                  Cancel run
                </button>
              )}
          </div>
          {needsQueryDefinition && doc && <QueryClarification doc={doc} view={view}/>}
          {view.run?.error_code && !needsQueryDefinition && (
            <p role="alert">
              Execution: {view.run.error_code}. {view.recovery.reason}
            </p>
          )}
          {view.run?.approvals
            .filter((a) => a.status === "pending")
            .map((a) => (
              <article
                key={a.approval_id}
                className="space-y-2 rounded-lg border border-warning/50 p-3"
              >
                <h3 className="text-sm font-semibold">Exact-payload approval</h3>
                <p className="text-xs">
                  {a.approval_id} · {a.action_digest}
                </p>
                <SavedDetails
                  label="Actual action payload"
                  value={a.resolved_payload ?? "Payload unavailable; approval disabled."}
                />
                <p className="text-xs">
                  Changing these inputs requires a new backend plan and fresh authorization.
                </p>
                {a.allowed_decisions.map((decision) => (
                  <button
                    key={decision}
                    className={actionButton}
                    disabled={
                      disabled ||
                      !a.resolved_payload ||
                      !a.action_digest ||
                      !backend.can("workflow.approve")
                    }
                    onClick={() =>
                      void command.act(
                        "approval:" + a.approval_id,
                        {
                          approval_id: a.approval_id,
                          workflow_id: a.workflow_id,
                          workflow_version: a.workflow_version,
                          decision,
                        },
                        async (b) => {
                          await api.request(
                            "decide_approval",
                            {
                              approval_id: a.approval_id,
                              workflow_id: a.workflow_id,
                              workflow_version: a.workflow_version,
                              decision,
                            },
                            String(b["request_key"]),
                          );
                          update();
                        },
                      )
                    }
                  >
                    {decision === "approved" ? "Approve exact payload" : "Reject action"}
                  </button>
                ))}
              </article>
            ))}
          {view.run?.adaptive&&<AdaptiveProgress run={view.run} onUpdated={update}/>}
          {tab==='workflow'&&<div className="h-[65vh] min-h-[480px] overflow-hidden rounded-xl border"><CompositionCanvas view={view} onSelect={setPanel}/></div>}
          {tab==='report'&&<div role="tabpanel" aria-label="Investigation report">
            <CompositionReport view={view}/>
            {Object.entries(view.run?.action_instances??{}).map(([id,instance])=><QueryEvidence key={id} instance={instance}/>)}
            {Object.values(view.run?.action_instances??{}).flatMap(instance=>receiptLinks(instance)).map(url=><a key={url} href={url} target="_blank" rel="noopener noreferrer" className="mx-5 block break-all text-sm text-primary underline">Open verified artifact: {url}</a>)}
            {doc.action_plan.actions.filter(a=>a.capability_id==='content.prepare').map(a=>{const output=view.run?.action_instances?.[a.action_id]?.output;return output&&typeof output['body']==='string'&&output['body']?<article key={a.action_id} className="mx-auto max-w-5xl space-y-3 p-5"><h3 className="font-semibold">Generated report content</h3><p className="whitespace-pre-wrap break-words text-sm">{output['body']}</p></article>:null;})}
          </div>}
          {tab==='steps'&&<ol className="space-y-3">
            {doc.action_plan.actions.map((a, i) => {
              const task = view.tasks.find((t) => t.id === a.action_id);
              const instance = view.run?.action_instances?.[a.action_id];
              return (
                <li key={a.action_id} className="min-w-0 space-y-2 rounded-lg border p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-sm font-medium">
                      {i + 1}. {a.action_id}
                    </h3>
                    <Outcome value={instance?.state ?? task?.state ?? "pending"} />
                    {instance?.provenance_type && <Outcome value={instance.provenance_type} />}
                  </div>
                  <p className="break-words text-xs">
                    {a.capability_id} · Agent: {task?.agent_id ?? "Not assigned"} · Tools:{" "}
                    {task?.tools.join(", ") || "Reasoning"} · Depends on:{" "}
                    {a.depends_on.join(", ") || "None"}
                  </p>
                  <p className="text-sm">{a.instructions}</p>
                  <QueryEvidence instance={instance}/>
                  <SavedDetails
                    label="Inputs, evidence and expected outputs"
                    value={{
                      bindings: a.bindings,
                      resolved_inputs: instance?.resolved_inputs,
                      expected_output_schema: a.expected_output_schema,
                      evidence_requirements: task?.required_evidence,
                      evidence_references: a.evidence_references,
                      required_approvals: a.required_approvals,
                      completion_criteria: task?.completion_criteria,
                    }}
                  />
                  {instance?.output && (
                    <>
                      <SavedDetails
                        label="Saved findings, evidence and receipts"
                        value={instance}
                      />
                      {receiptLinks(instance).map((url) => (
                        <a
                          key={url}
                          href={url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="block break-all text-sm text-primary underline"
                        >
                          Open verified artifact: {url}
                        </a>
                      ))}
                    </>
                  )}
                  {!!task?.errors.length && (
                    <SavedDetails label="Action errors" value={task.errors} />
                  )}
                </li>
              );
            })}
          </ol>}
          <CompositionInspector view={view} section={panel} onClose={()=>setPanel(null)}/>
          <p className="text-xs text-muted-foreground">
            ACTUAL source/provider reports, DERIVED values, INFERRED content and SYNTHETIC
            assumptions keep their provenance. Provider confirmation does not establish physical
            completion or commercial authorization.
          </p>
        </>
      )}
    </section>
  );
}
