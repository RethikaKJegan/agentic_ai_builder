"use client";
import { displayText } from "@/lib/display-text";
import { useEffect, useState } from "react";
import { api } from "@/api/client";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";
import { ServerRunView } from "@/features/runs/ServerRunView";
import { PageHeader } from "@/features/runs/RunTrace";

type Monitoring=Awaited<ReturnType<typeof api.monitoring>>;

export function LiveRuntimePanel() {
  const [data, setData] = useState<Monitoring | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [cursor,setCursor]=useState<{source_cursor?:string|undefined;policy_cursor?:string|undefined}>({});
  useEffect(() => {
    let cancelled = false;
    let timer:ReturnType<typeof setTimeout>;
    const load = async () => {
      try {
        const result=await api.monitoring(cursor);
        if (!cancelled) { setData(result); setError(null); }
      } catch (caught) { if (!cancelled) setError(caught instanceof Error ? caught : new Error("Monitoring is unavailable.")); }
      finally {if(!cancelled)timer=setTimeout(()=>void load(),5000);}
    };
    void load();
    return () => { cancelled = true; clearTimeout(timer); };
  }, [cursor]);
  return <div className="space-y-6">
    <p className="text-xs text-muted-foreground">Bounded polling every 15 seconds; persisted records remain authoritative. Enforced policies are read-only and scoped to the displayed revision.</p>
    <ApiFeedback error={error} />
    {!error && !data && <p className="rounded-xl border border-dashed border-border p-6 text-sm text-muted-foreground">Loading monitoring data…</p>}
    {data && <><div className="grid gap-3 md:grid-cols-4">{[["Runs", data.runs.total], ["Active", data.runs.active], ["Completed", data.runs.completed], ["Failed", data.runs.failed]].map(([label, value]) => <div key={String(label)} className="rounded-xl border border-border p-4"><p className="text-xs text-muted-foreground">{displayText(label)}</p><p className="mt-1 text-2xl font-semibold">{value}</p></div>)}</div>
      <div className="rounded-xl border border-border p-4"><p className="font-medium">Runtime usage</p><p className="mt-2 text-sm text-muted-foreground">{data.events} events · {data.usage.tool_calls} tool calls · {data.usage.llm_calls} model calls · {data.usage.tokens} tokens · ${Number(data.usage.estimated_cost_usd).toFixed(4)} estimated</p></div>
      <div className="rounded-xl border border-border p-4"><p className="font-medium">Live trigger health</p>{(data.sources ?? []).map(source => <div key={source.binding_id} className="mt-3 text-sm"><p>{source.workflow_id} · {source.provider_id} · {source.health}</p><p className="text-xs text-muted-foreground">Release: {source.release_state ?? "unknown"} · v{source.workflow_version ?? "unknown"} · Trigger: {source.delivery ?? "unknown"} / {source.event_type ?? "unknown"} · Source: {source.source ?? "not provided"}</p><p className="text-xs text-muted-foreground">Preparation: {source.preparation_succeeded ? "succeeded" : "not ready"}{source.schedule ? ` · Schedule: ${source.schedule} (${source.timezone ?? "timezone missing"})` : ""}</p>{source.release_state !== "active" && <p className="text-xs">This release cannot receive active automation events.</p>}{source.error_code && <p className="text-destructive">{source.error_code}: polling failed before dispatch. The checkpoint is retained for retry.</p>}<p className="text-xs text-muted-foreground">{source.baseline_ready ? "Baseline established" : "Waiting for baseline"} · Last successful poll: {source.last_successful_poll ?? "none"}</p></div>)}{!data.sources?.length && <p className="mt-2 text-sm text-muted-foreground">No registered triggers.</p>}</div>
      <div className="rounded-xl border border-border p-4"><p className="font-medium">Backend-enforced revision guardrails</p>{(data.policies ?? []).map(policy => <div key={policy.workflow_id} className="mt-3 text-sm"><p>{policy.workflow_id} · v{policy.version} · {policy.scope ?? "current workspace"} · {policy.enforcement ?? "approved revision"} · Policy version {policy.policy_version ?? "revision-bound"} · {policy.action_approval_required ? "Action approval required" : "No workflow action approval gate"}</p>{policy.agents.map(agent => <div key={agent.agent_id} className="mt-2 text-xs text-muted-foreground"><p>{agent.agent_id}</p><p>{Object.entries(agent.guardrails ?? {}).map(([key, enabled]) => `${key}: ${enabled ? "on" : "off"}`).join(" · ")}</p><p>Model calls ≤ {agent.limits.max_llm_calls} · Tool calls ≤ {agent.limits.max_tool_calls} · Retries ≤ {agent.limits.max_retries}</p></div>)}</div>)}</div>
      <div className="rounded-xl border border-border p-4"><p className="font-medium">Runtime audit</p>{(data.audit ?? []).map(event => <p key={event.event_id} className="mt-2 text-xs text-muted-foreground">{event.timestamp} · {event.event_type} · {event.run_id}</p>)}{!data.audit?.length && <p className="mt-2 text-sm text-muted-foreground">No runtime audit events yet.</p>}</div>
      <div className="rounded-xl border border-border p-4"><p className="font-medium">Run status distribution</p><div className="mt-4 space-y-2">{Object.entries(data.status_breakdown ?? {}).map(([status, count]) => <div key={status} className="flex items-center gap-3 text-xs"><span className="w-32 text-muted-foreground">{status}</span><div className="h-2 flex-1 rounded bg-muted"><div className="h-2 rounded bg-primary" style={{ width: `${data.runs.total ? Math.max(2, (count / data.runs.total) * 100) : 0}%` }} /></div><span>{count}</span></div>)}</div><p className="mt-4 text-xs text-muted-foreground">Average completed duration: {Number(data.duration_seconds?.avg ?? 0).toFixed(2)}s</p></div>
      <div className="rounded-xl border border-border"><p className="border-b border-border p-4 font-medium">Recent traces</p>{data.latest.length === 0 ? <p className="p-6 text-sm text-muted-foreground">No runtime traces yet.</p> : data.latest.map((run) => <div key={run.run_id} className="border-b border-border p-4 last:border-0"><p className="text-sm font-medium">{run.run_id} · {run.status}</p><p className="mt-1 text-xs text-muted-foreground">{run.correlation_id} · {run.trace_reference}</p></div>)}</div>
      <div className="flex flex-wrap gap-2"><button type="button" disabled={!cursor.source_cursor && !cursor.policy_cursor} onClick={()=>setCursor({})} className="rounded border px-3 py-2 text-xs disabled:opacity-40">First readiness page</button>{data.source_next_cursor && <button type="button" onClick={()=>setCursor({...cursor,source_cursor:data.source_next_cursor??undefined})} className="rounded border px-3 py-2 text-xs">More triggers</button>}{data.policy_next_cursor && <button type="button" onClick={()=>setCursor({...cursor,policy_cursor:data.policy_next_cursor??undefined})} className="rounded border px-3 py-2 text-xs">More enforced revisions</button>}</div>
    </>}
  </div>;
}

export default function Screen() {
  return <div className="mx-auto max-w-5xl space-y-6 p-6 md:p-10"><PageHeader title="Monitoring" sub="Workspace-scoped runtime usage, source health, guardrails and audit events." /><LiveRuntimePanel /><section className="space-y-4"><h2 className="text-lg font-medium">Filtered run history</h2><ServerRunView /></section></div>;
}
