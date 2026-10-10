import { useEffect, useState } from "react";
import { api } from "@/api/client";
import { useBackend } from "@/api/state";
import { toCanonical, hasWorkflowEdits } from "@/api/mapping";
import { useMesh } from "@/domain/store";
import type { Workflow } from "@/domain/types";
import { ApiFeedback } from "./ApiFeedback";
import { assertWorkflowReferences } from "@/api/control";

export function WorkflowControls({ workflow }: { workflow: Workflow }) {
  const backend = useBackend();
  const agents = useMesh((s) => s.agents);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState<Error | null>(null);
  const [correlation, setCorrelation] = useState<string>();
  const version = workflow.serverVersion;
  useEffect(() => {
    if (backend.status !== "connected" || !version) return;
    let active = true;
    void api.request("get_workflow", { workflow_id: workflow.id, workflow_version: version }).then((result) => {
      if (active && result.registry_review) useBackend.getState().acceptReview(result.registry_review);
    }).catch((caught) => { if (active) setError(caught instanceof Error ? caught : new Error("Registry review is unavailable.")); });
    return () => { active = false; };
  }, [backend.status, workflow.id, version]);
  if (backend.status !== "connected") return null;
  const dirty = hasWorkflowEdits(workflow, agents);
  let graphError: Error | null = null;
  try { assertWorkflowReferences(toCanonical(workflow, agents)); } catch (caught) { graphError = caught instanceof Error ? caught : new Error("Complete the workflow configuration."); }
  const unresolved = workflow.canonical?.metadata["unresolved_requirements"];
  const review = backend.reviews[workflow.id];
  const exactReview = review?.workflow_version === version ? review : undefined;
  const blockers = !!workflow.canonical && ((workflow.canonical.tools.length > 0 || workflow.canonical.agents.length > 0) && !exactReview?.ready || (Array.isArray(unresolved) && unresolved.length > 0) || (workflow.canonical.execution_policy.allow_external_writes === true && !backend.session?.approval_service_available));
  const action = async (name: "save" | "validate" | "approve" | "publish") => {
    if (busy) return;
    setBusy(name); setError(null);
    try {
      let result;
      if (name === "save") {
        const state = useMesh.getState();
        const current = state.workflows.find((w) => w.id === workflow.id) ?? workflow;
        const document = toCanonical(current, state.agents);
        result = await api.request("save_workflow_version", { workflow_id: document.workflow_id,
          workflow_version: document.version, base_version: current.serverVersion ?? 0, workflow: document });
      } else {
        if (!version) throw new Error("Save the draft before continuing.");
        const ref = { workflow_id: workflow.id, workflow_version: version };
        result = name === "validate" ? await api.request("validate_workflow", ref)
          : await api.request("approve_workflow", { ...ref, action: name });
      }
      useMesh.getState().acceptWorkflow(result.workflow);
      if (result.registry_review) backend.acceptReview(result.registry_review);
      setCorrelation(result.correlation_id);
    } catch (caught) { setError(caught instanceof Error ? caught : new Error("The operation failed.")); }
    finally { setBusy(""); }
  };
  const button = "rounded-lg border border-border px-3 py-1.5 text-xs hover:border-primary disabled:opacity-40";
  return <div className="shrink-0 space-y-2 border-b border-border px-3 py-2" aria-label="Workflow API controls">
    <div className="flex flex-wrap items-center gap-2">
      <span className="mr-auto text-xs text-muted-foreground">{version ? `Server revision v${version} · ${workflow.status}` : "Local draft · not saved to server"}</span>
      {backend.can("workflow.edit") && <button className={button} disabled={!!busy} onClick={() => void action("save")}>{busy === "save" ? "Saving…" : "Save revision"}</button>}
      {backend.can("workflow.validate") && <button className={button} disabled={!!busy || !version || dirty || !["draft", "validated"].includes(workflow.status)} onClick={() => void action("validate")}>{busy === "validate" ? "Validating…" : "Validate"}</button>}
      {backend.can("workflow.approve") && <button className={button} disabled={!!busy || dirty || !!graphError || workflow.status !== "validated" || blockers} onClick={() => void action("approve")}>Approve revision</button>}
      {backend.can("workflow.publish") && <button className={button} disabled={!!busy || dirty || !!graphError || workflow.status !== "approved" || blockers} onClick={() => void action("publish")}>Publish</button>}
    </div>
    {blockers && <p className="text-xs text-muted-foreground">Tool/capability assignments require registry authorization before approval or publication.</p>}
    {exactReview && <div className="space-y-1 text-xs text-muted-foreground" aria-label="Registry assignment review">
      <p>{exactReview.ready ? "Registry requirements authorized for this revision" : `Registry blockers: ${exactReview.reason_codes.join(", ")}`}</p>
      {exactReview.items.map((item, index) => <p key={`${item.agent_id}:${item.tool_id}:${index}`}>
        {item.agent_id} · {item.capability ?? "Agent registration"} · {item.tool_id ?? "No assigned tool"} · {item.authorization_state}
        {item.reason_codes.length > 0 && ` · ${item.reason_codes.join(", ")}`}
      </p>)}
    </div>}
    {!!workflow.canonical?.tools.length && <p className="text-xs text-muted-foreground">Requested tools: {workflow.canonical.tools.map((tool) => `${tool.capability} (${tool.tool_id})`).join(", ")}</p>}
    {version && dirty && <p className="text-xs text-muted-foreground">Save your edits as a new revision before validating or approving.</p>}
    <ApiFeedback error={error ?? graphError} correlationId={correlation} />
  </div>;
}
