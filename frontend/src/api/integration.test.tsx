import { readFileSync } from "node:fs";
import path from "node:path";
import { webcrypto } from "node:crypto";
import { TextEncoder } from "node:util";
import { render, screen, fireEvent, waitFor, cleanup, act } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, WorkflowClient, ApiError, type Session } from "./client";
import { CanonicalWorkflowSchema, CanonicalAgentSchema, CanonicalToolSchema, type RunEvent } from "./contracts.generated";
import { fromCanonical, toCanonical, hasWorkflowEdits } from "./mapping";
import { assertRunTransition, reconcileEvents } from "./control";
import { useMesh } from "@/domain/store";
import { useBackend } from "./state";
import { WorkflowControls } from "@/features/workflows/WorkflowControls";
import { ServerRunView, ApprovalControl } from "@/features/runs/ServerRunView";

const fixture = (name: string) => JSON.parse(readFileSync(path.resolve(process.cwd(), "../shared/contracts/examples", name), "utf8"));
const document = () => CanonicalWorkflowSchema.parse(fixture("workflows/invoice-review.json"));
const envelope = (data: unknown, status = 200) => new Response(JSON.stringify({ request_id: "req_test", status, data }), { status });
const session = (permissions: string[] = ["workflow.view", "workflow.edit", "workflow.validate"]): Session => ({
  auth: { subject: { subject_id: "builder", workspace_id: "local-workspace" }, roles: ["builder"], permissions, scopes: [], decision: "allow" },
  mode: "local-development", planning_available: true, runtime_available: false, approval_service_available: false,
});
beforeEach(() => {
  vi.stubGlobal("crypto", webcrypto);
  vi.stubGlobal("TextEncoder", TextEncoder);
  localStorage.clear();
  useMesh.setState({ workflows: [], agents: [] });
  useBackend.setState({ status: "connected", session: session(), tools: [], error: null, reviews: {}, overview: {},
    overviewSequence: 0, liveStatus: "live", lastOverviewUpdate: null });
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe("authoritative contract mapping", () => {
  it("validates every accepted workflow plus agent and tool fixtures", () => {
    for (const name of ["invoice-review", "employee-onboarding", "support-triage"]) expect(() => CanonicalWorkflowSchema.parse(fixture(`workflows/${name}.json`))).not.toThrow();
    expect(() => CanonicalAgentSchema.parse(fixture("agents/valid-classifier.json"))).not.toThrow();
    expect(() => CanonicalToolSchema.parse(fixture("tools/google-sheets-read.json"))).not.toThrow();
    expect(() => CanonicalAgentSchema.parse(fixture("agents/incomplete-agent.json"))).toThrow();
  });
  it("retains conditions, approvals, policies, schemas and unknown metadata across edits", () => {
    const original = document();
    original.metadata["review_reference"] = "review_123";
    const mapped = fromCanonical(original);
    const edited = { ...mapped.workflow, name: "Edited invoice review" };
    const result = toCanonical(edited, mapped.agents);
    expect(result.version).toBe(original.version + 1);
    expect(result.conditions).toEqual(original.conditions);
    expect(result.approval_gates).toEqual(original.approval_gates);
    expect(result.execution_policy).toEqual(original.execution_policy);
    expect(result.agents).toEqual(original.agents);
    expect(result.tools).toEqual(original.tools);
    expect(result.metadata["review_reference"]).toBe("review_123");
    expect(hasWorkflowEdits(mapped.workflow, mapped.agents)).toBe(false);
    expect(hasWorkflowEdits(edited, mapped.agents)).toBe(true);
  });
  it("isolates identical planner agent IDs across workflows", () => {
    const first = document();
    const agent = CanonicalAgentSchema.parse(fixture("agents/valid-classifier.json"));
    const { name: _name, retry_policy: _retry, guardrails: _guardrails, ...embedded } = agent;
    first.agents = [embedded];
    first.nodes.push({ node_id: "classification", kind: "agent", label: "Classification", agent_id: agent.agent_id });
    const second = { ...first, workflow_id: "another_workflow" };
    useMesh.getState().acceptWorkflow(first); useMesh.getState().acceptWorkflow(second);
    expect(new Set(useMesh.getState().agents.map((a) => a.id)).size).toBe(first.agents.length + second.agents.length);
    const firstView = useMesh.getState().workflows.find((w) => w.id === first.workflow_id)!;
    expect(toCanonical(firstView, useMesh.getState().agents).agents).toEqual(first.agents);
  });
  it("keeps a changed model paired with its provider", () => {
    const original = document();
    const agent = CanonicalAgentSchema.parse(fixture("agents/valid-classifier.json"));
    const { name: _name, retry_policy: _retry, guardrails: _guardrails, ...embedded } = agent;
    original.agents = [embedded];
    original.agents[0]!.model.provider = "custom_provider";
    const mapped = fromCanonical(original);
    expect(toCanonical(mapped.workflow, mapped.agents).agents[0]?.model.provider).toBe("custom_provider");
    mapped.agents[0]!.modelId = "claude-sonnet-4-5";
    expect(toCanonical(mapped.workflow, mapped.agents).agents[0]?.model.provider).toBe("anthropic");
  });
});

describe("API envelopes and retries", () => {
  it("reuses mutation keys across new client instances without persisting prompts", async () => {
    const bodies: { operation: string; idempotency_key: string; payload: unknown }[] = [];
    const transport: typeof fetch = vi.fn(async (_url, options) => {
      bodies.push(JSON.parse(String(options?.body)));
      return envelope({ workflow: document(), correlation_id: "corr_plan" });
    });
    await new WorkflowClient(transport).request("plan_workflow", { objective: "Review invoice approval" });
    await new WorkflowClient(transport).request("plan_workflow", { objective: "Review invoice approval" });
    expect(bodies[0]?.idempotency_key).toBe(bodies[1]?.idempotency_key);
    expect(bodies[0]?.payload).toEqual({ objective: "Review invoice approval" });
    expect(JSON.stringify(localStorage)).not.toContain("Review invoice approval");
  });
  it("displays only contract errors and refuses credentials, HTML and malformed graphs", async () => {
    const unsafe = new WorkflowClient(vi.fn(async () => envelope({ error: { error_code: "PROVIDER_FAILED", message: "Bearer provider_secret", request_id: "req_test", retryable: false } }, 502)));
    await expect(unsafe.request("list_tools", {})).rejects.toMatchObject({ message: "The API returned unsafe data. Nothing was displayed." });
    const html = new WorkflowClient(vi.fn(async () => new Response("<h1>internal provider error</h1>", { status: 500 })));
    await expect(html.request("list_tools", {})).rejects.toMatchObject({ error: { error_code: "INVALID_API_RESPONSE" } });
    const invalid = document(); invalid.edges[0]!.source = "missing_node";
    const client = new WorkflowClient(vi.fn(async () => envelope({ workflow: invalid })));
    await expect(client.request("plan_workflow", { objective: "Review" })).rejects.toMatchObject({ error: { error_code: "INVALID_WORKFLOW" } });
  });
  it("preserves safe error fields and correlation references", async () => {
    const client = new WorkflowClient(vi.fn(async () => envelope({ correlation_id: "corr_denied", error: { error_code: "OPERATION_NOT_AUTHORIZED", message: "Your session cannot edit.", request_id: "req_test", retryable: false, field: "workflow.version" } }, 403)));
    await expect(client.request("list_workflows", {})).rejects.toMatchObject({ correlationId: "corr_denied", error: { field: "workflow.version" } });
  });
});

describe("workflow UI integration", () => {
  it("publishes the revision and activates a release through the additive v2 boundary", async () => {
    const original = CanonicalWorkflowSchema.parse(fixture("workflows/support-triage.json"));
    original.status = "approved";
    original.metadata["unresolved_requirements"] = [];
    const mapped = fromCanonical(original);
    const published = { ...original, status: "published" as const };
    useMesh.setState({ agents: mapped.agents });
    useBackend.setState({ session: session(["workflow.publish"]), reviews: {
      [original.workflow_id]: { workflow_id: original.workflow_id, workflow_version: original.version, ready: true, reason_codes: [], items: [] },
    }, refreshOverview: vi.fn(async () => undefined) });
    const request = vi.spyOn(api, "request").mockResolvedValue({ workflow: published, registry_review: {
      workflow_id: original.workflow_id, workflow_version: original.version, ready: true, reason_codes: [], items: [],
    }, correlation_id: "corr_publish" } as never);
    const activate = vi.spyOn(api, "activateRelease").mockResolvedValue({ operation: { operation_id: "op_1", workspace_id: "local-workspace",
      workflow_id: original.workflow_id, subject_id: "builder", idempotency_key: "publish_key", expected_release_id: null,
      kind: "activate_release", state: "succeeded", error_code: null }, release: { release_id: "rel_1", workspace_id: "local-workspace",
      revision: { workflow_id: original.workflow_id, workflow_version: original.version }, state: "active", generation: 1,
      automation_identity_id: "auto_1", agent_versions: {}, tool_versions: {}, policy_version: 1, trigger_binding_ids: [], created_at: new Date().toISOString() } } as never);
    render(<WorkflowControls workflow={mapped.workflow} />);
    fireEvent.click(screen.getByRole("button", { name: "Publish" }));
    await waitFor(() => expect(activate).toHaveBeenCalledWith(expect.objectContaining({ workflow_id: original.workflow_id, expected_release_id: null })));
    expect(request).toHaveBeenCalledWith("approve_workflow", expect.objectContaining({ action: "publish" }));
  });
  it("keeps registry review details out of the editor while retaining a clear publish action", () => {
    const original = document();
    original.status = "approved";
    original.metadata["unresolved_requirements"] = [];
    original.execution_policy.allow_external_writes = false;
    const registered = CanonicalAgentSchema.parse(fixture("agents/valid-classifier.json"));
    const { name: _name, retry_policy: _retry, guardrails: _guardrails, ...embedded } = registered;
    original.agents = [{ ...embedded, capabilities: [] }];
    const mapped = fromCanonical(original);
    useMesh.setState({ agents: mapped.agents });
    const review = { workflow_id: original.workflow_id, workflow_version: original.version, ready: true, reason_codes: [], items: [] };
    useBackend.setState({ session: session(["workflow.publish"]), reviews: { [original.workflow_id]: review } });
    render(<WorkflowControls workflow={mapped.workflow} />);
    expect(screen.getByRole("button", { name: "Publish" })).toBeEnabled();
    expect(screen.queryByText("Registry requirements authorized for this revision")).toBeNull();
  });
  it("surfaces a server-side publication rejection without exposing registry internals", async () => {
    const original = document();
    original.status = "validated";
    const mapped = fromCanonical(original);
    useMesh.setState({ agents: mapped.agents });
    const review = { workflow_id: original.workflow_id, workflow_version: original.version, ready: false, reason_codes: ["APPROVAL_REQUIRED", "TOOL_UNAVAILABLE"], items: [
      { agent_id: "reader_agent", capability: "read_spreadsheet", tool_id: "google_sheets_read_rows", authorization_state: "pending_approval" as const, reason_codes: ["APPROVAL_REQUIRED"] },
      { agent_id: "sender_agent", capability: "send_email", tool_id: "smtp_send_email", authorization_state: "denied" as const, reason_codes: ["TOOL_UNAVAILABLE"] },
    ] };
    useBackend.setState({ session: session(["workflow.publish"]), reviews: { [original.workflow_id]: review } });
    vi.spyOn(api, "request").mockRejectedValue(new ApiError({ error_code: "REGISTRY_REVIEW_REQUIRED", message: "Resolve the workflow review before publishing.", request_id: "req_review", retryable: false }, "corr_review"));
    render(<WorkflowControls workflow={mapped.workflow} />);
    fireEvent.click(screen.getByRole("button", { name: "Publish" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Resolve the workflow review before publishing."));
  });
  it("saves an edited canonical revision as part of publishing and excludes it from browser draft persistence", async () => {
    const original = document();
    useMesh.getState().acceptWorkflow(original);
    useMesh.getState().renameWorkflow(original.workflow_id, "Invoice edits");
    const edited = useMesh.getState().workflows[0]!;
    useBackend.setState({ session: session(["workflow.publish"]), refreshOverview: vi.fn(async () => undefined) });
    const saved = { ...original, version: original.version + 1, name: "Invoice edits", status: "draft" as const, metadata: { ...original.metadata, workspace_id: "local-workspace" } };
    const save = vi.spyOn(api, "request").mockImplementation(async (operation, payload) => {
      if (operation === "save_workflow_version") return { workflow: { ...saved, ...("workflow" in payload ? payload.workflow : {}) }, correlation_id: "corr_saved" } as never;
      if (operation === "validate_workflow") return { workflow: { ...saved, status: "validated" }, correlation_id: "corr_validated" } as never;
      if (operation === "approve_workflow" && "action" in payload && payload.action === "approve") return { workflow: { ...saved, status: "approved" }, correlation_id: "corr_approved" } as never;
      return { workflow: { ...saved, status: "published" }, correlation_id: "corr_published" } as never;
    });
    vi.spyOn(api, "activateRelease").mockResolvedValue({} as never);
    render(<WorkflowControls workflow={edited} />);
    fireEvent.click(screen.getByRole("button", { name: "Publish" }));
    await waitFor(() => expect(save).toHaveBeenCalledWith("approve_workflow", expect.objectContaining({ action: "publish" })));
    expect(save).toHaveBeenCalledWith("save_workflow_version", expect.objectContaining({ base_version: original.version, workflow: expect.objectContaining({ name: "Invoice edits", version: original.version + 1 }) }));
    expect(useMesh.getState().workflows[0]?.serverVersion).toBe(original.version + 1);
    expect(JSON.parse(localStorage.getItem("mesh-local-drafts-v1")!).state.workflows).toEqual([]);
  });
  it("allows viewers to run a safe local test but not publish", () => {
    const mapped = fromCanonical(document());
    useMesh.setState({ agents: mapped.agents });
    useBackend.setState({ session: session(["workflow.view"]) });
    const view = render(<WorkflowControls workflow={mapped.workflow} />);
    expect(screen.getByRole("button", { name: "Test workflow" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Publish" })).toBeDisabled();
    view.unmount();
  });
  it("renders safe validation failures without changing revision state", async () => {
    const mapped = fromCanonical(document());
    useMesh.setState({ agents: mapped.agents });
    vi.spyOn(api, "request").mockRejectedValue(new ApiError({ error_code: "WORKFLOW_VALIDATION_FAILED", message: "Correct the edge.", request_id: "req_validate", retryable: false, field: "edges[0].source" }, "corr_validate"));
    useBackend.setState({ session: session(["workflow.publish"]) });
    render(<WorkflowControls workflow={mapped.workflow} />);
    fireEvent.click(screen.getByRole("button", { name: "Publish" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Correct the edge."));
  });
});

describe("registry review contract safety", () => {
  it("rejects mismatched revision and inconsistent readiness responses", async () => {
    const workflow = document();
    const review = { workflow_id: workflow.workflow_id, workflow_version: workflow.version + 1, ready: true, reason_codes: [] as string[], items: [] };
    const client = new WorkflowClient(vi.fn(async () => envelope({ workflow, registry_review: review })));
    await expect(client.request("get_workflow", { workflow_id: workflow.workflow_id })).rejects.toMatchObject({ error: { error_code: "REVISION_MISMATCH" } });
    review.workflow_version = workflow.version;
    review.reason_codes = ["APPROVAL_REQUIRED"];
    await expect(client.request("get_workflow", { workflow_id: workflow.workflow_id })).rejects.toMatchObject({ error: { error_code: "INVALID_REGISTRY_REVIEW" } });
  });
  it("drops server-issued grants when creating a new editable revision", () => {
    const workflow = document();
    const agent = CanonicalAgentSchema.parse(fixture("agents/valid-classifier.json"));
    const { name: _name, retry_policy: _retry, guardrails: _guardrails, ...embedded } = agent;
    workflow.agents = [{ ...embedded, allowed_tool_ids: ["google_sheets_read_rows"] }];
    workflow.tools = [{ tool_id: "google_sheets_read_rows", capability: "read_spreadsheet", configuration_reference: "authz_server_reference" }];
    const mapped = fromCanonical(workflow);
    const saved = toCanonical(mapped.workflow, mapped.agents);
    expect(saved.agents[0]?.allowed_tool_ids).toEqual([]);
    expect(saved.tools[0]).not.toHaveProperty("configuration_reference");
    expect(workflow.agents[0]?.allowed_tool_ids).toEqual(["google_sheets_read_rows"]);
  });
});

describe("approval and run consumers", () => {
  it("submits only the exact trusted pending approval binding and renders the returned decision", async () => {
    useBackend.setState({ session: { ...session(["workflow.approve"]), auth: { ...session(["workflow.approve"]).auth, roles: ["approver"] }, approval_service_available: true } });
    const approval = { approval_id: "approval_exact", workflow_id: "invoice_review", workflow_version: 3, status: "pending" as const, allowed_decisions: ["approved" as const, "rejected" as const] };
    const decision = vi.spyOn(api, "request").mockResolvedValue({ ...approval, status: "approved", allowed_decisions: [] } as never);
    render(<ApprovalControl approval={approval} />);
    fireEvent.click(screen.getByRole("button", { name: /^Approve$/ }));
    await waitFor(() => expect(screen.getByText(/approval_exact · approved/)).toBeVisible());
    expect(decision).toHaveBeenCalledWith("decide_approval", { approval_id: "approval_exact", workflow_id: "invoice_review", workflow_version: 3, decision: "approved" });
    expect(screen.queryByRole("button", { name: /^Approve$/ })).toBeNull();
  });
  it("shows all approval outcomes and gates decisions by trusted availability/permissions", () => {
    for (const status of ["pending", "approved", "rejected", "timed_out", "unmatched"] as const) {
      const view = render(<ApprovalControl approval={{ approval_id: "approval_1", workflow_id: "workflow_1", workflow_version: 1, status, allowed_decisions: ["approved", "rejected"] }} />);
      expect(screen.getByText(new RegExp(`approval_1 · ${status}`))).toBeVisible();
      expect(screen.queryByRole("button", { name: /^Approve$/ })).toBeNull();
      view.unmount();
    }
  });
  it("deduplicates events and rejects terminal transitions or mismatched revisions", () => {
    const event = fixture("api-control-fixtures.json").valid_run_event as RunEvent;
    const ref = { run_id: event.run_id, workflow_id: event.workflow_id, workflow_version: event.workflow_version };
    expect(reconcileEvents([event], [event], ref)).toEqual([event]);
    expect(() => reconcileEvents([], [{ ...event, workflow_version: 2 }], ref)).toThrow();
    expect(() => assertRunTransition("completed", "running")).toThrow();
    expect(() => assertRunTransition("running", "paused_for_approval")).not.toThrow();
    expect(() => assertRunTransition("queued", "completed")).not.toThrow();
    expect(() => reconcileEvents([event], [], { ...ref, workflow_version: 2 })).toThrow();
  });
  it("renders server run events and keeps runtime actions absent when unavailable", async () => {
    const view = render(<ServerRunView />);
    expect(screen.getByText(/runtime API is not connected/)).toBeVisible();
    expect(screen.queryByRole("button", { name: "Load run" })).toBeNull();
    const event = fixture("api-control-fixtures.json").valid_run_event as RunEvent;
    act(() => useBackend.setState({ session: { ...session(), runtime_available: true } }));
    vi.spyOn(api, "request").mockImplementation(async (operation) => operation === "get_run" ? ({ run: { run_id: event.run_id, workflow_id: event.workflow_id, workflow_version: event.workflow_version, status: "paused_for_approval", approvals: [] } }) as never : ({ items: [event], has_more: false }) as never);
    view.rerender(<ServerRunView />);
    fireEvent.change(screen.getByLabelText("Run ID"), { target: { value: event.run_id } });
    fireEvent.click(screen.getByRole("button", { name: "Load run" }));
    await waitFor(() => expect(screen.getByRole("list", { name: "Run events" })).toHaveTextContent(event.event_type));
  });
});
