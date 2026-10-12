import { useEffect, useMemo, useState } from "react";
import { api, type RunRecord } from "@/api/client";
import { useBackend } from "@/api/state";
import { reconcileEvents } from "@/api/control";
import type { RunEvent } from "@/api/contracts.generated";
import type { StepStatus } from "@/domain/types";

export function useWorkflowTrace(workflowId: string) {
  const backend = useBackend();
  const available = backend.status === "connected" && !!backend.session?.runtime_available && backend.can("runs.view");
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [selection, setSelection] = useState("");
  const [record, setRecord] = useState<{ run: RunRecord; events: RunEvent[] } | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(false);
  const runId = selection || runs[0]?.run_id || "";
  useEffect(() => {
    if (!available) return;
    let disposed = false;
    let timer: ReturnType<typeof setTimeout>;
    const refresh = async () => {
      try {
        const collection = await api.runs();
        if (!disposed) setRuns(collection.items.filter((run) => run.workflow_id === workflowId));
      } catch (caught) {
        if (!disposed) setError(caught instanceof Error ? caught : new Error("Run history could not be loaded."));
      } finally { if (!disposed) timer = setTimeout(() => void refresh(), 5000); }
    };
    void refresh();
    return () => { disposed = true; clearTimeout(timer); };
  }, [available, workflowId]);
  useEffect(() => {
    if (!available || !runId) return;
    let disposed = false;
    let timer: ReturnType<typeof setTimeout>;
    const refresh = async () => {
      setLoading(true);
      try {
        const result = await api.request("get_run", { run_id: runId });
        if (result.run.workflow_id !== workflowId) throw new Error("This run belongs to another workflow.");
        const timeline = await api.request("list_run_events", { run_id: runId });
        const events = reconcileEvents([], timeline.items, result.run);
        if (!disposed) { setRecord({ run: result.run, events }); setError(null); }
      } catch (caught) {
        if (!disposed) { setRecord(null); setError(caught instanceof Error ? caught : new Error("Trace loading failed.")); }
      } finally {
        if (!disposed) { setLoading(false); timer = setTimeout(() => void refresh(), 3000); }
      }
    };
    void refresh();
    return () => { disposed = true; clearTimeout(timer); };
  }, [available, runId, workflowId]);
  const current = available && record?.run.run_id === runId && record.run.workflow_id === workflowId ? record : null;
  const events = useMemo(() => current?.events ?? [], [current]);
  const runState = useMemo(() => {
    const states: Record<string, StepStatus | "running"> = {};
    for (const event of events) {
      const id = event.details?.["node_id"];
      if (typeof id !== "string") continue;
      const type = event.event_type;
      if (type === "node.started" || type === "node.observed" || type === "node.retry") states[id] = "running";
      if (type === "node.completed") states[id] = "success";
      if (type === "node.skipped") states[id] = "skipped";
      if (type === "node.failed") states[id] = event.details?.["status"] === "blocked" ? "blocked" : "failed";
      if (type === "approval.pending") states[id] = "paused";
      if (type === "approval.rejected") states[id] = "rejected";
      if (type === "approval.timed_out") states[id] = "failed";
    }
    return states;
  }, [events]);
  const activeEdges = useMemo(() => new Set(events.flatMap((event) => Array.isArray(event.details?.["selected_edges"]) ? event.details["selected_edges"].filter((id): id is string => typeof id === "string") : [])), [events]);
  return { available, runs, runId, selectRun: setSelection, run: current?.run ?? null, events, runState, activeEdges, error, loading };
}
export type WorkflowTrace = ReturnType<typeof useWorkflowTrace>;
