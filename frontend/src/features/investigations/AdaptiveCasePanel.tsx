"use client";
import { useEffect, useState } from "react";
import { api } from "@/api/client";
import { type BusinessCase } from "@/api/business-lifecycle";
import { adaptiveSchema, objectInput } from "@/api/orchestration";
import { useBackend } from "@/api/state";
import { GoogleAccountSelect } from "@/features/workflows/GoogleWorkflowConnection";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";
import { ConnectedPlan, actionButton } from "./ConnectedPlan";
import { AutomationPanel } from "./DurableAutomation";
import { SavedDetails } from "./LifecyclePanels";
import { useOrchestrationCommand } from "./useOrchestrationCommand";

export function AdaptiveCasePanel({
  value,
  onSnapshot,
}: {
  value: BusinessCase;
  onSnapshot: (value: BusinessCase) => void;
}) {
  const backend = useBackend();
  const command = useOrchestrationCommand();
  const parsed = adaptiveSchema.safeParse(value["adaptive"]);
  const adaptive = parsed.success ? parsed.data : null;
  const [stage, setStage] = useState("");
  const [google, setGoogle] = useState("");
  const [userValues, setUserValues] = useState("{}");
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [error, setError] = useState<Error | null>(null);
  const [refresh, setRefresh] = useState(0);
  const [fresh, setFresh] = useState(false);
  const scope = backend.session
    ? backend.session.auth.subject.workspace_id + ":" + backend.session.auth.subject.subject_id
    : "";
  useEffect(() => {
    let live = true;
    let timer: ReturnType<typeof setTimeout>;
    setFresh(false);
    async function read() {
      try {
        const saved = await api.businessCase(value.case_id);
        if (!live) return;
        if (saved.workspace_id + ":" + saved.owner_id !== scope)
          throw new Error("Saved case is outside the current workspace.");
        onSnapshot(saved);
        setFresh(true);
        setError(null);
        timer = setTimeout(() => void read(), 3000);
      } catch (e) {
        if (live) {
          setError(e as Error);
          setFresh(false);
        }
      }
    }
    void read();
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [value.case_id, scope, refresh, onSnapshot]);
  const pending = adaptive?.pending_wait;
  const writable =
    backend.can("workflow.execute") &&
    backend.can("workflow.edit") &&
    backend.session?.auth.scopes.includes("workspace:write");
  const blocked = command.busy || command.unknown || !fresh || !writable;
  return (
    <section
      className="my-4 min-w-0 space-y-4 rounded-xl border p-4"
      aria-label="Adaptive case orchestration"
    >
      <h2 className="font-semibold">Adaptive investigation</h2>
      <ApiFeedback error={error ?? command.error} />
      {command.unknown && (
        <p role="alert">
          Command outcome is unconfirmed. Refresh the case to inspect its command history before
          retrying the identical request.
        </p>
      )}
      {command.unknown && (
        <button className={actionButton} disabled={command.busy} onClick={command.retry}>
          Retry identical command
        </button>
      )}
      <button
        className={actionButton}
        disabled={command.busy}
        onClick={() => setRefresh((n) => n + 1)}
      >
        Refresh adaptive state
      </button>
      {!adaptive ? (
        <form
          className="space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            try {
              const user_values = objectInput(userValues);
              void command.act(
                "enable:" + value.case_id,
                {
                  expected_revision: value.revision,
                  stage_instance_id: stage,
                  plan_request: {
                    user_values,
                    ...(google ? { google_connection_id: google } : {}),
                  },
                },
                async (body) => {
                  onSnapshot(await api.adaptiveCommand(value.case_id, "enable", body));
                },
              );
            } catch (e) {
              command.setError(e as Error);
            }
          }}
        >
          <p className="text-sm text-muted-foreground">
            Enable on a prepared, idle ready stage compatible with connected actions. The existing
            process definitions, output requirements and authorization boundaries still apply.
          </p>
          <label className="block text-sm">
            Ready stage
            <select
              aria-label="Adaptive ready stage"
              required
              className="mt-1 w-full rounded-lg border bg-background p-2"
              value={stage}
              onChange={(e) => setStage(e.target.value)}
            >
              <option value="">Select a ready stage</option>
              {Object.values(value.stages)
                .filter((s) => s.execution_status === "READY" && !s.composition_id && !s.run_id)
                .map((s) => (
                  <option key={s.stage_instance_id} value={s.stage_instance_id}>
                    {s.definition.name}
                  </option>
                ))}
            </select>
          </label>
          <GoogleAccountSelect value={google} onChange={setGoogle} />
          <label className="block text-sm">
            Explicit recipient and resource inputs
            <textarea
              aria-label="Adaptive user values"
              className="mt-1 w-full rounded-lg border bg-background p-2"
              rows={3}
              value={userValues}
              onChange={(e) => setUserValues(e.target.value)}
            />
          </label>
          <button
            className={actionButton}
            disabled={blocked || !value.prepared_at || !stage || !backend.can("workflow.plan")}
          >
            Enable adaptive planning
          </button>
        </form>
      ) : (
        <>
          <ol aria-label="Five-state orchestration" className="flex flex-wrap gap-2">
            {["UNDERSTAND", "PLAN", "GATHER_AND_ASSESS", "EXECUTE", "EVALUATE"].map((phase) => (
              <li
                key={phase}
                aria-current={adaptive.phase === phase ? "step" : undefined}
                className={
                  "rounded-lg border px-2 py-1 text-xs " +
                  (adaptive.phase === phase
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground")
                }
              >
                {phase.replaceAll("_", " ")}
              </li>
            ))}
          </ol>
          <p role="status" className="text-sm">
            {adaptive.phase} · {adaptive.status} · Plan revision {adaptive.plan_revision ?? 0} ·
            Case revision {value.revision}
          </p>
          <button
            className={actionButton}
            disabled={blocked || !!pending || ["blocked", "completed"].includes(adaptive.status)}
            onClick={() =>
              void command.act(
                "drive:" + value.case_id,
                {
                  case_revision: value.revision,
                  max_commands: 16,
                  max_stage_executions: 32,
                  max_seconds: 20,
                },
                async (body) => {
                  const { case_revision: _, ...request } = body;
                  await api.businessCaseCommand(value.case_id, "drive", request);
                  onSnapshot(await api.businessCase(value.case_id));
                },
              )
            }
          >
            Continue bounded evaluation
          </button>
          {adaptive.status === "blocked" && (
            <p role="alert">
              Execution is blocked. Inspect saved failures and effect receipts. Unknown writes and
              interrupted evaluator calls require operator reconciliation before continuation.
            </p>
          )}
          {pending && (
            <div className="space-y-3 rounded-lg border border-warning/50 p-3">
              <h3 className="text-sm font-medium">
                {pending.kind === "input"
                  ? "Missing information required"
                  : "Waiting for external evidence"}
              </h3>
              <p className="text-xs">
                {String(pending["reason"] ?? "")} · Deadline:{" "}
                {new Date(pending.deadline * 1000).toISOString()}
              </p>
              <SavedDetails label="Saved wait requirements" value={pending} />
              {pending.kind === "input" && (
                <form
                  className="space-y-2"
                  onSubmit={(e) => {
                    e.preventDefault();
                    try {
                      const inputs = Object.fromEntries(
                        Object.entries(pending.schemas ?? {}).map(([key, schema]) => {
                          const text = answers[key] ?? "";
                          return [key, schema["type"] === "string" ? text : JSON.parse(text)];
                        }),
                      );
                      void command.act(
                        "supply:" + value.case_id,
                        { expected_revision: value.revision, wait_id: pending.wait_id, inputs },
                        async (body) => {
                          onSnapshot(await api.adaptiveCommand(value.case_id, "supply", body));
                          setAnswers({});
                        },
                      );
                    } catch (e) {
                      command.setError(e as Error);
                    }
                  }}
                >
                  {Object.entries(pending.schemas ?? {}).map(([name, schema]) => (
                    <label className="block text-sm" key={name}>
                      {name}
                      <input
                        aria-label={"Requested " + name}
                        required
                        value={answers[name] ?? ""}
                        onChange={(e) => setAnswers((a) => ({ ...a, [name]: e.target.value }))}
                        className="mt-1 w-full rounded-lg border bg-background p-2"
                        placeholder={
                          schema["type"] === "string"
                            ? "Enter the actual value"
                            : "Enter a value matching the displayed schema"
                        }
                      />
                    </label>
                  ))}
                  <button className={actionButton} disabled={blocked}>
                    Supply requested information
                  </button>
                </form>
              )}
            </div>
          )}
          {adaptive.composition_id && (
            <ConnectedPlan
              key={adaptive.composition_id}
              id={adaptive.composition_id}
              runId={adaptive.run_id ?? undefined}
              adaptive
            />
          )}
          <SavedDetails
            label="Evaluator decisions, evidence gaps and plan revision history"
            value={{
              decisions: adaptive.decisions,
              revision_history: adaptive.revision_history,
              observations: adaptive["observations"],
              usage: adaptive["reasoning_usage"],
              failures: adaptive["failure"],
              wait_history: adaptive["wait_history"],
            }}
          />
          <AutomationPanel
            target={
              pending
                ? {
                    caseId: value.case_id,
                    waitId: pending.wait_id,
                    stageId: adaptive.stage_instance_id,
                  }
                : undefined
            }
          />
        </>
      )}
    </section>
  );
}
