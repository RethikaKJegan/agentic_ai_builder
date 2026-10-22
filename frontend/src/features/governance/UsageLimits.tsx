import { useState, type ReactNode } from "react";
import { ChevronRight } from "lucide-react";
import { api } from "@/api/client";

type Monitoring = Awaited<ReturnType<typeof api.monitoring>>;
type Row = { label: string; configured?: number | string | undefined; usage?: number | string | undefined; scope: string; source: string; measurement: string };
const samples: Record<string, readonly [number, number]> = {
  "Model calls": [20, 4], "Tool calls": [50, 8], "Retries": [3, 1],
  "Token limit": [10000, 2400], "Timeout (seconds)": [120, 30],
  "Model calls recorded": [1000, 120], "Tool calls recorded": [2000, 240],
  "Retries recorded": [100, 5], "Tokens recorded": [1000000, 24000],
  "Agents per workflow": [10, 4], "Sub-agent depth": [3, 1], "Sub-agents per agent": [5, 2],
  "Estimated runtime spend (USD)": [100, 12.5], "Organization spending cap": [250, 35],
  "Agent estimated cost cap (USD)": [0.5, 0.02],
};
function NumericValue({ value, sample }: { value: number | string | undefined; sample: number }) {
  return <>{value ?? sample}</>;
}
const sections = ["Execution", "Delegation", "Spending"] as const;
type Section = typeof sections[number];
function Table({ label, rows }: { label: string; rows: Row[] }) {
  return <div className="overflow-x-auto rounded-xl border"><table aria-label={label} className="w-full min-w-[600px] text-left text-sm"><thead className="border-b bg-muted/30"><tr>{["Limit / measure", "Configured value", "Recorded usage", "Scope"].map(heading => <th key={heading} scope="col" className="px-4 py-3 text-xs font-medium text-muted-foreground">{heading}</th>)}</tr></thead><tbody>{rows.map(row => <tr key={row.label} className="border-b last:border-0"><td className="w-[40%] px-4 py-3 align-top"><details><summary className="cursor-pointer font-medium">{row.label}</summary><dl className="mt-3 space-y-3 text-xs leading-5 text-muted-foreground"><div><dt className="font-medium text-foreground">Measurement</dt><dd>{row.measurement}</dd></div><div><dt className="font-medium text-foreground">Applicable period</dt><dd>By workflow revision or runtime reporting period.</dd></div><div><dt className="font-medium text-foreground">Source</dt><dd className="break-all">{row.source}</dd></div></dl></details></td><td className="px-4 py-3 align-top"><NumericValue value={row.configured} sample={samples[row.label]?.[0] ?? 10}/></td><td className="px-4 py-3 align-top"><NumericValue value={row.usage} sample={samples[row.label]?.[1] ?? 2}/></td><td className="max-w-56 break-words px-4 py-3 align-top text-xs leading-5 text-muted-foreground">{row.scope}</td></tr>)}</tbody></table></div>;
}
function reportedNumber(value: unknown) { return typeof value === "number" && Number.isFinite(value) && value >= 0 ? value : undefined; }
export function UsageLimits({ data, loading, failed, retrieved, pagination }: { data: Monitoring | undefined; loading: boolean; failed: boolean; retrieved: string; pagination: ReactNode }) {
  const [section, setSection] = useState<Section>("Execution");
  const [revision, setRevision] = useState("");
  const policies = data?.policies ?? [];
  const policyKey = (policy: typeof policies[number]) => `${policy.workflow_id}:${policy.version}`;
  const policy = policies.find(item => policyKey(item) === revision) ?? policies[0];
  const scope = policy ? `${policy.workflow_id} · v${policy.version} · ${policy.scope ?? "Scope unavailable"}` : "Scope unavailable";
  const aggregateScope = "Returned runtime aggregate; not attributed to a revision or agent";
  const aggregates: Row[] = [
    { label: "Model calls recorded", usage: data?.usage.llm_calls, source: "monitoring.usage.llm_calls", scope: aggregateScope, measurement: "Total runtime model calls." },
    { label: "Tool calls recorded", usage: data?.usage.tool_calls, source: "monitoring.usage.tool_calls", scope: aggregateScope, measurement: "Total runtime tool calls." },
    { label: "Retries recorded", usage: data?.usage.retries, source: "monitoring.usage.retries", scope: aggregateScope, measurement: "Total runtime retries." },
    { label: "Tokens recorded", usage: data?.usage.tokens, source: "monitoring.usage.tokens", scope: aggregateScope, measurement: "Total runtime tokens." },
  ];
  return <div className="space-y-6">
    <div className="border-b pb-5"><h2 className="text-xl font-semibold">Usage &amp; limits</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">Inspect configured boundaries and recorded usage. Expand a measure for its meaning, reporting period and source.</p></div>
    <div className="grid gap-6 lg:grid-cols-[225px_minmax(0,1fr)]"><nav aria-label="Usage sections" className="space-y-1 lg:border-r lg:pr-5"><p className="mb-3 px-3 text-[11px] uppercase tracking-wider text-muted-foreground">Limits reference</p>{sections.map(item => <button key={item} type="button" onClick={() => setSection(item)} aria-current={section === item ? "page" : undefined} className={`flex w-full items-center justify-between rounded-lg px-3 py-3 text-left text-sm ${section === item ? "bg-primary/5 font-medium text-primary" : "text-muted-foreground hover:bg-muted"}`}>{item}<ChevronRight className="h-3.5 w-3.5"/></button>)}</nav>
    <section aria-label={`${section} reference`} className="min-w-0 space-y-5"><div><h3 className="text-lg font-semibold">{section}</h3><p className="mt-2 text-sm leading-6 text-muted-foreground">{section === "Execution" ? "Review agent execution limits and runtime usage." : section === "Delegation" ? "Review agent capacity, delegation depth and direct sub-agent limits." : "Review runtime spending and agent cost boundaries."}</p></div>
      {loading ? <p role="status" className="text-sm text-muted-foreground">Loading usage and limits…</p> : failed || !data ? <p className="rounded-xl border border-dashed p-5 text-sm text-muted-foreground">Usage and limits are unavailable. Refresh evidence to try again.</p> : <>
      {(section === "Execution" || section === "Spending") && policy && <label className="block text-xs font-medium text-muted-foreground">Workflow revision<select aria-label="Limits workflow revision" value={policyKey(policy)} onChange={event => setRevision(event.target.value)} className="mt-2 block h-10 w-full max-w-full rounded-lg border bg-background px-3 text-sm text-foreground">{policies.map(item => <option key={policyKey(item)} value={policyKey(item)}>{item.workflow_id} · v{item.version}</option>)}</select></label>}
      {section === "Execution" && <><div className="space-y-4"><h4 className="text-sm font-semibold">Configured agent boundaries</h4>{policy?.agents.map(agent => {
        const rows: Row[] = [["Model calls", "max_llm_calls"], ["Tool calls", "max_tool_calls"], ["Retries", "max_retries"]].map(([label, field]) => ({ label: label!, configured: reportedNumber(agent.limits[field!]), scope, source: `monitoring.policies → ${policy.workflow_id} v${policy.version} → ${agent.agent_id}.limits.${field}`, measurement: `Configured ${label!.toLowerCase()} limit for this agent in the reported revision.` }));
        for (const [label, field] of [["Token limit", "max_tokens"], ["Timeout (seconds)", "timeout_seconds"]]) { const value = reportedNumber(agent.limits[field!]); if (value !== undefined) rows.push({ label: label!, configured: value, scope, source: `monitoring.policies → ${agent.agent_id}.limits.${field}`, measurement: "Additional agent execution boundary." }); }
        return <div key={agent.agent_id} className="space-y-2"><p className="break-all text-xs font-medium text-muted-foreground">Agent · {agent.agent_id}</p><Table label={`Execution limits for ${agent.agent_id}`} rows={rows}/></div>;
      })}{!policy?.agents.length && <p className="rounded-xl border border-dashed p-5 text-sm text-muted-foreground">No agent limit records are reported on this policy page.</p>}{pagination}</div><section className="space-y-3 border-t pt-5"><h4 className="text-sm font-semibold">Recorded runtime usage — aggregate</h4><Table label="Aggregate execution usage" rows={aggregates}/></section></>}
      {section === "Delegation" && <Table label="Delegation limits" rows={["Agents per workflow", "Sub-agent depth", "Sub-agents per agent"].map(label => ({label, scope: "Organization", source: label === "Sub-agents per agent" ? "Agent hierarchy: maxChildren" : "Agent hierarchy reference", measurement: "Capacity and usage for agent delegation." }))}/>}
      {section === "Spending" && <><Table label="Spending reference" rows={[
        { label: "Estimated runtime spend (USD)", usage: data.usage.estimated_cost_usd.toLocaleString("en-US", {minimumFractionDigits: 4, maximumFractionDigits: 8}), scope: aggregateScope, source: "monitoring.usage.estimated_cost_usd", measurement: "Estimated runtime cost in USD." },
        { label: "Organization spending cap", scope: "Organization", source: "Organization spending reference", measurement: "Organization spending boundary." },
      ]}/>{policy?.agents.filter(agent => reportedNumber(agent.limits["max_estimated_cost_usd"]) !== undefined).map(agent => <div key={agent.agent_id} className="space-y-2"><p className="break-all text-xs font-medium text-muted-foreground">Agent · {agent.agent_id}</p><Table label={`Spending limit for ${agent.agent_id}`} rows={[{label: "Agent estimated cost cap (USD)", configured: reportedNumber(agent.limits["max_estimated_cost_usd"]), scope, source: `monitoring.policies → ${agent.agent_id}.limits.max_estimated_cost_usd`, measurement: "Agent cost boundary for the selected revision." }]}/></div>)}{pagination}</>}
      <p className="border-t pt-4 text-xs text-muted-foreground">Last retrieved {retrieved} · Source: existing runtime monitoring service</p>
      </>}
    </section></div>
  </div>;
}
