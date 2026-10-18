"use client";
import { displayText } from "@/lib/display-text";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/api/client";
import {
  databaseStepSchema,
  type DatabaseStep,
  type DatabaseOperation,
} from "@/api/data-operations";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";
import { Link } from "@/lib/navigation";

const button = "rounded-lg border px-3 py-2 text-sm disabled:opacity-40";
const input = "mt-1 w-full min-w-0 rounded-lg border bg-background p-2 text-sm";

export default function DatabaseOperations({ canManage }: { canManage: boolean }) {
  const [status, setStatus] = useState<Awaited<ReturnType<typeof api.databaseOperations>>>();
  const [error, setError] = useState<Error>();
  const [targetId, setTargetId] = useState("");
  const [action, setAction] = useState<DatabaseStep["action"]>("create");
  const [identity, setIdentity] = useState("{}");
  const [values, setValues] = useState("{}");
  const [unset, setUnset] = useState("[]");
  const [steps, setSteps] = useState<DatabaseStep[]>([]);
  const [operation, setOperation] = useState<DatabaseOperation>();
  const [record, setRecord] = useState<Awaited<ReturnType<typeof api.readDatabaseRecord>>>();
  const [reviewed, setReviewed] = useState(false);
  const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  const alive = useRef(true);
  const prepareKey = useRef<{ body: string; key: string } | undefined>(undefined);
  const recoveryKey = useRef<{ operationId: string; key: string } | undefined>(undefined);
  const load = useCallback(async () => {
    const result = await api.databaseOperations();
    if (alive.current) setStatus(result);
  }, []);
  useEffect(() => {
    alive.current = true;
    void load().catch((e) => setError(e));
    return () => {
      alive.current = false;
    };
  }, [load]);
  const target =
    status?.targets.find((t) => `${t.connection_id}:${t.dataset_id}` === targetId) ??
    status?.targets[0];
  const operationId = operation?.operation_id;
  const running = operation?.state === "running";
  useEffect(() => {
    if (!operationId || !running) return;
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const value = await api.databaseOperation(operationId!);
        if (active) {
          setOperation(value);
          if (value.state === "running") timer = setTimeout(() => void poll(), 1500);
        }
      } catch (e) {
        if (active)
          setError(
            e instanceof Error
              ? e
              : new Error("Refresh the operation status before taking another action."),
          );
      }
    }
    void poll();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [operationId, running]);
  async function run(task: () => Promise<void>) {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setError(undefined);
    try {
      await task();
    } catch (e) {
      if (alive.current)
        setError(
          e instanceof Error
            ? e
            : new Error(
                "The operation response could not be confirmed. Inspect its history before continuing.",
              ),
        );
    } finally {
      lock.current = false;
      if (alive.current) setBusy(false);
    }
  }
  function addStep() {
    try {
      if (!target) throw new Error("Choose an authorized dataset.");
      const step = databaseStepSchema.parse({
        connection_id: target.connection_id,
        dataset_id: target.dataset_id,
        action,
        identity: JSON.parse(identity),
        values: action === "delete" ? {} : JSON.parse(values),
        unset_fields: action === "update" ? JSON.parse(unset) : [],
      });
      if (!target.operations.includes(action))
        throw new Error("This operation is not authorized for the selected dataset.");
      setSteps((current) => [...current, step]);
      setOperation(undefined);
      setReviewed(false);
      setError(undefined);
    } catch {
      setError(
        new Error(
          "Check the action and JSON fields. Use exact identity keys and permitted scalar field values.",
        ),
      );
    }
  }
  const recoverable =
    operation &&
    !operation.recovery_of &&
    ["succeeded", "partial"].includes(operation.state) &&
    operation.steps.some((step) => step.state === "succeeded" && step.affected_records > 0);
  return (
    <section aria-label="Database operations" className="min-w-0 space-y-5">
      <div>
        <h2 className="text-xl font-semibold">Database operations</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Read a record or prepare controlled create, update and delete operations. Nothing is
          written until you execute a reviewed operation.
        </p>
      </div>
      <ApiFeedback error={error} onRetry={() => void run(load)} />
      {!status && !error && <p role="status">Loading authorized database targets…</p>}
      {status && status.targets.length === 0 && (
        <p role="status" className="rounded-xl border p-4 text-sm">
          No database operation targets are enabled for your account. A server policy must
          explicitly allow the datasets, operations and writable fields.
        </p>
      )}
      {target && (
        <div className="min-w-0 space-y-4 rounded-xl border p-4">
          <label className="block text-sm">
            Operation dataset
            <select
              className={input}
              disabled={busy || running}
              value={`${target.connection_id}:${target.dataset_id}`}
              onChange={(e) => {
                setTargetId(e.target.value);
                setRecord(undefined);
              }}
            >
              {status?.targets.map((t) => (
                <option
                  key={`${t.connection_id}:${t.dataset_id}`}
                  value={`${t.connection_id}:${t.dataset_id}`}
                >
                  {displayText(t.label)}
                </option>
              ))}
            </select>
          </label>
          <p className="break-words text-xs text-muted-foreground">
            Identity: {target.identity_fields.join(", ")} · Writable fields:{" "}
            {target.writable_fields.join(", ") || "none"}
          </p>
          <label className="block text-sm">
            Record identity (JSON)
            <textarea
              className={input}
              rows={3}
              value={identity}
              disabled={busy || running}
              onChange={(e) => {
                setIdentity(e.target.value);
                setRecord(undefined);
              }}
              placeholder={JSON.stringify(
                Object.fromEntries(target.identity_fields.map((name) => [name, "DEMO-001"])),
              )}
            />
          </label>
          <button
            className={button}
            disabled={!canManage || busy || running || !target.operations.includes("read")}
            onClick={() =>
              void run(async () => {
                const result = await api.readDatabaseRecord({
                  connection_id: target.connection_id,
                  dataset_id: target.dataset_id,
                  identity: JSON.parse(identity),
                });
                if (alive.current) setRecord(result);
              })
            }
          >
            Read record
          </button>
          {record && (
            <section aria-label="Record read result" className="min-w-0 rounded border p-3 text-sm">
              <p>
                {record.matched_records} record matched · {displayText(record.label)}
              </p>
              <pre className="mt-2 overflow-auto whitespace-pre-wrap break-all text-xs">
                {displayText(JSON.stringify(record.record, null, 2))}
              </pre>
            </section>
          )}
          <label className="block text-sm">
            Database action
            <select
              className={input}
              value={action}
              disabled={busy || running}
              onChange={(e) => setAction(e.target.value as DatabaseStep["action"])}
            >
              {(["create", "update", "delete"] as const).map((value) => (
                <option key={value} disabled={!target.operations.includes(value)} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          {action !== "delete" && (
            <label className="block text-sm">
              Field values (JSON)
              <textarea
                className={input}
                rows={4}
                aria-label="Field values (JSON)"
                value={values}
                disabled={busy || running}
                onChange={(e) => setValues(e.target.value)}
              />
              <span className="text-xs text-muted-foreground">
                Use native field names and scalar values. Enter exact decimal amounts as strings.
                Identity fields are separate.
              </span>
            </label>
          )}
          {action === "update" && target.engine === "mongodb" && (
            <label className="block text-sm">
              Remove fields (JSON array)
              <textarea
                className={input}
                rows={2}
                value={unset}
                disabled={busy || running}
                onChange={(e) => setUnset(e.target.value)}
              />
            </label>
          )}
          {action === "delete" && (
            <p className="rounded border p-3 text-sm">
              Delete removes the exact record. Recovery requires retained evidence, current
              inverse-operation permissions and unchanged state; it is not an unconditional Undo.
            </p>
          )}
          <button
            className={button}
            disabled={
              !canManage ||
              busy ||
              running ||
              steps.length >= 4 ||
              !target.operations.includes(action)
            }
            onClick={addStep}
          >
            Add operation step
          </button>
        </div>
      )}
      {!!steps.length && (
        <section aria-label="Draft database steps" className="space-y-3 rounded-xl border p-4">
          <h3 className="font-medium">Draft steps ({steps.length}/4)</h3>
          <p className="text-xs text-muted-foreground">
            Each step targets one distinct record. Cross-database steps commit independently; later
            failure can leave earlier changes committed.
          </p>
          {steps.map((step, index) => (
            <div key={index} className="min-w-0 rounded border p-3 text-xs">
              <p>
                {index + 1}. {step.action} ·{" "}
                {status?.targets.find(
                  (t) => t.dataset_id === step.dataset_id && t.connection_id === step.connection_id,
                )?.label ?? step.dataset_id}
              </p>
              <pre className="mt-2 overflow-auto whitespace-pre-wrap break-all">
                {displayText(JSON.stringify(
                  { identity: step.identity, values: step.values, remove: step.unset_fields },
                  null,
                  2,
                ))}
              </pre>
            </div>
          ))}
          <button
            className={button}
            disabled={!canManage || busy || running}
            onClick={() =>
              void run(async () => {
                const body = JSON.stringify(steps);
                if (prepareKey.current?.body !== body)
                  prepareKey.current = { body, key: crypto.randomUUID() };
                const result = await api.prepareDatabaseOperation(steps, prepareKey.current.key);
                if (alive.current) {
                  setOperation(result);
                  setReviewed(false);
                }
                await load();
              })
            }
          >
            Prepare operation
          </button>
        </section>
      )}
      {operation && (
        <section
          aria-label="Reviewed database operation"
          className="min-w-0 space-y-4 rounded-xl border p-4"
        >
          <h3 className="break-all font-medium">Operation {operation.operation_id}</h3>
          <p role="status">State: {operation.state}</p>
          {operation.recovery_of && (
            <p className="break-all text-sm">
              Compensating operation for {operation.recovery_of}. Review every inverse change before
              execution.
            </p>
          )}
          {operation.steps.map((step, index) => (
            <article key={index} className="min-w-0 rounded border p-3 text-sm">
              <p className="break-words font-medium">
                {index + 1}. {step.action} · {displayText(step.label)}
              </p>
              <p className="mt-1 text-xs">
                {step.tool_id} · {step.state} · matched {step.matched_records} · affected{" "}
                {step.affected_records}
              </p>
              {step.error_code && (
                <p role="alert" className="mt-2 text-xs">
                  {step.error_code}: the step did not report a successful confirmed commit.
                </p>
              )}
              {operation.preview_available && (
                <pre className="mt-2 max-h-80 overflow-auto whitespace-pre-wrap break-all text-xs">
                  {displayText(JSON.stringify(
                    {
                      identity: step.identity,
                      changes: step.values,
                      remove: step.unset_fields,
                      before: step.before,
                      after: step.after,
                    },
                    null,
                    2,
                  ))}
                </pre>
              )}
            </article>
          ))}
          {operation.workflow_run_id && <p className="break-words rounded border p-3 text-sm">
            This operation belongs to run {operation.workflow_run_id}. Review and execute it in the originating workflow's Execution tab.
            {operation.workflow_id && <Link className="ml-2 underline" to={`/app/workflows/${encodeURIComponent(operation.workflow_id)}`}>Open workflow</Link>}
          </p>}
          {operation.state === "prepared" && !operation.workflow_run_id && (
            <>
              <p className="text-xs text-muted-foreground">
                Prepared until {new Date(operation.expires_at * 1000).toLocaleTimeString()}.
                Existing records must still match the preview. Hard deletes and all inverse
                operations remain explicit.
              </p>
              <label className="flex items-start gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={reviewed}
                  disabled={busy || !operation.preview_available}
                  onChange={(e) => setReviewed(e.target.checked)}
                />
                I reviewed every target, field change and delete in this operation.
              </label>
              <button
                className={button}
                disabled={!canManage || busy || !reviewed || !operation.preview_available}
                onClick={() =>
                  void run(async () => {
                    const result = await api.executeDatabaseOperation(operation.operation_id);
                    if (alive.current) {
                      setOperation(result);
                      setReviewed(false);
                    }
                    await load();
                  })
                }
              >
                Execute reviewed operation
              </button>
            </>
          )}
          {!operation.preview_available && operation.state === "prepared" && (
            <p className="text-sm">
              The preview is unavailable under current policy or metadata. Prepare a fresh
              authorized operation.
            </p>
          )}
          {operation.state === "uncertain" && (
            <p role="alert" className="rounded border p-3 text-sm">
              The commit outcome is uncertain. This operation will not be replayed or automatically
              compensated. Reconcile the affected source records before preparing corrective
              changes.
            </p>
          )}
          {operation.state === "partial" && (
            <p role="alert" className="text-sm">
              Some steps committed before another step failed. Inspect each outcome; no shared
              cross-database rollback occurred.
            </p>
          )}
          <button
            className={button}
            disabled={busy}
            onClick={() =>
              void run(async () => {
                const result = await api.databaseOperation(operation.operation_id);
                if (alive.current) setOperation(result);
              })
            }
          >
            Refresh operation status
          </button>
          {recoverable && (
            <button
              className={button}
              disabled={!canManage || busy || operation.recovery_until * 1000 <= Date.now()}
              onClick={() =>
                void run(async () => {
                  if (recoveryKey.current?.operationId !== operation.operation_id)
                    recoveryKey.current = {
                      operationId: operation.operation_id,
                      key: crypto.randomUUID(),
                    };
                  const result = await api.recoverDatabaseOperation(
                    operation.operation_id,
                    recoveryKey.current.key,
                  );
                  if (alive.current) {
                    setOperation(result);
                    setReviewed(false);
                  }
                  await load();
                })
              }
            >
              Prepare guarded recovery
            </button>
          )}
          {operation.recovery_operation_id && (
            <p className="break-all text-xs">Linked recovery: {operation.recovery_operation_id}</p>
          )}
        </section>
      )}
      <button
        className={button}
        disabled={busy || running}
        onClick={() => {
          setSteps([]);
          setIdentity("{}");
          setValues("{}");
          setUnset("[]");
          setOperation(undefined);
          setRecord(undefined);
          setReviewed(false);
          prepareKey.current = undefined;
          recoveryKey.current = undefined;
        }}
      >
        New operation
      </button>
      {!!status?.items.length && (
        <section aria-label="Database operation history" className="space-y-2">
          <h3 className="font-medium">Recent operations</h3>
          {status.items.map((item) => (
            <button
              key={item.operation_id}
              className={`${button} block max-w-full break-all text-left`}
              disabled={busy}
              onClick={() =>
                void run(async () => {
                  const result = await api.databaseOperation(item.operation_id);
                  if (alive.current) {
                    setOperation(result);
                    setReviewed(false);
                  }
                })
              }
            >
              {item.operation_id} · {item.state}
            </button>
          ))}
        </section>
      )}
    </section>
  );
}
