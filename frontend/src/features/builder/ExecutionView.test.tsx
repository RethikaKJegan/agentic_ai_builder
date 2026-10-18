import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ExecutionView } from "./ExecutionView";
import type { WorkflowTrace } from "./useWorkflowTrace";
import { api, type Session } from "@/api/client";
import { useBackend } from "@/api/state";

vi.mock("@xyflow/react", () => ({ ReactFlow: () => null, ReactFlowProvider: ({ children }: { children: React.ReactNode }) => children, Background: () => null, Controls: () => null, MiniMap: () => null, MarkerType: { ArrowClosed: "arrowclosed" } }));
vi.mock("./MeshNode", () => ({ MeshNode: () => null }));
vi.mock("./AgentCommunication", () => ({ AgentCommunication: () => null }));
vi.mock("./ProcurementProjectCommunication", () => ({ ProcurementProjectCommunication: () => null }));
const approval = { approval_id: "approval_sheet", workflow_id: "inventory", workflow_version: 1, status: "pending" as const, allowed_decisions: ["approved" as const, "rejected" as const] };
function trace(): WorkflowTrace {
  return {
    available: true, runs: [], runId: "run_inventory", selectRun: vi.fn(),
    run: { run_id: "run_inventory", workflow_id: "inventory", workflow_version: 1, status: "paused_for_approval", approvals: [approval] },
    revision: { workflow: { id: "inventory", nodes: [{ id: "gate", type: "mesh", position: { x: 0, y: 0 }, data: { label: "Approve spreadsheet", kind: "approval" } }], edges: [] }, agents: [] },
    events: [{ event_id: "evt", event_type: "approval.pending", details: { approval_id: approval.approval_id, node_id: "gate", email_preview: { subject: "Inventory summary" } } }],
    runState: {}, activeEdges: new Set(), error: null, loading: false,
    hasMoreRuns: false, loadMoreRuns: vi.fn(), hasMoreEvents: false, loadMoreEvents: vi.fn(), retry: vi.fn(),
  } as unknown as WorkflowTrace;
}
beforeEach(() => {
  useBackend.setState({ status: "connected", session: { auth: { subject: { subject_id: "reviewer", workspace_id: "local-workspace" }, roles: ["approver"], permissions: ["runs.view", "workflow.approve"], scopes: [], decision: "allow" }, mode: "local-development", runtime_available: true, planning_available: true, approval_service_available: true } as Session });
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });
it.each(["approved", "rejected"] as const)("decides %s inline for the exact run approval and refreshes", async decision => {
  const current = trace();
  const request = vi.spyOn(api, "request").mockResolvedValue({ ...approval, status: decision, allowed_decisions: [] } as never);
  render(<ExecutionView trace={current} onDesign={vi.fn()} />);
  expect(screen.getByRole("region", { name: "Approvals for this run" })).toBeVisible();
  expect(screen.getByText("Approve spreadsheet")).toBeVisible();
  expect(screen.getByLabelText("Email awaiting approval")).toHaveTextContent("Inventory summary");
  fireEvent.click(screen.getByRole("button", { name: decision === "approved" ? "Approve" : "Reject" }));
  await waitFor(() => expect(current.retry).toHaveBeenCalledOnce());
  expect(request).toHaveBeenCalledExactlyOnceWith("decide_approval", { approval_id: "approval_sheet", workflow_id: "inventory", workflow_version: 1, decision });
  expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
});
it("hides decisions for terminal runs, wrong selection and mismatched bindings", () => {
  for (const mutate of [
    (value: WorkflowTrace) => { value.run!.status = "completed"; },
    (value: WorkflowTrace) => { value.runId = "other_run"; },
    (value: WorkflowTrace) => { value.run!.approvals = [{ ...approval, workflow_id: "other_workflow" }]; },
    (value: WorkflowTrace) => { value.run!.approvals = [{ ...approval, workflow_version: 2 }]; },
  ]) {
    const current = trace(); mutate(current);
    const view = render(<ExecutionView trace={current} onDesign={vi.fn()} />);
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
    view.unmount();
  }
});
it("keeps server permission checks for inline approvals", () => {
  useBackend.setState({ session: { ...useBackend.getState().session!, auth: { ...useBackend.getState().session!.auth, permissions: ["runs.view"] } } });
  render(<ExecutionView trace={trace()} onDesign={vi.fn()} />);
  expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
});
