import { readFileSync } from "node:fs";
import path from "node:path";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { beforeEach, afterEach, expect, it, vi } from "vitest";
import { ApiError } from "./client";
import Overview from "@/screens/app.index";
import { CanonicalWorkflowSchema } from "./contracts.generated";
import { useBackend } from "./state";
import { useMesh } from "@/domain/store";
import * as creation from "./create-workflow";
const { navigate } = vi.hoisted(() => ({ navigate: vi.fn() }));
vi.mock("@/lib/navigation", () => ({
  useNavigate: () => navigate,
  Link: ({ children, to }: { children: React.ReactNode; to: string }) => (
    <a href={to}>{children}</a>
  ),
}));
const document = () =>
  CanonicalWorkflowSchema.parse(
    JSON.parse(
      readFileSync(
        path.resolve(process.cwd(), "../shared/contracts/examples/workflows/support-triage.json"),
        "utf8",
      ),
    ),
  );
beforeEach(() => {
  localStorage.clear();
  navigate.mockReset();
  useMesh.setState({ workflows: [], agents: [] });
  useBackend.setState({
    status: "connected",
    error: null,
    session: {
      mode: "local-development",
      planning_available: true,
      runtime_available: true,
      approval_service_available: true,
      auth: {
        subject: { subject_id: "test", workspace_id: "local-workspace" },
        roles: ["builder"],
        permissions: ["workflow.plan", "workflow.view"],
        scopes: [],
        decision: "allow",
      },
    },
  });
  vi.spyOn(useBackend.getState(), "initialize").mockResolvedValue(undefined);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
it("retains the original prompt on planner failure and supports an explicit retry", async () => {
  const request = vi
    .spyOn(creation, "createWorkflow")
    .mockRejectedValueOnce(new ApiError({error_code:"INVALID_WORKFLOW",message:"A condition is missing.",field:"nodes.1",request_id:"req_generation",retryable:false}))
    .mockResolvedValueOnce({ workflow: document(), existing: false });
  render(<Overview />);
  const prompt = screen.getByLabelText("Process description");
  fireEvent.change(prompt, { target: { value: "My original automation prompt" } });
  fireEvent.click(screen.getByRole("button", { name: "Generate workflow" }));
  await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("nodes.1"));
  expect(prompt).toHaveValue("My original automation prompt");
  expect(navigate).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Retry generation" }));
  await waitFor(() =>
    expect(screen.getByRole("region", { name: "Generation result" })).toBeVisible(),
  );
  expect(request).toHaveBeenCalledTimes(2);
  expect(navigate).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Review and edit workflow" }));
  expect(navigate).toHaveBeenCalledOnce();
});
it("does not overwrite unsaved edits when reopening an existing planner identity", async () => {
  const d = document();
  useMesh.getState().acceptWorkflow(d);
  useMesh.getState().renameWorkflow(d.workflow_id, "Keep my dirty draft");
  vi.spyOn(creation, "createWorkflow").mockResolvedValue({ workflow: d, existing: true });
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  render(<Overview />);
  fireEvent.change(screen.getByLabelText("Process description"), {
    target: { value: "Repeated prompt" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Generate workflow" }));
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Review and edit workflow" })).toBeVisible(),
  );
  fireEvent.click(screen.getByRole("button", { name: "Review and edit workflow" }));
  expect(confirm).toHaveBeenCalled();
  expect(navigate).not.toHaveBeenCalled();
  expect(useMesh.getState().workflows[0]?.name).toBe("Keep my dirty draft");
  confirm.mockReturnValue(true);
  fireEvent.click(screen.getByRole("button", { name: "Review and edit workflow" }));
  expect(navigate).toHaveBeenCalledOnce();
  expect(useMesh.getState().workflows[0]?.name).toBe("Keep my dirty draft");
});
it("blocks regeneration of the displayed review unless explicitly chosen", async () => {
  const create = vi
    .spyOn(creation, "createWorkflow")
    .mockResolvedValue({ workflow: document(), existing: false });
  vi.spyOn(window, "confirm").mockReturnValue(false);
  render(<Overview />);
  fireEvent.change(screen.getByLabelText("Process description"), {
    target: { value: "Create this process" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Generate workflow" }));
  await waitFor(() =>
    expect(screen.getByRole("region", { name: "Generation result" })).toBeVisible(),
  );
  fireEvent.click(screen.getByRole("button", { name: "Generate workflow" }));
  expect(create).toHaveBeenCalledTimes(1);
});
