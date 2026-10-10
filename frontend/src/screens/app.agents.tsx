"use client";
import { useRouteSearch } from "@/lib/navigation";
import { Link, useNavigate } from "@/lib/navigation";
import { Bot, Network, Pause, Play, Plus } from "lucide-react";
import { can } from "@/domain/governance";
import { StatusPill } from "@/features/shell/StatusPill";
import { useMesh } from "@/domain/store";
import { getModel } from "@/domain/models";
import { AgentInspector } from "@/features/agents/AgentInspector";



export default function AgentsPage() {
  const { agent: selectedId } = useRouteSearch();
  const navigate = useNavigate({ from: "/app/agents" });
  const agents = useMesh((s) => s.agents);
  const workflows = useMesh((s) => s.workflows);
  const createAgent = useMesh((s) => s.createAgent);
  const setPaused = useMesh((s) => s.setAgentPaused);
  const role = useMesh((s) => s.role);
  const mayControl = can(role, "workflow.edit");
  const selected = agents.find((a) => a.id === selectedId) ?? agents[0];
  const usedIn = (id: string) => workflows.filter((w) => w.nodes.some((n) => n.data.agentId === id));

  return (
    <div className="flex h-full flex-col lg:flex-row">
      <div className="min-w-0 flex-1 overflow-y-auto px-6 py-10">
        <div className="flex items-end justify-between gap-4">
          <h1 className="text-3xl font-semibold">Agents</h1>
          <div className="flex gap-2">
            <Link to="/app/marketplace" className="inline-flex h-9 items-center rounded-lg border border-border px-3.5 text-sm hover:border-primary hover:text-primary">Browse marketplace</Link>
            <button onClick={() => navigate({ search: { agent: createAgent() } })} className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-primary px-3.5 text-sm font-medium text-primary-foreground hover:bg-primary-deep"><Plus className="h-4 w-4" />New agent</button>
          </div>
        </div>
        <p className="mt-2 text-sm text-muted-foreground">Local agent drafts. Changes apply to drafts that reference them.</p>
        {agents.length === 0 ? (
          <p className="mt-8 rounded-xl border border-dashed border-border p-6 text-sm text-muted-foreground">Create an agent or add an agent step to a workflow. <Link to="/app" className="text-primary">Create one</Link>.</p>
        ) : (
          <div className="mt-8 divide-y divide-border rounded-xl border border-border">
            {agents.map((a) => {
              const uses = usedIn(a.id);
              const parent = a.parentAgentId ? agents.find((x) => x.id === a.parentAgentId) : undefined;
              const isMaster = agents.some((x) => x.parentAgentId === a.id);
              return (
                <div key={a.id} className={`flex w-full items-center gap-3 px-4 py-3.5 transition-colors ${selected?.id === a.id ? "bg-highlight" : "hover:bg-canvas"}`}>
                  <button onClick={() => navigate({ search: { agent: a.id } })} className="flex min-w-0 flex-1 items-center gap-4 text-left">
                    <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${isMaster ? "bg-primary-deep" : "bg-primary"} text-primary-foreground`}>{isMaster ? <Network className="h-4 w-4" /> : <Bot className="h-4 w-4" />}</span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium">{a.name}</p>
                      <p className="truncate text-xs text-muted-foreground">{isMaster ? "Master agent" : parent ? `Sub-agent of ${parent.name}` : a.role} · {getModel(a.modelId).name}</p>
                    </div>
                    <span className="hidden text-xs text-muted-foreground md:inline">{uses.length ? `in ${uses[0]!.name}${uses.length > 1 ? ` +${uses.length - 1}` : ""}` : "unused"}</span>
                  </button>
                  <StatusPill status={a.paused ? "paused" : "draft"} tone={a.paused ? "warning" : "neutral"} />
                  <button disabled={!mayControl} onClick={() => setPaused(a.id, !a.paused)} className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-40" aria-label={a.paused ? `Resume ${a.name}` : `Pause ${a.name}`} title={mayControl ? undefined : "Draft configuration only"}>
                    {a.paused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
      {selected && (
        <aside className="w-full shrink-0 overflow-y-auto border-t border-border p-5 lg:w-[380px] lg:border-l lg:border-t-0">
          <h2 className="mb-4 text-lg font-medium">{selected.name}</h2>
          <AgentInspector agent={selected} />
        </aside>
      )}
    </div>
  );
}
