import type { RunEvent } from "@/api/contracts.generated";
import type { Workflow, WorkflowNode } from "./types";
import dagre from "@dagrejs/dagre";

export interface CommunicationLink {
  id: string;
  source: string;
  target: string;
  kind: "hierarchy" | "route" | "data";
  label: string;
  edgeId?: string;
}
export interface CommunicationEntity {
  node: WorkflowNode;
  agentId?: string | undefined;
  role: "Master agent" | "Sub-agent" | "Agent" | "Workflow step";
  parentNodeId?: string | undefined;
}

export function communicationGraph(workflow: Workflow, events: RunEvent[] = [], runId?: string) {
  const nodes = [...workflow.nodes];
  if (!runId && workflow.canonical?.metadata?.["dynamic_delegation"]) {
    for (const agent of workflow.canonical.agents) {
      const parent = nodes.find((node) => node.data.agentId === agent.parent_agent_id || node.data.agentId === `${workflow.id}::${agent.parent_agent_id}`);
      if (agent.hierarchy_role !== "sub_agent" || !parent || nodes.some((node) => node.data.agentId === agent.agent_id || node.data.agentId === `${workflow.id}::${agent.agent_id}`)) continue;
      nodes.push({ id: `available_${agent.agent_id}`, type: "mesh", position: { x: 0, y: 0 }, data: { kind: "agent", label: `Available: ${agent.role}`, agentId: agent.agent_id, role: "sub", parentNodeId: parent.id } });
    }
  }
  const validEvents = events.filter((event) => event.run_id === runId && event.workflow_id === workflow.id && event.workflow_version === workflow.serverVersion);
  for (const event of validEvents) {
    const d = event.details;
    if (event.event_type === "node.observed" && d?.["kind"] === "tool" && typeof d["node_id"] === "string" && typeof d["parent_node_id"] === "string" && typeof d["tool_id"] === "string") {
      if (nodes.some((n) => n.id === d["parent_node_id"]) && !nodes.some((n) => n.id === d["node_id"]))
        nodes.push({ id: d["node_id"], type: "mesh", position: { x: 0, y: 0 }, data: { kind: "tool", label: d["tool_id"], tool: d["tool_id"], agentId: typeof d["agent_id"] === "string" ? d["agent_id"] : undefined, parentNodeId: d["parent_node_id"] } });
      continue;
    }
    if (event.event_type !== "agent.spawned" || typeof d?.["node_id"] !== "string" || typeof d["agent_id"] !== "string" || typeof d["parent_node_id"] !== "string") continue;
    if (!nodes.some((n) => n.id === d["parent_node_id"]) || nodes.some((n) => n.id === d["node_id"])) continue;
    nodes.push({ id: d["node_id"], type: "mesh", position: { x: 0, y: 0 }, data: { kind: "agent", label: typeof d["label"] === "string" ? d["label"] : "Spawned sub-agent", agentId: d["agent_id"], parentNodeId: d["parent_node_id"], role: "sub" } });
  }
  const ids = new Set(nodes.map((node) => node.id));
  const entities: CommunicationEntity[] = nodes.map((node) => {
    const canonical = workflow.canonical?.nodes.find((item) => item.node_id === node.id);
    const reference = node.data.agentId ?? canonical?.agent_id;
    const prefix = `${workflow.id}::`;
    const agentId = reference?.startsWith(prefix) ? reference.slice(prefix.length) : reference;
    const definition = workflow.canonical?.agents.find((agent) => agent.agent_id === agentId);
    const parent =
      node.data.parentNodeId ??
      (definition?.parent_agent_id
        ? workflow.canonical?.nodes.find(
            (item) => item.kind === "agent" && item.agent_id === definition.parent_agent_id,
          )?.node_id
        : undefined);
    const role =
      node.data.kind !== "agent"
        ? "Workflow step"
        : node.data.role === "master" || definition?.hierarchy_role === "master"
          ? "Master agent"
          : parent || node.data.role === "sub" || definition?.hierarchy_role === "sub_agent"
            ? "Sub-agent"
            : "Agent";
    return {
      node,
      agentId,
      role,
      parentNodeId: parent && ids.has(parent) && parent !== node.id ? parent : undefined,
    };
  });
  const links: CommunicationLink[] = workflow.edges
    .filter((edge) => ids.has(edge.source) && ids.has(edge.target))
    .map((edge) => ({
      ...edge,
      kind: "route",
      edgeId: edge.id,
      label: edge.label ? `Route · ${edge.label}` : "Workflow route",
    }));
  for (const entity of entities) {
    if (entity.node.data.kind === "agent" && entity.parentNodeId)
      links.push({
        id: JSON.stringify(["hierarchy", entity.parentNodeId, entity.node.id]),
        source: entity.parentNodeId,
        target: entity.node.id,
        kind: "hierarchy",
        label: "Parent relationship",
      });
  }
  return { entities, links };
}

export function handoffEvents(events: RunEvent[], workflow: Workflow, runId: string) {
  return events.filter(
    (event) =>
      event.event_type === "node.handoff" &&
      event.run_id === runId &&
      event.workflow_id === workflow.id &&
      event.workflow_version === workflow.serverVersion &&
      typeof event.details?.["source_node_id"] === "string" &&
      typeof event.details?.["target_node_id"] === "string",
  );
}

export function withRecordedDataLinks(
  links: CommunicationLink[],
  events: RunEvent[],
  nodes: WorkflowNode[],
) {
  const result = links.filter((link) => !(link.kind === "hierarchy" && events.some((event) =>
    event.details?.["transfer_kind"] === "delegated_task" && event.details?.["source_node_id"] === link.source && event.details?.["target_node_id"] === link.target)));
  const ids = new Set(nodes.map((node) => node.id));
  for (const event of events) {
    const source = event.details?.["source_node_id"];
    const target = event.details?.["target_node_id"];
    if (
      typeof source !== "string" ||
      typeof target !== "string" ||
      !ids.has(source) ||
      !ids.has(target) ||
      !["mapped_data", "delegated_task", "delegated_result"].includes(String(event.details?.["transfer_kind"]))
    )
      continue;
    if (
      result.some(
        (link) =>
          link.kind !== "hierarchy" &&
          link.source === source &&
          link.target === target &&
          link.edgeId === event.details?.["edge_id"],
      )
    )
      continue;
    const id = JSON.stringify(["data", source, target]);
    if (!result.some((link) => link.id === id))
      result.push({ id, source, target, kind: "data", label: event.details?.["transfer_kind"] === "delegated_task" ? "Delegated task" : event.details?.["transfer_kind"] === "delegated_result" ? "Returned result" : "Recorded data mapping" });
  }
  return result;
}

export function eventsForLink(events: RunEvent[], link: CommunicationLink) {
  if (link.kind === "hierarchy") return [];
  return events.filter(
    (event) =>
      event.details?.["source_node_id"] === link.source &&
      event.details?.["target_node_id"] === link.target &&
      (link.kind === "data"
        ? event.details?.["edge_id"] === null
        : event.details?.["edge_id"] === link.edgeId),
  );
}

/** Place nodes by forward dependencies. Return messages remain displayed edges,
 * but do not form cycles or duplicate constraints in the layout graph. */
export function communicationPositions(entities: CommunicationEntity[], links: CommunicationLink[], events: RunEvent[]) {
  const layout = new dagre.graphlib.Graph();
  layout.setGraph({ rankdir: "TB", nodesep: 70, ranksep: 100 });
  layout.setDefaultEdgeLabel(() => ({}));
  entities.forEach((entity) => layout.setNode(entity.node.id, { width: 280, height: 150 }));
  links.forEach((link) => {
    if (eventsForLink(events, link).some((event) => event.details?.["transfer_kind"] === "delegated_result")) return;
    layout.setEdge(link.source, link.target, {});
  });
  dagre.layout(layout);
  return Object.fromEntries(entities.map((entity) => {
    const point = layout.node(entity.node.id);
    return [entity.node.id, { x: point.x - 140, y: point.y - 75 }];
  }));
}

/** UUIDv5 in the standard DNS namespace. Stable across reloads; no document mutation. */
export async function communicationUuid(workflowId: string, nodeId: string): Promise<string> {
  const namespace = Uint8Array.from("6ba7b8109dad11d180b400c04fd430c8".match(/../g)!, (hex) =>
    parseInt(hex, 16),
  );
  const name = new TextEncoder().encode(JSON.stringify(["mesh.workflow.node", workflowId, nodeId]));
  const bytes = new Uint8Array(namespace.length + name.length);
  bytes.set(namespace);
  bytes.set(name, namespace.length);
  const hash = new Uint8Array(await crypto.subtle.digest("SHA-1", bytes)).slice(0, 16);
  hash[6] = (hash[6]! & 0x0f) | 0x50;
  hash[8] = (hash[8]! & 0x3f) | 0x80;
  const hex = Array.from(hash, (byte) => byte.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

/** Use the final outcome of the exact attempt, including an error branch after completion. */
export function handoffResult(timeline: RunEvent[], handoff: RunEvent) {
  const details = handoff.details;
  if (typeof details?.["target_invocation_id"] !== "string") return undefined;
  return timeline.filter((event) =>
    (event.event_type === "node.completed" || event.event_type === "node.failed") &&
    event.run_id === handoff.run_id && event.workflow_id === handoff.workflow_id &&
    event.workflow_version === handoff.workflow_version &&
    event.details?.["node_id"] === details["target_node_id"] &&
    event.details?.["invocation_id"] === details["target_invocation_id"]
  ).at(-1);
}
