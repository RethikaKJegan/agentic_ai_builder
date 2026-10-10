import { useState } from "react";
import { FlaskConical, Rocket, X } from "lucide-react";
import { api } from "@/api/client";
import { useBackend } from "@/api/state";
import { toCanonical, hasWorkflowEdits } from "@/api/mapping";
import { useMesh } from "@/domain/store";
import type { Workflow } from "@/domain/types";
import { runTotals, simulateRun, type SimResult } from "@/domain/simulator";
import { RunTrace } from "@/features/runs/RunTrace";
import { assertWorkflowReferences } from "@/api/control";

export function WorkflowControls({ workflow }: { workflow: Workflow }) {
  const backend = useBackend();
  const agents = useMesh((s) => s.agents);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState<string>();
  const [test, setTest] = useState<SimResult>();
  const version = workflow.serverVersion;
  const activeRelease = backend.overview[workflow.id];
  if (backend.status !== "connected") return null;
  const dirty = hasWorkflowEdits(workflow, agents);
  let graphError: Error | null = null;
  try { assertWorkflowReferences(toCanonical(workflow, agents)); } catch (caught) { graphError = caught instanceof Error ? caught : new Error("Complete the workflow configuration."); }
  const saveDraft = async () => {
    const state = useMesh.getState();
    const current = state.workflows.find((item) => item.id === workflow.id) ?? workflow;
    const document = toCanonical(current, state.agents);
    const result = await api.request("save_workflow_version", { workflow_id: document.workflow_id,
      workflow_version: document.version, base_version: current.serverVersion ?? 0, workflow: document });
    useMesh.getState().acceptWorkflow(result.workflow);
    if (result.registry_review) backend.acceptReview(result.registry_review);
    return result.workflow;
  };
  const testWorkflow = () => {
    setError(undefined);
    if (graphError) { setError(graphError.message); return; }
    const state = useMesh.getState();
    const current = state.workflows.find((item) => item.id === workflow.id) ?? workflow;
    // This simulation is local. It cannot call a connector, send mail, or modify a provider resource.
    setTest(simulateRun(current, state.agents, current.description || "Safe editor test", {}, undefined, state.controlContext(current.id)));
  };
  const publish = async () => {
    if (busy || graphError || backend.status !== "connected") return;
    setBusy("publish"); setError(undefined);
    try {
      let document = workflow.canonical;
      if (dirty || !document || !version) document = await saveDraft();
      const ref = { workflow_id: document.workflow_id, workflow_version: document.version };
      if (document.status === "draft") {
        const validated = await api.request("validate_workflow", ref);
        useMesh.getState().acceptWorkflow(validated.workflow);
        document = validated.workflow;
      }
      if (document.status === "validated") {
        const approved = await api.request("approve_workflow", { ...ref, action: "approve" });
        useMesh.getState().acceptWorkflow(approved.workflow);
        document = approved.workflow;
      }
      if (document.status !== "approved") throw new Error("This revision cannot be published. Resolve its review requirements first.");
      const published = await api.request("approve_workflow", { workflow_id: document.workflow_id, workflow_version: document.version, action: "publish" });
      useMesh.getState().acceptWorkflow(published.workflow);
      await api.activateRelease({ workflow_id: document.workflow_id, workflow_version: document.version,
        expected_release_id: activeRelease?.activation_state === "active" ? activeRelease.release_id : null, triggers: [] });
      await backend.refreshOverview();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "The workflow could not be published."); }
    finally { setBusy(""); }
  };
  const saved = workflow.updatedAt ? new Date(workflow.updatedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "just now";
  const totals = test ? runTotals(test.steps) : null;
  return <>
    <span className="hidden items-center gap-1 text-xs text-muted-foreground lg:flex">{dirty ? "Unsaved edits" : `Saved ${saved}`}</span>
    <button type="button" onClick={testWorkflow} className="flex h-8 items-center gap-1 rounded-lg border border-border px-2.5 text-sm hover:border-border-accent" aria-label="Test workflow"><FlaskConical className="h-4 w-4" />Test</button>
    <button type="button" onClick={() => void publish()} disabled={!!busy || !!graphError || backend.status !== "connected" || !backend.can("workflow.publish")} className="flex h-8 items-center gap-1 rounded-lg bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary-deep disabled:opacity-40"><Rocket className="h-4 w-4" />{busy ? "Publishing…" : "Publish"}</button>
    {error && <p role="alert" className="absolute right-4 top-14 z-30 max-w-md rounded-lg border border-destructive/40 bg-background px-3 py-2 text-xs text-destructive shadow-sm">{error}</p>}
    {test && <div role="dialog" aria-modal="true" aria-label="Safe test run" className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/20 p-4">
      <div className="max-h-[80vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-border bg-background p-5 shadow-xl">
        <div className="flex items-start gap-3"><div className="min-w-0 flex-1"><h2 className="font-display text-xl font-semibold">Test run</h2><p className="mt-1 text-sm text-muted-foreground">Simulated locally. No email, Sheets update, webhook, or external connector was called.</p></div><button onClick={() => setTest(undefined)} className="rounded-md p-1 text-muted-foreground hover:bg-muted" aria-label="Close test run"><X className="h-5 w-5" /></button></div>
        <div className="my-4 grid grid-cols-4 gap-2 rounded-xl bg-muted/50 p-3 text-center text-xs"><span><b className="block text-base">{test.status}</b>Status</span><span><b className="block text-base">{test.steps.length}</b>Steps</span><span><b className="block text-base">{totals?.tokens ?? 0}</b>Tokens</span><span><b className="block text-base">${totals?.cost.toFixed(4) ?? "0.0000"}</b>Estimated</span></div>
        <RunTrace steps={test.steps} />
      </div>
    </div>}
  </>;
}
