import { readFileSync } from "node:fs";
import path from "node:path";
import {
  render,
  renderHook,
  screen,
  waitFor,
  fireEvent,
  cleanup,
  act,
} from "@testing-library/react";
import { beforeEach, afterEach, expect, it, vi } from "vitest";
import { api } from "./client";
import { CanonicalWorkflowSchema, type RunEvent } from "./contracts.generated";
import { fromCanonical, hasWorkflowEdits } from "./mapping";
import { useMesh } from "@/domain/store";
import { useBackend } from "./state";
import { dependencyOrder, graphIssues } from "@/domain/graph-review";
import { reconcileEvents } from "./control";
import { useWorkflowTrace } from "@/features/builder/useWorkflowTrace";
import { PlanReview } from "@/features/workflows/PlanReview";
import { LifecycleJourney } from "@/features/workflows/LifecycleJourney";
import { GraphTools } from "@/features/builder/GraphTools";
import { HierarchyView } from "@/features/builder/HierarchyView";
vi.mock("@/lib/navigation", () => ({
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
const recorded = () => ({
  run_id: "run_historical",
  workflow_id: document().workflow_id,
  workflow_version: 1,
  status: "completed" as const,
  approvals: [],
});
beforeEach(() => {
  localStorage.clear();
  useMesh.setState({ workflows: [], agents: [] });
  useBackend.setState({
    status: "connected",
    overview: {},
    reviews: {},
    session: {
      mode: "local-development",
      planning_available: true,
      runtime_available: true,
      approval_service_available: true,
      auth: {
        subject: { subject_id: "test", workspace_id: "local-workspace" },
        roles: ["admin"],
        permissions: ["workflow.view", "runs.view"],
        scopes: [],
        decision: "allow",
      },
    },
  });
  vi.spyOn(api, "releaseState").mockResolvedValue({
    workflow_id: document().workflow_id,
    release: null,
  });
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
it("orders mobile steps by dependencies instead of insertion order and retains cyclic leftovers", () => {
  const g = fromCanonical(document()).workflow;
  const reversed = [...g.nodes].reverse();
  const ordered = dependencyOrder(reversed, g.edges);
  expect(ordered[0]?.data.kind).toBe("trigger");
  for (const e of g.edges)
    expect(ordered.findIndex((n) => n.id === e.source)).toBeLessThan(
      ordered.findIndex((n) => n.id === e.target),
    );
  const cyclic = [
    ...g.edges,
    { id: "cycle", source: g.edges[0]!.target, target: g.edges[0]!.source },
  ];
  expect(dependencyOrder(g.nodes, cyclic)).toHaveLength(g.nodes.length);
  expect(graphIssues(g.nodes, cyclic).some((i) => i.message.includes("cycle"))).toBe(true);
});
it("identifies disconnected steps, invalid references and missing branch outcomes", () => {
  const invoice = CanonicalWorkflowSchema.parse(
    JSON.parse(
      readFileSync(
        path.resolve(process.cwd(), "../shared/contracts/examples/workflows/invoice-review.json"),
        "utf8",
      ),
    ),
  );
  const g = fromCanonical(invoice).workflow;
  const condition = g.nodes.find((n) => n.data.kind === "condition")!;
  const issues = graphIssues(
    g.nodes,
    g.edges
      .filter((e) => e.source !== condition.id)
      .concat({ id: "broken", source: "absent", target: "missing" }),
  );
  expect(issues.some((x) => x.message.includes("missing step"))).toBe(true);
  expect(issues.some((x) => x.message.includes("branch"))).toBe(true);
  expect(issues.some((x) => x.message.includes("disconnected"))).toBe(true);
});
it("reviews actual proposal fields and never claims activation or reviewed tool grants", () => {
  render(<PlanReview document={document()} generated />);
  expect(screen.getByText("Generated plan — human review required")).toBeVisible();
  expect(screen.getByText("Goal")).toBeVisible();
  expect(screen.getByText("Approval points")).toBeVisible();
  expect(screen.getByText(/Saving a draft does not make it operational/)).toBeVisible();
  expect(screen.getByText("No agent definitions declared.")).toBeVisible();
});
it("shows newer draft separately from the older active release and unavailable simulation", async () => {
  const d = document();
  d.version = 2;
  useMesh.getState().acceptWorkflow(d);
  const g = useMesh.getState().workflows[0]!;
  vi.mocked(api.releaseState).mockResolvedValue({
    workflow_id: d.workflow_id,
    release: {
      release_id: "rel_old",
      workflow_version: 1,
      state: "active",
      trigger_binding_count: 1,
    },
  });
  useBackend.setState({
    overview: {
      [d.workflow_id]: {
        workflow_id: d.workflow_id,
        name: d.name,
        draft_version: 2,
        published_version: 1,
        release_id: "rel_old",
        activation_state: "active",
        active_run_count: 0,
        latest_run_id: null,
        latest_run_status: null,
        pending_approval_count: 0,
        updated_at: "2026-10-17T00:00:00Z",
      },
    },
  });
  render(<LifecycleJourney workflow={g} />);
  await waitFor(() => expect(screen.getByText(/Release: active · v1/)).toBeInTheDocument());
  expect(screen.getByText(/Draft revision: v2/)).toBeInTheDocument();
  fireEvent.click(screen.getByText("Workflow lifecycle · 14 stages"));
  expect(screen.getByText(/8. Simulate safely · unavailable/)).toBeVisible();
  expect(screen.getAllByText(/Activate release · blocked/).length).toBeGreaterThan(0);
});
it("exposes keyboard-operable connection and outline actions", () => {
  const g = fromCanonical(document()).workflow;
  const connect = vi.fn(),
    select = vi.fn();
  render(
    <GraphTools
      nodes={g.nodes}
      edges={g.edges}
      onConnect={connect}
      onSelect={select}
      onRemove={() => {}}
    />,
  );
  fireEvent.click(screen.getByText(/Workflow outline and connections/));
  fireEvent.change(screen.getByLabelText("Connection source"), {
    target: { value: g.nodes[0]!.id },
  });
  fireEvent.change(screen.getByLabelText("Connection target"), {
    target: { value: g.nodes.at(-1)!.id },
  });
  fireEvent.click(screen.getByRole("button", { name: "Connect steps" }));
  expect(connect).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole("button", { name: new RegExp("1\\.") }));
  expect(select).toHaveBeenCalled();
});
it("hierarchy labels presentation relationships separately from execution dependencies", () => {
  const d = document();
  d.agents = [
    {
      agent_id: "agent_one",
      role: "Helper",
      goal: "Review requests",
      instructions: "Review carefully",
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
    },
  ];
  d.nodes.push({ node_id: "helper", kind: "agent", label: "Helper", agent_id: "agent_one" });
  const mapped = fromCanonical(d);
  render(<HierarchyView workflow={mapped.workflow} agents={mapped.agents} onEdit={() => {}} />);
  expect(
    screen.getByText(/Presentation-only hierarchy links do not create runtime delegation/),
  ).toBeVisible();
  expect(screen.getAllByRole("button", { name: "Edit in Design" }).length).toBeGreaterThan(0);
});
it("reconciles recorded sequence rather than wall-clock time and rejects conflicting sequence identities", () => {
  const run = recorded();
  const a: RunEvent = {
    event_id: "a",
    run_id: run.run_id,
    workflow_id: run.workflow_id,
    workflow_version: 1,
    source: "runtime",
    timestamp: "2026-10-17T12:00:00Z",
    event_type: "node.started",
    details: { recorded_sequence: 2 },
  };
  const b = {
    ...a,
    event_id: "b",
    timestamp: "2000-01-01T00:00:00Z",
    event_type: "node.completed",
    details: { recorded_sequence: 3 },
  };
  expect(reconcileEvents([], [b, a], run).map((e) => e.event_id)).toEqual(["a", "b"]);
  expect(() => reconcileEvents([], [a, { ...b, details: { recorded_sequence: 2 } }], run)).toThrow(
    /reused an event sequence/,
  );
  expect(
    reconcileEvents(
      [],
      [
        { ...a, details: {} },
        { ...b, details: {} },
      ],
      run,
    ).map((e) => e.event_id),
  ).toEqual(["a", "b"]);
});
it("loads exact historical revision without replacing dirty draft or inferring missing node success", async () => {
  const d = document();
  d.version = 2;
  useMesh.getState().acceptWorkflow(d);
  useMesh.getState().renameWorkflow(d.workflow_id, "Unsaved current draft");
  vi.spyOn(api, "runs").mockResolvedValue({
    items: [recorded()],
    total: 1,
    has_more: false,
    next_cursor: null,
  });
  const request = vi.spyOn(api, "request").mockImplementation(async (operation) => {
    if (operation === "get_run") return { run: recorded() } as never;
    if (operation === "list_run_events")
      return { items: [], total: 0, has_more: false, next_cursor: null } as never;
    if (operation === "get_workflow") return { workflow: document() } as never;
    throw new Error("Unexpected operation");
  });
  const { result } = renderHook(() => useWorkflowTrace(d.workflow_id));
  await waitFor(() => expect(result.current.revision?.workflow.serverVersion).toBe(1));
  expect(request).toHaveBeenCalledWith("get_workflow", {
    workflow_id: d.workflow_id,
    workflow_version: 1,
  });
  expect(result.current.runState).toEqual({});
  const current = useMesh.getState().workflows[0]!;
  expect(current.name).toBe("Unsaved current draft");
  expect(hasWorkflowEdits(current, useMesh.getState().agents)).toBe(true);
});
it("fails closed when exact historical revision is unavailable or mismatched", async () => {
  vi.spyOn(api, "runs").mockResolvedValue({
    items: [recorded()],
    total: 1,
    has_more: false,
    next_cursor: null,
  });
  vi.spyOn(api, "request").mockImplementation(async (op) => {
    if (op === "get_run") return { run: recorded() } as never;
    if (op === "list_run_events") return { items: [] } as never;
    if (op === "get_workflow") {
      const wrong = document();
      wrong.version = 2;
      return { workflow: wrong } as never;
    }
    throw new Error("unexpected");
  });
  const { result } = renderHook(() => useWorkflowTrace(document().workflow_id));
  await waitFor(() =>
    expect(result.current.error?.message).toContain("different historical revision"),
  );
  expect(result.current.revision).toBeNull();
  expect(result.current.events).toEqual([]);
});
it("does not fetch runtime data while Design is selected or runs permission is missing", async () => {
  const runs = vi.spyOn(api, "runs");
  const { result, rerender } = renderHook(
    ({ enabled }) => useWorkflowTrace(document().workflow_id, enabled),
    { initialProps: { enabled: false } },
  );
  expect(result.current.available).toBe(false);
  expect(runs).not.toHaveBeenCalled();
  act(() =>
    useBackend.setState({
      session: {
        ...useBackend.getState().session!,
        auth: { ...useBackend.getState().session!.auth, permissions: ["workflow.view"] },
      },
    }),
  );
  rerender({ enabled: true });
  expect(runs).not.toHaveBeenCalled();
});
it("ignores a late response from a previously selected run", async () => {
  const first = recorded(),
    second = { ...recorded(), run_id: "run_second", workflow_version: 2 };
  const d = document();
  d.version = 2;
  let resolveFirst: (value: unknown) => void = () => {};
  vi.spyOn(api, "runs").mockResolvedValue({
    items: [first, second],
    total: 2,
    has_more: false,
    next_cursor: null,
  });
  vi.spyOn(api, "request").mockImplementation(async (op, payload) => {
    const p = payload as { run_id?: string; workflow_version?: number };
    if (op === "get_run")
      return p.run_id === first.run_id
        ? ((await new Promise<unknown>((resolve) => {
            resolveFirst = resolve;
          })) as never)
        : ({ run: second } as never);
    if (op === "list_run_events") return { items: [] } as never;
    if (op === "get_workflow")
      return { workflow: p.workflow_version === 2 ? d : document() } as never;
    throw new Error("unexpected");
  });
  const { result } = renderHook(() => useWorkflowTrace(d.workflow_id));
  await waitFor(() => expect(result.current.runId).toBe(first.run_id));
  act(() => result.current.selectRun(second.run_id));
  await waitFor(() => expect(result.current.revision?.workflow.serverVersion).toBe(2));
  await act(async () => {
    resolveFirst({ run: first });
  });
  expect(result.current.run?.run_id).toBe(second.run_id);
  expect(result.current.revision?.workflow.serverVersion).toBe(2);
});
it("shows canonical master and delegated specialist templates even without specialist graph nodes", () => {
  const d = document();
  const base = {
    role: "Master role",
    goal: "Coordinate work",
    instructions: "Delegate carefully",
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
  };
  d.agents = [
    { ...base, agent_id: "master_agent", hierarchy_role: "master" },
    {
      ...base,
      agent_id: "specialist_agent",
      role: "Specialist role",
      hierarchy_role: "sub_agent",
      parent_agent_id: "master_agent",
    },
  ];
  d.nodes.push({
    node_id: "master_step",
    kind: "agent",
    label: "Master",
    agent_id: "master_agent",
  });
  d.metadata["dynamic_delegation"] = { master_step: { max_rounds: 2, max_tasks: 3 } };
  const mapped = fromCanonical(d);
  render(<HierarchyView workflow={mapped.workflow} agents={mapped.agents} onEdit={() => {}} />);
  expect(screen.getByText("Master · Master role")).toBeVisible();
  expect(screen.getByText("Delegated · Specialist role")).toBeVisible();
  expect(screen.getByText(/Specialist template; runtime delegation configured/)).toBeVisible();
});

it("shows confirmed publication while the global overview is still loading", async () => {
  const d=document();d.status="published";const mapped=fromCanonical(d);useMesh.setState({workflows:[mapped.workflow],agents:mapped.agents});
  render(<LifecycleJourney workflow={mapped.workflow}/>);
  await waitFor(()=>expect(screen.getByText(/Published revision: v1/)).toBeInTheDocument());
  expect(screen.queryByText(/Published revision: none recorded/)).toBeNull();
});
