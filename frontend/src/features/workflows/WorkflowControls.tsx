"use client";
import { displayText } from "@/lib/display-text";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { InputError } from "@/api/feedback";
import { api, ApiError } from "@/api/client";
import { useBackend } from "@/api/state";
import { toCanonical, hasWorkflowEdits } from "@/api/mapping";
import { useMesh } from "@/domain/store";
import type { Workflow } from "@/domain/types";
import { assertWorkflowReferences } from "@/api/control";
import { ApiFeedback } from "./ApiFeedback";
import { SheetAccessReview } from "./SheetAccessReview";
import { CustomerAutomationReview } from "./CustomerAutomationReview";
import { ProcurementReview } from "./ProcurementReview";
import { editSnapshot, acceptConfirmed } from "./workflow-state";
import { useUnsavedWorkflow } from "./unsaved";

type Action = "save" | "validate" | "submit" | "approve" | "publish" | "activate" | "reload";
const labels: Record<Action, string> = { save: "Save draft", validate: "Validate", submit: "Submit for approval", approve: "Approve", publish: "Publish", activate: "Activate", reload: "Reload server revision" };
const permissions: Record<Action, string> = { save: "workflow.edit", validate: "workflow.validate", submit: "workflow.validate", approve: "workflow.approve", publish: "workflow.publish", activate: "workflow.publish", reload: "workflow.view" };

export function WorkflowControls({ workflow, onStarted, compact = false }: { workflow: Workflow; onStarted?: () => void; compact?: boolean }) {
  const backend = useBackend(); const agents = useMesh(state => state.agents);
  const [busy, setBusy] = useState<Action | "">(""); const pending = useRef(false);
  const [error, setError] = useState<Error>(); const [message, setMessage] = useState("");
  useUnsavedWorkflow(workflow.id);
  const version = workflow.serverVersion; const document = workflow.canonical;
  const failedAt=useRef<{document:Workflow["canonical"]}|null>(null);
  useEffect(()=>{if(failedAt.current && failedAt.current.document!==document){failedAt.current=null;setError(undefined);}},[document]);
  const dirty = hasWorkflowEdits(workflow, agents);
  let graphError = "";
  try { assertWorkflowReferences(toCanonical(workflow, agents)); } catch (caught) { graphError = caught instanceof Error ? caught.message : "Complete the workflow configuration."; }
  const blocker = (action: Action) => {
    if (backend.status !== "connected") return "Connect to the backend to use this action.";
    if (!backend.can(permissions[action])) return `${permissions[action]} permission is required.`;
    if (action === "reload") return version ? "" : "This local draft has no server revision.";
    if (action === "save") return (workflow.remote ? "Resolve the newer server revision before saving." : "") || graphError || (!dirty ? "No unsaved changes." : "");
    if (dirty) return "Save draft before this action.";
    if (!version || !document) return "Save this draft first.";
    if (action === "validate") return document.status === "draft" || document.status === "validated" ? "" : "Save an edited draft to validate a new revision.";
    if (action === "submit") return document.status !== "validated" ? "Validate this revision first." : document.metadata["approval_submission"] ? "This revision is submitted for review." : "";
    if (action === "approve") return document.status === "validated" ? "" : "A validated revision is required.";
    if (action === "publish") return document.status === "approved" ? "" : "Explicit approval is required before publication.";
    return document.status === "published" ? "" : "Publish this revision before activation.";
  };
  const act = async (action: Action) => {
    if (pending.current || blocker(action)) return;
    if (action === "reload" && dirty && !window.confirm("Reload the server revision and discard this editor's unsaved changes?")) return;
    if (action === "activate" && !window.confirm(`Activate published revision v${version}? Configured events will be allowed to start runs under this revision's reviewed policies.`)) return;
    pending.current = true; setBusy(action); setError(undefined); setMessage("");
    try {
      const state = useMesh.getState(); const current = state.workflows.find(item => item.id === workflow.id) ?? workflow;
      const snapshot = editSnapshot(current, state.agents);
      const ref = { workflow_id: current.id, workflow_version: current.serverVersion! };
      if (action === "activate") {
        const active = useBackend.getState().overview[current.id];
        const result = await api.activateRelease({ ...ref, expected_release_id: active?.activation_state === "active" ? active.release_id : null, triggers: [] });
        setMessage(`Activation ${result.operation.state} · release ${result.release.release_id}`);
      } else {
        const result = action === "save" ? await api.request("save_workflow_version", { workflow_id: current.id, workflow_version: (current.serverVersion ?? 0) + 1, base_version: current.serverVersion ?? 0, workflow: toCanonical(current, state.agents) })
          : action === "reload" ? await api.request("get_workflow", { workflow_id: current.id })
            : action === "submit" ? await api.submitApproval(ref)
              : action === "validate" ? await api.request("validate_workflow", ref)
                : await api.request("approve_workflow", { ...ref, action: action === "approve" ? "approve" : "publish" });
        if (action === "reload") { const now=useMesh.getState(); const edited=now.workflows.find(w=>w.id===current.id);if(edited&&editSnapshot(edited,now.agents)!==snapshot)throw new InputError("Your draft changed while reload was loading. Edits were retained; review and confirm reload again.");now.acceptWorkflow(result.workflow); } else acceptConfirmed(result.workflow, snapshot);
        if (result.registry_review) backend.acceptReview(result.registry_review);
        if (action === "validate" && result.workflow.status !== "validated") throw new InputError("Validation did not pass. Resolve the server validation and Registry blockers, then validate again.");
        setMessage(`${labels[action]} confirmed · v${result.workflow.version} · ${result.workflow.status}`);
      }
      await backend.refreshOverview();
    } catch (caught) { failedAt.current={document:useMesh.getState().workflows.find(w=>w.id===workflow.id)?.canonical}; setError(caught instanceof Error ? caught : new Error("The action could not be confirmed.")); if(caught instanceof ApiError && caught.error.error_code==="REVISION_CONFLICT"){try{const latest=await api.request("get_workflow",{workflow_id:workflow.id});useMesh.getState().observeWorkflows([latest.workflow]);}catch{/* Existing error and working draft remain visible. */}} }
    finally { pending.current = false; setBusy(""); }
  };
  useEffect(() => { if (message && compact) toast.success(message); }, [message, compact]);
  const timestamp = document?.metadata["updated_at"];
  const saved = typeof timestamp === "string" && Number.isFinite(Date.parse(timestamp)) ? new Date(timestamp).toLocaleString() : null;
  const conflict = error instanceof ApiError && ["REVISION_CONFLICT", "RELEASE_CONFLICT"].includes(error.error.error_code);
  const activePublished=!dirty&&document?.status==='published'&&backend.overview[workflow.id]?.activation_state==='active';
  const primary:Action=dirty?'save':document?.status==='draft'?'validate':document?.status==='validated'?(document.metadata['approval_submission']?'approve':'submit'):document?.status==='approved'?'publish':'activate';
  const renderAction=(action:Action)=>{const reason=blocker(action);return <div key={action}><button type="button" disabled={!!busy||!!reason} title={displayText(reason||labels[action])} aria-describedby={`${workflow.id}-${action}-reason`} onClick={()=>void act(action)} className={`rounded-lg border px-3 py-2 text-xs disabled:opacity-40 ${action===primary?'border-primary bg-primary text-primary-foreground':'border-border hover:bg-muted'}`}>{displayText(busy===action?`${labels[action]}…`:labels[action])}</button><span id={`${workflow.id}-${action}-reason`} className="sr-only">{displayText(reason)}</span></div>;};
  return <section aria-label="Workflow actions" className={`flex flex-wrap items-center gap-2 ${compact?"":"w-full"}`}>
    {!compact && <div className="text-[11px] leading-5 text-muted-foreground" role="status">{document ? `${document.status} · server revision v${version}` : "Local draft · no server revision"} · {dirty ? "Unsaved changes" : "No unsaved changes"}{saved ? ` · Saved ${saved}` : version ? " · Saved timestamp unavailable" : ""}</div>}
    <ProcurementReview workflow={workflow} onStarted={onStarted} />
    <SheetAccessReview targets={document?.metadata["sheet_write_targets"]} />
    <CustomerAutomationReview policy={document?.metadata["customer_automation"]} emailPolicy={document?.metadata["email_recipient_policy"]} />
    {activePublished ? onStarted?<button onClick={onStarted} className="rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground">Open execution</button>:<span className="rounded-full bg-emerald-50 px-3 py-1 text-xs text-emerald-800">Release active</span> : renderAction(primary)}
    <details className="relative"><summary className="cursor-pointer rounded-lg border px-3 py-2 text-xs">Revision actions</summary><div className="absolute right-0 top-11 z-40 w-72 space-y-3 rounded-xl border bg-background p-4 shadow-xl">    <div className="text-[11px] leading-5 text-muted-foreground" role="status">{document ? `${document.status} · server revision v${version}` : "Local draft · no server revision"} · {dirty ? "Unsaved changes" : "No unsaved changes"}{saved ? ` · Saved ${saved}` : version ? " · Saved timestamp unavailable" : ""}</div>
<p className="text-xs text-muted-foreground">Each action remains a separate server-confirmed transition.</p><div className="flex flex-wrap gap-2">{(['save','validate','submit','approve','publish','activate','reload'] as const).filter(a=>activePublished||a!==primary).map(renderAction)}</div>{dirty&&document&&<p className="text-[11px] text-muted-foreground">Saving creates a new editable revision. The active release keeps its reviewed revision.</p>}</div></details>
    {conflict && <p role="alert" className="w-full text-sm">The server changed. Your edits are retained. Copy any changes you want to keep before choosing Reload server revision, then reapply them to the latest draft.</p>}
    <div className={error||(!compact&&message)?"w-full":"hidden"}><ApiFeedback error={error} />{message && !compact && <p role="status" className="text-sm text-emerald-700">{displayText(message)}</p>}</div>
  </section>;
}
