"use client";
import { useEffect, useState } from "react";
import { api } from "@/api/client";
import { GoogleAccountSelect } from "@/features/workflows/GoogleWorkflowConnection";
import { useBackend } from "@/api/state";
import { type ActionDocument, receiptLinks } from "@/api/orchestration";
import { type CompositionView } from "@/api/compositions";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";
import { SavedDetails, Outcome } from "./LifecyclePanels";
import { useOrchestrationCommand } from "./useOrchestrationCommand";

export const actionButton = "rounded-lg border px-3 py-2 text-sm disabled:opacity-40";
export function ConnectedPlan({
  id,
  runId,
  onRun,
  adaptive = false,
}: {
  id: string;
  runId?: string | undefined;
  onRun?: (id: string) => void;
  adaptive?: boolean;
}) {
  const backend = useBackend();
  const command = useOrchestrationCommand();
  const [doc, setDoc] = useState<ActionDocument | null>(null);
  const [view, setView] = useState<CompositionView | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [refresh, setRefresh] = useState(0);
  const [stale, setStale] = useState(true);
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
        if (d.scope.workspace + ":" + d.scope.owner !== scope)
          throw new Error("Plan is outside the selected workspace.");
        setDoc(d);
        setView(v);
        setError(null);
        setStale(false);
        timer = setTimeout(() => void read(), 3000);
      } catch (e) {
        if (live) {
          setError(e as Error);
          setStale(true);
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
  async function workflowAction(
    operation:
      "save_workflow_version" | "validate_workflow" | "approve_workflow" | "execute_workflow",
  ) {
    if (!view) return;
    const ref = { workflow_id: view.workflow_id, workflow_version: view.workflow_version ?? 1 };
    await command.act(
      id + ":" + operation,
      { ...ref, run_id: view.run?.run_id ?? null },
      async (body) => {
        if (operation === "save_workflow_version") {
          const workflow = await api.compositionWorkflow(id);
          await api.request(
            operation,
            {
              workflow_id: workflow.workflow_id,
              workflow_version: workflow.version,
              base_version: 0,
              workflow,
            },
            String(body["request_key"]),
          );
        } else if (operation === "validate_workflow") await api.request(operation, ref);
        else if (operation === "approve_workflow")
          await api.request(operation, { ...ref, action: "approve" });
        else {
          const result = await api.request(
            operation,
            { ...ref, inputs: {} },
            String(body["request_key"]),
          );
          onRun?.(result.run.run_id);
        }
        update();
      },
    );
  }
  const disabled = command.busy || stale || command.unknown;
  return (
    <section aria-label="Connected action plan" className="min-w-0 space-y-4 rounded-xl border p-4">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="font-semibold">Connected action plan</h2>
        <button className={actionButton} disabled={command.busy} onClick={update}>
          Refresh plan
        </button>
      </div>
      <ApiFeedback error={error ?? command.error} />
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
          <p className="break-words text-sm">{doc.action_plan.goal}</p>
          <p className="text-xs">
            Plan revision {doc.action_plan.revision} ·{" "}
            {view.run?.status ?? view.workflow_status ?? "Not saved"} · Account:{" "}
            {doc.google_connection_id ?? "Existing server connection"}
          </p>
          <GoogleAccountSelect
            value={doc.google_connection_id ?? ""}
            onChange={() => {}}
            disabled
          />
          <SavedDetails
            label="Completion criteria and missing inputs"
            value={{
              completion_criteria: doc.action_plan.completion_criteria,
              missing_inputs: doc.action_plan.missing_inputs,
            }}
          />
          <div className="flex flex-wrap gap-2">
            {!view.workflow_status && (
              <button
                className={actionButton}
                disabled={disabled || !backend.can("workflow.edit")}
                onClick={() => void workflowAction("save_workflow_version")}
              >
                Save workflow draft
              </button>
            )}
            {view.workflow_status === "draft" && (
              <button
                className={actionButton}
                disabled={disabled || !backend.can("workflow.validate")}
                onClick={() => void workflowAction("validate_workflow")}
              >
                Validate workflow
              </button>
            )}
            {view.workflow_status === "validated" && (
              <button
                className={actionButton}
                disabled={disabled || !backend.can("workflow.approve")}
                onClick={() => void workflowAction("approve_workflow")}
              >
                Approve workflow
              </button>
            )}
            {!adaptive &&
              !view.run &&
              ["approved", "published"].includes(view.workflow_status ?? "") && (
                <button
                  className={actionButton}
                  disabled={
                    disabled ||
                    !backend.can("workflow.execute") ||
                    !backend.session?.runtime_available
                  }
                  onClick={() => void workflowAction("execute_workflow")}
                >
                  Run reviewed plan
                </button>
              )}
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
          {view.run?.error_code && (
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
          <ol className="space-y-3">
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
