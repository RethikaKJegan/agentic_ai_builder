import type { WorkflowNode } from "@/domain/types";
import type { WorkflowTrace } from "./useWorkflowTrace";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";
import { StatusPill } from "@/features/shell/StatusPill";

function Evidence({ title, value }: { title: string; value: unknown }) {
  return <section className="space-y-1"><h3 className="text-sm font-semibold">{title}</h3>{value === undefined ? <p className="text-xs text-muted-foreground">Not captured for this run.</p> : <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-muted/50 p-3 text-xs">{typeof value === "string" ? value : JSON.stringify(value, null, 2)}</pre>}</section>;
}
export function NodeTrace({ node, trace }: { node: WorkflowNode; trace: WorkflowTrace }) {
  const events = trace.events.filter((event) => event.details?.["node_id"] === node.id);
  const observed = events.filter((event) => event.event_type === "node.observed").at(-1)?.details;
  const completed = events.filter((event) => event.event_type === "node.completed").at(-1)?.details;
  const decisions = events.filter((event) => event.event_type === "agent.decision");
  const last = events.at(-1);
  const status = trace.runState[node.id];
  const first = events.find((event) => event.event_type === "node.observed" || event.event_type === "node.started");
  const duration = first && last && completed ? Math.max(0, Date.parse(last.timestamp) - Date.parse(first.timestamp)) : undefined;
  const retries = events.filter((event) => event.event_type === "node.retry").length;
  const decision = completed?.["outcome"] ?? (status === "skipped" ? "Skipped" : status === "paused" ? "Waiting for approval" : status === "failed" || status === "blocked" ? last?.details?.["error_code"] : completed ? "Completed" : undefined);
  const explanation = completed?.["explanation"] ?? (status === "skipped" ? last?.details?.["explanation"] : completed && completed["output"] !== undefined && node.data.kind === "agent" ? "The agent returned the recorded output below. Any explanation supplied by the agent is included in that output; no additional rationale was recorded." : completed && Array.isArray(completed["selected_edges"]) ? "The step completed and selected the recorded successor edges." : undefined);
  return <div className="space-y-4" aria-label="Node execution trace">
    <ApiFeedback error={trace.error} />
    {!trace.available ? <p className="text-sm text-muted-foreground">Execution traces require a connected runtime and permission to view runs.</p> : !trace.runId ? <p className="text-sm text-muted-foreground">No recorded runs for this workflow yet.</p> : !trace.run ? <p role="status" className="text-sm">{trace.loading ? "Loading execution trace…" : "Execution trace unavailable."}</p> : <>
      <p className="break-all text-xs text-muted-foreground">{trace.run.run_id} · revision v{trace.run.workflow_version}</p>
      <StatusPill status={status ?? "not executed"} />
      {!events.length && <p className="text-sm text-muted-foreground">This step has no recorded events in the selected run. It may not have been reached or may belong to a different revision.</p>}
      <p className="text-xs text-muted-foreground">{duration === undefined ? "Timing not recorded or execution pending" : `${duration} ms recorded duration`} · {retries} retries</p>
      <Evidence title="Observation" value={observed?.["observation"]} />
      <Evidence title="Decision" value={decision} />
      <Evidence title="How the decision was made" value={completed?.["expression"] !== undefined ? { expression: completed["expression"], evaluated_value: completed["evaluated_value"] } : observed ? { kind: observed["kind"], agent_id: observed["agent_id"], tool_id: observed["tool_id"], policy: observed["policy"] } : undefined} />
      <Evidence title="Why" value={explanation} />
      {decisions.length > 0 && <Evidence title="Delegation decisions" value={decisions.map((event) => ({ invocation_id: event.details?.["invocation_id"], action: event.details?.["action"], explanation: event.details?.["explanation"], decision: event.details?.["output"] }))} />}
      <Evidence title="Result" value={completed?.["output"]} />
      <Evidence title="Next steps" value={completed?.["next_nodes"]} />
      <section><h3 className="text-sm font-semibold">Timeline · {events.length} events</h3><ol className="mt-2 space-y-2">{events.map((event) => <li key={event.event_id} className="rounded-lg border border-border p-2 text-xs"><p className="font-medium">{event.event_type}</p><time className="text-muted-foreground">{new Date(event.timestamp).toLocaleString()}</time><details className="mt-1"><summary className="cursor-pointer">Recorded details</summary><pre className="overflow-auto whitespace-pre-wrap break-words pt-2">{JSON.stringify(event.details, null, 2)}</pre></details></li>)}</ol></section>
    </>}
  </div>;
}
