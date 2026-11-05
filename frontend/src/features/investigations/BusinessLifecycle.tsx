"use client";
import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/api/client";
import { InputError } from "@/api/feedback";
import { useBackend } from "@/api/state";
import {
  type BusinessCase,
  type ProcessDefinition,
  type CaseOperation,
  fieldInputs,
  userFields,
  words,
} from "@/api/business-lifecycle";
import { type CompositionView } from "@/api/compositions";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";
import { CompositionInspector } from "./CompositionPanels";
import {
  LifecycleStages,
  LifecycleEvidence,
  LifecycleReport,
  SavedDetails,
  Outcome,
  EventForm,
} from "./LifecyclePanels";

import {GoogleAccountSelect} from "@/features/workflows/GoogleWorkflowConnection";
import {AdaptiveCasePanel} from "./AdaptiveCasePanel";

const button = "rounded-lg border px-3 py-2 text-sm disabled:opacity-40";
type Pending = {
  id: string | null;
  operation: CaseOperation | "create";
  body: Record<string, unknown>;
  simpson?: boolean;
  slot: string;
};
const terminal = (value: BusinessCase) =>
  ["COMPLETED", "COMPLETED_PROVISIONALLY", "CANCELLED"].includes(value.case_status);
export default function BusinessLifecycle({
  initialCaseId,
}: {
  initialCaseId?: string | undefined;
}) {
  const session = useBackend((s) => s.session);
  const status = useBackend((s) => s.status);
  if (status !== "connected" || !session)
    return (
      <p className="p-4 text-sm text-muted-foreground">
        Connect to the backend to open persistent cases.
      </p>
    );
  const scope = session.auth.subject.workspace_id + ":" + session.auth.subject.subject_id;
  return <LifecycleWorkspace key={scope} scope={scope} initialCaseId={initialCaseId} />;
}
function LifecycleWorkspace({
  scope,
  initialCaseId,
}: {
  scope: string;
  initialCaseId?: string | undefined;
}) {
  const backend = useBackend();
  const [packages, setPackages] = useState<Awaited<ReturnType<typeof api.clientPackages>>["items"]>(
    [],
  );
  const [packageKey, setPackageKey] = useState("");
  const [processes, setProcesses] = useState<ProcessDefinition[]>([]);
  const [processKey, setProcessKey] = useState("");
  const [index, setIndex] = useState<Awaited<ReturnType<typeof api.businessCases>>>({
    items: [],
    next_cursor: null,
  });
  const [savedId, setSavedId] = useState(initialCaseId ?? "");
  const [value, setValue] = useState<BusinessCase | null>(null);
  const [goal, setGoal] = useState("");
  const [googleConnection,setGoogleConnection]=useState("");
  const [inputs, setInputs] = useState<Record<string, string>>({});
  const [pane, setPane] = useState("Progress");
  const [error, setError] = useState<Error | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [uncertain, setUncertain] = useState(false);
  const [stop, setStop] = useState("");
  const [details, setDetails] = useState<Record<string, unknown>>({});
  const [composition, setComposition] = useState<CompositionView | null>(null);
  const [agentStage, setAgentStage] = useState("");
  const [drawer, setDrawer] = useState<string | null>(null);
  const lock = useRef(false);
  const issuing=useRef(false);
  const live = useRef(true);
  const pending = useRef<Pending | null>(null);
  const loadGeneration = useRef(0);
  const process = processes.find((p) => `${p.process_definition_id}:${p.version}` === processKey);
  const selectedPackage = packages.find((p) => `${p.package_id}:${p.revision}` === packageKey);
  const canWrite =
    backend.can("workflow.edit") && backend.session?.auth.scopes.includes("workspace:write");
  const canExecute =
    canWrite && backend.can("workflow.execute") && backend.session?.runtime_available;
  const canApprove =
    backend.can("workflow.approve") &&
    backend.session?.auth.roles.some((role) => role === "admin" || role === "approver");
  useEffect(() => {
    live.current = true;
    return () => {
      live.current = false;
    };
  }, []);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setValue(null);
    setError(null);
    Promise.all([
      api.businessCases(),
      api.businessProcesses(),
      api.simpsonProcess(),
      backend.can("workflow.plan") ? api.clientPackages() : Promise.resolve({ items: [] }),
    ])
      .then(async ([cases, catalogue, simpson, available]) => {
        const installed = await Promise.all(
          catalogue.items
            .filter(
              (p) =>
                p.process_definition_id !== simpson.process_definition_id ||
                p.version !== simpson.version,
            )
            .map((p) => api.businessProcess(p.process_definition_id, p.version)),
        );
        if (!active) return;
        setIndex(cases);
        setPackages(available.items);
        setProcesses([simpson, ...installed]);
        setProcessKey(`${simpson.process_definition_id}:${simpson.version}`);
        if (initialCaseId) await openCase(initialCaseId);
      })
      .catch((e) => {
        if (active)
          setError(
            e instanceof Error
              ? e
              : new InputError("Could not load saved lifecycle configuration."),
          );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
    // A keyed parent clears all scoped data before loading another identity.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scope, initialCaseId]);
  async function openCase(id: string, preserveStage = false) {
    const generation = ++loadGeneration.current;
    setValue(null);
    setDetails({});
    setComposition(null);
    setError(null);
    try {
      const saved = await api.businessCase(id);
      if (!live.current || generation !== loadGeneration.current) return;
      if (`${saved.workspace_id}:${saved.owner_id}` !== scope)
        throw new InputError("This case is outside the current workspace and owner.");
      setValue(saved);
      setSavedId(saved.case_id);
      setAgentStage(
        preserveStage && saved.stages[agentStage]?.composition_id ? agentStage :
        saved.process_definition.stages.find(
          (d) => saved.stages[d.stage_instance_id]?.composition_id,
        )?.stage_instance_id ?? "",
      );
    } catch (e) {
      if (live.current && generation === loadGeneration.current)
        setError(e instanceof Error ? e : new InputError("Could not open the saved case."));
    }
  }
  async function refresh() {
    if (value) await openCase(value.case_id, true);
    try {
      const list = await api.businessCases();
      if (live.current) setIndex(list);
    } catch (e) {
      if (live.current) setError(e as Error);
    }
  }
  async function choosePackage(key: string) {
    if (lock.current) return;
    setPackageKey(key);
    setInputs({});
    setProcessKey("");
    setError(null);
    setLoading(true);
    try {
      const selected = packages.find((p) => `${p.package_id}:${p.revision}` === key);
      const items = selected
        ? (await api.clientPackage(selected.package_id, selected.revision)).process_definitions
        : [
            await api.simpsonProcess(),
            ...(await Promise.all(
              (await api.businessProcesses()).items.map((p) =>
                api.businessProcess(p.process_definition_id, p.version),
              ),
            )),
          ];
      if (live.current) {
        setProcesses(items);
        setProcessKey(items[0] ? `${items[0].process_definition_id}:${items[0].version}` : "");
      }
    } catch (e) {
      setProcesses([]);
      setError(e as Error);
    } finally {
      if (live.current) setLoading(false);
    }
  }
  async function send(command: Pending) {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setError(null);
    let confirmed = false;
    try {
      const result =
        command.operation === "create"
          ? await api.createBusinessCase(command.body, command.simpson)
          : await api.businessCaseCommand(command.id!, command.operation, command.body);
      if (!live.current) return;
      confirmed = true;
      pending.current = null;
      setUncertain(false);
      try {
        sessionStorage.removeItem(command.slot);
      } catch {
        /* Storage is optional; the confirmed response is authoritative. */
      }
      const id = command.operation === "create" ? result.case_id : command.id!;
      if ("stop_reason" in result) setStop(String(result.stop_reason));
      else setStop("");
      await openCase(id);
      setIndex(await api.businessCases());
    } catch (e) {
      if (live.current) {
        if (confirmed) {
          setError(e as Error);
          return;
        }
        const rejected = e instanceof ApiError && e.context.outcome === "rejected";
        setError(
          e instanceof Error ? e : new InputError("The command response could not be confirmed."),
        );
        setUncertain(!rejected);
        if (rejected) {
          pending.current = null;
          try {
            sessionStorage.removeItem(command.slot);
          } catch {
            /* Keep command handling available without browser storage. */
          }
          if (command.id) await openCase(command.id);
          setError(e as Error);
        }
      }
    } finally {
      lock.current = false;
      if (live.current) setBusy(false);
    }
  }
  async function command(operation: CaseOperation | "create", extra: Record<string, unknown> = {}) {
    if (lock.current || issuing.current || uncertain) return;
    issuing.current=true;setBusy(true);
    try {
      let body: Record<string, unknown>;
      let simpson = false;
      if (operation === "create") {
        if (!process) throw new InputError("Choose an available process.");
        simpson =
          !selectedPackage &&
          process.process_definition_id === "simpson_warranty_lifecycle" &&
          process.version === 1;
        body = {
          original_user_goal: goal,
          ...(googleConnection?{google_connection_id:googleConnection}:{}),
          inputs: fieldInputs(process, inputs),
          ...(simpson
            ? {}
            : {
                process_definition_id: process.process_definition_id,
                process_definition_version: process.version,
              }),
          ...(selectedPackage
            ? {
                client_package_id: selectedPackage.package_id,
                client_package_revision: selectedPackage.revision,
              }
            : {}),
        };
      } else {
        if (!value) return;
        body = {
          ...(operation === "events"
            ? {}
            : operation === "drive"
              ? { max_commands: 16, max_seconds: 20, max_stage_executions: 32 }
              : { expected_revision: value.revision }),
          ...extra,
        };
      }
      const fingerprint = await crypto.subtle.digest(
        "SHA-256",
        new TextEncoder().encode(JSON.stringify({ id: value?.case_id, operation, body })),
      );
      const slot =
        `mesh-lifecycle-command-v1:${scope}:` +
        Array.from(new Uint8Array(fingerprint), (n) => n.toString(16).padStart(2, "0")).join("");
      let key: string;
      try {
        key = sessionStorage.getItem(slot) ?? crypto.randomUUID();
        sessionStorage.setItem(slot, key);
      } catch {
        key = crypto.randomUUID();
      }
      const next: Pending = {
        id: value?.case_id ?? null,
        operation,
        body: { ...body, request_key: key },
        simpson,
        slot,
      };
      pending.current = next;
      await send(next);
    } catch (e) {
      setError(e instanceof Error ? e : new InputError("Review the required process inputs."));
    } finally {
      issuing.current=false;if(live.current&&!lock.current)setBusy(false);
    }
  }
  useEffect(() => {
    if (!value) return;
    let active = true;
    setDetails({});
    setComposition(null);
    const read = async () => {
      if (pane === "Agents & tools") {
        const stage = value.stages[agentStage];
        if (stage?.composition_id) {
          const view = await api.compositionView(stage.composition_id, stage.run_id ?? undefined);
          if (active) setComposition(view);
        }
      } else if (pane === "Memory & recovery") {
        const names = ["memory", "learning", "recovery", "history", "reassessments"];
        const results = await Promise.allSettled(
          names.map((n) => api.businessCaseSection(value.case_id, n)),
        );
        if (active)
          setDetails(
            Object.fromEntries(
              results.map((r, i) => [
                names[i]!,
                r.status === "fulfilled" ? r.value : { unavailable: true },
              ]),
            ),
          );
      } else if (pane === "Report") {
        const report = await api.businessCaseSection(value.case_id, "report");
        if (active) setDetails(report);
      }
    };
    void read().catch((e) => {
      if (active) setError(e as Error);
    });
    return () => {
      active = false;
    };
  }, [value, pane, agentStage]);
  async function approval(
    operation: "validate_workflow" | "approve_workflow",
    decision?: {
      approval_id: string;
      decision: "approved" | "rejected";
      workflow_id: string;
      workflow_version: number;
    },
  ) {
    if (lock.current || !composition) return;
    lock.current = true;
    setBusy(true);
    setError(null);
    try {
      if (decision) await api.request("decide_approval", decision);
      else if (operation === "validate_workflow")
        await api.request(operation, {
          workflow_id: composition.workflow_id,
          workflow_version: composition.workflow_version!,
        });
      else
        await api.request(operation, {
          workflow_id: composition.workflow_id,
          workflow_version: composition.workflow_version!,
          action: "approve",
        });
      if (live.current) {
        setComposition(
          await api.compositionView(composition.composition_id, composition.run?.run_id),
        );
        await refresh();
      }
    } catch (e) {
      if (live.current) setError(e as Error);
    } finally {
      lock.current = false;
      if (live.current) setBusy(false);
    }
  }
  return (
    <section
      className="my-5 min-w-0 rounded-xl border bg-background p-4 md:p-5"
      aria-label="Persistent business lifecycle"
    >
      <div className="flex flex-wrap items-center gap-3">
        <h3 className="text-lg font-medium">Persistent business lifecycle</h3>
        <button
          className={button + " ml-auto"}
          disabled={busy || loading}
          onClick={() => void refresh()}
        >
          Refresh cases
        </button>
      </div>
      <ApiFeedback error={error} />
      {uncertain && (
        <div role="alert" className="my-3 rounded-lg border border-warning/40 p-3 text-sm">
          <p>
            The command outcome is uncertain. Refresh saved state before continuing. Retrying uses
            the same request key and exact payload.
          </p>
          <button
            disabled={busy || !pending.current}
            className={button + " mt-2"}
            onClick={() => {
              if (pending.current) void send(pending.current);
            }}
          >
            Retry same command
          </button>
        </div>
      )}
      <form
        className="my-4 flex flex-wrap items-end gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          void openCase(savedId);
        }}
      >
        <label className="min-w-0 flex-1 text-sm">
          Saved case
          <select
            aria-label="Saved lifecycle case"
            disabled={busy}
            value={index.items.some((i) => i.case_id === savedId) ? savedId : ""}
            onChange={(e) => setSavedId(e.target.value)}
            className="mt-1 w-full rounded-lg border bg-background p-2"
          >
            <option value="">Choose a saved case</option>
            {index.items.map((i) => (
              <option key={i.case_id} value={i.case_id}>
                {i.original_user_goal.slice(0, 75)} · {words(i.case_status)}
              </option>
            ))}
          </select>
        </label>
        <label className="min-w-0 flex-1 text-sm">
          Case ID
          <input
            aria-label="Lifecycle case ID"
            disabled={busy}
            value={savedId}
            onChange={(e) => setSavedId(e.target.value)}
            className="mt-1 w-full rounded-lg border bg-background p-2"
            required
          />
        </label>
        <button disabled={busy || !savedId} className={button}>
          Open case
        </button>
        {index.next_cursor && (
          <button
            type="button"
            disabled={busy}
            className={button}
            onClick={() =>
              void api.businessCases(index.next_cursor!).then(setIndex).catch(setError)
            }
          >
            Older cases
          </button>
        )}
      </form>
      <details open={!value} className="my-4 rounded-lg border p-3">
        <summary className="cursor-pointer text-sm font-medium">Create lifecycle case</summary>
        <form
          className="mt-4 space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            void command("create");
          }}
        >
          <div className="grid gap-3 md:grid-cols-2">
            <label className="text-sm">
              Client knowledge package
              <select
                disabled={busy || loading || uncertain}
                value={packageKey}
                onChange={(e) => void choosePackage(e.target.value)}
                className="mt-1 w-full rounded-lg border bg-background p-2"
              >
                <option value="">Available workspace processes</option>
                {packages.map((p) => (
                  <option
                    key={`${p.package_id}:${p.revision}`}
                    value={`${p.package_id}:${p.revision}`}
                  >
                    {p.client_id} · {p.package_id} v{p.revision}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm">
              Business process
              <select
                required
                disabled={busy || loading || uncertain}
                value={processKey}
                onChange={(e) => {
                  setProcessKey(e.target.value);
                  setInputs({});
                }}
                className="mt-1 w-full rounded-lg border bg-background p-2"
              >
                {processes.map((p) => (
                  <option
                    key={`${p.process_definition_id}:${p.version}`}
                    value={`${p.process_definition_id}:${p.version}`}
                  >
                    {p.process_definition_id} v{p.version} · {p.stages.length} stages
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label className="block text-sm">
            Investigation goal
            <textarea
              aria-label="Lifecycle investigation goal"
              disabled={busy || uncertain}
              required
              maxLength={4000}
              rows={2}
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              className="mt-1 w-full rounded-lg border bg-background p-2"
            />
          </label>
          <GoogleAccountSelect value={googleConnection} onChange={setGoogleConnection} disabled={busy||uncertain}/>
          <div className="grid gap-3 md:grid-cols-2">
            {process &&
              userFields(process).map(({ path, spec, required }) => {
                const type = spec.schema["type"];
                const options = spec.schema["enum"];
                return (
                  <label key={path} className="min-w-0 text-sm">
                    {words(path)}
                    {required ? " *" : ""}
                    {type === "boolean" || Array.isArray(options) ? (
                      <select
                        aria-label={words(path)}
                        value={inputs[path] ?? ""}
                        disabled={busy || uncertain}
                        required={required}
                        onChange={(e) => setInputs((v) => ({ ...v, [path]: e.target.value }))}
                        className="mt-1 w-full rounded-lg border bg-background p-2"
                      >
                        <option value="">Use available evidence or configured fallback</option>
                        {(Array.isArray(options) ? options : ["true", "false"]).map((o) => (
                          <option key={String(o)} value={String(o)}>
                            {String(o)}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        aria-label={words(path)}
                        value={inputs[path] ?? ""}
                        disabled={busy || uncertain}
                        required={required}
                        onChange={(e) => setInputs((v) => ({ ...v, [path]: e.target.value }))}
                        className="mt-1 w-full rounded-lg border bg-background p-2"
                      />
                    )}
                  </label>
                );
              })}
          </div>
          <button
            disabled={busy || loading || uncertain || !canWrite || !process}
            className={button + " bg-primary text-primary-foreground"}
          >
            Create case
          </button>
          {loading && (
            <p role="status" className="text-sm">
              Loading saved configuration…
            </p>
          )}
          <p className="text-xs text-muted-foreground">
            Unspecified fields use backend evidence and permitted case-local fallback. Analytical
            proposals do not authorize real actions.
          </p>
        </form>
      </details>
      {value && (
        <>
          <div className="space-y-3 border-t pt-4">
            <p className="break-words text-sm font-medium">{value.original_user_goal}</p>
            <p className="break-words text-xs text-muted-foreground">
              {value.case_id} · {value.client_id} · {value.process_definition_id} v
              {value.process_definition_version} · Revision {value.revision}
            </p>
            <p className="text-xs">
              Updated <time dateTime={value.updated_at}>{value.updated_at}</time>
            </p>
            <div className="flex flex-wrap gap-3">
              <p className="text-sm">
                Execution: <Outcome value={value.execution_status} />
              </p>
              <p className="text-sm">
                Business outcome: <Outcome value={value.business_outcome_status} />
              </p>
            </div>
            <p className="text-xs text-muted-foreground">
              Analytical completion does not confirm business authorization or physical activity.
            </p>
            <div className="flex flex-wrap gap-2">
              {(["prepare", "start", "drive", "resume", "cancel"] as const).map((op) => (
                <button
                  key={op}
                  disabled={
                    busy ||
                    uncertain ||
                    (!!value["adaptive"] && ["start", "resume"].includes(op)) ||
                    terminal(value) ||
                    !canWrite ||
                    (op !== "prepare" && !canExecute) ||
                    (op === "prepare" && !!value.prepared_at) ||
                    (op !== "prepare" && op !== "cancel" && !value.prepared_at)
                  }
                  className={button}
                  onClick={() => {
                    if (
                      op !== "cancel" ||
                      window.confirm("Cancel this case and its active runtime work?")
                    )
                      void command(op);
                  }}
                >
                  {op === "drive"
                    ? "Drive / continue"
                    : words(op).replace(/^./, (c) => c.toUpperCase())}
                </button>
              ))}
              <button disabled={busy} className={button} onClick={() => void refresh()}>
                Refresh status
              </button>
              <button className={button} onClick={() => setPane("Report")}>
                Inspect report
              </button>
            </div>
            {stop && (
              <p role="status" className="text-xs">
                Driver stopped: {words(stop)}. Further execution requires an explicit command.
              </p>
            )}
          </div>
          <AdaptiveCasePanel key={value.case_id} value={value} onSnapshot={setValue}/>
          <nav aria-label="Lifecycle inspection" className="my-4 flex flex-wrap gap-2">
            {[
              "Progress",
              "Agents & tools",
              "Evidence & assumptions",
              "Pending activities",
              "Memory & recovery",
              "Report",
            ].map((p) => (
              <button
                key={p}
                className={button + (pane === p ? " bg-muted font-medium" : "")}
                aria-pressed={pane === p}
                onClick={() => setPane(p)}
              >
                {p}
              </button>
            ))}
          </nav>
          {pane === "Progress" && <LifecycleStages value={value} />}
          {pane === "Evidence & assumptions" && <LifecycleEvidence value={value} />}
          {pane === "Agents & tools" && (
            <section className="space-y-3">
              <h3 className="font-medium">Agent and tool execution</h3>
              <label className="block text-sm">
                Stage execution
                <select
                  aria-label="Agent stage"
                  value={agentStage}
                  onChange={(e) => { setComposition(null); setAgentStage(e.target.value); }}
                  className="mt-1 w-full rounded-lg border bg-background p-2"
                >
                  <option value="">Choose a capability stage</option>
                  {value.process_definition.stages
                    .filter((d) => value.stages[d.stage_instance_id]?.composition_id)
                    .map((d) => (
                      <option key={d.stage_instance_id} value={d.stage_instance_id}>
                        {d.name}
                      </option>
                    ))}
                </select>
              </label>
              {!composition ? (
                <p className="text-sm text-muted-foreground">
                  Select a stage with a saved agent composition.
                </p>
              ) : (
                <>
                  <p className="text-sm">
                    Workflow {composition.workflow_status ?? "not saved"} · Run{" "}
                    {composition.run?.status ?? "not started"}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    <button className={button} onClick={() => setDrawer("agents")}>
                      Inspect master and specialists
                    </button>
                    <button className={button} onClick={() => setDrawer("memory")}>
                      Inspect runtime recovery
                    </button>
                    {composition.workflow_status === "draft" && (
                      <button
                        className={button}
                        disabled={busy || !backend.can("workflow.validate")}
                        onClick={() => void approval("validate_workflow")}
                      >
                        Validate workflow
                      </button>
                    )}
                    {composition.workflow_status === "validated" && (
                      <button
                        className={button}
                        disabled={busy || !canApprove}
                        onClick={() => void approval("approve_workflow")}
                      >
                        Approve workflow
                      </button>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    These are the existing workflow and action gates. After approval, use Drive /
                    continue on the case.
                  </p>
                  {composition.run?.approvals
                    .filter((a) => a.status === "pending")
                    .map((a) => (
                      <article className="rounded-lg border p-3" key={a.approval_id}>
                        <h4 className="text-sm font-medium">External action approval required</h4>
                        <SavedDetails
                          label="Exact prepared action"
                          value={a.resolved_payload ?? composition.run?.actions}
                        />
                        {a.allowed_decisions.map((decision) => (
                          <button
                            key={decision}
                            disabled={busy || !canApprove}
                            className={button + " mt-2 mr-2"}
                            onClick={() =>
                              void approval("approve_workflow", {
                                approval_id: a.approval_id,
                                workflow_id: a.workflow_id,
                                workflow_version: a.workflow_version,
                                decision,
                              })
                            }
                          >
                            {decision === "approved" ? "Approve action" : "Reject action"}
                          </button>
                        ))}
                      </article>
                    ))}
                  <SavedDetails
                    label="Saved tool calls and verified receipts"
                    value={value.stages[agentStage]?.tool_execution_records}
                  />
                  <CompositionInspector
                    view={composition}
                    section={drawer}
                    onClose={() => setDrawer(null)}
                  />
                </>
              )}
            </section>
          )}
          {pane === "Pending activities" && (
            <section className="space-y-3">
              <h3 className="font-medium">Pending real-world activities</h3>
              {Object.entries(value.waits).map(([id, w]) => {
                const stage = value.stages[String(w["stage_instance_id"])];
                const requirement = stage?.definition.external_event_requirements.find(
                  (r) => r["event_type"] === w["event_type"],
                );
                const maySubmit =
                  canWrite &&
                  backend.can("events.ingest") &&
                  (!requirement?.["requires_authorization"] || canApprove) &&
                  ["PENDING", "TIMED_OUT"].includes(String(w["current_status"]));
                return (
                  <article className="min-w-0 rounded-lg border p-3" key={id}>
                    <h4 className="text-sm font-medium">{words(String(w["event_type"]))}</h4>
                    <p className="mt-1 text-xs">
                      {String(w["current_status"])} · Expected source {String(w["expected_source"])}
                    </p>
                    <p className="mt-1 text-xs">
                      Deadline:{" "}
                      {typeof w["deadline"] === "number"
                        ? new Date(w["deadline"] * 1000).toISOString()
                        : "Unavailable"}
                    </p>
                    <SavedDetails
                      label="Correlation and event contract"
                      value={{
                        correlation_keys: w["correlation_keys"],
                        schema: requirement?.["schema"],
                      }}
                    />
                    {maySubmit && (
                      <details className="mt-3">
                        <summary className="cursor-pointer text-sm">
                          Submit authenticated source event
                        </summary>
                        <EventForm
                          wait={w}
                          disabled={busy || uncertain}
                          onSubmit={(body) => void command("events", body)}
                        />
                      </details>
                    )}
                  </article>
                );
              })}
              {Object.keys(value.waits).length === 0 && (
                <p className="text-sm text-muted-foreground">No saved event waits.</p>
              )}
            </section>
          )}
          {pane === "Memory & recovery" && (
            <section className="space-y-3">
              <h3 className="font-medium">Memory, learning and reassessment</h3>
              <p className="text-xs text-muted-foreground">
                Experience recommendations are advisory. Execution feedback does not independently
                verify business outcomes.
              </p>
              {Object.entries(details).map(([name, data]) => (
                <SavedDetails key={name} label={words(name)} value={data} />
              ))}
              <SavedDetails label="New evidence conflicts" value={value.conflicts} />
              {value.conflicts
                .filter(
                  (c) =>
                    c["reason"] === "late_event_requires_downstream_reassessment" &&
                    !c["resolved_by"],
                )
                .map((conflict, i) => (
                  <ReassessmentForm
                    key={i}
                    conflict={conflict}
                    disabled={busy || uncertain || !canExecute}
                    onSubmit={(body) => void command("reassess", body)}
                  />
                ))}
              {(value.reassessments ?? []).map((r, i) => (
                <button
                  key={i}
                  className={button}
                  onClick={() =>
                    void api
                      .businessCaseRevision(value.case_id, Number(r["original_revision"]))
                      .then((original) =>
                        setDetails((d) => ({
                          ...d,
                          ["Original revision " + original.revision]: original,
                        })),
                      )
                      .catch(setError)
                  }
                >
                  Inspect original revision {String(r["original_revision"])}
                </button>
              ))}
            </section>
          )}
          {pane === "Report" &&
            (Object.keys(details).length ? (
              <LifecycleReport value={value} report={details} />
            ) : (
              <p role="status" className="text-sm">
                Loading saved report…
              </p>
            ))}
        </>
      )}
    </section>
  );
}
function ReassessmentForm({
  conflict,
  disabled,
  onSubmit,
}: {
  conflict: Record<string, unknown>;
  disabled: boolean;
  onSubmit: (body: Record<string, unknown>) => void;
}) {
  const [bindings, setBindings] = useState("");
  const [error, setError] = useState("");
  const event = conflict["event"] as Record<string, unknown>;
  return (
    <details className="rounded-lg border p-3">
      <summary className="cursor-pointer text-sm">
        Review late evidence for {String(conflict["stage"])}
      </summary>
      <SavedDetails label="Saved authenticated event" value={event} />
      <form
        className="mt-3 space-y-2"
        onSubmit={(e) => {
          e.preventDefault();
          try {
            const parsed: unknown = JSON.parse(bindings);
            if (
              !parsed ||
              typeof parsed !== "object" ||
              Array.isArray(parsed) ||
              Object.values(parsed).some((v) => typeof v !== "string")
            )
              throw new Error();
            setError("");
            onSubmit({
              event_id: event["event_id"],
              source: event["source"],
              input_bindings: parsed,
            });
          } catch {
            setError(
              "Map declared stage input names to saved event payload paths in a JSON object.",
            );
          }
        }}
      >
        <label className="block text-xs">
          Reviewed input bindings
          <textarea
            required
            rows={3}
            value={bindings}
            onChange={(e) => setBindings(e.target.value)}
            className="mt-1 w-full rounded-lg border bg-background p-2 font-mono"
          />
        </label>
        <p className="text-xs text-muted-foreground">
          Original conclusions are archived. Only affected analytical stages can rerun; uncertain
          writes require reconciliation.
        </p>
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        <button disabled={disabled} className={button}>
          Create reviewed reassessment
        </button>
      </form>
    </details>
  );
}
