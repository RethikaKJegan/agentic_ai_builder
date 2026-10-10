"use client";
import { Link, useNavigate } from "@/lib/navigation";
import { Copy, MoreHorizontal, Plus, Trash2 } from "lucide-react";
import { useMesh } from "@/domain/store";
import { StatusPill } from "@/features/shell/StatusPill";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { toast } from "sonner";
import { useBackend } from "@/api/state";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";



export default function WorkflowsPage() {
  const workflows = useMesh((s) => s.workflows);
  const runs = useMesh((s) => s.runs);
  const dup = useMesh((s) => s.duplicateWorkflow);
  const del = useMesh((s) => s.deleteWorkflow);
  const navigate = useNavigate();
  const backend = useBackend();

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold">Workflows</h1>
          <p className="mt-2 text-sm text-muted-foreground">{workflows.filter((w) => w.serverVersion).length} server workflows · {workflows.filter((w) => !w.serverVersion).length} local drafts</p>
        </div>
        <Link to="/app" className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-primary px-3.5 text-sm font-medium text-primary-foreground hover:bg-primary-deep"><Plus className="h-4 w-4" /> New</Link>
      </div>
      {backend.status === "loading" && <p className="mt-4 text-sm text-muted-foreground">Loading server workflows…</p>}
      <ApiFeedback error={backend.error} />
      {workflows.length === 0 ? (
        <p className="mt-8 rounded-xl border border-dashed border-border p-8 text-center text-sm text-muted-foreground">No workflows yet. <Link to="/app" className="text-primary">Create your first draft</Link>.</p>
      ) : (
        <div className="mt-8 divide-y divide-border rounded-xl border border-border">
          {workflows.map((w) => {
            const count = runs.filter((r) => r.workflowId === w.id).length;
            return (
              <div key={w.id} className="flex items-center gap-4 px-4 py-3.5 hover:bg-canvas">
                <Link to="/app/workflows/$id" params={{ id: w.id }} className="min-w-0 flex-1">
                  <p className="truncate font-medium">{w.name}</p>
                  <p className="truncate text-xs text-muted-foreground">{w.nodes.length} steps · {count} runs · edited {new Date(w.updatedAt).toLocaleDateString()}</p>
                </Link>
                <StatusPill status={`${w.serverVersion ? `v${w.serverVersion} · ` : "local · "}${w.status}`} tone={w.status === "published" ? "success" : "neutral"} />
                <DropdownMenu>
                  <DropdownMenuTrigger className="rounded-md p-1.5 text-muted-foreground hover:bg-muted" aria-label={`Actions for ${w.name}`}><MoreHorizontal className="h-4 w-4" /></DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onSelect={() => { const id = dup(w.id); if (id) navigate({ to: "/app/workflows/$id", params: { id } }); }}><Copy className="mr-2 h-4 w-4" /> Duplicate</DropdownMenuItem>
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
