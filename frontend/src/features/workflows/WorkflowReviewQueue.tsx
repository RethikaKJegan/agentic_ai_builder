"use client";
import { displayText } from "@/lib/display-text";
import { useEffect, useRef, useState } from "react";
import { api } from "@/api/client";
import { useBackend } from "@/api/state";
import type { CanonicalWorkflow } from "@/api/contracts.generated";
import { useMesh } from "@/domain/store";
import { hasWorkflowEdits } from "@/api/mapping";
import { Link } from "@/lib/navigation";
import { ApiFeedback } from "./ApiFeedback";
export function WorkflowReviewQueue() {
  const backend = useBackend(); const [items, setItems] = useState<CanonicalWorkflow[]>([]); const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error>(); const [busy, setBusy] = useState(""); const pending = useRef(false);
  useEffect(() => {
    if (backend.status !== "connected") return;
    let active = true;
    api.request("list_workflows", {}).then(result => { if (active) setItems(result.items.filter(item => item.status === "validated" && !!item.metadata["approval_submission"])); })
      .catch(caught => { if (active) setError(caught instanceof Error ? caught : new Error("Workflow reviews could not be loaded.")); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [backend.status]);
  const approve = async (workflow: CanonicalWorkflow) => {
    if (pending.current || !backend.can("workflow.approve")) return;
    pending.current = true; setBusy(workflow.workflow_id); setError(undefined);
    try {
      const result = await api.request("approve_workflow", { workflow_id: workflow.workflow_id, workflow_version: workflow.version, action: "approve" });
      const state = useMesh.getState(); const current = state.workflows.find(item => item.id === workflow.workflow_id);
      if (!current || !hasWorkflowEdits(current, state.agents)) state.acceptWorkflow(result.workflow);
      setItems(items => items.filter(item => item.workflow_id !== workflow.workflow_id));
    } catch (caught) { setError(caught instanceof Error ? caught : new Error("Workflow approval failed.")); }
    finally { pending.current = false; setBusy(""); }
  };
  return <section aria-label="Workflow revision approvals" className="mb-6 space-y-3 rounded-xl border p-4"><h2 className="font-medium">Workflow revisions awaiting approval</h2>
    <p className="text-sm text-muted-foreground">Review the exact saved revision before approval. Approval does not publish or activate it.</p>
    <ApiFeedback error={error} />{loading && <p role="status">Loading submitted revisions…</p>}
    {!loading && !error && !items.length && <p className="text-sm text-muted-foreground">No submitted revisions await approval.</p>}
    {items.map(workflow => <div key={workflow.workflow_id} className="flex flex-wrap items-center gap-3 border-t pt-3"><Link to="/app/workflows/$id" params={{ id: workflow.workflow_id }} className="min-w-0 flex-1 text-primary underline">{displayText(workflow.name)} · v{workflow.version}</Link>
      <button type="button" disabled={!!busy || !backend.can("workflow.approve")} onClick={() => void approve(workflow)} className="rounded-lg border px-3 py-2 text-sm disabled:opacity-40">{busy === workflow.workflow_id ? "Approving…" : "Approve revision"}</button>
    </div>)}{!backend.can("workflow.approve") && <p className="text-sm text-muted-foreground">workflow.approve permission is required to approve submitted revisions.</p>}
  </section>;
}
