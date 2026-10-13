import { fromCanonical } from "@/api/mapping";
import { communicationGraph } from "./communication";
import type { api } from "@/api/client";
export type ProjectCommunication = Awaited<ReturnType<typeof api.procurementProjectCommunication>>;

export function procurementGraph(project: ProjectCommunication) {
  const nodes: { id: string; label: string; role: string; runId?: string | undefined; status: string; details: unknown; parent: string }[] = [];
  const edges: { id: string; source: string; target: string; label: string; recorded: boolean }[] = [];
  const root = `project:${project.project_id}`;
  nodes.push({ id: root, label: project.root_workflow.name, role: "Project coordinator", status: project.phase,
    parent: "", details: { project_id: project.project_id, phase: project.phase, workflow_id: project.root_workflow.workflow_id,
      version: project.root_workflow.version, run: project.root_run, events: project.root_events } });
  const actions = project.actions.length ? project.actions : project.configured_workflow ? [{ key: "configured",
    workflow: project.configured_workflow, run: null, events: [] }] : [];
  for (const action of actions) {
    const namespace = action.run?.run_id ?? `configured:${action.workflow.workflow_id}`;
    const group = `${namespace}:group`;
    nodes.push({ id: group, label: action.key, role: "Recorded project action", status: action.run?.status ?? "Configured",
      runId: action.run?.run_id, parent: root, details: { workflow_id: action.workflow.workflow_id,
        workflow_version: action.workflow.version, run: action.run } });
    edges.push({ id: `project:${group}`, source: root, target: group, label: "Coordinator action", recorded: false });
    const workflow = fromCanonical(action.workflow).workflow;
    const validEvents = action.events.filter(e => e.run_id === action.run?.run_id &&
      e.workflow_id === action.workflow.workflow_id && e.workflow_version === action.workflow.version);
    const graph = communicationGraph(workflow, validEvents, action.run?.run_id);
    for (const entity of graph.entities) {
      const id = `${namespace}:${entity.node.id}`;
      const events = validEvents.filter(e => e.details?.["node_id"] === entity.node.id || e.details?.["source_node_id"] === entity.node.id || e.details?.["target_node_id"] === entity.node.id);
      const last = [...events].reverse().find(e => ["node.completed", "node.failed", "node.skipped", "approval.pending", "agent.completed"].includes(e.event_type));
      nodes.push({ id, label: entity.node.data.label, role: entity.role, runId: action.run?.run_id,
        status: last?.event_type ?? action.run?.status ?? "Configured", parent: group,
        details: { original_node_id: entity.node.id, agent_id: entity.agentId, run_id: action.run?.run_id,
          workflow_id: action.workflow.workflow_id, version: action.workflow.version, events } });
    }
    const entry = graph.entities.find(e => e.node.data.kind === "trigger");
    if (entry) edges.push({ id: `${group}:entry`, source: group, target: `${namespace}:${entry.node.id}`, label: "Action graph", recorded: false });
    for (const link of graph.links) edges.push({ id: `${namespace}:${link.id}`, source: `${namespace}:${link.source}`,
      target: `${namespace}:${link.target}`, label: link.label, recorded: false });
    for (const event of validEvents) {
      if (event.event_type !== "node.handoff") continue;
      const d = event.details;
      const source = d?.["source_node_id"]; const target = d?.["target_node_id"];
      if (typeof source !== "string" || typeof target !== "string") continue;
      if (!nodes.some(n => n.id === `${namespace}:${source}`) || !nodes.some(n => n.id === `${namespace}:${target}`)) continue;
      edges.push({ id: `${namespace}:event:${event.event_id}`, source: `${namespace}:${source}`, target: `${namespace}:${target}`,
        label: "Recorded handoff", recorded: true });
    }
  }
  return { nodes, edges };
}

export function compactProcurementGraph(project: ProjectCommunication) {
  const full = procurementGraph(project);
  const root = full.nodes[0];
  if (!root) return full;
  const nodes = full.nodes.filter(n => !n.parent);
  const edges: typeof full.edges = [];
  const stages = new Map<string, ProjectCommunication["actions"]>();
  for (const action of project.actions) {
    const stage = action.key === "ingestion" ? "Master and specialist review" : action.key.startsWith("research_") ? "Supplier research and verification" :
      action.key === "tracking" ? "Create tracking spreadsheet" : action.key.startsWith("sync_") ? "Save tracking records" :
      action.key.startsWith("ful_extract_") ? "Fulfilment master and specialists" :
      action.key.startsWith("ful_read_") ? "Monitor PO replies" :
      action.key.startsWith("ful_notify_") ? "Fulfilment follow-ups and notifications" :
      action.key.startsWith("ful_calendar_") ? "Fulfilment Calendar updates" :
      action.key.startsWith("calendar_") ? "Calendar deadlines" :
      action.key.startsWith("read_quotes_") || action.key.startsWith("extract_") || action.key.startsWith("clarify_") ? "Read and validate quotations" :
      action.key.startsWith("send_award_") || action.key.startsWith("send_po_") ? "Awards and purchase orders" :
      action.key.startsWith("draft_") ? "Prepare RFQ drafts" : action.key.startsWith("send_") ? "Send RFQs" : "Project actions";
    stages.set(stage, [...(stages.get(stage) ?? []), action]);
  }
  if (!project.actions.length) return full;
  for (const [label, actions] of stages) {
    const id = `${root.id}:stage:${label}`;
    const unfinished = actions.find(a => a.run.status !== "completed");
    nodes.push({ id, label: `${label} (${actions.length})`, role: "Project stage", status: unfinished?.run.status ?? "completed", parent: root.id,
      details: { actions: actions.map(a => ({ action: a.key, run_id: a.run.run_id, workflow_id: a.workflow.workflow_id, status: a.run.status,
        events: a.events.filter(e => e.run_id === a.run.run_id && e.workflow_id === a.workflow.workflow_id && e.workflow_version === a.workflow.version) })) } });
    edges.push({ id: `stage:${id}`, source: root.id, target: id, label: "Coordinator stage", recorded: false });
    if (label === "Master and specialist review" || label === "Fulfilment master and specialists") {
      const action = label === "Master and specialist review" ? actions[0] : actions[actions.length - 1];
      if (!action) continue;
      const specialists = full.nodes.filter(n => n.runId === action.run.run_id && ["Master agent", "Sub-agent"].includes(n.role));
      nodes.push(...specialists);
      for (const n of specialists) edges.push({ id: `stage-member:${n.id}`, source: id, target: n.id, label: "Stage member", recorded: false });
      const ids = new Set(specialists.map(n => n.id));
      edges.push(...full.edges.filter(e => e.recorded && ids.has(e.source) && ids.has(e.target)));
    }
  }
  return { nodes, edges };
}
