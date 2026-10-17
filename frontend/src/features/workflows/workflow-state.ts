import { workflowEditSnapshot, olderDocument } from "@/api/mapping";
import { useMesh } from "@/domain/store";
import type { Workflow, Agent } from "@/domain/types";
import type { CanonicalWorkflow } from "@/api/contracts.generated";

export function editSnapshot(workflow: Workflow, agents: Agent[]) {
  return workflowEditSnapshot(workflow,agents);
}
export function acceptConfirmed(document: CanonicalWorkflow, submittedSnapshot: string) {
  const state = useMesh.getState();
  const current = state.workflows.find(workflow => workflow.id === document.workflow_id);
  if (olderDocument(document,current?.canonical)) return;
  if (!current || editSnapshot(current, state.agents) === submittedSnapshot) state.acceptWorkflow(document);
  else useMesh.setState({ workflows: state.workflows.map(workflow => workflow.id === document.workflow_id
    ? { ...workflow, canonical: structuredClone(document), serverVersion: document.version, status: document.status, remote: undefined, tabConflict: undefined } : workflow) });
}
