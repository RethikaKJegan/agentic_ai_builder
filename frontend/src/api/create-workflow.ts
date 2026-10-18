import { api, ApiError, type Payloads, type WorkflowClient } from "./client";

/** A repeated planner identity opens its saved revision instead of replacing it. */
export async function createWorkflow(payload: Payloads["plan_workflow"], client: WorkflowClient = api) {
  const planned = await client.request("plan_workflow", payload);

  try {
    const existing = await client.request("get_workflow", {
      workflow_id: planned.workflow.workflow_id,
    });
    return { ...existing, existing: true };
  } catch (error) {
    if (
      !(error instanceof ApiError) ||
      error.error.error_code !== "WORKFLOW_NOT_FOUND"
    ) {
      throw error;
    }
  }

  try {
    const initial = { ...planned.workflow, version: 1, status: "draft" as const };
    const saved = await client.request("save_workflow_version", {
      workflow_id: planned.workflow.workflow_id,
      workflow_version: 1,
      base_version: 0,
      workflow: initial,
    });
    return { ...saved, existing: false };
  } catch (error) {
    if (!(error instanceof ApiError) || error.error.error_code !== "REVISION_CONFLICT") throw error;
    const saved = await client.request("get_workflow", { workflow_id: planned.workflow.workflow_id });
    return { ...saved, existing: true };
  }
}
