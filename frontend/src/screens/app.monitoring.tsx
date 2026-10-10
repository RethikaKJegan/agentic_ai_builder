"use client";
import { useEffect, useState } from "react";
import { PageHeader } from "@/features/runs/RunTrace";

type Monitoring = { runs: { total: number; active: number; completed: number; failed: number }; status_breakdown?: Record<string, number>; duration_seconds?: { avg: number }; events: number; usage: { llm_calls: number; tool_calls: number; tokens: number; retries: number; estimated_cost_usd: number }; latest: { run_id: string; status: string; correlation_id: string; trace_reference: string }[];
  sources?: { binding_id: string; workflow_id: string; provider_id: string; health: string; error_code?: string; baseline_ready: boolean; last_successful_poll?: string }[];
  policies?: { workflow_id: string; version: number; action_approval_required: boolean; agents: { agent_id: string; guardrails: Record<string, boolean>; limits: { max_llm_calls: number; max_tool_calls: number; max_retries: number } }[] }[];
  audit?: { event_id: string; event_type: string; run_id: string; timestamp: string }[];
};

export function LiveRuntimePanel() {
  const [data, setData] = useState<Monitoring | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const response = await fetch("/api/backend/monitoring", { credentials: "same-origin", cache: "no-store" });
        const envelope = await response.json();
        if (!response.ok) throw new Error(envelope?.data?.error?.message ?? "Monitoring is unavailable.");
        if (!cancelled) { setData(envelope.data); setError(null); }
      } catch (caught) { if (!cancelled) setError(caught instanceof Error ? caught.message : "Monitoring is unavailable."); }
    };
    void load();
    const timer = window.setInterval(() => void load(), 5000);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, []);
  return <div className="space-y-6">
    {error && <p className="rounded-xl border border-dashed border-border p-6 text-sm text-muted-foreground">{error}</p>}
    {!error && !data && <p className="rounded-xl border border-dashed border-border p-6 text-sm text-muted-foreground">Loading monitoring data…</p>}
    {data && <><div className="grid gap-3 md:grid-cols-4">{[["Runs", data.runs.total], ["Active", data.runs.active], ["Completed", data.runs.completed], ["Failed", data.runs.failed]].map(([label, value]) => <div key={String(label)} className="rounded-xl border border-border p-4"><p className="text-xs text-muted-foreground">{label}</p><p className="mt-1 text-2xl font-semibold">{value}</p></div>)}</div>
      <div className="rounded-xl border border-border p-4"><p className="font-medium">Runtime usage</p><p className="mt-2 text-sm text-muted-foreground">{data.events} events · {data.usage.tool_calls} tool calls · {data.usage.llm_calls} model calls · {data.usage.tokens} tokens · ${Number(data.usage.estimated_cost_usd).toFixed(4)} estimated</p></div>
      <div className="rounded-xl border border-border p-4"><p className="font-medium">Live trigger health</p>{(data.sources ?? []).map(source => <div key={source.binding_id} className="mt-3 text-sm"><p>{source.workflow_id} · {source.provider_id} · {source.health}</p>{source.error_code && <p className="text-destructive">{source.error_code}: polling failed before dispatch. The checkpoint is retained for retry.</p>}<p className="text-xs text-muted-foreground">{source.baseline_ready ? "Baseline established" : "Waiting for baseline"} · Last successful poll: {source.last_successful_poll ?? "none"}</p></div>)}{!data.sources?.length && <p className="mt-2 text-sm text-muted-foreground">No registered triggers.</p>}</div>
      <div className="rounded-xl border border-border p-4"><p className="font-medium">Reviewed workflow guardrails</p>{(data.policies ?? []).map(policy => <div key={policy.workflow_id} className="mt-3 text-sm"><p>{policy.workflow_id} · v{policy.version} · {policy.action_approval_required ? "Action approval required" : "No workflow action approval gate"}</p>{policy.agents.map(agent => <div key={agent.agent_id} className="mt-2 text-xs text-muted-foreground"><p>{agent.agent_id}</p><p>{Object.entries(agent.guardrails ?? {}).map(([key, enabled]) => `${key}: ${enabled ? "on" : "off"}`).join(" · ")}</p><p>Model calls ≤ {agent.limits.max_llm_calls} · Tool calls ≤ {agent.limits.max_tool_calls} · Retries ≤ {agent.limits.max_retries}</p></div>)}</div>)}</div>
      <div className="rounded-xl border border-border p-4"><p className="font-medium">Runtime audit</p>{(data.audit ?? []).map(event => <p key={event.event_id} className="mt-2 text-xs text-muted-foreground">{event.timestamp} · {event.event_type} · {event.run_id}</p>)}{!data.audit?.length && <p className="mt-2 text-sm text-muted-foreground">No runtime audit events yet.</p>}</div>
      <div className="rounded-xl border border-border p-4"><p className="font-medium">Run status distribution</p><div className="mt-4 space-y-2">{Object.entries(data.status_breakdown ?? {}).map(([status, count]) => <div key={status} className="flex items-center gap-3 text-xs"><span className="w-32 text-muted-foreground">{status}</span><div className="h-2 flex-1 rounded bg-muted"><div className="h-2 rounded bg-primary" style={{ width: `${data.runs.total ? Math.max(2, (count / data.runs.total) * 100) : 0}%` }} /></div><span>{count}</span></div>)}</div><p className="mt-4 text-xs text-muted-foreground">Average completed duration: {Number(data.duration_seconds?.avg ?? 0).toFixed(2)}s</p></div>
      <div className="rounded-xl border border-border"><p className="border-b border-border p-4 font-medium">Recent traces</p>{data.latest.length === 0 ? <p className="p-6 text-sm text-muted-foreground">No runtime traces yet.</p> : data.latest.map((run) => <div key={run.run_id} className="border-b border-border p-4 last:border-0"><p className="text-sm font-medium">{run.run_id} · {run.status}</p><p className="mt-1 text-xs text-muted-foreground">{run.correlation_id} · {run.trace_reference}</p></div>)}</div>
    </>}
  </div>;
}

export default function Screen() {
  return <div className="mx-auto max-w-5xl space-y-6 p-6 md:p-10"><PageHeader title="Monitoring" sub="Workspace-scoped runtime usage, source health, guardrails and audit events." /><LiveRuntimePanel /></div>;
}
