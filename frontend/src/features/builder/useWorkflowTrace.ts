import { useEffect, useMemo, useState } from "react";
import { api, type RunRecord } from "@/api/client";
import { useBackend } from "@/api/state";
import { useRunFeed } from "@/features/runs/useRunFeed";
import { fromCanonical } from "@/api/mapping";
import type { StepStatus } from "@/domain/types";

export function useWorkflowTrace(workflowId: string, enabled = true) {
  const backend = useBackend();
  const available = enabled && backend.status === "connected" && !!backend.session?.runtime_available && backend.can("runs.view");
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [selection, setSelection] = useState("");
  const [revision, setRevision] = useState<{runId:string;value:ReturnType<typeof fromCanonical>}|null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [cursor,setCursor]=useState<string|null>(null);
  const [historyPage,setHistoryPage]=useState<string|undefined>();
  const [attempt, setAttempt] = useState(0);
  const runId = selection || runs[0]?.run_id || "";
  useEffect(() => {
    if (!available) return;
    let disposed = false;
    let timer: ReturnType<typeof setTimeout>;
    const refresh = async () => {
      try {
        const collection = await api.runs({workflow_id:workflowId,limit:50,cursor:historyPage});
        if (!disposed) {setRuns(current=>historyPage?[...new Map([...current,...collection.items].map(run=>[run.run_id,run])).values()]:collection.items);setCursor(collection.next_cursor??null);setError(null);}
      } catch (caught) {
        if (!disposed) setError(caught instanceof Error ? caught : new Error("Run history could not be loaded."));
      } finally { if (!disposed) timer = setTimeout(() => void refresh(), 5000); }
    };
    void refresh();
    return () => { disposed = true; clearTimeout(timer); };
  }, [available, workflowId, attempt,historyPage]);
  const feed=useRunFeed(runId,available,attempt);
  const historicalRunId=feed.run?.workflow_id===workflowId?feed.run.run_id:undefined;
  const historicalVersion=feed.run?.workflow_id===workflowId?feed.run.workflow_version:undefined;
  useEffect(()=>{
    if(!historicalRunId || !historicalVersion)return;
    let disposed=false;
    void api.request("get_workflow",{workflow_id:workflowId,workflow_version:historicalVersion}).then(result=>{
      if(result.workflow.workflow_id!==workflowId || result.workflow.version!==historicalVersion)throw new Error("The server returned a different historical revision.");
      if(!disposed){setRevision({runId:historicalRunId,value:fromCanonical(result.workflow)});setError(null);}
    }).catch(caught=>{if(!disposed)setError(caught instanceof Error?caught:new Error("Historical revision is unavailable."));});
    return()=>{disposed=true;};
  },[historicalRunId,historicalVersion,workflowId,attempt]);
  const current=useMemo(()=>available && feed.run?.workflow_id===workflowId && revision?.runId===runId?{run:feed.run,events:feed.events,revision:revision.value}:null,[available,feed.run,feed.events,workflowId,revision,runId]);
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
  return { available, runs, runId, selectRun: setSelection, run: current?.run ?? null, revision: current?.revision ?? null, events, runState, activeEdges, error:error??feed.error, loading:feed.loading, hasMoreRuns:!!cursor, loadMoreRuns:()=>setHistoryPage(cursor??undefined), hasMoreEvents:feed.hasMore, loadMoreEvents:feed.refresh, retry: () => setAttempt(n => n + 1) };
}
export type WorkflowTrace = ReturnType<typeof useWorkflowTrace>;
