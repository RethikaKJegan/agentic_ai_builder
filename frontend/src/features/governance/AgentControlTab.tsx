import { displayText } from "@/lib/display-text";
import { useMemo } from "react";
import { Switch } from "@/components/ui/switch";
import { useBackend } from "@/api/state";
import { useMesh } from "@/domain/store";
import { resolveControls, SENSITIVE_TOOLS, usageFrom, type AgentControls } from "@/domain/governance";
import { MODELS, TOOL_CATALOG } from "@/domain/models";
import { toast } from "sonner";

type Scope = "organization" | "workspace";
const NUMERIC: { key: "maxAgentsPerWorkflow" | "maxRunsPerDay" | "maxSpendUsd" | "maxDepth" | "maxChildren"; label: string; hint: string; step?: number }[] = [
  { key: "maxAgentsPerWorkflow", label: "Max agents per workflow", hint: "Includes master and sub-agents" },
  { key: "maxRunsPerDay", label: "Max runs per day", hint: "Rolling 24 hours" },
  { key: "maxSpendUsd", label: "Max estimated spend / day", hint: "USD, rolling 24 hours", step: 0.5 },
  { key: "maxDepth", label: "Max sub-agent depth", hint: "Master = level 0" },
  { key: "maxChildren", label: "Max sub-agents per agent", hint: "Direct children" },
];

export function AgentControlTab() {
  const { controls, setControls, agents, runs, workflows } = useMesh();
  const backend=useBackend();
  const allowed=backend.status==="connected" && backend.session?.auth.decision==="allow" && backend.session.auth.roles.includes("admin");
  const eff = resolveControls(controls.organization, controls.workspace);
  const usage = useMemo(() => usageFrom(runs), [runs]);
  const totalCost = runs.reduce((a, r) => a + r.steps.reduce((b, s) => b + s.cost, 0), 0);
  const paused = agents.filter((a) => a.paused).length;

  const set = (scope: Scope, patch: Partial<AgentControls>) => {
    if (!allowed) return;
    const org = controls.organization;
    const capped = scope === "workspace" && Object.entries(patch).some(([k, v]) => typeof v === "number" && v > (org as unknown as Record<string, number>)[k]!);
    setControls(scope, patch);
    if (capped) toast.warning("Capped at the organization limit", { description: "Workspace controls can only be stricter than organization controls." });
  };

  const meter = (label: string, used: number, limit: number, fmt = (n: number) => String(n)) => {
    const pct = Math.min(100, limit ? (used / limit) * 100 : 100);
    return (
      <div className="rounded-xl border border-border p-3">
        <div className="flex justify-between text-xs"><span className="text-muted-foreground">{displayText(label)}</span><span className="font-medium">{fmt(used)} / {fmt(limit)}</span></div>
        <div className="mt-2 h-1.5 rounded-full bg-muted"><div className={`h-full rounded-full ${pct >= 100 ? "bg-destructive" : pct >= 80 ? "bg-warning" : "bg-primary"}`} style={{ width: `${pct}%` }} /></div>
      </div>
    );
  };

  const Column = ({ scope }: { scope: Scope }) => {
    const c = controls[scope];
    return (
      <div className="rounded-2xl border border-border">
        <p className="border-b border-border px-4 py-3 text-sm font-medium">{scope === "organization" ? "Draft organization" : "Draft workspace"}</p>
        <div className="divide-y divide-border">
          <label className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
            <span>Agent execution<span className="block text-xs text-muted-foreground">{c.executionEnabled ? "Draft execution enabled" : "Draft execution disabled"}</span></span>
            <Switch checked={c.executionEnabled} disabled={!allowed} onCheckedChange={(v) => set(scope, { executionEnabled: v })} aria-label={`${scope} agent execution`} />
          </label>
          {NUMERIC.map((n) => (
            <div key={n.key} className="flex items-center justify-between gap-3 px-4 py-2.5 text-sm">
              <label htmlFor={`${scope}-${n.key}`}>{displayText(n.label)}<span className="block text-xs text-muted-foreground">{n.hint}{scope === "workspace" ? ` · org max ${controls.organization[n.key]}` : ""}</span></label>
              <input
                id={`${scope}-${n.key}`} type="number" min={0} step={n.step ?? 1} disabled={!allowed}
                defaultValue={c[n.key]} key={`${scope}-${n.key}-${c[n.key]}`}
                onBlur={(e) => { const v = Number(e.target.value); if (!Number.isFinite(v) || v < 0) { toast.error("Enter a number of 0 or more"); e.target.value = String(c[n.key]); return; } if (v !== c[n.key]) set(scope, { [n.key]: v }); }}
                onKeyDown={(e) => { if (e.key === "Enter") (e.target as HTMLInputElement).blur(); }}
                className="h-8 w-20 rounded-lg border border-border bg-background px-2 text-right text-sm outline-none focus:border-primary disabled:opacity-60"
              />
            </div>
          ))}
          <label className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
            <span>Approval for sensitive actions<span className="block text-xs text-muted-foreground">{SENSITIVE_TOOLS.join(", ")}</span></span>
            <Switch checked={c.approvalForSensitive} disabled={!allowed} onCheckedChange={(v) => set(scope, { approvalForSensitive: v })} aria-label={`${scope} approval for sensitive actions`} />
          </label>
          <details className="group px-4 py-3 text-sm">
            <summary className="cursor-pointer list-none text-xs font-medium text-primary">Tools & models · {c.allowedTools ? `${c.allowedTools.length} tools allowed` : "all tools"} · {c.blockedModels.length} models restricted</summary>
            <div className="mt-3 flex items-center justify-between text-xs"><span className="text-muted-foreground">Restrict tools</span><Switch checked={c.allowedTools !== null} disabled={!allowed} onCheckedChange={(v) => set(scope, { allowedTools: v ? [...TOOL_CATALOG] : null })} aria-label={`${scope} restrict tools`} /></div>
            {c.allowedTools && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {TOOL_CATALOG.map((t) => {
                  const on = c.allowedTools!.includes(t);
                  return <button key={t} disabled={!allowed} aria-pressed={on} onClick={() => set(scope, { allowedTools: on ? c.allowedTools!.filter((x) => x !== t) : [...c.allowedTools!, t] })} className={`rounded-full border px-2 py-0.5 text-[11px] ${on ? "border-primary bg-highlight text-primary-deep" : "border-border text-muted-foreground line-through"}`}>{t}</button>;
                })}
              </div>
            )}
            <p className="mt-3 text-xs text-muted-foreground">Restricted models</p>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {MODELS.map((m) => {
                const on = c.blockedModels.includes(m.id);
                return <button key={m.id} disabled={!allowed} aria-pressed={on} onClick={() => set(scope, { blockedModels: on ? c.blockedModels.filter((x) => x !== m.id) : [...c.blockedModels, m.id] })} className={`rounded-full border px-2 py-0.5 text-[11px] ${on ? "border-destructive/50 bg-destructive/10 text-destructive" : "border-border text-muted-foreground"}`}>{displayText(m.name)}</button>;
              })}
            </div>
          </details>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-4">
      <p role="status" className="rounded-lg border p-3 text-sm text-muted-foreground">Local draft controls only. These settings do not change live execution, approvals or server budgets. See Live governance &amp; usage for enforced policies.</p>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        {[["Total agents", agents.length], ["Active", agents.length - paused], ["Paused", paused], ["Total runs", runs.length], ["Est. spend", `$${totalCost.toFixed(2)}`]].map(([l, v]) => (
          <div key={l as string} className="rounded-xl border border-border p-3"><p className="text-xs text-muted-foreground">{l}</p><p className="mt-1 font-display text-xl font-semibold">{v}</p></div>
        ))}
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {meter("Runs today vs limit", usage.runsToday, eff.maxRunsPerDay)}
        {meter("Spend today vs limit", usage.spendToday, eff.maxSpendUsd, (n) => `$${n.toFixed(2)}`)}
      </div>
      <div className="flex flex-wrap items-center gap-2 rounded-xl border border-border bg-canvas px-4 py-2.5 text-xs">
        <span className="font-medium">Effective browser draft:</span>
        <span className={eff.executionEnabled ? "text-success" : "text-destructive"}>{eff.executionEnabled ? "Execution on" : "Execution off"}</span>
        <span className="text-muted-foreground">· ≤{eff.maxAgentsPerWorkflow} agents/workflow · depth ≤{eff.maxDepth} · ≤{eff.maxChildren} children · {eff.allowedTools ? `${eff.allowedTools.length} tools` : "all tools"} · {eff.blockedModels.length} models restricted{eff.approvalForSensitive ? " · approval on sensitive actions" : ""}</span>
        <span className="ml-auto text-muted-foreground">Workflows over limit: {workflows.filter((w) => w.nodes.filter((n) => n.data.kind === "agent").length > eff.maxAgentsPerWorkflow).length}</span>
      </div>
      {!allowed && <p className="rounded-lg border border-border bg-canvas p-3 text-sm text-muted-foreground">Read-only: a server-authenticated administrator is required to edit browser draft controls.</p>}
      <div className="grid gap-4 lg:grid-cols-2">
        <Column scope="organization" />
        <Column scope="workspace" />
      </div>
      <p className="text-xs text-muted-foreground">Local control drafts follow organization → workspace → workflow → agent. Lower levels can only be stricter. Changes are saved in this browser; runtime enforcement is awaiting backend integration.</p>
    </div>
  );
}
