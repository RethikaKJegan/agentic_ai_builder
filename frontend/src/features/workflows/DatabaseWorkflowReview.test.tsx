import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api, type ApprovalRecord } from "@/api/client";
import { useBackend } from "@/api/state";
import type { CanonicalWorkflow } from "@/api/contracts.generated";
import type { DatabaseOperation } from "@/api/data-operations";
import { ApprovalControl } from "@/features/runs/ServerRunView";
import { DatabaseWorkflowReview } from "./DatabaseWorkflowReview";

const operation: DatabaseOperation = {
  operation_id: "dbop_" + "a".repeat(32),
  state: "prepared",
  created_at: Date.now() / 1000,
  expires_at: Date.now() / 1000 + 600,
  recovery_until: Date.now() / 1000 + 86400,
  recovery_of: null,
  recovery_operation_id: null,
  preview_available: true,
  steps: [
    {
      action: "update",
      connection_id: "mongo",
      dataset_id: "records",
      label: "Atlas / records",
      tool_id: "mongodb_update_record",
      state: "pending",
      matched_records: 0,
      affected_records: 0,
      error_code: null,
      identity: { _id: "demo" },
      values: { name: "Reviewed change" },
      unset_fields: [],
      before: { _id: "demo", name: "Before" },
      after: null,
    },
  ],
};
const approval: ApprovalRecord = {
  approval_id: "review",
  workflow_id: "workflow",
  workflow_version: 1,
  status: "pending" as const,
  allowed_decisions: ["approved", "rejected"],
};

beforeEach(() => {
  useBackend.setState({
    status: "connected",
    error: null,
    session: {
      mode: "local-development",
      planning_available: false,
      runtime_available: true,
      approval_service_available: true,
      auth: {
        subject: { subject_id: "owner", workspace_id: "one" },
        roles: ["admin"],
        permissions: ["runs.view", "workflow.approve"],
        scopes: ["workspace:read", "workspace:write"],
        decision: "allow",
      },
    },
  });
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("shows planned sources and mapped operations without claiming execution", () => {
  const document = {
    metadata: {
      database_scope: {
        sources: [
          {
            connection_id: "mongo",
            dataset_id: "records",
            label: "Atlas / records",
            engine: "mongodb",
            context_hash: "a".repeat(64),
          },
        ],
        graph_hash: null,
      },
    },
    nodes: [
      {
        node_id: "prepare",
        label: "Prepare update",
        tool_id: "database_prepare_operation",
        agent_id: "specialist",
        configuration: { input_mapping: { steps: "outputs.master.steps" } },
      },
    ],
  } as unknown as CanonicalWorkflow;
  render(<DatabaseWorkflowReview document={document} />);
  expect(screen.getByRole("region", { name: "Planned database operations" })).toBeInTheDocument();
  expect(screen.getByText(/Atlas \/ records/)).toBeInTheDocument();
  expect(screen.getByText(/These are planned sources/)).toBeInTheDocument();
  expect(screen.getByText(/outputs.master.steps/)).toBeInTheDocument();
});

it("requires the concrete database preview checkbox before approval", async () => {
  vi.spyOn(api, "databaseOperation").mockResolvedValue(operation);
  const decide = vi
    .spyOn(api, "request")
    .mockResolvedValue({ ...approval, status: "approved", allowed_decisions: [] } as never);
  render(<ApprovalControl approval={approval} databaseOperationId={operation.operation_id} />);
  expect(screen.getByRole("button", { name: "Approve" })).toBeDisabled();
  await screen.findByText(/Reviewed change/);
  expect(screen.getByRole("button", { name: "Reject" })).toBeEnabled();
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(screen.getByRole("button", { name: "Approve" }));
  await waitFor(() => expect(decide).toHaveBeenCalledTimes(1));
});

it("blocks approval when the current preview is stale or unavailable", async () => {
  vi.spyOn(api, "databaseOperation").mockResolvedValue({ ...operation, preview_available: false });
  render(<ApprovalControl approval={approval} databaseOperationId={operation.operation_id} />);
  await screen.findByRole("alert");
  expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Approve" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Reject" })).toBeEnabled();
});

it("blocks approval when evidence loading fails", async () => {
  vi.spyOn(api, "databaseOperation").mockRejectedValue(new Error("unavailable"));
  render(<ApprovalControl approval={approval} databaseOperationId={operation.operation_id} />);
  await screen.findByText(/could not be loaded/);
  expect(screen.getByRole("button", { name: "Approve" })).toBeDisabled();
});
