import type { RunEvent, RunStatus, CanonicalWorkflow } from "./contracts.generated";

const transitions: Record<RunStatus, RunStatus[]> = {
  queued: ["running", "failed", "blocked", "cancelled"],
  running: ["paused_for_approval", "completed", "failed", "blocked", "cancelled"],
  paused_for_approval: ["running", "rejected", "failed", "blocked", "cancelled"],
  completed: [], failed: [], rejected: [], cancelled: [], blocked: [],
};
export function assertRunTransition(previous: RunStatus, next: RunStatus) {
  // Polling can skip intermediate states. Accept reachable states, never terminal resurrection.
  const pending: RunStatus[] = [previous];
  const seen = new Set<RunStatus>();
  while (pending.length) {
    const status = pending.shift()!;
    if (status === next) return;
    if (seen.has(status)) continue;
    seen.add(status);
    pending.push(...transitions[status]);
  }
  throw new Error("The runtime reported an impossible run transition.");
}
export function reconcileEvents(existing: RunEvent[], incoming: RunEvent[], reference: { run_id: string; workflow_id: string; workflow_version: number }): RunEvent[] {
  const events = new Map(existing.map((event) => [event.event_id, event]));
  for (const event of [...existing, ...incoming]) {
    if (event.run_id !== reference.run_id || event.workflow_id !== reference.workflow_id || event.workflow_version !== reference.workflow_version) throw new Error("The event belongs to a different run revision.");
    const duplicate = events.get(event.event_id);
    if (duplicate && JSON.stringify(duplicate) !== JSON.stringify(event)) throw new Error("The runtime reused an event ID with different data.");
    events.set(event.event_id, event);
  }
  const result = [...events.values()];
  const sequence = (event: RunEvent) => event.details?.["recorded_sequence"];
  if (result.every(event => Number.isSafeInteger(sequence(event)))) {
    const unique = new Set(result.map(sequence));
    if (unique.size !== result.length) throw new Error("The runtime reused an event sequence.");
    result.sort((a, b) => Number(sequence(a)) - Number(sequence(b)));
  }
  // Legacy responses already arrive in database sequence order. Equal/skewed
  // timestamps must never reorder causal events or manufacture completion.
  return result;
}
export function assertWorkflowReferences(workflow: CanonicalWorkflow) {
  const nodes = new Set(workflow.nodes.map((n) => n.node_id));
  if (nodes.size !== workflow.nodes.length) throw new Error("Workflow nodes must have unique identifiers.");
  for (const edge of workflow.edges) {
    if (!nodes.has(edge.source) || !nodes.has(edge.target)) throw new Error("An edge references a missing workflow node.");
    const source = workflow.nodes.find((n) => n.node_id === edge.source);
    if (source?.kind === "condition") {
      const condition = workflow.conditions.find((c) => c.condition_id === source.condition_id);
      if (!condition || !edge.outcome || !condition.outcomes.includes(edge.outcome)) throw new Error("A branch has an unmatched condition outcome.");
    }
  }
  for (const node of workflow.nodes) {
    if (node.kind === "agent" && !workflow.agents.some((a) => a.agent_id === node.agent_id)) throw new Error("An agent node references a missing definition.");
    if (node.kind === "tool" && !workflow.tools.some((t) => t.tool_id === node.tool_id)) throw new Error("A tool node references a missing tool requirement.");
    if (node.kind === "condition" && !workflow.conditions.some((c) => c.condition_id === node.condition_id)) throw new Error("A condition definition is missing.");
    if (node.kind === "approval" && !workflow.approval_gates.some((g) => g.approval_gate_id === node.approval_gate_id)) throw new Error("An approval policy is missing.");
  }
}
