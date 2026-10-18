import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { databaseOperationsSchema, type DatabaseOperation } from "@/api/data-operations";
import fixture from "../../../e2e/fixtures/database-operations.json";
import DatabaseOperations from "./DatabaseOperations";

vi.mock("next/navigation", () => ({
  usePathname: () => "/app/data-intelligence",
  useParams: () => ({}),
  useSearchParams: () => new URLSearchParams(),
  useRouter: () => ({ push: vi.fn() }),
}));

const status = () => databaseOperationsSchema.parse(structuredClone(fixture));
const prepared = (): DatabaseOperation => ({
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
      action: "create",
      connection_id: "pg",
      dataset_id: "pg_records",
      label: fixture.targets[0]!.label,
      tool_id: "postgresql_create_record",
      state: "pending",
      matched_records: 0,
      affected_records: 0,
      error_code: null,
      identity: { id: "DEMO-001" },
      values: { name: "Demo" },
      unset_fields: [],
      before: null,
      after: null,
    },
  ],
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

async function draft() {
  fireEvent.change(screen.getByLabelText("Record identity (JSON)"), {
    target: { value: '{"id":"DEMO-001"}' },
  });
  fireEvent.change(screen.getByLabelText("Field values (JSON)"), {
    target: { value: '{"name":"Demo"}' },
  });
  fireEvent.click(screen.getByRole("button", { name: "Add operation step" }));
  fireEvent.click(screen.getByRole("button", { name: "Prepare operation" }));
  await screen.findByRole("button", { name: "Execute reviewed operation" });
}

it("shows disabled policy honestly without simulated targets", async () => {
  vi.spyOn(api, "databaseOperations").mockResolvedValue({
    ...status(),
    configured: false,
    targets: [],
  });
  render(<DatabaseOperations canManage />);
  expect(await screen.findByText(/No database operation targets are enabled/)).toBeVisible();
  expect(screen.queryByRole("button", { name: "Read record" })).toBeNull();
});

it("routes workflow-owned prepared changes to Execution without a console execute button", async () => {
  const operation = { ...prepared(), workflow_run_id: "run_owned", workflow_id: "workflow_owned" };
  vi.spyOn(api, "databaseOperations").mockResolvedValue({ ...status(), items: [operation] });
  vi.spyOn(api, "databaseOperation").mockResolvedValue(operation);
  render(<DatabaseOperations canManage />);
  const history = await screen.findByRole("region", { name: "Database operation history" });
  fireEvent.click(history.querySelector("button")!);
  const link = await screen.findByRole("link", { name: "Open workflow" });
  expect(link).toHaveAttribute("href", "/app/workflows/workflow_owned");
  expect(screen.queryByRole("button", { name: "Execute reviewed operation" })).toBeNull();
});

it("requires exact preview review before execution and separately reviews recovery", async () => {
  vi.spyOn(api, "databaseOperations").mockResolvedValue(status());
  const prepare = vi.spyOn(api, "prepareDatabaseOperation").mockResolvedValue(prepared());
  const complete = prepared();
  complete.state = "succeeded";
  complete.steps[0]!.state = "succeeded";
  complete.steps[0]!.affected_records = 1;
  const execute = vi.spyOn(api, "executeDatabaseOperation").mockResolvedValue(complete);
  const inverse = prepared();
  inverse.operation_id = "dbop_" + "b".repeat(32);
  inverse.recovery_of = complete.operation_id;
  inverse.steps[0]!.action = "delete";
  vi.spyOn(api, "recoverDatabaseOperation").mockResolvedValue(inverse);
  render(<DatabaseOperations canManage />);
  await screen.findByLabelText("Operation dataset");
  await draft();
  expect(prepare).toHaveBeenCalledWith(
    [
      {
        connection_id: "pg",
        dataset_id: "pg_records",
        action: "create",
        identity: { id: "DEMO-001" },
        values: { name: "Demo" },
        unset_fields: [],
      },
    ],
    expect.any(String),
  );
  expect(execute).not.toHaveBeenCalled();
  expect(screen.getByRole("button", { name: "Execute reviewed operation" })).toBeDisabled();
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(screen.getByRole("button", { name: "Execute reviewed operation" }));
  expect(await screen.findByText("State: succeeded")).toBeVisible();
  expect(execute).toHaveBeenCalledExactlyOnceWith(complete.operation_id);
  fireEvent.click(screen.getByRole("button", { name: "Prepare guarded recovery" }));
  expect(await screen.findByText(/Compensating operation for/)).toBeVisible();
  expect(screen.getByRole("button", { name: "Execute reviewed operation" })).toBeDisabled();
  expect(execute).toHaveBeenCalledOnce();
});

it("reads an exact record without preparing a write", async () => {
  vi.spyOn(api, "databaseOperations").mockResolvedValue(status());
  const read = vi
    .spyOn(api, "readDatabaseRecord")
    .mockResolvedValue({
      record: { id: "DEMO-001", name: "Demo" },
      matched_records: 1,
      label: fixture.targets[0]!.label,
    });
  const prepare = vi.spyOn(api, "prepareDatabaseOperation");
  render(<DatabaseOperations canManage />);
  await screen.findByLabelText("Operation dataset");
  fireEvent.change(screen.getByLabelText("Record identity (JSON)"), {
    target: { value: '{"id":"DEMO-001"}' },
  });
  fireEvent.click(screen.getByRole("button", { name: "Read record" }));
  expect(await screen.findByLabelText("Record read result")).toHaveTextContent("Demo");
  expect(read).toHaveBeenCalledWith({
    connection_id: "pg",
    dataset_id: "pg_records",
    identity: { id: "DEMO-001" },
  });
  expect(prepare).not.toHaveBeenCalled();
});

it("does not retry uncertain writes or offer automatic compensation", async () => {
  vi.spyOn(api, "databaseOperations").mockResolvedValue(status());
  vi.spyOn(api, "prepareDatabaseOperation").mockResolvedValue(prepared());
  const result = prepared();
  result.state = "uncertain";
  result.steps[0]!.state = "uncertain";
  result.steps[0]!.error_code = "DATA_WRITE_UNCERTAIN";
  const execute = vi.spyOn(api, "executeDatabaseOperation").mockResolvedValue(result);
  render(<DatabaseOperations canManage />);
  await screen.findByLabelText("Operation dataset");
  await draft();
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(screen.getByRole("button", { name: "Execute reviewed operation" }));
  expect(await screen.findByText(/The commit outcome is uncertain/)).toBeVisible();
  expect(screen.queryByRole("button", { name: "Execute reviewed operation" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Prepare guarded recovery" })).toBeNull();
  await waitFor(() => expect(execute).toHaveBeenCalledOnce());
});
