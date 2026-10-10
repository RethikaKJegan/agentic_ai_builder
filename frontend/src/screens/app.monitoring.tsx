"use client";
import { useEffect, useState } from "react";
import { PageHeader } from "@/features/runs/RunTrace";

type Monitoring = { runs: { total: number; active: number; completed: number; failed: number }; events: number; usage: { llm_calls: number; tool_calls: number; tokens: number; retries: number; estimated_cost_usd: number }; latest: { run_id: string; status: string; correlation_id: string; trace_reference: string }[] };

export default function Screen() {
  const [data, setData] = useState<Monitoring | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const response = await fetch("/api/backend/monitoring", { credentials: "same-origin", cache: "no-store" });
        const envelope = await response.json();
        if (!response.ok) throw new Error(envelope?.data?.error?.message ?? "Monitoring is unavailable.");
        if (!cancelled) setData(envelope.data);
      } catch (caught) { if (!cancelled) setError(caught instanceof Error ? caught.message : "Monitoring is unavailable."); }
    };
    void load();
    const timer = window.setInterval(() => void load(), 5000);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, []);
  return <div className="mx-auto max-w-5xl space-y-6 p-6 md:p-10"><PageHeader title="Monitoring" sub="Workspace-scoped runtime usage, events and trace references." />
    {error && <p className="rounded-xl border border-dashed border-border p-6 text-sm text-muted-foreground">{error}</p>}
    {!error && !data && <p className="rounded-xl border border-dashed border-border p-6 text-sm text-muted-foreground">Loading monitoring data…</p>}
    {data && <><div className="grid gap-3 md:grid-cols-4">{[["Runs", data.runs.total], ["Active", data.runs.active], ["Completed", data.runs.completed], ["Failed", data.runs.failed]].map(([label, value]) => <div key={String(label)} className="rounded-xl border border-border p-4"><p className="text-xs text-muted-foreground">{label}</p><p className="mt-1 text-2xl font-semibold">{value}</p></div>)}</div>
      <div className="rounded-xl border border-border p-4"><p className="font-medium">Runtime usage</p><p className="mt-2 text-sm text-muted-foreground">{data.events} events · {data.usage.tool_calls} tool calls · {data.usage.llm_calls} model calls · {data.usage.tokens} tokens · ${Number(data.usage.estimated_cost_usd).toFixed(4)} estimated</p></div>
      <div className="rounded-xl border border-border"><p className="border-b border-border p-4 font-medium">Recent traces</p>{data.latest.length === 0 ? <p className="p-6 text-sm text-muted-foreground">No runtime traces yet.</p> : data.latest.map((run) => <div key={run.run_id} className="border-b border-border p-4 last:border-0"><p className="text-sm font-medium">{run.run_id} · {run.status}</p><p className="mt-1 text-xs text-muted-foreground">{run.correlation_id} · {run.trace_reference}</p></div>)}</div>
    </>}
  </div>;
}
