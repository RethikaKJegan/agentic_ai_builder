import { useMemo, useState } from "react";
import { Link } from "@/lib/navigation";
import { ArrowDown, ArrowUp, Search } from "lucide-react";
import { useMesh } from "@/domain/store";
import { can } from "@/domain/governance";
import { StatusPill } from "@/features/shell/StatusPill";

type SortKey = "name" | "workflow" | "runs" | "cost";

export function UsageTab() {
  const { agents, runs, workflows, role, setAgentPaused } = useMesh();
  const mayControl = can(role, "workflow.edit");
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<"all" | "active" | "paused">("all");
  const [sort, setSort] = useState<{ key: SortKey; dir: 1 | -1 }>({ key: "cost", dir: -1 });

  const rows = useMemo(() => {
    const nodeAgent = new Map<string, string>();
    workflows.forEach((w) => w.nodes.forEach((n) => { if (n.data.agentId) nodeAgent.set(n.id, n.data.agentId); }));
    const stats = new Map<string, { runs: Set<string>; cost: number; blocked: number }>();
    runs.forEach((r) => r.steps.forEach((s) => {
      if (s.kind !== "agent") return;
      const id = s.agentId ?? nodeAgent.get(s.nodeId);
      if (!id) return;
      const st = stats.get(id) ?? { runs: new Set(), cost: 0, blocked: 0 };
      st.runs.add(r.id);
      st.cost += s.cost;
      if (s.status === "blocked") st.blocked++;
      stats.set(id, st);
    }));
    return agents.map((a) => {
      const st = stats.get(a.id);
      const wf = workflows.filter((w) => w.nodes.some((n) => n.data.agentId === a.id));
      return { agent: a, workflow: wf[0]?.name ?? "—", more: Math.max(0, wf.length - 1), runs: st?.runs.size ?? 0, cost: st?.cost ?? 0, blocked: st?.blocked ?? 0 };
    });
  }, [agents, runs, workflows]);

  const shown = rows
    .filter((r) => (status === "all" ? true : status === "paused" ? r.agent.paused : !r.agent.paused))
    .filter((r) => `${r.agent.name} ${r.workflow}`.toLowerCase().includes(q.toLowerCase()))
    .sort((a, b) => {
      const v = sort.key === "name" ? a.agent.name.localeCompare(b.agent.name) : sort.key === "workflow" ? a.workflow.localeCompare(b.workflow) : a[sort.key] - b[sort.key];
      return v * sort.dir;
    });
  const maxCost = Math.max(0.0001, ...rows.map((r) => r.cost));
  const kpi = [
    ["Active Agents", agents.filter((a) => !a.paused).length],
    ["Total Runs", runs.length],
    ["Estimated Cost", `$${runs.reduce((a, r) => a + r.steps.reduce((b, s) => b + s.cost, 0), 0).toFixed(2)}`],
    ["Blocked Executions", runs.filter((r) => r.status === "blocked").length],
  ] as const;

  const Th = ({ k, label, right }: { k: SortKey; label: string; right?: boolean }) => (
    <th scope="col" aria-sort={sort.key === k ? (sort.dir === 1 ? "ascending" : "descending") : "none"} className={`px-4 py-2.5 font-medium ${right ? "text-right" : "text-left"}`}>
      <button onClick={() => setSort((s) => ({ key: k, dir: s.key === k ? (s.dir === 1 ? -1 : 1) : k === "cost" || k === "runs" ? -1 : 1 }))} className="inline-flex items-center gap-1 hover:text-foreground">
        {label}{sort.key === k && (sort.dir === 1 ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
      </button>
    </th>
  );

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {kpi.map(([l, v]) => <div key={l} className="rounded-2xl border border-border p-4"><p className="text-xs text-muted-foreground">{l}</p><p className="mt-1 font-display text-2xl font-semibold">{v}</p></div>)}
      </div>
      <p className="text-xs text-muted-foreground">Live usage is awaiting runtime integration.</p>
      <div className="flex flex-wrap items-center gap-2">
        <label className="relative min-w-[200px] flex-1">
          <span className="sr-only">Search agents</span>
          <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search agent or workflow" className="h-9 w-full rounded-lg border border-border bg-background pl-8 pr-3 text-sm outline-none focus:border-primary" />
        </label>
        <label className="text-xs text-muted-foreground"><span className="sr-only">Status</span>
          <select value={status} onChange={(e) => setStatus(e.target.value as typeof status)} className="h-9 rounded-lg border border-border bg-background px-2 text-sm text-foreground">
            <option value="all">All statuses</option><option value="active">Active</option><option value="paused">Paused</option>
          </select>
        </label>
      </div>
      <div className="overflow-x-auto rounded-2xl border border-border" tabIndex={0} role="region" aria-label="Agent usage table">
        <table className="w-full min-w-[640px] text-sm">
          <thead className="border-b border-border text-xs text-muted-foreground">
            <tr><Th k="name" label="Agent" /><Th k="workflow" label="Workflow" /><Th k="runs" label="Runs" right /><Th k="cost" label="Estimated Cost" right /><th scope="col" className="px-4 py-2.5 text-left font-medium">Status</th><th scope="col" className="px-4 py-2.5 text-right font-medium">Actions</th></tr>
          </thead>
          <tbody className="divide-y divide-border">
            {shown.map((r) => (
              <tr key={r.agent.id}>
                <td className="px-4 py-2.5"><span className="font-medium">{r.agent.name}</span>{r.agent.parentAgentId && <span className="block text-[11px] text-muted-foreground">sub-agent</span>}</td>
                <td className="max-w-[200px] truncate px-4 py-2.5 text-muted-foreground">{r.workflow}{r.more ? ` +${r.more}` : ""}</td>
                <td className="px-4 py-2.5 text-right tabular-nums">{r.runs}</td>
                <td className="px-4 py-2.5 text-right">
                  <span className="tabular-nums">${r.cost.toFixed(4)}</span>
                  <span className="mt-1 block h-1 rounded-full bg-muted"><span className="block h-full rounded-full bg-primary" style={{ width: `${(r.cost / maxCost) * 100}%` }} /></span>
                </td>
                <td className="px-4 py-2.5"><div className="flex flex-wrap gap-1"><StatusPill status={r.agent.paused ? "paused" : "active"} tone={r.agent.paused ? "warning" : "success"} />{r.blocked > 0 && <StatusPill status={`${r.blocked} blocked`} tone="danger" />}</div></td>
                <td className="whitespace-nowrap px-4 py-2.5 text-right">
                  <button disabled={!mayControl} onClick={() => setAgentPaused(r.agent.id, !r.agent.paused)} className="rounded-md px-2 py-1 text-xs font-medium text-primary hover:bg-highlight disabled:opacity-40">{r.agent.paused ? "Resume" : "Pause"}</button>
                  <Link to="/app/agents" search={{ agent: r.agent.id }} className="rounded-md px-2 py-1 text-xs text-muted-foreground hover:text-foreground">Open</Link>
                </td>
              </tr>
            ))}
            {shown.length === 0 && <tr><td colSpan={6} className="px-4 py-8 text-center text-sm text-muted-foreground">{rows.length ? "No agents match these filters." : "No agents yet. Generate a workflow to create some."}</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
