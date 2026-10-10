"use client";
import { useState } from "react";
import { api, type ApprovalRecord, type RunRecord } from "@/api/client";
import { useBackend } from "@/api/state";
import type { RunEvent } from "@/api/contracts.generated";
import { assertRunTransition, reconcileEvents } from "@/api/control";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";
import { StatusPill } from "@/features/shell/StatusPill";

export function ApprovalControl({ approval, onUpdated }: { approval: ApprovalRecord; onUpdated?: (() => void) | undefined }) {
  const backend = useBackend();
  const [record, setRecord] = useState(approval);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const decide = async (decision: "approved" | "rejected") => {
    if (busy) return;
    setBusy(true); setError(null);
    try {
      const result = await api.request("decide_approval", { approval_id: record.approval_id, workflow_id: record.workflow_id,
        workflow_version: record.workflow_version, decision });
      setRecord(result); onUpdated?.();
    } catch (caught) { setError(caught instanceof Error ? caught : new Error("The decision failed.")); }
    finally { setBusy(false); }
  };
  return <div className="space-y-2 rounded-lg border border-border p-3">
    <p className="text-sm">Approval {record.approval_id} · {record.status} · v{record.workflow_version}</p>
    {record.status === "pending" && backend.session?.approval_service_available && backend.can("workflow.approve") && <div className="flex gap-2">{record.allowed_decisions.map((decision) => <button key={decision} className="rounded-lg border border-border px-3 py-1.5 text-xs disabled:opacity-40" disabled={busy} onClick={() => void decide(decision)}>{decision === "approved" ? "Approve" : "Reject"}</button>)}</div>}
    {record.status === "unmatched" && <p className="text-xs text-muted-foreground">This approval does not match the current workflow revision.</p>}
    <ApiFeedback error={error} />
  </div>;
}

export function ServerRunView({ approvalsOnly = false }: { approvalsOnly?: boolean }) {
  const backend = useBackend();
  const [runId, setRunId] = useState("");
  const [run, setRun] = useState<RunRecord | null>(null);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const load = async () => {
    if (!runId.trim() || busy) return;
    setBusy(true); setError(null);
    try {
      const result = await api.request("get_run", { run_id: runId.trim() });
      if (run?.run_id === result.run.run_id) {
        if (run.workflow_id !== result.run.workflow_id || run.workflow_version !== result.run.workflow_version) throw new Error("The runtime changed the workflow revision for an existing run.");
        assertRunTransition(run.status, result.run.status);
      }
      const timeline = await api.request("list_run_events", { run_id: result.run.run_id });
      const incoming = reconcileEvents(run?.run_id === result.run.run_id ? events : [], timeline.items, result.run);
      setRun(result.run); setEvents(incoming);
    } catch (caught) { setError(caught instanceof Error ? caught : new Error("Run loading failed.")); }
    finally { setBusy(false); }
  };
  if (!backend.session?.runtime_available) return <p className="rounded-2xl border border-dashed border-border p-10 text-center text-sm text-muted-foreground">The runtime API is not connected. No {approvalsOnly ? "approval requests" : "execution records"} are available.</p>;
  return <div className="space-y-4">
    <form onSubmit={(event) => { event.preventDefault(); void load(); }} className="flex gap-2">
      <input aria-label="Run ID" value={runId} onChange={(event) => setRunId(event.target.value)} className="min-w-0 flex-1 rounded-lg border border-border px-3 py-2 text-sm" placeholder="Run ID from an execution response" />
      <button disabled={busy || !runId.trim()} className="rounded-lg border border-border px-4 text-sm disabled:opacity-40">{busy ? "Loading…" : "Load run"}</button>
    </form>
    <ApiFeedback error={error} />
    {run && <><p className="text-sm">{run.run_id} · {run.workflow_id} · v{run.workflow_version} <StatusPill status={run.status} /></p>
      {run.approvals.map((approval) => {
        const matched = approval.workflow_id === run.workflow_id && approval.workflow_version === run.workflow_version;
        const record = matched ? approval : { ...approval, status: "unmatched" as const, allowed_decisions: [] };
        return <ApprovalControl key={`${record.approval_id}:${record.status}`} approval={record} onUpdated={() => void load()} />;
      })}
      {!approvalsOnly && <ol className="divide-y divide-border rounded-xl border border-border" aria-label="Run events">{events.map((event) => <li key={event.event_id} className="p-3"><p className="text-sm">{event.event_type}</p><p className="text-xs text-muted-foreground">{event.timestamp} · {event.source} · {event.event_id} · v{event.workflow_version}</p></li>)}</ol>}
    </>}
  </div>;
}
