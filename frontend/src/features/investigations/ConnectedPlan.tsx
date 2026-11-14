"use client";
import { Link } from "@/lib/navigation";
import { communicationStatuses } from "@/domain/communication-status";
import { useEffect, useMemo, useRef, useState } from "react";
import { AutomationPanel } from "./DurableAutomation";
import { KnowledgeMap } from "./KnowledgeMap";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Info, Play, RefreshCw, Settings2, Network, Loader2 } from "lucide-react";
import { QueryClarification } from "./QueryClarification";
import { QueryEvidence } from "./QueryEvidence";
import { AdaptiveProgress } from "@/features/builder/AdaptiveProgress";
import { AutomationProgress } from "./AutomationProgress";
import { api } from "@/api/client";
import { GoogleAccountSelect } from "@/features/workflows/GoogleWorkflowConnection";
import { useBackend } from "@/api/state";
import { type ActionDocument, receiptLinks } from "@/api/orchestration";
import { newerComposition, type CompositionView } from "@/api/compositions";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";
import { SavedDetails, Outcome } from "./LifecyclePanels";
import { CompositionCanvas } from "./CompositionCanvas";
import { CompositionInspector, CompositionReport } from "./CompositionPanels";
import { useOrchestrationCommand } from "./useOrchestrationCommand";

import { subwayDisplay } from "@/domain/subway-presentation";

export const actionButton = "rounded-lg border px-3 py-2 text-sm disabled:opacity-40";
export function ConnectedPlan(props: {
  id: string;
  runId?: string | undefined;
  onRun?: ((id: string) => void) | undefined;
  adaptive?: boolean;
  scheduled?: boolean;
}) {
  const subject = useBackend((s) => s.session?.auth.subject);
  return (
    <ScopedConnectedPlan
      key={JSON.stringify([subject?.workspace_id, subject?.subject_id, props.id, props.runId])}
      {...props}
    />
  );
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
  const [detailView,setDetailView]=useState<CompositionView|null>(null);
  const [detailError,setDetailError]=useState<Error|null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [refresh, setRefresh] = useState(0);
  const [stale, setStale] = useState(true);
  const [tab, setTab] = useState<"workflow" | "steps" | "report" | "knowledge" | "background">(
    "workflow",
  );
  const [panel, setPanel] = useState<string | null>(null);
  const [operation, setOperation] = useState<"run" | "approve" | null>(null);
  const runAttempt = useRef<string | null>(null);
  const [details, setDetails] = useState(false);
  const scope = backend.session
    ? backend.session.auth.subject.workspace_id + ":" + backend.session.auth.subject.subject_id
    : "";
  useEffect(() => {
    let live = true;
    let timer: ReturnType<typeof setTimeout>;
    setStale(true);
    let document:ActionDocument|null=null;
    async function read() {
      try {
        const [d, v] = await Promise.all([document?Promise.resolve(document):api.actionPlan(id), api.compositionView(id, runId,'summary')]);
        document=d;
        if (!live) return;
        if (
          d.composition_id !== id ||
          v.composition_id !== id ||
          (runId && v.run?.run_id !== runId) ||
          d.scope.workspace + ":" + d.scope.owner !== scope ||
          d.action_plan.scope.workspace_id + ":" + d.action_plan.scope.owner_id !== scope
        )
          throw new Error("Plan is outside the selected workspace.");
        setDoc(v.run?.action_plan ? { ...d, action_plan: v.run.action_plan } : d);
        setView(previous=>newerComposition(previous,v));
        setError(null);
        setStale(false);
        if(!v.run||!['completed','failed','blocked','cancelled','rejected'].includes(v.run.status))timer = setTimeout(() => void read(), 3000);
      } catch (e) {
        if (live) {
          setError(e as Error);
          setStale(true);
          timer = setTimeout(() => void read(), 3000);
        }
      }
    }
    if (scope) void read();
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [id, runId, refresh, scope]);
  const detailSnapshot=useRef(view);detailSnapshot.current=view;
  const selectedState=view?.tasks.find(t=>t.id===panel)?.state;
  useEffect(()=>{
    const current=detailSnapshot.current;
    if(!current||(!panel&&!['report','knowledge','background','steps'].includes(tab)&&!details&&current.run?.status!=='paused_for_approval'))return;
    let live=true;setDetailError(null);
    const task=panel&&current.tasks.some(t=>t.id===panel)?panel:undefined;
    void api.compositionView(id,current.run?.run_id,task?'task':'full',task).then(value=>{if(live)setDetailView(value);}).catch(e=>{if(live)setDetailError(e as Error);});
    return ()=>{live=false;};
  },[id,view?.run?.run_id,view?.run?.status,selectedState,panel,tab,details,refresh]);
  const inspectedView=useMemo(()=>detailView&&view&&detailView.run?.run_id===view.run?.run_id?{...detailView,run:detailView.run&&view.run?{...detailView.run,status:view.run.status,approvals:detailView.run.approvals.filter(a=>view.run?.approvals.some(v=>v.approval_id===a.approval_id&&v.status===a.status))}:view.run,tasks:detailView.tasks.map(task=>({...task,state:view.tasks.find(t=>t.id===task.id)?.state??task.state}))}:view,[detailView,view]);
  const update = () => setRefresh((n) => n + 1);
  async function startRun() {
    if (!view) return;
    runAttempt.current ??= crypto.randomUUID();
    setOperation("run");
    await command.act("run:" + id + ":" + runAttempt.current, { composition_id: id }, async (body) => {
      const key = String(body["request_key"]);
      const current = await api.compositionView(id);
      let ref = { workflow_id: current.workflow_id, workflow_version: current.workflow_version ?? 1 };
      if (!current.workflow_status) {
        const workflow = await api.compositionWorkflow(id);
        ref = { workflow_id: workflow.workflow_id, workflow_version: workflow.version };
        await api.request("save_workflow_version", { ...ref, base_version: 0, workflow }, key + "_save");
      }
      try {
        if (scheduled || adaptive) await api.submitApproval(ref);
        else {
          const result = await api.request("execute_workflow", { ...ref, inputs: {} }, key + "_execute");
          onRun?.(result.run.run_id);
          runAttempt.current = null;
        }
      } finally { update(); }
    });
    setOperation(null);
  }
  async function approveWorkflow() {
    if (!view?.workflow_version) return;
    setOperation("approve");
    await command.act("approve-workflow:" + id, { workflow_id: view.workflow_id, workflow_version: view.workflow_version }, async body => {
      await api.request("approve_workflow", { workflow_id: view.workflow_id, workflow_version: view.workflow_version!, action: "approve" }, String(body["request_key"]));
      update();
    });
    setOperation(null);
  }
  const displayDoc = useMemo(
    () => subwayDisplay(doc, backend.session?.auth.subject.workspace_id),
    [doc, backend.session?.auth.subject.workspace_id],
  );
  const displayView = useMemo(
    () => subwayDisplay(inspectedView??view, backend.session?.auth.subject.workspace_id),
    [inspectedView,view, backend.session?.auth.subject.workspace_id],
  );
  const demoData =
    backend.session?.auth.subject.workspace_id === "client-subway" &&
    !!(doc?.["binding_context"] as { validated_context?: { demo_context?: unknown } } | undefined)
      ?.validated_context?.demo_context;
  const disabled = command.busy || stale || command.unknown || view?.state === "blocked";
  const [calendarRecovery, setCalendarRecovery] = useState<{
    composition_id: string;
    request_key: string;
  } | null>(null);
  useEffect(
    () => setCalendarRecovery(null),
    [id, backend.session?.auth.subject.workspace_id, backend.session?.auth.subject.subject_id],
  );
  const needsQueryDefinition =
    !!view?.recovery.can_clarify &&
    view.tasks.some((t) => t.result?.classification === "query_clarification");
  const overview = doc?.["overview_intent"] as { route?: { intent_type?: string } } | undefined;
  const automation = scheduled || overview?.route?.intent_type === "recurring";
  return (
    <section aria-label="Connected action plan" className="min-w-0 space-y-4 rounded-xl border p-4">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b pb-4">
        <div className="min-w-0">
          <p className="mb-1 text-xs font-medium uppercase tracking-widest text-muted-foreground">
            Workflow workspace
          </p>
          <h1 className="text-xl font-semibold">
            {displayView?.display_name ?? "Investigation workflow"}
          </h1>
          <p className="mt-1 text-xs text-muted-foreground">
            {displayView?.run?.status?.replaceAll("_", " ") ??
              displayView?.workflow_status ??
              "Preparing"}
            {displayDoc && ` · Plan revision ${displayDoc.action_plan.revision}`}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button className={actionButton} disabled={!displayView} onClick={() => setDetails(true)}>
            <Info size={14} className="mr-2 inline" />
            Details
          </button>
          <button
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 disabled:opacity-40"
            disabled={
              disabled ||
              !displayView ||
              (!!displayView.run &&
                ["queued", "running", "paused_for_approval"].includes(displayView.run.status)) ||
              !backend.can("workflow.execute") ||
              !backend.session?.runtime_available
            }
            onClick={() => void startRun()}
          >
            {operation === "run" ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Play size={14} />
            )}
            {operation === "run" ? "Starting run…" : displayView?.run ? "Run again" : "Run"}
          </button>
          <button
            className={actionButton}
            aria-label="Refresh plan"
            disabled={command.busy}
            onClick={update}
          >
            <RefreshCw size={14} />
          </button>
        </div>
      </div>
      <ApiFeedback error={error ?? command.error} />
      {displayView?.workflow_status === "validated" && <div role="status" className="flex flex-wrap items-center gap-3 text-sm"><span>Awaiting approval. Review the workflow and its configured actions.</span>{backend.can("workflow.approve") && <button className={actionButton} disabled={command.busy || stale} onClick={() => void approveWorkflow()}>Approve workflow</button>}</div>}
      {operation && (
        <div
          role="status"
          aria-live="polite"
          className="flex items-center gap-3 rounded-xl border bg-muted/30 p-4 text-sm"
        >
          <Loader2 className="h-5 w-5 animate-spin" />
          {operation === "approve" ? "Submitting approval…" : "Checking and starting run…"}
        </div>
      )}
      {displayView?.run && (
        <div aria-label="Delivery status" className="flex flex-wrap gap-3 text-sm">
          {communicationStatuses(displayView.run.action_instances).map((status, i) => (
            <span key={i} className="rounded-lg border px-3 py-2">
              {status.label}
            </span>
          ))}
        </div>
      )}
      {displayView?.run &&
        (displayView.run.error_code === "CALENDAR_REVIEW_TIME_PASSED" ||
          (!!(doc?.["overview_intent"] as Record<string, unknown> | undefined)?.["communication"] &&
            displayView.run.status === "paused_for_approval" &&
            displayView.run.approvals.some(
              (a) =>
                a.status === "pending" &&
                typeof (
                  a.resolved_payload?.["event"] as { start?: { dateTime?: unknown } } | undefined
                )?.start?.dateTime === "string" &&
                Date.parse(
                  (a.resolved_payload!["event"] as { start: { dateTime: string } }).start.dateTime,
                ) <= Date.now(),
            ))) && (
          <div className="space-y-2 text-sm">
            <p>
              The reading-session time passed before it could be sent. You can prepare a new
              Calendar-only review using the saved report.
            </p>
            <button
              className={actionButton}
              disabled={command.busy || !backend.can("workflow.plan")}
              onClick={() =>
                void command.act("calendar-recovery:" + displayView.run!.run_id, {}, async () => {
                  const next = await api.overviewIntent({
                    operation: "recover_calendar",
                    request_key: "calendar-recovery-" + crypto.randomUUID(),
                    composition_id: id,
                    run_id: displayView.run!.run_id,
                  });
                  if (next.composition_id && next.request_key)
                    setCalendarRecovery({
                      composition_id: next.composition_id,
                      request_key: next.request_key,
                    });
                })
              }
            >
              Prepare Calendar-only review
            </button>
            {calendarRecovery && (
              <Link
                className={actionButton}
                to="/app/workflows/investigate"
                search={{
                  connected: "1",
                  composition: calendarRecovery.composition_id,
                  overview: calendarRecovery.request_key,
                }}
              >
                Review new reading session
              </Link>
            )}
          </div>
        )}

      {displayView?.state === "blocked" && (
        <div role="status" className="rounded-lg border border-warning/50 p-3 text-sm">
          <p className="font-medium">Workflow draft blocked</p>
          <p>
            This workflow is saved, but unresolved execution requirements prevent approval or
            execution. No follow-up answer is requested and no action has been performed.
          </p>
          {displayView.gaps.map((gap, i) =>
            typeof gap["description"] === "string" ? (
              <p key={i} className="mt-2">
                {gap["description"]}
              </p>
            ) : null,
          )}
        </div>
      )}
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
      {!displayDoc || !displayView ? (
        <p role="status">
          {error ? "Plan unavailable. Refresh to read saved state." : "Loading persisted plan…"}
        </p>
      ) : (
        <>
          <div
            role="tablist"
            aria-label="Investigation views"
            className="flex max-w-full gap-1 overflow-x-auto border-b pb-1"
          >
            {(["workflow", "steps", "report", "knowledge", "background"] as const).map((value) => (
              <button
                key={value}
                role="tab"
                aria-label={
                  value === "report"
                    ? "Reports"
                    : value === "knowledge"
                      ? "Ontology"
                      : value[0]!.toUpperCase() + value.slice(1)
                }
                aria-selected={tab === value}
                disabled={
                  value === "report" && !displayView.run && !displayView.tasks.some((t) => t.result)
                }
                onClick={() => setTab(value)}
                className={`shrink-0 rounded-lg px-4 py-2.5 text-sm disabled:opacity-40 ${tab === value ? "bg-primary/10 font-semibold text-primary" : "text-muted-foreground hover:bg-muted"}`}
              >
                {value === "report"
                  ? "Reports"
                  : value === "knowledge"
                    ? "Ontology"
                    : value[0]!.toUpperCase() + value.slice(1)}
              </button>
            ))}
          </div>
          {tab === "knowledge" && <KnowledgeMap doc={displayDoc} view={inspectedView??displayView} />}
          {tab === "background" && (
            <section className="space-y-4" aria-label="Workflow background">
              <div>
                <h3 className="font-semibold">Behind the workflow</h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  Inspect the agents, tools and saved execution details supporting this workflow.
                </p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <button
                  className="rounded-xl border p-5 text-left hover:bg-muted/30"
                  onClick={() => setPanel("agents")}
                >
                  <Network className="mb-3 h-5 w-5 text-primary" />
                  <p className="text-sm font-medium">Agents and tools</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Task assignments and connected capabilities
                  </p>
                </button>
                <button
                  className="rounded-xl border p-5 text-left hover:bg-muted/30"
                  onClick={() => setPanel("memory")}
                >
                  <Settings2 className="mb-3 h-5 w-5 text-primary" />
                  <p className="text-sm font-medium">Memory and recovery</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Saved context, failures and recovery history
                  </p>
                </button>
              </div>
              <SavedDetails
                label="Execution diagnostics"
                value={{ run: displayView.run, planning: displayView.planning }}
              />
              <AutomationPanel workflowId={displayView.workflow_id} />
            </section>
          )}
          <Sheet open={details} onOpenChange={setDetails}>
            <SheetContent className="w-full overflow-y-auto sm:max-w-xl">
              <SheetHeader>
                <SheetTitle>Workflow details</SheetTitle>
                <SheetDescription>Saved request, account and execution settings.</SheetDescription>
              </SheetHeader>
              <div className="mt-6 space-y-5">
                <section>
                  <h3 className="text-sm font-semibold">Your request</h3>
                  <p className="mt-2 whitespace-pre-wrap text-sm text-muted-foreground">
                    {displayDoc.action_plan.goal}
                  </p>
                </section>
                <GoogleAccountSelect
                  value={displayDoc.google_connection_id ?? ""}
                  onChange={() => {}}
                  disabled
                />
                <SavedDetails
                  label="Completion criteria and missing inputs"
                  value={{
                    completion_criteria: displayDoc.action_plan.completion_criteria,
                    missing_inputs: displayDoc.action_plan.missing_inputs,
                  }}
                />
                <SavedDetails
                  label="Schedule and request context"
                  value={{
                    overview: displayDoc["overview_intent"],
                    request: displayView.request_context,
                  }}
                />
                <SavedDetails
                  label="Workflow references"
                  value={{
                    workflow_id: displayView.workflow_id,
                    version: displayView.workflow_version,
                    plan_revision: displayDoc.action_plan.revision,
                    run_id: displayView.run?.run_id,
                  }}
                />
              </div>
            </SheetContent>
          </Sheet>
          <div className="flex flex-wrap gap-2">
            {!adaptive &&
              displayView.run &&
              ["running", "queued", "paused_for_approval"].includes(displayView.run.status) && (
                <button
                  className={actionButton}
                  disabled={disabled || !backend.can("workflow.execute")}
                  onClick={() =>
                    void command.act("cancel:" + displayView.run!.run_id, {}, async () => {
                      await api.cancelComposition(id, displayView.run!.run_id);
                      update();
                    })
                  }
                >
                  Cancel run
                </button>
              )}
          </div>
          {needsQueryDefinition && displayDoc && <QueryClarification doc={doc!} view={view!} />}
          {displayView.run?.error_code && !needsQueryDefinition && !automation && (
            <p role="alert">
              {(doc?.["overview_intent"] as Record<string, unknown> | undefined)?.[
                "communication"
              ] ? (
                "A requested delivery needs attention. Confirmed email and Calendar results remain saved. Check the delivery status before retrying an action."
              ) : (
                <>
                  Execution: {displayView.run.error_code}. {displayView.recovery.reason}
                </>
              )}
            </p>
          )}
          {displayView.run?.approvals
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
          {displayView.run && automation && tab !== "background" && (
            <AutomationProgress
              run={displayView.run}
              onUpdated={update}
              onDetails={() => setTab("background")}
            />
          )}
          {displayView.run?.adaptive && (!automation || tab === "background") && (
            <AdaptiveProgress run={displayView.run} onUpdated={update} />
          )}
          {tab === "workflow" && (
            <div className="h-[65vh] min-h-[480px] overflow-hidden rounded-xl border">
              <CompositionCanvas view={displayView} onSelect={setPanel} />
            </div>
          )}
          {tab === "report" && (
            <div role="tabpanel" aria-label="Investigation report">
              <ApiFeedback error={detailError} /><CompositionReport view={inspectedView??displayView} />
              {Object.entries(displayView.run?.action_instances ?? {}).map(([id, instance]) => (
                <QueryEvidence key={id} instance={instance} />
              ))}
              {Object.values(displayView.run?.action_instances ?? {})
                .flatMap((instance) => receiptLinks(instance))
                .map((url) => (
                  <a
                    key={url}
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mx-5 block break-all text-sm text-primary underline"
                  >
                    Open verified artifact: {url}
                  </a>
                ))}
              {displayDoc.action_plan.actions
                .filter((a) => a.capability_id === "content.prepare")
                .map((a) => {
                  const output = displayView.run?.action_instances?.[a.action_id]?.output;
                  return output && typeof output["body"] === "string" && output["body"] ? (
                    <article key={a.action_id} className="mx-auto max-w-5xl space-y-3 p-5">
                      <h3 className="font-semibold">Generated report content</h3>
                      <p className="whitespace-pre-wrap break-words text-sm">{output["body"]}</p>
                    </article>
                  ) : null;
                })}
            </div>
          )}
          {tab === "steps" && (
            <ol className="space-y-3">
              {displayDoc.action_plan.actions.map((a, i) => {
                const task = displayView.tasks.find((t) => t.id === a.action_id);
                const instance = displayView.run?.action_instances?.[a.action_id];
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
                    <QueryEvidence instance={instance} />
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
            </ol>
          )}
          <ApiFeedback error={detailError} /><CompositionInspector view={inspectedView??displayView} section={panel} onClose={() => setPanel(null)} />
          {!demoData && (
            <p className="text-xs text-muted-foreground">
              ACTUAL source/provider reports, DERIVED values, INFERRED content and SYNTHETIC
              assumptions keep their provenance. Provider confirmation does not establish physical
              completion or commercial authorization.
            </p>
          )}
        </>
      )}
    </section>
  );
}
