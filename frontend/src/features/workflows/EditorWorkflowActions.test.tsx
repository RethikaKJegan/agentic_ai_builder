import { readFileSync } from "node:fs";
import path from "node:path";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api, type Session } from "@/api/client";
import { CanonicalWorkflowSchema, type CanonicalWorkflow } from "@/api/contracts.generated";
import { useMesh } from "@/domain/store";
import { useBackend } from "@/api/state";
import { EditorWorkflowActions } from "./EditorWorkflowActions";
vi.mock("./ProcurementReview", () => ({ ProcurementReview: () => null }));
vi.mock("./SheetAccessReview", () => ({ SheetAccessReview: () => null }));
vi.mock("./CustomerAutomationReview", () => ({ CustomerAutomationReview: () => null }));
vi.mock("@/lib/navigation", () => ({
  Link: ({ children }: { children: React.ReactNode }) => <span>{children}</span>,
}));
let document: CanonicalWorkflow;
let release: Awaited<ReturnType<typeof api.releaseState>>["release"];
const permissions = [
  "workflow.view",
  "workflow.edit",
  "workflow.validate",
  "workflow.approve",
  "workflow.publish",
  "workflow.execute",
  "runs.view",
];
const started = vi.fn();
function View() {
  const workflow = useMesh((state) => state.workflows[0]);
  return workflow ? (
    <EditorWorkflowActions workflow={workflow} onStarted={started} onExecution={vi.fn()} />
  ) : null;
}
beforeEach(() => {
  document = CanonicalWorkflowSchema.parse(
    JSON.parse(
      readFileSync(
        path.resolve(process.cwd(), "../shared/contracts/examples/workflows/support-triage.json"),
        "utf8",
      ),
    ),
  );
  document.status = "draft";
  document.inputs = [];
  document.metadata = {};
  release = null;
  started.mockReset();
  useMesh.setState({ workflows: [], agents: [] });
  useMesh.getState().acceptWorkflow(document);
  useBackend.setState({
    status: "connected",
    overview: {},
    reviews: {},
    session: {
      runtime_available: true,
      auth: { roles: ["admin"], decision: "allow", permissions },
    } as unknown as Session,
    can: (p) => permissions.includes(p),
    refreshOverview: vi.fn().mockResolvedValue(undefined),
  });
  vi.spyOn(api, "releaseState").mockImplementation(
    async () =>
      ({ workflow_id: document.workflow_id, release }) as Awaited<
        ReturnType<typeof api.releaseState>
      >,
  );
  vi.spyOn(api, "submitApproval").mockImplementation(
    async () =>
      ({
        workflow: (document = {
          ...document,
          metadata: { approval_submission: { workflow_version: document.version } },
        }),
      }) as Awaited<ReturnType<typeof api.submitApproval>>,
  );
  vi.spyOn(api, "activateRelease").mockImplementation(async (payload) => {
    release = {
      release_id: "active-release",
      workflow_version: payload.workflow_version,
      state: "active",
      trigger_binding_count: 0,
    };
    return {
      operation: { state: "succeeded" },
      release: { release_id: "active-release" },
    } as Awaited<ReturnType<typeof api.activateRelease>>;
  });
  vi.spyOn(api, "request").mockImplementation((async (
    operation: Parameters<typeof api.request>[0],
    payload: Parameters<typeof api.request>[1],
  ) => {
    if (operation === "get_workflow") return { workflow: structuredClone(document) };
    if (operation === "save_workflow_version") {
      document = structuredClone((payload as { workflow: CanonicalWorkflow }).workflow);
      return { workflow: structuredClone(document) };
    }
    if (operation === "validate_workflow") document = { ...document, status: "validated" };
    if (operation === "approve_workflow")
      document = {
        ...document,
        status: (payload as { action: string }).action === "approve" ? "approved" : "published",
      };
    if (operation === "execute_workflow")
      return {
        run: {
          run_id: "run-accepted",
          workflow_id: document.workflow_id,
          workflow_version: (payload as { workflow_version: number }).workflow_version,
          status: "queued",
          approvals: [],
        },
      };
    return { workflow: structuredClone(document) };
  }) as never);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
it("runs exact saved stages once and preserves edits present before preparation", async () => {
  useMesh.getState().renameWorkflow(document.workflow_id, "Reviewed draft");
  render(<View />);
  fireEvent.click(screen.getByRole("button", { name: "Prepare & Activate" }));
  fireEvent.click(screen.getByRole("button", { name: "Preparing…" }));
  await screen.findByText(`Active · v${document.version + 1}`);
  const calls = vi.mocked(api.request).mock.calls;
  expect(calls.map((call) => call[0])).toEqual([
    "get_workflow",
    "save_workflow_version",
    "validate_workflow",
    "approve_workflow",
    "approve_workflow",
  ]);
  expect(document.name).toBe("Reviewed draft");
  expect(api.submitApproval).toHaveBeenCalledTimes(1);
  expect(api.activateRelease).toHaveBeenCalledTimes(1);
  const version = document.version;
  for (const call of calls.slice(2)) expect(call[1]).toMatchObject({ workflow_version: version });
});
it("submits for another reviewer without publishing when approval permission is absent", async () => {
  useBackend.setState({ can: (p) => p !== "workflow.approve" && permissions.includes(p) });
  render(<View />);
  fireEvent.click(screen.getByRole("button", { name: "Prepare & Activate" }));
  await screen.findByText(/Awaiting an authorized reviewer/);
  expect(api.submitApproval).toHaveBeenCalledTimes(1);
  expect(
    vi.mocked(api.request).mock.calls.filter((call) => call[0] === "approve_workflow"),
  ).toHaveLength(0);
  expect(api.activateRelease).not.toHaveBeenCalled();
});
it("stops after failed validation and never activates", async () => {
  const previous = vi.mocked(api.request).getMockImplementation()!;
  vi.mocked(api.request).mockImplementation((async (...args: Parameters<typeof api.request>) => {
    if (args[0] === "validate_workflow") return { workflow: structuredClone(document) };
    return previous(...args);
  }) as never);
  render(<View />);
  fireEvent.click(screen.getByRole("button", { name: "Prepare & Activate" }));
  await screen.findByRole("alert");
  expect(api.submitApproval).not.toHaveBeenCalled();
  expect(api.activateRelease).not.toHaveBeenCalled();
});
it("stops on edits made while validation is in flight and retains the new draft", async () => {
  const previous = vi.mocked(api.request).getMockImplementation()!;
  vi.mocked(api.request).mockImplementation((async (...args: Parameters<typeof api.request>) => {
    if (args[0] === "validate_workflow")
      useMesh.getState().renameWorkflow(document.workflow_id, "Concurrent edit");
    return previous(...args);
  }) as never);
  render(<View />);
  fireEvent.click(screen.getByRole("button", { name: "Prepare & Activate" }));
  await screen.findByRole("alert");
  expect(useMesh.getState().workflows[0]!.name).toBe("Concurrent edit");
  expect(api.activateRelease).not.toHaveBeenCalled();
  expect(api.submitApproval).not.toHaveBeenCalled();
});
it("reconciles an already published revision without reapproval and activates only it", async () => {
  document.status = "published";
  useMesh.getState().acceptWorkflow(document);
  render(<View />);
  fireEvent.click(screen.getByRole("button", { name: "Prepare & Activate" }));
  await screen.findByText(`Active · v${document.version}`);
  expect(vi.mocked(api.request).mock.calls.map((call) => call[0])).toEqual(["get_workflow"]);
  expect(api.submitApproval).not.toHaveBeenCalled();
  expect(api.activateRelease).toHaveBeenCalledWith(
    expect.objectContaining({ workflow_version: document.version, expected_release_id: null }),
  );
});
it("runs the active version despite draft edits and reports the accepted run", async () => {
  document.status = "published";
  release = {
    release_id: "old-active",
    workflow_version: document.version,
    state: "active",
    trigger_binding_count: 0,
  };
  useMesh.getState().acceptWorkflow(document);
  useMesh.getState().renameWorkflow(document.workflow_id, "Unsaved name");
  render(<View />);
  const run = await screen.findByRole("button", { name: `Run active v${document.version}` });
  fireEvent.click(run);
  fireEvent.click(run);
  await waitFor(() =>
    expect(started).toHaveBeenCalledWith(
      expect.objectContaining({ run_id: "run-accepted", workflow_version: document.version }),
    ),
  );
  expect(
    vi.mocked(api.request).mock.calls.filter((call) => call[0] === "execute_workflow"),
  ).toHaveLength(1);
  expect(
    vi.mocked(api.request).mock.calls.some((call) => call[0] === "save_workflow_version"),
  ).toBe(false);
  expect(useMesh.getState().workflows[0]!.name).toBe("Unsaved name");
});
it("collects required inputs and refuses a changed active release before execution", async () => {
  document.status = "published";
  document.inputs = [{ name: "message", type: "string", required: true, description: "Input" }];
  release = {
    release_id: "first-release",
    workflow_version: document.version,
    state: "active",
    trigger_binding_count: 0,
  };
  useMesh.getState().acceptWorkflow(document);
  render(<View />);
  fireEvent.click(await screen.findByRole("button", { name: "Run" }));
  await screen.findByLabelText("message");
  fireEvent.change(screen.getByLabelText("message"), { target: { value: "Reviewed input" } });
  release = { ...release, release_id: "changed-release" };
  fireEvent.click(screen.getByRole("button", { name: "Start run" }));
  await screen.findByRole("alert");
  expect(
    vi.mocked(api.request).mock.calls.filter((call) => call[0] === "execute_workflow"),
  ).toHaveLength(0);
  expect(started).not.toHaveBeenCalled();
});
it("refetches and executes an older active revision while a newer draft is open", async () => {
  const older = { ...structuredClone(document), status: "published" as const };
  document = { ...document, version: document.version + 1, status: "draft" };
  release = {
    release_id: "older-release",
    workflow_version: older.version,
    state: "active",
    trigger_binding_count: 0,
  };
  useMesh.getState().acceptWorkflow(document);
  const previous = vi.mocked(api.request).getMockImplementation()!;
  vi.mocked(api.request).mockImplementation((async (...args: Parameters<typeof api.request>) => {
    if (
      args[0] === "get_workflow" &&
      (args[1] as { workflow_version?: number }).workflow_version === older.version
    )
      return { workflow: older };
    return previous(...args);
  }) as never);
  render(<View />);
  fireEvent.click(await screen.findByRole("button", { name: `Run active v${older.version}` }));
  await waitFor(() =>
    expect(started).toHaveBeenCalledWith(
      expect.objectContaining({ workflow_version: older.version }),
    ),
  );
  expect(useMesh.getState().workflows[0]!.serverVersion).toBe(document.version);
});
it("stops at a server-denied approval without publishing or activating", async () => {
  const previous = vi.mocked(api.request).getMockImplementation()!;
  vi.mocked(api.request).mockImplementation((async (...args: Parameters<typeof api.request>) => {
    if (args[0] === "approve_workflow") throw new Error("Approval denied");
    return previous(...args);
  }) as never);
  render(<View />);
  fireEvent.click(screen.getByRole("button", { name: "Prepare & Activate" }));
  await screen.findByRole("alert");
  expect(api.activateRelease).not.toHaveBeenCalled();
  expect(
    vi.mocked(api.request).mock.calls.filter((call) => call[0] === "approve_workflow"),
  ).toHaveLength(1);
});
