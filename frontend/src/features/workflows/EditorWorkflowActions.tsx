"use client";
import { useRef, useState } from "react";
import { api, type RunRecord } from "@/api/client";
import { useBackend } from "@/api/state";
import { useMesh } from "@/domain/store";
import { hasWorkflowEdits, toCanonical } from "@/api/mapping";
import { assertWorkflowReferences } from "@/api/control";
import { InputError } from "@/api/feedback";
import type { CanonicalWorkflow } from "@/api/contracts.generated";
import type { Workflow } from "@/domain/types";
import { acceptConfirmed, editSnapshot } from "./workflow-state";
import { ApiFeedback } from "./ApiFeedback";
import { RunWorkflowDialog } from "./RunWorkflowDialog";
import { WorkflowControls } from "./WorkflowControls";

export function EditorWorkflowActions({ workflow, onStarted, onExecution }: {
  workflow: Workflow; onStarted: (run: RunRecord) => void; onExecution: () => void;
}) {
  const backend = useBackend();
  const agents = useMesh(state => state.agents);
  const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  const [error, setError] = useState<Error>();
  const [runDocument, setRunDocument] = useState<CanonicalWorkflow>();
  const dirty = hasWorkflowEdits(workflow, agents);
  async function run() {
    if (lock.current) return;
    lock.current = true; setBusy(true); setError(undefined);
    try {
      if (!backend.can("workflow.execute")) throw new InputError("workflow.execute permission is required.");
      if (!backend.session?.runtime_available) throw new InputError("The runtime is unavailable.");
      const state = useMesh.getState();
      const current = state.workflows.find(item => item.id === workflow.id) ?? workflow;
      if (current.remote) throw new InputError("Review the newer server revision before running this draft.");
      const snapshot = editSnapshot(current, state.agents);
      let document = current.canonical;
      if (!current.serverVersion || hasWorkflowEdits(current, state.agents)) {
        if (!backend.can("workflow.edit")) throw new InputError("workflow.edit permission is required to save changes.");
        const canonical = toCanonical(current, state.agents);
        assertWorkflowReferences(canonical);
        const result = await api.request("save_workflow_version", {
          workflow_id: current.id, workflow_version: (current.serverVersion ?? 0) + 1,
          base_version: current.serverVersion ?? 0, workflow: canonical,
        });
        acceptConfirmed(result.workflow, snapshot); document = result.workflow;
      } else {
        const result = await api.request("get_workflow", { workflow_id: current.id, workflow_version: current.serverVersion });
        document = result.workflow;
      }
      const now = useMesh.getState();
      const edited = now.workflows.find(item => item.id === workflow.id) ?? workflow;
      if (editSnapshot(edited, now.agents) !== snapshot && hasWorkflowEdits(edited, now.agents))
        throw new InputError("The draft changed while saving. Your edits are retained; run the reviewed version again.");
      if (!document) throw new InputError("The saved revision could not be confirmed.");
      setRunDocument(document);
    } catch (caught) { setError(caught instanceof Error ? caught : new InputError("Run could not be started.")); }
    finally { lock.current = false; setBusy(false); }
  }
  return <section aria-label="Workflow launch actions" className="flex min-w-0 flex-wrap items-center gap-2">
    <button type="button" disabled={busy || backend.status !== "connected" || !backend.can("workflow.execute")} onClick={() => void run()} className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-40">{busy ? "Preparing run…" : "Run"}</button>
    <span className="text-xs text-muted-foreground">{dirty ? "Changes are saved before Run." : `Revision v${workflow.serverVersion ?? 1}`} · Run checks configuration and permissions automatically.</span>
    <details className="w-full"><summary className="cursor-pointer text-xs text-muted-foreground">Revision and schedule actions</summary><div className="mt-3"><WorkflowControls workflow={workflow} onStarted={onExecution}/></div></details>
    <ApiFeedback error={error}/>
    {runDocument && <RunWorkflowDialog workflow={runDocument} autoStart onClose={() => setRunDocument(undefined)} onStarted={onStarted}/>}
  </section>;
}
