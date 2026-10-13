import { expect, it } from "vitest";
import { procurementGraph, type ProjectCommunication } from "./procurement-communication";
import fixture from "../../../shared/contracts/examples/workflows/support-triage.json";
const action = (id: string) => ({ key: `send_${id}`, workflow: {
  ...fixture,
  workflow_id: `workflow_${id}`, version: 1, name: "RFQ send", agents: [], nodes: [
    { node_id: "start", kind: "trigger", label: "Start" }, { node_id: "action", kind: "tool", label: "Send RFQ", tool_id: "extension_mail_send" },
  ], edges: [{ edge_id: "route", source: "start", target: "action" }], metadata: {},
}, run: { run_id: id, status: "completed", workflow_id: `workflow_${id}`, workflow_version: 1 }, events: [
  { event_id: `evt_${id}`, run_id: id, workflow_id: `workflow_${id}`, workflow_version: 1, event_type: "node.completed",
    details: { node_id: "action", output: { message_id: `message_${id}` } } },
] });
const project = { project_id: "project_demo", phase: "RFQS_SENT", root_workflow: { name: "Procurement", workflow_id: "root", version: 1 },
  configured_workflow: null, truncated: false, actions: [action("run_1"), action("run_2")] } as unknown as ProjectCommunication;

it("shows all project actions in one graph with distinct run-qualified node IDs", () => {
  const graph = procurementGraph(project);
  expect(graph.nodes.filter(n => n.label === "Send RFQ")).toHaveLength(2);
  expect(new Set(graph.nodes.map(n => n.id)).size).toBe(graph.nodes.length);
  expect(graph.nodes.find(n => n.id === "run_1:action")?.details).toMatchObject({ run_id: "run_1", original_node_id: "action" });
  expect(graph.nodes.find(n => n.id === "run_2:action")?.details).toMatchObject({ events: [expect.objectContaining({ details: { node_id: "action", output: { message_id: "message_run_2" } } })] });
});

it("does not invent message exchanges between separate actions", () => {
  expect(procurementGraph(project).edges.filter(e => e.recorded)).toHaveLength(0);
});
