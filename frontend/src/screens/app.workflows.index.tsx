"use client";
import { displayText } from "@/lib/display-text";
import { Link, useNavigate } from "@/lib/navigation";
import { Copy, MoreHorizontal, Pencil, Play, Plus, Power, Trash2 } from "lucide-react";
import { useMesh } from "@/domain/store";
import { StatusPill } from "@/features/shell/StatusPill";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { toast } from "sonner";
import { useBackend } from "@/api/state";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";
import { api } from "@/api/client";
import { RunWorkflowDialog } from "@/features/workflows/RunWorkflowDialog";
import { RenameWorkflowDialog } from "@/features/workflows/RenameWorkflowDialog";
import type { Workflow } from "@/domain/types";
import type { CanonicalWorkflow } from "@/api/contracts.generated";
import { useEffect, useRef, useState } from "react";



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
  const lock = useRef(false);
  const [busy, setBusy] = useState(false);
  const [runDocument, setRunDocument] = useState<CanonicalWorkflow>();
  const [renaming,setRenaming]=useState<Workflow>();
  const [actionError, setActionError] = useState<Error | null>(null);
  useEffect(() => {
    if (backendStatus !== "connected") return;
    let stopped=false;let timer:ReturnType<typeof setTimeout>;
    const refresh=async()=>{
      await refreshOverview();
      if(!stopped)timer=setTimeout(()=>void refresh(),15000);
    };
    void refresh();
    return()=>{stopped=true;clearTimeout(timer);};
  }, [backendStatus, refreshOverview]);

  const run = async (workflowId: string) => {
    const state = useBackend.getState(); const overview = state.overview[workflowId];
    if (lock.current || !overview?.published_version || !state.can("workflow.execute") || !state.session?.runtime_available) return;
    lock.current = true; setBusy(true); setActionError(null);
    try { setRunDocument((await api.request("get_workflow", { workflow_id: workflowId, workflow_version: overview.published_version })).workflow); }
    catch (error) { setActionError(error instanceof Error ? error : new Error("The published revision could not be loaded.")); }
    finally { lock.current = false; setBusy(false); }
  };

  const remove = async (workflowId: string, name: string) => {
    if (lock.current) return;
    const overview = useBackend.getState().overview[workflowId];
    if (!window.confirm(`Delete "${name}"? Runs and audit evidence will be retained.`)) return;
    lock.current = true; setBusy(true); setActionError(null);
    try {
      await api.deleteWorkflow(workflowId, overview?.release_id ?? null);
      useMesh.getState().deleteWorkflow(workflowId);
      await useBackend.getState().refreshOverview();
      toast(`Deleted "${name}"`);
    } catch (error) { setActionError(error instanceof Error ? error : new Error("Delete failed.")); }
    finally { lock.current = false; setBusy(false); }
  };

  const disable = async (workflowId: string) => {
    if (lock.current || !window.confirm("Disable this workflow and stop accepting new trigger runs? Queued dispatches will be cancelled; run history is retained.")) return;
    lock.current = true; setBusy(true); setActionError(null);
    const overview = useBackend.getState().overview[workflowId];
    try {
      await api.disableRelease(workflowId, overview?.release_id ?? null);
      await useBackend.getState().refreshOverview();
      toast("Workflow disabled");
    } catch (error) { setActionError(error instanceof Error ? error : new Error("Disable failed.")); }
    finally { lock.current = false; setBusy(false); }
  };

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold">Workflows</h1>
          <p className="mt-2 text-sm text-muted-foreground">{visibleWorkflows.filter((w) => w.serverVersion).length}{backend.workflowTotal !== null ? ` of ${backend.workflowTotal}` : ""} server workflows · {visibleWorkflows.filter((w) => !w.serverVersion).length} local drafts</p>
        </div>
        <Link to="/app" className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-primary px-3.5 text-sm font-medium text-primary-foreground hover:bg-primary-deep"><Plus className="h-4 w-4" /> New</Link>
      </div>
      <p className="mt-4 rounded-lg border border-border p-3 text-sm text-muted-foreground">Open a workflow, review its design and configuration, then use Prepare & Activate. Run the active release directly in the editor and follow its progress in Execution. Draft revisions and active releases remain separate.</p>
      {backend.status === "loading" && <p className="mt-4 text-sm text-muted-foreground">Loading server workflows…</p>}
      <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
        <span className={`h-2 w-2 rounded-full ${backend.liveStatus === "live" ? "bg-emerald-500" : "bg-amber-500"}`} />
        {backend.liveStatus === "live" ? "Live overview" : "Overview connection stale"}
        {backend.lastOverviewUpdate && ` · updated ${new Date(backend.lastOverviewUpdate).toLocaleTimeString()}`}
      </div>
      <ApiFeedback error={actionError ?? backend.error} />
      {(backend.workflowCursor || backend.workflowNextCursor) && <nav aria-label="Workflow pages" className="mt-4 flex gap-3">
        <button type="button" disabled={backend.workflowPageBusy || !backend.workflowCursor} onClick={() => void backend.loadWorkflowPage(null)} className="rounded-lg border px-3 py-2 text-sm disabled:opacity-40">First workflows</button>
        <button type="button" disabled={backend.workflowPageBusy || !backend.workflowNextCursor} onClick={() => void backend.loadWorkflowPage(backend.workflowNextCursor)} className="rounded-lg border px-3 py-2 text-sm disabled:opacity-40">{backend.workflowPageBusy ? "Loading workflows…" : "Next workflows"}</button>
      </nav>}
      {runDocument && <RunWorkflowDialog workflow={runDocument} onClose={() => setRunDocument(undefined)} />}
      {renaming && <RenameWorkflowDialog workflow={renaming} onClose={()=>setRenaming(undefined)}/>}
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
                  <p className="truncate font-medium">{displayText(w.name)}</p>
                  <p className="truncate text-xs text-muted-foreground">{w.nodes.length} steps · {live?.active_run_count ?? count} active runs · {live?.pending_approval_count ?? 0} pending approvals</p>
                  <p className="truncate text-xs text-muted-foreground">draft {live?.draft_version ? `v${live.draft_version}` : "—"} · published {live?.published_version ? `v${live.published_version}` : "—"} · latest {live?.latest_run_status ?? "no runs"}</p>
                </Link>
                <StatusPill status={live?.activation_state ?? `${w.serverVersion ? `v${w.serverVersion} · ` : "local · "}${w.status}`} tone={live?.activation_state === "active" ? "success" : "neutral"} />
                <DropdownMenu>
                  <DropdownMenuTrigger disabled={busy} className="rounded-md p-1.5 text-muted-foreground hover:bg-muted" aria-label={displayText(`Actions for ${w.name}`)}><MoreHorizontal className="h-4 w-4" /></DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem disabled={busy || !live?.published_version || !backend.session?.runtime_available || !backend.can("workflow.execute")} onSelect={() => void run(w.id)}><Play className="mr-2 h-4 w-4" /> Run published</DropdownMenuItem>
                    {(!backend.can("workflow.execute") || !backend.session?.runtime_available || !live?.published_version) && <p className="max-w-56 px-2 py-1 text-xs text-muted-foreground">{!backend.can("workflow.execute") ? "workflow.execute permission is required." : !backend.session?.runtime_available ? "The runtime is unavailable." : "Publish a revision before running."}</p>}
                    <DropdownMenuItem onSelect={() => navigate({ to: "/app/workflows/$id", params: { id: w.id } })}><Pencil className="mr-2 h-4 w-4" /> Edit draft</DropdownMenuItem>
                    <DropdownMenuItem disabled={busy || live?.activation_state !== "active" || !backend.can("workflow.publish")} title={live?.activation_state !== "active" ? "No active release to disable." : !backend.can("workflow.publish") ? "workflow.publish permission is required." : undefined} onSelect={() => void disable(w.id)}><Power className="mr-2 h-4 w-4" /> Disable</DropdownMenuItem>
                    <DropdownMenuItem disabled={busy || (!!w.serverVersion && !backend.can("workflow.edit"))} onSelect={()=>setRenaming(w)}><Pencil className="mr-2 h-4 w-4" /> Rename</DropdownMenuItem>
                    <DropdownMenuItem onSelect={() => { const id = dup(w.id); if (id) toast("Duplicated as a local draft. Save draft to persist it on the server."); if (id) navigate({ to: "/app/workflows/$id", params: { id } }); }}><Copy className="mr-2 h-4 w-4" /> Duplicate</DropdownMenuItem>
                    {w.serverVersion && backend.can("workflow.delete") && <DropdownMenuItem className="text-destructive" onSelect={() => void remove(w.id, w.name)}><Trash2 className="mr-2 h-4 w-4" /> Delete workflow</DropdownMenuItem>}
                    {!w.serverVersion && <DropdownMenuItem className="text-destructive" onSelect={() => { if (window.confirm(`Delete local draft "${w.name}" from this browser?`)) { del(w.id); toast(`Deleted local draft "${w.name}"`); } }}><Trash2 className="mr-2 h-4 w-4" /> Delete local draft</DropdownMenuItem>}
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
