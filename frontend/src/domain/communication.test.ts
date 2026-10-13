import { expect, test, vi, afterEach } from "vitest";
import { webcrypto } from "node:crypto";
import {
  communicationGraph,
  hasCommunication,
  communicationPositions,
  communicationUuid,
  eventsForLink,
  handoffEvents,
  handoffResult,
  withRecordedDataLinks,
} from "./communication";
import type { Workflow } from "./types";
import type { CanonicalWorkflow, RunEvent } from "@/api/contracts.generated";
afterEach(() => vi.unstubAllGlobals());

test("tool-backed specialists retain communication access and actual agent identity", () => {
  const toolWorkflow = { ...workflow, nodes: [{ id: "master", type: "mesh", position: { x: 0, y: 0 },
    data: { kind: "tool", label: "Read requirements", agentId: "wf_communication::master_agent" } }], edges: [] } as Workflow;
  expect(hasCommunication(toolWorkflow)).toBe(true);
  expect(communicationGraph(toolWorkflow).entities[0]?.agentId).toBe("master_agent");
});
const workflow: Workflow = {
  id: "wf_communication",
  workspaceId: "ws",
  name: "Hierarchy",
  description: "",
  prompt: "",
  scenario: "hierarchy",
  status: "draft",
  versions: [],
  createdAt: "",
  updatedAt: "",
  serverVersion: 2,
  nodes: ["master", "research", "analysis"].map((id) => ({
    id,
    type: "mesh",
    position: { x: 0, y: 0 },
    data: { kind: "agent", label: id, agentId: `wf_communication::${id}_agent` },
  })),
  edges: [{ id: "route", source: "master", target: "research" }],
  canonical: {
    nodes: ["master", "research", "analysis"].map((id) => ({
      node_id: id,
      kind: "agent",
      agent_id: `${id}_agent`,
    })),
    agents: [
      { agent_id: "master_agent", hierarchy_role: "master" },
      { agent_id: "research_agent", hierarchy_role: "sub_agent", parent_agent_id: "master_agent" },
      { agent_id: "analysis_agent", hierarchy_role: "sub_agent", parent_agent_id: "master_agent" },
    ],
  } as unknown as CanonicalWorkflow,
};
const event: RunEvent = {
  event_id: "evt_handoff",
  run_id: "run_one",
  workflow_id: workflow.id,
  workflow_version: 2,
  event_type: "node.handoff",
  timestamp: "2026-10-11T10:00:00Z",
  source: "runtime",
  details: {
    source_node_id: "master",
    target_node_id: "research",
    edge_id: "route",
    transfer_kind: "execution_transition",
  },
};
test("spawned task instances and return handoffs appear only in their exact run", () => {
  const spawn: RunEvent = { ...event, event_type: "agent.spawned", details: { node_id: "delegated_task", agent_id: "research_agent", parent_node_id: "master", label: "Research task", invocation_id: "uuid" } };
  const runtimeWorkflow = { ...workflow, nodes: workflow.nodes.slice(0, 1), edges: [] };
  const graph = communicationGraph(runtimeWorkflow, [spawn], "run_one");
  expect(graph.entities).toHaveLength(2);
  expect(graph.entities[1]?.role).toBe("Sub-agent");
  expect(communicationGraph(runtimeWorkflow, [spawn], "another_run").entities).toHaveLength(1);
  const task = { ...event, details: { source_node_id: "master", target_node_id: "delegated_task", edge_id: null, transfer_kind: "delegated_task" } };
  const result = { ...event, details: { source_node_id: "delegated_task", target_node_id: "master", edge_id: null, transfer_kind: "delegated_result" } };
  const links = withRecordedDataLinks(graph.links, [task, result], graph.entities.map((entity) => entity.node));
  expect(links.filter((link) => link.kind === "data")).toHaveLength(2);
  expect(eventsForLink([task, result], links.find((link) => link.label === "Returned result")!)).toEqual([result]);
});
test("delegated connector observations produce tool nodes with request and result links", () => {
  const observed = { ...event, event_type: "node.observed", details: { node_id: "delegated_tool_read", parent_node_id: "research", agent_id: "research_agent", tool_id: "google_sheets_read_rows", kind: "tool" } };
  const graph = communicationGraph(workflow, [observed], event.run_id);
  const tool = graph.entities.find((entity) => entity.node.id === "delegated_tool_read");
  expect(tool?.node.data.kind).toBe("tool");
  expect(tool?.node.data.tool).toBe("google_sheets_read_rows");
  expect(tool?.role).toBe("Workflow step");
  expect(communicationGraph(workflow, [observed], "other_run").entities).toHaveLength(workflow.nodes.length);
  const handoffs = [
    { ...event, details: { source_node_id: "research", target_node_id: "delegated_tool_read", edge_id: null, transfer_kind: "delegated_task" } },
    { ...event, details: { source_node_id: "delegated_tool_read", target_node_id: "research", edge_id: null, transfer_kind: "delegated_result" } },
  ];
  const links = withRecordedDataLinks(graph.links, handoffs, graph.entities.map((entity) => entity.node));
  expect(links.filter((link) => link.kind === "data")).toHaveLength(2);
  expect(Object.values(communicationPositions(graph.entities, links, handoffs)).every((point) => Number.isFinite(point.x) && Number.isFinite(point.y))).toBe(true);
});

test("multiple specialist instances with bidirectional handoffs have finite, separate positions", () => {
  const runtimeWorkflow = { ...workflow, nodes: workflow.nodes.slice(0, 1), edges: [] };
  const instances = ["task_a", "task_b", "task_summary"];
  const spawns = instances.map((id) => ({ ...event, event_type: "agent.spawned", details: { node_id: id, agent_id: "research_agent", parent_node_id: "master", label: id } }));
  const graph = communicationGraph(runtimeWorkflow, spawns, event.run_id);
  const transfers = instances.flatMap((id) => [
    { ...event, details: { source_node_id: "master", target_node_id: id, edge_id: null, transfer_kind: "delegated_task" } },
    { ...event, details: { source_node_id: id, target_node_id: "master", edge_id: null, transfer_kind: "delegated_result" } },
  ]);
  const links = withRecordedDataLinks(graph.links, transfers, graph.entities.map((entity) => entity.node));
  const positions = communicationPositions(graph.entities, links, transfers);
  expect(Object.values(positions).every((point) => Number.isFinite(point.x) && Number.isFinite(point.y))).toBe(true);
  expect(new Set(Object.values(positions).map((point) => `${point.x},${point.y}`)).size).toBe(4);
  expect(instances.every((id) => positions[id]!.y > positions["master"]!.y)).toBe(true);
  expect(links.filter((link) => link.kind === "data")).toHaveLength(6);
});
test("canonical hierarchy preserves identities and does not invent return routes", () => {
  const graph = communicationGraph(workflow);
  expect(graph.entities.map((entity) => entity.role)).toEqual([
    "Master agent",
    "Sub-agent",
    "Sub-agent",
  ]);
  expect(graph.entities[1]?.agentId).toBe("research_agent");
  expect(graph.links.filter((link) => link.kind === "hierarchy")).toHaveLength(2);
  expect(graph.links.some((link) => link.source === "research" && link.target === "master")).toBe(
    false,
  );
});
test("local draft hierarchy also works without canonical records", () => {
  const graph = communicationGraph({
    ...workflow,
    canonical: undefined,
    nodes: workflow.nodes.map((node) => ({
      ...node,
      data: {
        ...node.data,
        role: node.id === "master" ? "master" : "sub",
        parentNodeId: node.id === "master" ? undefined : "master",
      },
    })),
  });
  expect(graph.entities[0]?.role).toBe("Master agent");
  expect(graph.entities[1]?.parentNodeId).toBe("master");
});
test("UUIDs survive reloads and separate workflows and nodes", async () => {
  vi.stubGlobal("crypto", webcrypto);
  const first = await communicationUuid(workflow.id, "master");
  expect(first).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-5[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
  expect(await communicationUuid(workflow.id, "master")).toBe(first);
  expect(await communicationUuid(workflow.id, "research")).not.toBe(first);
  expect(await communicationUuid("other_workflow", "master")).not.toBe(first);
});
test("handoff evidence excludes other runs, workflows and revisions", () => {
  const events = handoffEvents(
    [
      event,
      { ...event, run_id: "run_two" },
      { ...event, workflow_id: "other" },
      { ...event, workflow_version: 1 },
    ],
    workflow,
    "run_one",
  );
  expect(events).toEqual([event]);
  const graph = communicationGraph(workflow);
  expect(eventsForLink(events, graph.links[0]!)).toEqual([event]);
  expect(eventsForLink(events, graph.links[1]!)).toEqual([]);
});
test("nonadjacent recorded data adds an inspectable connection without fabricating peers", () => {
  const data = {
    ...event,
    details: {
      source_node_id: "research",
      target_node_id: "analysis",
      edge_id: null,
      transfer_kind: "mapped_data",
    },
  };
  const graph = communicationGraph(workflow);
  const links = withRecordedDataLinks(graph.links, [data, data], workflow.nodes);
  const added = links.filter((link) => link.kind === "data");
  expect(added).toHaveLength(1);
  expect(eventsForLink([data], added[0]!)).toEqual([data]);
  expect(links.some((link) => link.source === "analysis" && link.target === "research")).toBe(
    false,
  );
});

test("handoff results match the exact attempt and retain its final error outcome", () => {
  const handoff = { ...event, details: { ...event.details, target_invocation_id: "attempt_1" } };
  const completed = { ...event, event_type: "node.completed", details: { node_id: "research", invocation_id: "attempt_1", output: null } };
  const failed = { ...completed, event_type: "node.failed", details: { ...completed.details, error_code: "CONNECTOR_FAILED" } };
  expect(handoffResult([completed, failed, { ...failed, run_id: "run_two" }, { ...completed, details: { ...completed.details, invocation_id: "attempt_2" } }], handoff)).toEqual(failed);
  expect(handoffResult([completed], { ...handoff, workflow_version: 1 })).toBeUndefined();
});
