// Ready-made workflow patterns that can be dropped onto the canvas.
import { uid } from "./ids";
import { makeAgent } from "./templates";
import type { Agent, NodeKind, WorkflowEdge, WorkflowNode, WorkflowNodeData } from "./types";

export type PatternKind = "sequential" | "parallel" | "conditional" | "approval" | "supervisor";

export const PATTERNS: { id: PatternKind; name: string; description: string }[] = [
  { id: "sequential", name: "Sequential", description: "Agent → Agent → Output" },
  { id: "parallel", name: "Parallel", description: "Split → agents in parallel → Merge" },
  { id: "conditional", name: "Conditional", description: "Decision → critical / standard branches" },
  { id: "approval", name: "Human approval", description: "Agent → Approval → Action" },
  { id: "supervisor", name: "Supervisor", description: "Master → sub-agents → Combined result" },
];

interface P { key: string; kind: NodeKind; label: string; dx: number; dy: number; agent?: string; extra?: Partial<WorkflowNodeData> }

const SPECS: Record<PatternKind, { nodes: P[]; edges: [string, string, string?][] }> = {
  sequential: {
    nodes: [
      { key: "a", kind: "agent", label: "First agent", dx: 0, dy: 0, agent: "Step Agent A" },
      { key: "b", kind: "agent", label: "Second agent", dx: 300, dy: 0, agent: "Step Agent B" },
      { key: "o", kind: "output", label: "Output", dx: 600, dy: 0 },
    ],
    edges: [["a", "b"], ["b", "o"]],
  },
  parallel: {
    nodes: [
      { key: "s", kind: "transform", label: "Split work", dx: 0, dy: 120 },
      { key: "a", kind: "agent", label: "Parallel task A", dx: 300, dy: 0, agent: "Parallel Agent A" },
      { key: "b", kind: "agent", label: "Parallel task B", dx: 300, dy: 120, agent: "Parallel Agent B" },
      { key: "c", kind: "agent", label: "Parallel task C", dx: 300, dy: 240, agent: "Parallel Agent C" },
      { key: "m", kind: "transform", label: "Merge results", dx: 600, dy: 120, extra: { combine: true } },
    ],
    edges: [["s", "a"], ["s", "b"], ["s", "c"], ["a", "m"], ["b", "m"], ["c", "m"]],
  },
  conditional: {
    nodes: [
      { key: "d", kind: "condition", label: "Decision", dx: 0, dy: 70 },
      { key: "c", kind: "agent", label: "Critical path", dx: 300, dy: 0, agent: "Critical Handler" },
      { key: "s", kind: "agent", label: "Standard path", dx: 300, dy: 140, agent: "Standard Handler" },
    ],
    edges: [["d", "c", "critical"], ["d", "s", "standard"]],
  },
  approval: {
    nodes: [
      { key: "a", kind: "agent", label: "Prepare action", dx: 0, dy: 0, agent: "Action Preparer" },
      { key: "p", kind: "approval", label: "Human approval", dx: 300, dy: 0 },
      { key: "t", kind: "tool", label: "Perform action", dx: 600, dy: 0, extra: { tool: "Email send" } },
    ],
    edges: [["a", "p"], ["p", "t"]],
  },
  supervisor: {
    nodes: [
      { key: "m", kind: "agent", label: "Master agent", dx: 0, dy: 120, agent: "Supervisor Agent", extra: { role: "master" } },
      { key: "a", kind: "agent", label: "Sub-agent A", dx: 300, dy: 0, agent: "Sub-agent A", extra: { role: "sub" } },
      { key: "b", kind: "agent", label: "Sub-agent B", dx: 300, dy: 120, agent: "Sub-agent B", extra: { role: "sub" } },
      { key: "c", kind: "agent", label: "Sub-agent C", dx: 300, dy: 240, agent: "Sub-agent C", extra: { role: "sub" } },
      { key: "r", kind: "transform", label: "Combined result", dx: 600, dy: 120, extra: { combine: true } },
    ],
    edges: [["m", "a"], ["m", "b"], ["m", "c"], ["a", "r"], ["b", "r"], ["c", "r"]],
  },
};

/** Creates connected nodes (and new agents) for a pattern at a canvas position. */
export function insertPattern(kind: PatternKind, at: { x: number; y: number }, workspaceId = "ws_default"): { nodes: WorkflowNode[]; edges: WorkflowEdge[]; agents: Agent[] } {
  const spec = SPECS[kind];
  const ids: Record<string, string> = {};
  const agents: Agent[] = [];
  const agentByKey: Record<string, Agent> = {};
  spec.nodes.forEach((p) => { ids[p.key] = uid("node"); });
  const masterKey = spec.nodes.find((p) => p.extra?.role === "master")?.key;
  const nodes: WorkflowNode[] = spec.nodes.map((p) => {
    let agentId: string | undefined;
    if (p.agent) {
      const a = makeAgent({ name: p.agent, role: p.extra?.role === "master" ? "Master agent" : p.extra?.role === "sub" ? "Sub-agent" : "Assistant", purpose: p.label, instructions: "", modelId: "gpt-5-mini", tools: [], knowledge: [] }, workspaceId);
      agents.push(a);
      agentByKey[p.key] = a;
      agentId = a.id;
    }
    return { id: ids[p.key]!, type: "mesh", position: { x: at.x + p.dx, y: at.y + p.dy }, data: { kind: p.kind, label: p.label, description: "", agentId, ...p.extra, ...(p.extra?.role === "sub" && masterKey ? { parentNodeId: ids[masterKey] } : {}) } };
  });
  if (masterKey) agents.forEach((a) => { if (a !== agentByKey[masterKey] && a.role === "Sub-agent") a.parentAgentId = agentByKey[masterKey]!.id; });
  const edges: WorkflowEdge[] = spec.edges.map(([a, b, label]) => ({ id: uid("edge"), source: ids[a]!, target: ids[b]!, label }));
  return { nodes, edges, agents };
}
