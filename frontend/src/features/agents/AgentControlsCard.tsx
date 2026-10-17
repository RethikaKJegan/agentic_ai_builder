import { useMemo } from "react";
import { ChevronDown, ShieldAlert } from "lucide-react";
import { Link } from "@/lib/navigation";
import { Switch } from "@/components/ui/switch";
import { useMesh } from "@/domain/store";
import { can, resolveControls } from "@/domain/governance";
import { StatusPill } from "@/features/shell/StatusPill";
import type { Agent } from "@/domain/types";

/** Compact agent-level controls: status, hierarchy, budget, approval and usage. */
export function AgentControlsCard({ agent }: { agent: Agent }) {
  const agents = useMesh((s) => s.agents);
  const runs = useMesh((s) => s.runs);
  const role = useMesh((s) => s.role);
  const controls = useMesh((s) => s.controls);
  const update = useMesh((s) => s.updateAgent);
  const setPaused = useMesh((s) => s.setAgentPaused);
  const audited = useMesh((s) => s.audited);
  const allowed = can(role, "workflow.edit");
  const parent = agent.parentAgentId ? agents.find((a) => a.id === agent.parentAgentId) : undefined;
  const children = agents.filter((a) => a.parentAgentId === agent.id);
  const eff = resolveControls(controls.organization, controls.workspace);
  const restricted = eff.allowedTools ? agent.tools.filter((t) => !eff.allowedTools!.includes(t)) : [];

  const usage = useMemo(() => {
    const mine = runs.filter((r) => r.steps.some((s) => s.agentId === agent.id));
    const cost = mine.reduce((a, r) => a + r.steps.filter((s) => s.agentId === agent.id).reduce((b, s) => b + s.cost, 0), 0);
    const blocked = mine.filter((r) => r.steps.some((s) => s.agentId === agent.id && s.status === "blocked")).length;
    return { runs: mine, cost, blocked };
  }, [runs, agent.id]);

  return (
    <section aria-label="Agent controls" className="mb-4 space-y-2 rounded-xl border border-border p-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium">Controls</p>
        {!allowed && <span className="text-[11px] text-muted-foreground">Read-only for your role</span>}
      </div>
      <label className="flex items-center justify-between gap-3 text-sm">
        <span>{agent.paused ? "Paused" : "Active"}<span className="block text-[11px] text-muted-foreground">{agent.paused ? (children.length ? "This local draft marks the agent and sub-agents paused; live runs are unchanged." : "This local draft is paused; live runs are unchanged.") : "Draft configuration only"}</span></span>
        <Switch checked={!agent.paused} disabled={!allowed} onCheckedChange={(v) => setPaused(agent.id, !v)} aria-label="Agent active" />
      </label>
      <p className="text-[11px] text-muted-foreground">
        {parent ? <>Sub-agent of <Link to="/app/agents" search={{ agent: parent.id }} className="text-primary">{parent.name}</Link>{parent.paused && <span className="text-warning"> · parent paused</span>}</> : children.length ? `Master agent · ${children.length} sub-agent${children.length > 1 ? "s" : ""}` : "Standalone agent"}
      </p>
      <div className="flex items-center justify-between gap-3 text-sm">
        <label htmlFor={`budget-${agent.id}`}>Max execution budget<span className="block text-[11px] text-muted-foreground">Estimated USD, lifetime · empty = no cap</span></label>
        <input
          id={`budget-${agent.id}`}
          type="number" min={0} step={0.01} inputMode="decimal" disabled={!allowed}
          value={agent.budgetUsd ?? ""}
          onChange={(e) => update(agent.id, { budgetUsd: e.target.value === "" ? null : Math.max(0, Number(e.target.value)) })}
          onBlur={() => audited("Set agent budget", `${agent.name} → ${agent.budgetUsd == null ? "no cap" : `$${agent.budgetUsd}`}`)}
          className="h-8 w-24 rounded-lg border border-border bg-background px-2 text-right text-sm outline-none focus:border-primary"
        />
      </div>
      <label className="flex items-center justify-between gap-3 text-sm">
        <span>Require approval<span className="block text-[11px] text-muted-foreground">Pause each run for human sign-off before this agent acts</span></span>
        <Switch checked={!!agent.requireApproval} disabled={!allowed} onCheckedChange={(v) => { update(agent.id, { requireApproval: v }); audited(v ? "Required approval for agent" : "Removed agent approval", agent.name); }} aria-label="Require approval" />
      </label>
      {restricted.length > 0 && <p className="flex items-start gap-1 text-[11px] text-warning"><ShieldAlert className="mt-0.5 h-3 w-3 shrink-0" />Blocked by agent controls: {restricted.join(", ")} not on the allowed tool list.</p>}
      <details className="group">
        <summary className="flex cursor-pointer list-none items-center gap-1 text-xs font-medium text-primary">Usage & history <ChevronDown className="h-3 w-3 transition-transform group-open:rotate-180" /></summary>
        <p className="mt-2 text-xs text-muted-foreground">{usage.runs.length} runs · ${usage.cost.toFixed(4)} estimated · {usage.blocked} blocked <span className="text-muted-foreground/70">(backend pending)</span></p>
        <ul className="mt-1.5 space-y-1">
          {usage.runs.slice(0, 5).map((r) => <li key={r.id} className="flex items-center gap-2 text-xs"><StatusPill status={r.status} /><span className="min-w-0 flex-1 truncate">{r.workflowName}</span><span className="text-muted-foreground">{new Date(r.startedAt).toLocaleDateString()}</span></li>)}
          {usage.runs.length === 0 && <li className="text-xs text-muted-foreground">Run history is awaiting backend integration.</li>}
        </ul>
      </details>
    </section>
  );
}
