"use client";
import { Link, useNavigate } from "@/lib/navigation";
import { Copy, MoreHorizontal, Pencil, Play, Plus, Power, Trash2 } from "lucide-react";
import { useMesh } from "@/domain/store";
import { StatusPill } from "@/features/shell/StatusPill";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { toast } from "sonner";
import { useBackend } from "@/api/state";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";
import { api } from "@/api/client";
import { useEffect, useState } from "react";



export default function WorkflowsPage() {
  const workflows = useMesh((s) => s.workflows);
  const runs = useMesh((s) => s.runs);
  const dup = useMesh((s) => s.duplicateWorkflow);
  const del = useMesh((s) => s.deleteWorkflow);
  const navigate = useNavigate();
  const backend = useBackend();
  const backendStatus = backend.status;
  const refreshOverview = backend.refreshOverview;
  const visibleWorkflows = backend.status === "connected" && backend.lastOverviewUpdate
    ? workflows.filter((workflow) => !workflow.serverVersion || backend.overview[workflow.id])
    : workflows;
  const [actionError, setActionError] = useState<Error | null>(null);
  useEffect(() => {
    if (backendStatus !== "connected") return;
    void refreshOverview();
    const timer = window.setInterval(() => void useBackend.getState().refreshOverview(), 5000);
    const source = typeof EventSource === "undefined" ? null : new EventSource(`/api/backend/workflow-overview/events?after_sequence=${useBackend.getState().overviewSequence}`);
    if (source) {
      source.onopen = () => useBackend.setState({ liveStatus: "live" });
      source.onmessage = (message) => {
        const sequence = Number(message.lastEventId);
        if (!Number.isSafeInteger(sequence) || sequence <= useBackend.getState().overviewSequence) return;
        useBackend.setState({ overviewSequence: sequence });
        void useBackend.getState().refreshOverview();
      };
      source.onerror = () => useBackend.setState({ liveStatus: "stale" });
    }
    return () => { window.clearInterval(timer); source?.close(); };
  }, [backendStatus, refreshOverview]);

  const run = async (workflowId: string) => {
    const workflow = useMesh.getState().workflows.find((item) => item.id === workflowId);
    const overview = useBackend.getState().overview[workflowId];
    if (!workflow?.canonical || !overview?.published_version) return;
    const inputs: Record<string, unknown> = {};
    for (const field of workflow.canonical.inputs) {
      const value = window.prompt(`Run input: ${field.name}${field.required ? " (required)" : ""}`);
      if (value === null) return;
      if (value || field.required) inputs[field.name] = field.type === "number" ? Number(value) : field.type === "boolean" ? value === "true" : value;
    }
    try {
      const result = await api.request("execute_workflow", { workflow_id: workflowId, workflow_version: overview.published_version, inputs });
      toast(`Run ${result.run.run_id} is ${result.run.status}`);
      await useBackend.getState().refreshOverview();
    } catch (error) { setActionError(error instanceof Error ? error : new Error("Run failed.")); }
  };

  const remove = async (workflowId: string, name: string) => {
    const overview = useBackend.getState().overview[workflowId];
    if (!window.confirm(`Delete "${name}"? Runs and audit evidence will be retained.`)) return;
    try {
      await api.deleteWorkflow(workflowId, overview?.release_id ?? null);
      useMesh.getState().deleteWorkflow(workflowId);
      await useBackend.getState().refreshOverview();
      toast(`Deleted "${name}"`);
    } catch (error) { setActionError(error instanceof Error ? error : new Error("Delete failed.")); }
  };

  const disable = async (workflowId: string) => {
    const overview = useBackend.getState().overview[workflowId];
    try {
      await api.disableRelease(workflowId, overview?.release_id ?? null);
      await useBackend.getState().refreshOverview();
      toast("Workflow disabled");
    } catch (error) { setActionError(error instanceof Error ? error : new Error("Disable failed.")); }
  };

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold">Workflows</h1>
          <p className="mt-2 text-sm text-muted-foreground">{visibleWorkflows.filter((w) => w.serverVersion).length} server workflows · {visibleWorkflows.filter((w) => !w.serverVersion).length} local drafts</p>
        </div>
        <Link to="/app" className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-primary px-3.5 text-sm font-medium text-primary-foreground hover:bg-primary-deep"><Plus className="h-4 w-4" /> New</Link>
      </div>
      {backend.status === "loading" && <p className="mt-4 text-sm text-muted-foreground">Loading server workflows…</p>}
      <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
        <span className={`h-2 w-2 rounded-full ${backend.liveStatus === "live" ? "bg-emerald-500" : "bg-amber-500"}`} />
        {backend.liveStatus === "live" ? "Live overview" : "Overview connection stale"}
        {backend.lastOverviewUpdate && ` · updated ${new Date(backend.lastOverviewUpdate).toLocaleTimeString()}`}
      </div>
      <ApiFeedback error={actionError ?? backend.error} />
      {visibleWorkflows.length === 0 ? (
        <p className="mt-8 rounded-xl border border-dashed border-border p-8 text-center text-sm text-muted-foreground">No workflows yet. <Link to="/app" className="text-primary">Create your first draft</Link>.</p>
      ) : (
        <div className="mt-8 divide-y divide-border rounded-xl border border-border">
          {visibleWorkflows.map((w) => {
            const count = runs.filter((r) => r.workflowId === w.id).length;
            const live = backend.overview[w.id];
            return (
              <div key={w.id} className="flex items-center gap-4 px-4 py-3.5 hover:bg-canvas">
                <Link to="/app/workflows/$id" params={{ id: w.id }} className="min-w-0 flex-1">
                  <p className="truncate font-medium">{w.name}</p>
                  <p className="truncate text-xs text-muted-foreground">{w.nodes.length} steps · {live?.active_run_count ?? count} active runs · {live?.pending_approval_count ?? 0} pending approvals</p>
                  <p className="truncate text-xs text-muted-foreground">draft {live?.draft_version ? `v${live.draft_version}` : "—"} · published {live?.published_version ? `v${live.published_version}` : "—"} · latest {live?.latest_run_status ?? "no runs"}</p>
                </Link>
                <StatusPill status={live?.activation_state ?? `${w.serverVersion ? `v${w.serverVersion} · ` : "local · "}${w.status}`} tone={live?.activation_state === "active" ? "success" : "neutral"} />
                <DropdownMenu>
                  <DropdownMenuTrigger className="rounded-md p-1.5 text-muted-foreground hover:bg-muted" aria-label={`Actions for ${w.name}`}><MoreHorizontal className="h-4 w-4" /></DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    {live?.published_version && backend.session?.runtime_available && <DropdownMenuItem onSelect={() => void run(w.id)}><Play className="mr-2 h-4 w-4" /> Run published</DropdownMenuItem>}
                    <DropdownMenuItem onSelect={() => navigate({ to: "/app/workflows/$id", params: { id: w.id } })}><Pencil className="mr-2 h-4 w-4" /> Edit draft</DropdownMenuItem>
                    {live?.activation_state === "active" && backend.can("workflow.publish") && <DropdownMenuItem onSelect={() => void disable(w.id)}><Power className="mr-2 h-4 w-4" /> Disable</DropdownMenuItem>}
                    <DropdownMenuItem onSelect={() => { const id = dup(w.id); if (id) navigate({ to: "/app/workflows/$id", params: { id } }); }}><Copy className="mr-2 h-4 w-4" /> Duplicate</DropdownMenuItem>
                    {w.serverVersion && backend.can("workflow.delete") && <DropdownMenuItem className="text-destructive" onSelect={() => void remove(w.id, w.name)}><Trash2 className="mr-2 h-4 w-4" /> Delete workflow</DropdownMenuItem>}
                    {!w.serverVersion && <DropdownMenuItem className="text-destructive" onSelect={() => { del(w.id); toast(`Deleted "${w.name}"`); }}><Trash2 className="mr-2 h-4 w-4" /> Delete local draft</DropdownMenuItem>}
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
