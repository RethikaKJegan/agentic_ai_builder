import type { WorkflowNode, WorkflowEdge } from "./types";
export type GraphIssue = { nodeId?: string; message: string };
/** Stable topological order; cyclic/unreachable leftovers stay visible for repair. */
export function dependencyOrder(nodes: WorkflowNode[], edges: WorkflowEdge[]) {
  const ids = new Set(nodes.map((n) => n.id));
  const degree = new Map(nodes.map((n) => [n.id, 0]));
  edges.forEach((e) => {
    if (ids.has(e.source) && ids.has(e.target)) degree.set(e.target, degree.get(e.target)! + 1);
  });
  const ready = nodes.filter((n) => degree.get(n.id) === 0);
  const result: WorkflowNode[] = [];
  while (ready.length) {
    const n = ready.shift()!;
    result.push(n);
    for (const e of edges.filter((e) => e.source === n.id && ids.has(e.target))) {
      degree.set(e.target, degree.get(e.target)! - 1);
      if (degree.get(e.target) === 0) ready.push(nodes.find((x) => x.id === e.target)!);
    }
  }
  return [...result, ...nodes.filter((n) => !result.some((x) => x.id === n.id))];
}
export function graphIssues(nodes: WorkflowNode[], edges: WorkflowEdge[]): GraphIssue[] {
  const issues: GraphIssue[] = [];
  const ids = new Set(nodes.map((n) => n.id));
  if (ids.size !== nodes.length) issues.push({ message: "Duplicate node identifiers." });
  if (nodes.filter((n) => n.data.kind === "trigger").length !== 1)
    issues.push({ message: "Design requires exactly one start trigger." });
  if (!nodes.some((n) => n.data.kind === "output"))
    issues.push({ message: "Add an output to identify the end state." });
  edges.forEach((e) => {
    if (!ids.has(e.source) || !ids.has(e.target))
      issues.push({ message: `Connection ${e.id} references a missing step.` });
  });
  const reached = new Set(nodes.filter((n) => n.data.kind === "trigger").map((n) => n.id));
  for (let i = 0; i < nodes.length; i++)
    edges.forEach((e) => {
      if (reached.has(e.source) && ids.has(e.target)) reached.add(e.target);
    });
  for (const n of nodes) {
    if (!reached.has(n.id))
      issues.push({
        nodeId: n.id,
        message: `${n.data.label}: disconnected from the start trigger.`,
      });
    if (n.data.kind !== "output" && !edges.some((e) => e.source === n.id))
      issues.push({
        nodeId: n.id,
        message: `${n.data.label}: connect a successor or use an output end state.`,
      });
    const outcomes =
      n.data.kind === "condition"
        ? ((n.data["condition"] as { outcomes?: string[] } | undefined)?.outcomes ?? [])
        : n.data.kind === "approval"
          ? ["approved", "rejected"]
          : [];
    if (n.data.kind === "condition" && !outcomes.length)
      issues.push({ nodeId: n.id, message: `${n.data.label}: declare condition outcomes.` });
    for (const outcome of outcomes) {
      if (!edges.some((e) => e.source === n.id && e.label === outcome)) {
        // A rejection with on_reject=stop intentionally has no outgoing edge.
        if (
          n.data.kind === "approval" &&
          outcome === "rejected" &&
          (n.data["approval"] as { on_reject?: string } | undefined)?.on_reject !== "branch"
        )
          continue;
        issues.push({ nodeId: n.id, message: `${n.data.label}: missing ${outcome} branch.` });
      }
    }
    if (n.data.kind === "condition")
      edges
        .filter((e) => e.source === n.id)
        .forEach((e) => {
          if (!e.label || !outcomes.includes(e.label))
            issues.push({
              nodeId: n.id,
              message: `${n.data.label}: unmatched branch ${e.label || "(unlabeled)"}.`,
            });
        });
  }
  const visiting = new Set<string>(),
    done = new Set<string>();
  const visit = (id: string): boolean => {
    if (visiting.has(id)) return true;
    if (done.has(id)) return false;
    visiting.add(id);
    const cycle = edges
      .filter((e) => e.source === id && ids.has(e.target))
      .some((e) => visit(e.target));
    visiting.delete(id);
    done.add(id);
    return cycle;
  };
  if (nodes.some((n) => visit(n.id)))
    issues.push({
      message: "A directed cycle is present. Runtime v1 requires an acyclic execution graph.",
    });
  return issues;
}
