import type { RunEvent } from "@/api/contracts.generated";
import type { Workflow } from "./types";
import {
  communicationGraph,
  eventsForLink,
  handoffEvents,
  withRecordedDataLinks,
} from "./communication";

export const friendlyLabel = (value: string) => value.replaceAll("_", " ").replaceAll(".", " ");
export const friendlyRole = (role: string) =>
  role === "Master agent" ? "Coordinator" : role === "Sub-agent" ? "Helper agent" : role;

export interface DiagramCard {
  id: string;
  nodeId: string;
  workflowId: string;
  label: string;
  role: string;
  status: string;
  spawned: boolean;
  parent?: string | undefined;
  description?: string | undefined;
  reason?: string | undefined;
  input?: unknown;
  output?: unknown;
  problem?: unknown;
  events: RunEvent[];
  runId?: string | undefined;
  invocationId?: string | undefined;
  agentId?: string | undefined;
}
export interface DiagramConnection {
  id: string;
  source: string;
  target: string;
  label: string;
  recorded: boolean;
  active: boolean;
  returned: boolean;
  events: RunEvent[];
}
export interface DiagramModel {
  cards: DiagramCard[];
  connections: DiagramConnection[];
}

export function workflowDiagram(
  workflow: Workflow,
  timeline: RunEvent[],
  runId?: string,
  runStatus?: string,
): DiagramModel {
  const events = timeline.filter(
    (e) =>
      !!runId &&
      e.run_id === runId &&
      e.workflow_id === workflow.id &&
      e.workflow_version === workflow.serverVersion,
  );
  const graph = communicationGraph(workflow, events, runId);
  const handoffs = handoffEvents(events, workflow, runId ?? "");
  const prefix = runId ?? `plan:${workflow.id}`;
  const qualify = (id: string) => `${prefix}:${id}`;
  const name = (id: unknown) => graph.entities.find((e) => e.node.id === id)?.node.data.label;
  const cards = graph.entities.map((entity) => {
    const id = entity.node.id;
    const own = events.filter((e) => e.details?.["node_id"] === id);
    const related = events.filter(
      (e) =>
        e.details?.["node_id"] === id ||
        e.details?.["target_node_id"] === id ||
        e.details?.["source_node_id"] === id,
    );
    const spawn = own.find((e) => e.event_type === "agent.spawned");
    const last = own
      .filter((e) =>
        [
          "node.started",
          "node.completed",
          "node.failed",
          "node.skipped",
          "approval.pending",
          "approval.rejected",
          "approval.timed_out",
        ].includes(e.event_type),
      )
      .at(-1);
    const observed = own.filter((e) => e.event_type === "node.observed").at(-1);
    const attempt = last?.details?.["invocation_id"] ?? observed?.details?.["invocation_id"];
    const completed = own
      .filter(
        (e) =>
          e.event_type === "node.completed" &&
          (attempt === undefined || e.details?.["invocation_id"] === attempt),
      )
      .at(-1);
    const task = handoffs
      .filter(
        (e) =>
          e.details?.["target_node_id"] === id && e.details?.["transfer_kind"] === "delegated_task",
      )
      .at(-1);
    const received = handoffs
      .filter(
        (e) =>
          e.details?.["target_node_id"] === id &&
          e.details?.["transfer_kind"] !== "delegated_result",
      )
      .at(-1);
    const definition = workflow.canonical?.agents.find((a) => a.agent_id === entity.agentId);
    const reason = task?.details?.["reason"] ?? spawn?.details?.["reason"];
    const status = !runId
      ? "Planned"
      : last?.event_type === "node.completed"
        ? "Completed"
        : last?.event_type === "node.failed" || last?.event_type === "approval.timed_out"
          ? "Failed"
          : last?.event_type === "approval.rejected"
            ? "Approval rejected"
            : last?.event_type === "node.skipped"
              ? "Skipped"
              : last?.event_type === "approval.pending"
                ? "Waiting for approval"
                : last || spawn || observed
                  ? ["running", "queued"].includes(runStatus ?? "")
                    ? "Working"
                    : runStatus === "paused"
                      ? "Paused"
                      : "Outcome not recorded"
                  : "No activity recorded";
    return {
      id: qualify(id),
      nodeId: id,
      workflowId: workflow.id,
      label: entity.node.data.label.replace(/^Available: /, ""),
      role: friendlyRole(entity.role),
      status,
      spawned: !!spawn,
      parent: name(spawn?.details?.["parent_node_id"] ?? entity.parentNodeId),
      description: entity.node.data.kind === "agent" ? definition?.goal : undefined,
      reason: typeof reason === "string" ? reason : undefined,
      input:
        task?.details?.["receiver_input"] ??
        observed?.details?.["observation"] ??
        received?.details?.["receiver_input"] ??
        (!runId
          ? workflow.canonical?.nodes.find((n) => n.node_id === id)?.configuration?.["input"]
          : undefined),
      output: completed?.details?.["output"],
      problem: own.filter((e) => e.event_type === "node.failed").at(-1)?.details?.["error_code"],
      events: related,
      runId,
      invocationId:
        typeof spawn?.details?.["invocation_id"] === "string"
          ? spawn.details["invocation_id"]
          : undefined,
      agentId: entity.agentId,
    };
  });
  const connections = withRecordedDataLinks(
    graph.links,
    handoffs,
    graph.entities.map((e) => e.node),
  ).map((link) => {
    const matched = eventsForLink(handoffs, link);
    const kind = matched[0]?.details?.["transfer_kind"];
    const target = cards.find((c) => c.nodeId === link.target);
    const active = matched.length > 0 && target?.status === "Working";
    return {
      id: qualify(link.id),
      source: qualify(link.source),
      target: qualify(link.target),
      label:
        kind === "delegated_task"
          ? "Task assigned"
          : kind === "delegated_result"
            ? "Result returned"
            : kind === "mapped_data"
              ? "Information shared"
              : matched.length
                ? "Continued here"
                : link.kind === "hierarchy"
                  ? "Available helper"
                  : "Planned next step",
      recorded: matched.length > 0,
      active,
      returned: kind === "delegated_result",
      events: matched,
    };
  });
  // A recorded exchange replaces a redundant configured line between the same cards.
  // Otherwise prefer the helper relationship over an identical planned route.
  const visibleConnections = connections.filter(
    (connection) =>
      connection.recorded ||
      (!connections.some(
        (other) =>
          other.recorded &&
          other.source === connection.source &&
          other.target === connection.target,
      ) &&
        !(
          connection.label === "Planned next step" &&
          connections.some(
            (other) =>
              other.label === "Available helper" &&
              other.source === connection.source &&
              other.target === connection.target,
          )
        )),
  );
  return { cards, connections: visibleConnections };
}
