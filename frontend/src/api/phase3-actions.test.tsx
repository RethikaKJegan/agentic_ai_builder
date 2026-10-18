import { readFileSync } from "node:fs";
import path from "node:path";
import { webcrypto } from "node:crypto";
import { TextEncoder } from "node:util";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { beforeEach, afterEach, expect, it, vi } from "vitest";
import { api, ApiError, WorkflowClient, type Session } from "./client";
import { CanonicalWorkflowSchema, CanonicalToolSchema, CanonicalAgentSchema } from "./contracts.generated";
import { useMesh } from "@/domain/store";
import { useBackend } from "./state";
import { hasWorkflowEdits } from "./mapping";
import { WorkflowControls } from "@/features/workflows/WorkflowControls";
import { RunWorkflowDialog } from "@/features/workflows/RunWorkflowDialog";
import { parseRunInputs } from "@/features/workflows/run-inputs";
import { confirmDraftNavigation } from "@/features/workflows/unsaved";
import { ServerRunView } from "@/features/runs/ServerRunView";
import { RevisionHistory } from "@/features/workflows/RevisionHistory";
import { WorkflowReviewQueue } from "@/features/workflows/WorkflowReviewQueue";
import Settings from "@/screens/app.settings";
import Integrations from "@/screens/app.integrations";
vi.mock("@/lib/navigation", () => ({ Link: ({ children, to, search }: { children: React.ReactNode; to: string; search?: Record<string, string> }) => <a href={to + (search ? "?" + new URLSearchParams(search).toString() : "")}>{children}</a> }));
const fixture = (name: string) => JSON.parse(readFileSync(path.resolve(process.cwd(), "../shared/contracts/examples", name), "utf8"));
const workflow = () => CanonicalWorkflowSchema.parse(fixture("workflows/support-triage.json"));
const permissions = ["workflow.view", "workflow.edit", "workflow.validate", "workflow.approve", "workflow.publish", "workflow.execute", "tools.read", "runs.view"];
const session = (): Session => ({ auth: { subject: { subject_id: "local-builder", workspace_id: "local-workspace" }, roles: ["admin", "approver"], permissions, scopes: ["workspace:write"], decision: "allow" }, mode: "local-development", planning_available: true, runtime_available: true, approval_service_available: true });
const failure = (code: string) => new ApiError({ error_code: code, message: "The server rejected this action.", request_id: "req_phase3", retryable: false });
function Controls() { const current = useMesh(state => state.workflows[0]); return current ? <WorkflowControls workflow={current} /> : null; }
beforeEach(() => {
  vi.stubGlobal("crypto", webcrypto); vi.stubGlobal("TextEncoder", TextEncoder); localStorage.clear();
  useMesh.setState({ workflows: [], agents: [] });
  useBackend.setState({ status: "connected", session: session(), tools: [], reviews: {}, overview: {}, error: null, refreshOverview: vi.fn(async () => undefined) });
  vi.spyOn(window, "confirm").mockReturnValue(true);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it("publish makes only the explicit publication request and never activates", async () => {
  const original = workflow(); original.status = "approved"; useMesh.getState().acceptWorkflow(original);
  const request = vi.spyOn(api, "request").mockResolvedValue({ workflow: { ...original, status: "published" } } as never);
  const activation = vi.spyOn(api, "activateRelease"); render(<Controls />);
  fireEvent.click(screen.getByRole("button", { name: "Publish" }));
  await waitFor(() => expect(screen.getByText(/Publish confirmed/)).toBeVisible());
  expect(request).toHaveBeenCalledTimes(1); expect(request).toHaveBeenCalledWith("approve_workflow", { workflow_id: original.workflow_id, workflow_version: original.version, action: "publish" });
  expect(activation).not.toHaveBeenCalled();
});
it("validation and approval are explicit independent transitions", async () => {
  const original = workflow(); original.status = "draft"; useMesh.getState().acceptWorkflow(original);
  const request = vi.spyOn(api, "request").mockImplementation(async operation => ({ workflow: { ...original, status: operation === "validate_workflow" ? "validated" : "approved" } }) as never);
  render(<Controls />); expect(screen.getByRole("button", { name: "Publish" })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Validate" }));
  await waitFor(() => expect(screen.getByText(/Validate confirmed/)).toBeVisible()); expect(request).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole("button", { name: /^Approve$/ }));
  await waitFor(() => expect(screen.getByText(/Approve confirmed/)).toBeVisible());
  expect(request.mock.calls.map(call => call[0])).toEqual(["validate_workflow", "approve_workflow"]);
});
it("submission never approves and activation can be cancelled", async () => {
  const original = workflow(); original.status = "validated"; useMesh.getState().acceptWorkflow(original);
  const submit = vi.spyOn(api, "submitApproval").mockResolvedValue({ workflow: { ...original, metadata: { ...original.metadata, approval_submission: { submitted_at: new Date().toISOString() } } } } as never);
  const request = vi.spyOn(api, "request"); render(<Controls />);
  fireEvent.click(screen.getByRole("button", { name: "Submit for approval" }));
  await waitFor(() => expect(submit).toHaveBeenCalledTimes(1)); expect(request).not.toHaveBeenCalled();
  await waitFor(() => expect(screen.getByRole("button", { name: "Submit for approval" })).toBeDisabled());
  cleanup(); useMesh.getState().acceptWorkflow({ ...original, status: "published" });
  vi.mocked(window.confirm).mockReturnValue(false); const activate = vi.spyOn(api, "activateRelease"); render(<Controls />);
  fireEvent.click(screen.getByRole("button", { name: "Activate" })); expect(activate).not.toHaveBeenCalled();
});
it("save keeps newer edits entered during the request and records the confirmed revision", async () => {
  const original = workflow(); useMesh.getState().acceptWorkflow(original); useMesh.getState().renameWorkflow(original.workflow_id, "First edit");
  let finish!: (value: never) => void; const request = vi.spyOn(api, "request").mockImplementation(() => new Promise(resolve => { finish = resolve; }) as never);
  render(<Controls />); fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
  useMesh.getState().renameWorkflow(original.workflow_id, "Newer edit");
  finish({ workflow: { ...original, name: "First edit", version: original.version + 1, status: "draft", metadata: { ...original.metadata, updated_at: "2026-10-17T08:00:00Z" } } } as never);
  await waitFor(() => expect(useMesh.getState().workflows[0]!.serverVersion).toBe(original.version + 1));
  expect(request).toHaveBeenCalledTimes(1); expect(useMesh.getState().workflows[0]!.name).toBe("Newer edit");
  expect(hasWorkflowEdits(useMesh.getState().workflows[0]!, useMesh.getState().agents)).toBe(true);
  expect(JSON.parse(localStorage.getItem("mesh-local-drafts-v1")!).state.workflows[0].name).toBe("Newer edit");
});
it("conflicts retain edits and offer reload rather than overwriting", async () => {
  const original = workflow(); useMesh.getState().acceptWorkflow(original); useMesh.getState().renameWorkflow(original.workflow_id, "Keep my edit");
  const request = vi.spyOn(api, "request").mockRejectedValue(failure("REVISION_CONFLICT")); render(<Controls />);
  fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
  await waitFor(() => expect(screen.getByText(/Your edits are retained/)).toBeVisible());
  expect(useMesh.getState().workflows[0]!.name).toBe("Keep my edit"); expect(screen.getByRole("button", { name: "Reload server revision" })).toBeEnabled();
  vi.mocked(window.confirm).mockReturnValue(false); const beforeReload=request.mock.calls.length; fireEvent.click(screen.getByRole("button", { name: "Reload server revision" })); expect(request).toHaveBeenCalledTimes(beforeReload);
});
it("navigation and unload warn while dirty server drafts remain persisted", () => {
  const original = workflow(); useMesh.getState().acceptWorkflow(original); useMesh.getState().renameWorkflow(original.workflow_id, "Dirty edit"); render(<Controls />);
  vi.mocked(window.confirm).mockReturnValue(false); expect(confirmDraftNavigation()).toBe(false);
  const event = new Event("beforeunload", { cancelable: true }); window.dispatchEvent(event); expect(event.defaultPrevented).toBe(true);
  expect(JSON.parse(localStorage.getItem("mesh-local-drafts-v1")!).state.workflows[0].name).toBe("Dirty edit");
});
it("duplicates remap agent ownership and never mutate the original agent", () => {
  const original = workflow();
  const { name: _name, retry_policy: _retry, guardrails: _guardrails, ...agent } = CanonicalAgentSchema.parse(fixture("agents/valid-classifier.json"));
  original.agents = [agent]; original.nodes.push({ node_id: "fixture_agent", kind: "agent", label: "Agent", agent_id: agent.agent_id });
  useMesh.getState().acceptWorkflow(original);
  const originalAgent = useMesh.getState().agents[0]!; const id = useMesh.getState().duplicateWorkflow(original.workflow_id)!;
  const duplicate = useMesh.getState().workflows.find(item => item.id === id)!;
  const clone = useMesh.getState().agents.find(item => duplicate.nodes.some(node => node.data.agentId === item.id))!;
  expect(clone.id).not.toBe(originalAgent.id); useMesh.getState().updateAgent(clone.id, { instructions: "Isolated edit" });
  expect(useMesh.getState().agents.find(item => item.id === originalAgent.id)!.instructions).toBe(originalAgent.instructions);
  expect(duplicate.serverVersion).toBeUndefined();
});
it.each(["NaN", "Infinity", "1.5", "9007199254740992", " "])("rejects invalid required integers: %s", value => {
  expect(() => parseRunInputs([{ name: "count", type: "integer", required: true }], { count: value })).toThrow();
});
it("parses all canonical input types without coercing missing booleans or containers", () => {
  const fields = (["string", "number", "integer", "boolean", "array", "object"] as const).map(type => ({ name: type, type, required: true }));
  expect(parseRunInputs(fields, { string: "hello", number: "1.5", integer: "0", boolean: "false", array: "[]", object: "{}" })).toEqual({ string: "hello", number: 1.5, integer: 0, boolean: false, array: [], object: {} });
  expect(() => parseRunInputs([{ name: "data", type: "object", required: true }], { data: "null" })).toThrow();
  expect(() => parseRunInputs([{ name: "data", type: "array", required: true }], { data: "{}" })).toThrow();
  expect(parseRunInputs([{ name: "optional", type: "boolean", required: false }], {})).toEqual({});
});
it("run cancel and invalid values create no run, while repeat clicks submit once", async () => {
  const original = workflow(); original.status = "published"; original.inputs = [{ name: "count", type: "integer", required: true }];
  const request = vi.spyOn(api, "request").mockResolvedValue({ run: { run_id: "run_phase3", workflow_id: original.workflow_id, workflow_version: original.version, status: "queued", approvals: [] } } as never);
  const close = vi.fn(); const view = render(<RunWorkflowDialog workflow={original} onClose={close} />);
  fireEvent.click(screen.getByRole("button", { name: "Cancel" })); expect(close).toHaveBeenCalledOnce(); expect(request).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText("count"), { target: { value: "1.5" } }); fireEvent.click(screen.getByRole("button", { name: "Start run" }));
  expect(screen.getByRole("alert")).toHaveTextContent("safe integer"); expect(request).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText("count"), { target: { value: "2" } });
  fireEvent.click(screen.getByRole("button", { name: "Start run" })); fireEvent.click(screen.getByRole("button", { name: "Submitting…" }));
  await waitFor(() => expect(screen.getByRole("link", { name: "View run details" })).toHaveAttribute("href", "/app/runs?run=run_phase3")); expect(request).toHaveBeenCalledTimes(1); view.unmount();
});
it("run controls explain missing permission and event-only execution", () => {
  const original = workflow(); original.status = "published"; const auth = session(); auth.auth.permissions = ["workflow.view"]; useBackend.setState({ session: auth });
  const view = render(<RunWorkflowDialog workflow={original} onClose={vi.fn()} />); expect(screen.getByRole("button", { name: "Start run" })).toBeDisabled(); expect(screen.getByText(/workflow.execute permission/)).toBeVisible();
  view.unmount(); useBackend.setState({ session: session() }); original.metadata = { execution_input_mode: "automatic", trigger_templates: [{ provider_id: "google_sheets" }] };
  render(<RunWorkflowDialog workflow={original} onClose={vi.fn()} />); expect(screen.getByText(/waits for its configured event/)).toBeVisible(); expect(screen.queryByRole("button", { name: "Start run" })).toBeNull();
});
it("failed settings save remains unsaved, and repeated clicks do not duplicate the request", async () => {
  vi.spyOn(api, "settings").mockResolvedValue({ items: [{ key: "notifications", value: "email", updated_at: "2026-10-17T08:00:00Z" }], total: 1 });
  const save = vi.spyOn(api, "saveNotification").mockRejectedValue(failure("OPERATION_NOT_AUTHORIZED")); render(<Settings />);
  await waitFor(() => expect(screen.getByLabelText("Notification preference")).toHaveValue("email"));
  fireEvent.change(screen.getByLabelText("Notification preference"), { target: { value: "daily" } });
  fireEvent.click(screen.getByRole("button", { name: "Save setting" })); fireEvent.click(screen.getByRole("button", { name: "Saving…" }));
  await waitFor(() => expect(screen.getByRole("alert")).toBeVisible()); expect(screen.getByLabelText("Notification preference")).toHaveValue("daily"); expect(screen.getByText("Unsaved changes")).toBeVisible();
  expect(screen.queryByText("Setting saved on the server.")).toBeNull(); expect(save).toHaveBeenCalledTimes(1);
});
it("failed initial settings load never enables saving over an unknown value", async () => {
  vi.spyOn(api, "settings").mockRejectedValue(failure("API_UNAVAILABLE")); render(<Settings />);
  await waitFor(() => expect(screen.getByRole("alert")).toBeVisible()); expect(screen.getByLabelText("Notification preference")).toBeDisabled(); expect(screen.getByRole("button", { name: "Save setting" })).toBeDisabled();
});
it("configured integrations stay unverified and failed connectivity never displays success", async () => {
  const tool = CanonicalToolSchema.parse(fixture("tools/google-sheets-read.json")); tool.provider_id = "smtp"; tool.availability = "enabled";
  useBackend.setState({ tools: [{ tool_id: tool.tool_id, definition: tool, version: 1, credential_configured: true, authorization_state: "requires_assignment" }] });
  const check = vi.spyOn(api, "integrationCheck").mockResolvedValueOnce({ provider: "smtp", configured: true, verified: false, tested: false, live_test_supported: true, state: "configured", message: "Configuration only." })
    .mockResolvedValueOnce({ provider: "smtp", configured: true, verified: false, tested: false, live_test_supported: true, state: "connection_failed", message: "Connection verification failed." });
  render(<Integrations />); expect(screen.getByText("Configured · not verified")).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Check configuration" })); await waitFor(() => expect(screen.getByRole("button", { name: "Verify connection" })).toBeVisible());
  fireEvent.click(screen.getByRole("button", { name: "Verify connection" })); await waitFor(() => expect(screen.getByText("Connection failed")).toBeVisible());
  expect(check.mock.calls).toEqual([["smtp", "configuration"], ["smtp", "connection"]]); expect(screen.queryByText("Verified", { exact: true })).toBeNull();
});
it("client rejects HTTP failures and inconsistent integration success envelopes", async () => {
  const data = { provider: "smtp", configured: true, verified: true, tested: true, state: "configured", live_test_supported: false, message: "Incorrect success" };
  const client = new WorkflowClient(vi.fn(async () => new Response(JSON.stringify({ request_id: "req_phase3", status: 200, data }), { status: 200 })));
  await expect(client.integrationCheck("smtp")).rejects.toMatchObject({ error: { error_code: "INVALID_API_DATA" } });
});

it("browser back cancellation restores the editor URL without losing dirty edits", () => {
  window.history.replaceState({}, "", "/app/workflows/wf_guard");
  const original = workflow(); useMesh.getState().acceptWorkflow(original); useMesh.getState().renameWorkflow(original.workflow_id, "Back guarded edit");
  render(<Controls />); vi.mocked(window.confirm).mockReturnValue(false);
  window.history.pushState({}, "", "/app/workflows");
  window.dispatchEvent(new PopStateEvent("popstate"));
  expect(window.location.pathname).toBe("/app/workflows/wf_guard");
  expect(useMesh.getState().workflows[0]!.name).toBe("Back guarded edit");
});

it("historical revision viewing never replaces current dirty editor state", async () => {
  const original = workflow(); original.version = 2; useMesh.getState().acceptWorkflow(original);
  useMesh.getState().renameWorkflow(original.workflow_id, "Current unsaved name");
  const request = vi.spyOn(api, "request").mockResolvedValue({ workflow: { ...original, version: 1, name: "Historical name" } } as never);
  render(<RevisionHistory workflowId={original.workflow_id} latest={2} open onClose={vi.fn()} />);
  fireEvent.change(screen.getByLabelText("Saved revision number"), { target: { value: "1" } });
  fireEvent.click(screen.getByRole("button", { name: "View revision" }));
  await waitFor(() => expect(screen.getByLabelText("Saved revision document")).toHaveTextContent("Historical name"));
  expect(request).toHaveBeenCalledWith("get_workflow", { workflow_id: original.workflow_id, workflow_version: 1 });
  expect(useMesh.getState().workflows[0]!.name).toBe("Current unsaved name");
});
it("submitted review approval keeps independent dirty edits and makes one approval request", async () => {
  const original = workflow(); original.status = "validated"; original.metadata["approval_submission"] = { submitted_at: "2026-10-17" };
  useMesh.getState().acceptWorkflow(original); useMesh.getState().renameWorkflow(original.workflow_id, "My newer edits");
  const request = vi.spyOn(api, "request").mockImplementation(async operation => operation === "list_workflows" ? { items: [original] } as never : { workflow: { ...original, status: "approved" } } as never);
  render(<WorkflowReviewQueue />); await waitFor(() => expect(screen.getByRole("button", { name: "Approve revision" })).toBeEnabled());
  fireEvent.click(screen.getByRole("button", { name: "Approve revision" }));
  await waitFor(() => expect(screen.getByText("No submitted revisions await approval.")).toBeVisible());
  expect(request.mock.calls.filter(call => call[0] === "approve_workflow")).toHaveLength(1);
  expect(useMesh.getState().workflows[0]!.name).toBe("My newer edits");
});
it("uncertain run retries reuse the durable client idempotency key across client instances", async () => {
  const bodies: Record<string, unknown>[] = []; const original = workflow(); original.status = "published";
  const payload = { workflow_id: original.workflow_id, workflow_version: original.version, inputs: {} };
  const first = new WorkflowClient(vi.fn(async (_url, options) => { bodies.push(JSON.parse(String(options?.body))); return new Response(JSON.stringify({ request_id: "req_fail", status: 503, data: { error: { error_code: "API_UNAVAILABLE", message: "Uncertain request outcome", request_id: "req_fail", retryable: true } } }), { status: 503 }); }));
  await expect(first.request("execute_workflow", payload)).rejects.toBeInstanceOf(ApiError);
  const second = new WorkflowClient(vi.fn(async (_url, options) => { bodies.push(JSON.parse(String(options?.body))); return new Response(JSON.stringify({ request_id: "req_ok", status: 200, data: { run: { run_id: "run_one", workflow_id: original.workflow_id, workflow_version: original.version, status: "queued", approvals: [] } } }), { status: 200 }); }));
  await second.request("execute_workflow", payload);
  expect(bodies[0]!["idempotency_key"]).toBe(bodies[1]!["idempotency_key"]);
});

it("run detail loading rejects overlapping selections until the first response finishes", async () => {
  vi.spyOn(api, "runs").mockResolvedValue({ items: [{ run_id: "run_a", workflow_id: "workflow_a", workflow_version: 1, status: "completed", approvals: [] }, { run_id: "run_b", workflow_id: "workflow_a", workflow_version: 1, status: "completed", approvals: [] }], total: 2, has_more: false, next_cursor: null } as never);
  let finish!: (value: never) => void;
  const request = vi.spyOn(api, "request").mockImplementation(() => new Promise(resolve => { finish = resolve; }) as never);
  window.history.replaceState({}, "", "/app/runs"); render(<ServerRunView />);
  const first = await screen.findByRole("button", { name: /run_a/ }); const second = screen.getByRole("button", { name: /run_b/ });
  fireEvent.click(first); expect(second).toBeDisabled(); fireEvent.click(second); expect(request).toHaveBeenCalledTimes(1);
  request.mockResolvedValue({ items: [], total: 0, has_more: false, next_cursor: null } as never);
  finish({ run: { run_id: "run_a", workflow_id: "workflow_a", workflow_version: 1, status: "completed", approvals: [] } } as never);
  await waitFor(() => expect(second).toBeEnabled());
});

it("keeps a retry key after an uncertain run request but uses a fresh key for a new dialog", async () => {
  const original = workflow(); original.status = "published"; original.inputs = [];
  const request = vi.spyOn(api, "request").mockRejectedValueOnce(new Error("Uncertain transport outcome"))
    .mockResolvedValue({ run: { run_id: "run_new_intent", workflow_id: original.workflow_id, workflow_version: original.version, status: "queued", approvals: [] } } as never);
  const first = render(<RunWorkflowDialog workflow={original} onClose={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "Start run" }));
  await waitFor(() => expect(screen.getByRole("button", { name: "Start run" })).toBeEnabled());
  expect(request).toHaveBeenCalledTimes(1);
  const key = request.mock.calls[0]?.[2]; expect(typeof key).toBe("string"); expect(key).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Start run" }));
  await screen.findByRole("link", { name: "View run details" });
  expect(request.mock.calls[1]?.[2]).toBe(key);
  first.unmount();
  render(<RunWorkflowDialog workflow={original} onClose={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "Start run" }));
  await screen.findByRole("link", { name: "View run details" });
  expect(request.mock.calls[2]?.[2]).not.toBe(key);
});
