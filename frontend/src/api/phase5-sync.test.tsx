import { readFileSync } from "node:fs";
import path from "node:path";
import { webcrypto } from "node:crypto";
import { TextEncoder } from "node:util";
import { render, screen, fireEvent, waitFor, cleanup, act } from "@testing-library/react";
import { beforeEach, afterEach, it, expect, vi } from "vitest";
import { api, ApiError, WorkflowClient } from "./client";
import { CanonicalWorkflowSchema } from "./contracts.generated";
import { fromCanonical, toCanonical, hasWorkflowEdits, workflowEditSnapshot } from "./mapping";
import { useMesh } from "@/domain/store";
import { useBackend } from "./state";
import { acceptConfirmed } from "@/features/workflows/workflow-state";
import { rebaseDraft } from "@/features/workflows/rebase";
import { DraftConflict } from "@/features/workflows/DraftConflict";
import { fieldMessages, InputError } from "./feedback";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";
import { draftStorage } from "@/domain/draft-storage";
const doc = () =>
  CanonicalWorkflowSchema.parse(
    JSON.parse(
      readFileSync(
        path.resolve(process.cwd(), "../shared/contracts/examples/workflows/invoice-review.json"),
        "utf8",
      ),
    ),
  );
const agent = () => ({
  agent_id: "helper_agent",
  role: "Helper",
  goal: "Review carefully",
  instructions: "Classify the input",
  model: { provider: "openai", model_id: "gpt-5" },
  capabilities: [],
  allowed_tool_ids: [],
  permissions: [],
  input_schema: { type: "object" },
  output_schema: { type: "object" },
  limits: {
    max_llm_calls: 1,
    max_tool_calls: 0,
    max_tokens: 1000,
    max_retries: 0,
    timeout_seconds: 60,
  },
  approval_requirements: [],
});
const wrap = (data: unknown, status = 200) =>
  new Response(JSON.stringify({ request_id: "req_phase5", status, data }), { status });
const failed = (code: string, status: number, retryable = false) =>
  wrap(
    {
      error: {
        error_code: code,
        message: "A safe server error.",
        request_id: "req_phase5",
        retryable,
      },
    },
    status,
  );
beforeEach(() => {
  vi.stubGlobal("crypto", webcrypto);
  vi.stubGlobal("TextEncoder", TextEncoder);
  localStorage.clear();
  sessionStorage.clear();
  useMesh.setState({ workflows: [], agents: [] });
  useBackend.setState({ overviewError: null, error: null });
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});
it("keeps graph/condition mutations separate from the immutable server baseline", () => {
  const d = doc();
  const mapped = fromCanonical(d);
  const condition = mapped.workflow.nodes.find((n) => n.data.kind === "condition")!;
  (condition.data["condition"] as { expression: string }).expression = "true";
  expect(mapped.workflow.canonical?.conditions[0]?.expression).toBe(d.conditions[0]?.expression);
  expect(hasWorkflowEdits(mapped.workflow, mapped.agents)).toBe(true);
});
it("tracks and persists delegated agents with no graph node", () => {
  const d = doc();
  d.agents = [agent()];
  useMesh.getState().acceptWorkflow(d);
  useMesh
    .getState()
    .updateAgent(`${d.workflow_id}::helper_agent`, { instructions: "New specialist instructions" });
  const s = useMesh.getState();
  expect(hasWorkflowEdits(s.workflows[0]!, s.agents)).toBe(true);
  const persisted = JSON.parse(localStorage.getItem("mesh-local-drafts-v1")!);
  expect(persisted.state.agents[0].instructions).toBe("New specialist instructions");
  expect(toCanonical(s.workflows[0]!, s.agents).agents[0]?.instructions).toBe(
    "New specialist instructions",
  );
});
it("ignores a late clean read after a user starts editing", () => {
  const d = doc();
  useMesh.getState().acceptWorkflow(d);
  useMesh.getState().renameWorkflow(d.workflow_id, "Do not overwrite");
  useMesh.getState().observeWorkflows([d]);
  expect(useMesh.getState().workflows[0]?.name).toBe("Do not overwrite");
});
it("records a newer server revision without moving the dirty baseline", () => {
  const d = doc();
  useMesh.getState().acceptWorkflow(d);
  useMesh.getState().renameWorkflow(d.workflow_id, "Local");
  const remote = { ...d, version: 2, name: "Remote" };
  useMesh.getState().observeWorkflows([remote]);
  const w = useMesh.getState().workflows[0]!;
  expect(w.serverVersion).toBe(1);
  expect(w.remote?.version).toBe(2);
  expect(w.name).toBe("Local");
});
it("accepts clean newer revisions atomically and never downgrades a published baseline", () => {
  const d = doc();
  useMesh.getState().acceptWorkflow(d);
  const listener = vi.fn();
  const unsubscribe = useMesh.subscribe(listener);
  useMesh.getState().observeWorkflows([
    { ...d, status: "published" },
    { ...d, workflow_id: "second_workflow" },
  ]);
  expect(listener).toHaveBeenCalledTimes(1);
  unsubscribe();
  useMesh.getState().observeWorkflows([d]);
  expect(useMesh.getState().workflows.find((w) => w.id === d.workflow_id)?.canonical?.status).toBe(
    "published",
  );
});
it("preserves newer delegated edits entered while a save was pending", () => {
  const d = doc();
  d.agents = [agent()];
  useMesh.getState().acceptWorkflow(d);
  const before = workflowEditSnapshot(useMesh.getState().workflows[0]!, useMesh.getState().agents);
  useMesh
    .getState()
    .updateAgent(`${d.workflow_id}::helper_agent`, { instructions: "Typed while saving" });
  acceptConfirmed({ ...d, version: 2 }, before);
  const s = useMesh.getState();
  expect(s.workflows[0]?.serverVersion).toBe(2);
  expect(s.agents[0]?.instructions).toBe("Typed while saving");
  expect(hasWorkflowEdits(s.workflows[0]!, s.agents)).toBe(true);
});
it("does not apply an old save confirmation after a newer revision was loaded", () => {
  const d = doc();
  useMesh.getState().acceptWorkflow({ ...d, version: 3 });
  acceptConfirmed({ ...d, version: 2 }, "old");
  expect(useMesh.getState().workflows[0]?.serverVersion).toBe(3);
});
it("preserves canonical metadata, branch/approval configuration and layout but clears grants", () => {
  const d = doc();
  d.metadata["custom"] = { owner: "reviewed" };
  d.agents = [{ ...agent(), allowed_tool_ids: ["tool_granted"] }];
  d.tools = [
    { tool_id: "tool_granted", capability: "read", configuration_reference: "opaque_binding" },
  ];
  d.nodes[0]!.configuration = { ui: { supported_custom_hint: "keep" } };
  const mapped = fromCanonical(d);
  mapped.workflow.nodes[0]!.position = { x: 42, y: 99 };
  const result = toCanonical(mapped.workflow, mapped.agents);
  expect(result.metadata["custom"]).toEqual({ owner: "reviewed" });
  expect(result.nodes[0]?.configuration?.["ui"]).toMatchObject({ supported_custom_hint: "keep" });
  expect(result.nodes[0]?.layout).toEqual({ x: 42, y: 99 });
  expect(result.conditions).toEqual(d.conditions);
  expect(result.approval_gates).toEqual(d.approval_gates);
  expect(result.agents[0]?.allowed_tool_ids).toEqual([]);
  expect(result.tools[0]).not.toHaveProperty("configuration_reference");
});
it("rebases disjoint edits and refuses overlapping changes", () => {
  const d = doc();
  const mapped = fromCanonical(d);
  mapped.workflow.name = "Local name";
  const remote = { ...d, version: 2, description: "Remote description" };
  const result = rebaseDraft(mapped.workflow, mapped.agents, remote);
  expect(result.conflicts).toEqual([]);
  expect(result.workflow).toMatchObject({
    name: "Local name",
    description: "Remote description",
    version: 3,
    status: "draft",
  });
  expect(
    rebaseDraft(mapped.workflow, mapped.agents, { ...remote, name: "Remote name" }).conflicts,
  ).toContain("name");
});
it("rebases keyed node/agent additions without altering the original documents", () => {
  const d = doc();
  const mapped = fromCanonical(d);
  mapped.workflow.nodes[0]!.data.label = "Local trigger";
  const remote = structuredClone(d);
  remote.version = 2;
  remote.nodes.at(-1)!.label = "Remote output";
  const result = rebaseDraft(mapped.workflow, mapped.agents, remote);
  expect(result.workflow?.nodes[0]?.label).toBe("Local trigger");
  expect(result.workflow?.nodes.at(-1)?.label).toBe("Remote output");
  expect(d.nodes[0]?.label).not.toBe("Local trigger");
});
it("retains each tab recovery draft even when shared storage changes", () => {
  useMesh.getState().acceptWorkflow(doc());
  useMesh.getState().renameWorkflow(doc().workflow_id, "This tab");
  const own = draftStorage.getItem("mesh-local-drafts-v1");
  localStorage.setItem(
    "mesh-local-drafts-v1",
    JSON.stringify({ version: 1, state: { workflows: [{ name: "Other tab" }] } }),
  );
  expect(draftStorage.getItem("mesh-local-drafts-v1")).toBe(own);
});
it("renders safe field issues and references while hiding raw exception details", () => {
  const error = new ApiError(
    {
      error_code: "INVALID_WORKFLOW",
      message: "Check these fields.",
      request_id: "req_safe",
      retryable: false,
      field: "nodes.1",
      related_errors: [
        {
          error_code: "INVALID_INPUT",
          message: "Required field missing.",
          field: "agents.0.instructions",
        },
      ],
    },
    "corr_safe",
  );
  const view = render(<ApiFeedback error={error} />);
  expect(screen.getByLabelText("Field errors")).toHaveTextContent("agents.0.instructions");
  expect(screen.getByRole("alert")).toHaveTextContent("req_safe");
  view.rerender(
    <ApiFeedback error={new Error("Traceback /private/internal/path password=hidden")} />,
  );
  expect(screen.getByRole("alert")).not.toHaveTextContent("hidden");
  expect(screen.getByRole("alert")).not.toHaveTextContent("/private");
});
it("labels unconfirmed mutation outcomes and never submits a safe-read callback automatically", () => {
  const retry = vi.fn();
  render(
    <ApiFeedback
      error={
        new ApiError(
          {
            error_code: "API_UNAVAILABLE",
            message: "Connection lost.",
            request_id: "req_lost",
            retryable: true,
          },
          undefined,
          { outcome: "unknown" },
        )
      }
      onRetry={retry}
    />,
  );
  expect(screen.getByRole("alert")).toHaveTextContent("Outcome unknown");
  expect(screen.queryByRole("button", { name: "Retry read" })).toBeNull();
  expect(retry).not.toHaveBeenCalled();
});
it("retries one recognized transient GET and preserves the client request reference", async () => {
  let calls = 0;
  const transport = vi.fn<typeof fetch>(async () =>
    ++calls === 1
      ? failed("API_DATABASE_BUSY", 503, true)
      : wrap({ items: [], total: 0, has_more: false, next_cursor: null }),
  );
  const result = await new WorkflowClient(transport).request("list_workflows", {});
  expect(result.items).toEqual([]);
  expect(transport).toHaveBeenCalledTimes(2);
  expect(new Headers(transport.mock.calls[0]![1]?.headers).get("X-Request-ID")).toBe(
    new Headers(transport.mock.calls[1]![1]?.headers).get("X-Request-ID"),
  );
});
it("does not retry transient mutation failures and retains their exact payload key across explicit attempts", async () => {
  const keys: string[] = [];
  const transport = vi.fn<typeof fetch>(async (_url, options) => {
    keys.push(JSON.parse(String(options?.body)).idempotency_key);
    throw new TypeError("lost response");
  });
  const client = new WorkflowClient(transport);
  const payload = {
    workflow_id: doc().workflow_id,
    workflow_version: 2,
    base_version: 1,
    workflow: { ...doc(), version: 2 },
  };
  await expect(client.request("save_workflow_version", payload)).rejects.toMatchObject({
    context: { outcome: "unknown" },
  });
  expect(transport).toHaveBeenCalledTimes(1);
  await expect(client.request("save_workflow_version", payload)).rejects.toBeInstanceOf(ApiError);
  expect(keys[0]).toBe(keys[1]);
});
it("keeps procurement mutation retry identities across clients", async () => {
  const keys: string[] = [];
  const transport = vi.fn<typeof fetch>(async (_url, options) => {
    keys.push(JSON.parse(String(options?.body)).idempotency_key);
    throw new TypeError("lost");
  });
  for (let i = 0; i < 2; i++)
    await expect(
      new WorkflowClient(transport).procurementSuppliersReview(
        "project_one",
        "approved",
        ["candidate_one"],
        "digest_one",
      ),
    ).rejects.toBeInstanceOf(ApiError);
  expect(keys[0]).toBe(keys[1]);
  expect(transport).toHaveBeenCalledTimes(2);
});
it("clears only recovered overview errors and preserves an unrelated action error", async () => {
  const failure = new ApiError({
    error_code: "API_UNAVAILABLE",
    message: "Overview unavailable",
    request_id: "req_overview",
    retryable: true,
  });
  vi.spyOn(api, "overview")
    .mockRejectedValueOnce(failure)
    .mockResolvedValue({ items: [], next_sequence: 1, has_more: false });
  await useBackend.getState().refreshOverview();
  expect(useBackend.getState().error).toBe(failure);
  await useBackend.getState().refreshOverview();
  expect(useBackend.getState().error).toBeNull();
});
it("exports invalid working drafts without discarding edits or submitting a mutation", async () => {
  const d = doc();
  useMesh.getState().acceptWorkflow(d);
  const state = useMesh.getState();
  useMesh.setState({
    workflows: [{ ...state.workflows[0]!, name: "", remote: { ...d, version: 2 } }],
  });
  render(<DraftConflict workflow={useMesh.getState().workflows[0]!} />);
  fireEvent.click(screen.getByRole("button", { name: "Export working draft" }));
  expect((screen.getByLabelText("Working draft export") as HTMLTextAreaElement).value).toContain(
    "mesh-working-draft-recovery-v1",
  );
});
it("requires a fresh confirmation if edits arrive during discard/reload", async () => {
  const d = doc();
  useMesh.getState().acceptWorkflow(d);
  useMesh.getState().renameWorkflow(d.workflow_id, "Before");
  useMesh.setState((s) => ({
    workflows: s.workflows.map((w) => ({ ...w, remote: { ...d, version: 2 } })),
  }));
  let resolve!: (value: unknown) => void;
  vi.spyOn(api, "request").mockImplementation(
    async () =>
      (await new Promise<unknown>((r) => {
        resolve = r;
      })) as never,
  );
  vi.spyOn(window, "confirm").mockReturnValue(true);
  render(<DraftConflict workflow={useMesh.getState().workflows[0]!} />);
  fireEvent.click(screen.getByRole("button", { name: "Discard and reload latest" }));
  act(() => useMesh.getState().renameWorkflow(d.workflow_id, "Typed later"));
  await act(async () => resolve({ workflow: { ...d, version: 2 } }));
  await waitFor(() => expect(screen.getByText(/confirm reload again/)).toBeInTheDocument());
  expect(useMesh.getState().workflows[0]?.name).toBe("Typed later");
});

it("does not persist or broadcast unchanged server observations", () => {
  const d = doc();
  useMesh.getState().acceptWorkflow(d);
  useMesh.getState().renameWorkflow(d.workflow_id, "Keep local");
  const storage = vi.spyOn(draftStorage, "setItem");
  const listener = vi.fn();
  const unsubscribe = useMesh.subscribe(listener);
  useMesh.getState().observeWorkflows([d]);
  unsubscribe();
  expect(listener).not.toHaveBeenCalled();
  expect(storage).not.toHaveBeenCalled();
});
it("records a confirmed first-save response without overwriting the still-local draft", () => {
  const id = useMesh.getState().createBlankWorkflow("Local first save");
  const local = useMesh.getState().workflows.find((w) => w.id === id)!;
  const document = toCanonical(local, useMesh.getState().agents, 1);
  useMesh.getState().renameWorkflow(id, "Typed after submission");
  useMesh.getState().observeWorkflows([document]);
  const state = useMesh.getState().workflows.find((w) => w.id === id)!;
  expect(state.name).toBe("Typed after submission");
  expect(state.serverVersion).toBeUndefined();
  expect(state.remote?.version).toBe(1);
});
it("refuses to merge deletion with a concurrent node change", () => {
  const d = doc();
  const mapped = fromCanonical(d);
  mapped.workflow.nodes = mapped.workflow.nodes.filter((n) => n.id !== d.nodes.at(-1)!.node_id);
  const remote = structuredClone(d);
  remote.version = 2;
  remote.nodes.at(-1)!.label = "Changed remotely";
  const result = rebaseDraft(mapped.workflow, mapped.agents, remote);
  expect(result.workflow).toBeNull();
  expect(result.conflicts.some((p) => p.includes(d.nodes.at(-1)!.node_id))).toBe(true);
});
it("validates monitoring null fields and converts unsafe server errors to safe feedback", async () => {
  const data = {
    runs: { total: 0, active: 0, completed: 0, failed: 0 },
    events: 0,
    usage: { llm_calls: 0, tool_calls: 0, tokens: 0, retries: 0, estimated_cost_usd: 0 },
    latest: [],
    sources: [
      {
        binding_id: "bind",
        workflow_id: "workflow",
        provider_id: "provider",
        health: "error",
        error_code: null,
        baseline_ready: false,
        last_successful_poll: null,
      },
    ],
    policies: [
      {
        workflow_id: "workflow",
        version: 1,
        action_approval_required: false,
        agents: [
          {
            agent_id: "agent",
            guardrails: null,
            limits: { max_llm_calls: 1, max_tool_calls: 0, max_retries: 0 },
          },
        ],
      },
    ],
  };
  const client = new WorkflowClient(vi.fn(async () => wrap(data)));
  expect((await client.monitoring()).sources?.[0]?.last_successful_poll).toBeNull();
  const error = new ApiError({
    error_code: "PROVIDER_FAILED",
    message: "TypeError: private stack details",
    request_id: "req_safe",
    retryable: false,
    related_errors: [
      { error_code: "INVALID_FIELD", message: "Traceback internal stack", field: "nodes.1" },
    ],
  });
  expect(error.message).not.toContain("TypeError");
  expect(error.error.related_errors?.[0]?.message).not.toContain("Traceback");
});

it("maps only the exact canonical input path into safe inline errors", () => {
  expect(
    fieldMessages(new InputError("Enter a safe integer.", "inputs.count"), "inputs.count"),
  ).toEqual(["Enter a safe integer."]);
  expect(fieldMessages(new InputError("Other field.", "inputs.other"), "inputs.count")).toEqual([]);
});
