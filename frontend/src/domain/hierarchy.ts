// Master → sub-agent orchestration planning. Deterministic keyword planning, no live LLM.
import dagre from "@dagrejs/dagre";
import { uid } from "./ids";
import { NODE_H, NODE_W } from "./layout";
import { makeAgent } from "./templates";
import type { Agent, Workflow, WorkflowEdge, WorkflowNode } from "./types";

interface ChildSpec { key: string; match: RegExp; name: string; label: string; purpose: string; modelId: string; tools: string[]; task?: { kind: "tool" | "approval"; label: string; tool?: string } }

const CHILDREN: ChildSpec[] = [
  { key: "research", match: /research|collect|gather|look ?up|investigat/i, name: "Research Agent", label: "Research", purpose: "Collects complaint, account and context details.", modelId: "gemini-2-5-flash", tools: ["CRM lookup"], task: { kind: "tool", label: "Customer lookup", tool: "CRM lookup" } },
  { key: "extract", match: /extract|parse|read (the )?invoice|capture/i, name: "Extraction Agent", label: "Extraction", purpose: "Extracts structured fields from incoming documents.", modelId: "gemini-2-5-flash", tools: ["Document parser"], task: { kind: "tool", label: "Parse document", tool: "Document parser" } },
  { key: "analysis", match: /analy[sz]|classif|assess|severity|triage|score/i, name: "Analysis Agent", label: "Analysis", purpose: "Classifies severity, intent and priority.", modelId: "claude-haiku-4-5", tools: [] },
  { key: "validate", match: /validat|reconcil|match|verify|check against/i, name: "Validation Agent", label: "Validation", purpose: "Validates records against the system of record.", modelId: "gpt-5-mini", tools: ["ERP ledger"], task: { kind: "tool", label: "Ledger check", tool: "ERP ledger" } },
  { key: "risk", match: /fraud|risk|complian|anomal/i, name: "Risk Agent", label: "Risk review", purpose: "Flags fraud, compliance and anomaly signals.", modelId: "claude-sonnet-4-5", tools: [] },
  { key: "response", match: /draft|respon|reply|write|compose/i, name: "Response Agent", label: "Response drafting", purpose: "Drafts an on-brand reply.", modelId: "claude-sonnet-4-5", tools: ["Ticketing"], task: { kind: "tool", label: "Update ticket", tool: "Ticketing" } },
  { key: "schedule", match: /schedul|book|meeting|calendar/i, name: "Scheduling Agent", label: "Scheduling", purpose: "Schedules follow-ups and meetings.", modelId: "gpt-5-mini", tools: ["Calendar"], task: { kind: "tool", label: "Book slot", tool: "Calendar" } },
  { key: "escalate", match: /escalat|approv|critical|large|manager/i, name: "Escalation Agent", label: "Escalation", purpose: "Requests human approval when required.", modelId: "gpt-5-mini", tools: [], task: { kind: "approval", label: "Human approval" } },
];

const DOMAINS: { match: RegExp; name: string; master: string; output: string; tool?: string }[] = [
  { match: /complain|support|ticket|customer/i, name: "Customer support orchestration", master: "Customer Support Orchestrator", output: "Send response", tool: "Email send" },
  { match: /invoice|payment|finance|purchase order|vendor/i, name: "Invoice processing supervisor", master: "Finance Operations Orchestrator", output: "Post to ledger" },
  { match: /lead|sales|prospect|pipeline/i, name: "Sales pipeline orchestration", master: "Sales Pipeline Orchestrator", output: "Update CRM" },
];

export function planChildren(prompt: string): ChildSpec[] {
  const picked = CHILDREN.filter((c) => c.match.test(prompt));
  if (picked.length >= 2) return picked;
  const fallback = CHILDREN.filter((c) => c.key === "research" || c.key === "analysis" || c.key === "response");
  return [...picked, ...fallback.filter((f) => !picked.includes(f))].slice(0, Math.max(3, picked.length));
}

/** Top-to-bottom layout used for hierarchy workflows. */
export function layoutTB(nodes: WorkflowNode[], edges: WorkflowEdge[]): WorkflowNode[] {
  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: "TB", nodesep: 36, ranksep: 70 });
  g.setDefaultEdgeLabel(() => ({}));
  nodes.forEach((n) => g.setNode(n.id, { width: NODE_W, height: NODE_H }));
  edges.forEach((e) => g.setEdge(e.source, e.target));
  dagre.layout(g);
  return nodes.map((n) => {
    const p = g.node(n.id);
    return p ? { ...n, position: { x: p.x - NODE_W / 2, y: p.y - NODE_H / 2 } } : n;
  });
}

export const isHierarchy = (nodes: WorkflowNode[]) => nodes.some((n) => n.data.role === "master" && n.data.orientation === "tb");

export function planHierarchy(prompt: string, workspaceId = "ws_default"): { workflow: Workflow; agents: Agent[] } {
  const domain = DOMAINS.find((d) => d.match.test(prompt)) ?? { name: "Process orchestration", master: "Process Orchestrator", output: "Deliver result", tool: undefined };
  const kids = planChildren(prompt);
  const agents: Agent[] = [];
  const master = makeAgent({ name: domain.master, role: "Master agent", purpose: "Plans the work, delegates to sub-agents and combines their results.", instructions: `Break the request into tasks and delegate to: ${kids.map((k) => k.name).join(", ")}. Combine results into one outcome.`, modelId: "claude-sonnet-4-5", tools: [], knowledge: [] }, workspaceId);
  agents.push(master);
  const tb = "tb" as const;
  const trigger: WorkflowNode = { id: uid("node"), type: "mesh", position: { x: 0, y: 0 }, data: { kind: "trigger", label: "Request received", description: "Incoming item starts the run", orientation: tb } };
  const masterNode: WorkflowNode = { id: uid("node"), type: "mesh", position: { x: 0, y: 0 }, data: { kind: "agent", label: domain.master, description: "Delegates and combines", agentId: master.id, role: "master", orientation: tb } };
  const combine: WorkflowNode = { id: uid("node"), type: "mesh", position: { x: 0, y: 0 }, data: { kind: "transform", label: "Combined result", description: "Merges sub-agent outputs", combine: true, orientation: tb } };
  const output: WorkflowNode = { id: uid("node"), type: "mesh", position: { x: 0, y: 0 }, data: { kind: "output", label: domain.output, description: "Final outcome delivered", tool: domain.tool, orientation: tb } };
  const nodes: WorkflowNode[] = [trigger, masterNode];
  const edges: WorkflowEdge[] = [{ id: uid("edge"), source: trigger.id, target: masterNode.id }];
  for (const k of kids) {
    const a = makeAgent({ name: k.name, role: "Sub-agent", purpose: k.purpose, instructions: `${k.purpose} Report results to ${domain.master}.`, modelId: k.modelId, tools: k.tools, knowledge: [] }, workspaceId);
    a.parentAgentId = master.id;
    agents.push(a);
    const sub: WorkflowNode = { id: uid("node"), type: "mesh", position: { x: 0, y: 0 }, data: { kind: "agent", label: k.name, description: k.purpose, agentId: a.id, role: "sub", parentNodeId: masterNode.id, orientation: tb } };
    nodes.push(sub);
    edges.push({ id: uid("edge"), source: masterNode.id, target: sub.id });
    let last = sub.id;
    if (k.task) {
      const t: WorkflowNode = { id: uid("node"), type: "mesh", position: { x: 0, y: 0 }, data: { kind: k.task.kind, label: k.task.label, description: k.task.kind === "approval" ? "Only critical cases need sign-off" : `${k.task.tool} (demo connector)`, tool: k.task.tool, parentNodeId: sub.id, orientation: tb, onlyCritical: k.task.kind === "approval" ? true : undefined } };
      nodes.push(t);
      edges.push({ id: uid("edge"), source: sub.id, target: t.id });
      last = t.id;
    }
    edges.push({ id: uid("edge"), source: last, target: combine.id });
  }
  nodes.push(combine, output);
  edges.push({ id: uid("edge"), source: combine.id, target: output.id });
  const now = new Date().toISOString();
  return {
    agents,
    workflow: { id: uid("wf"), workspaceId, name: domain.name, description: prompt, prompt, scenario: "hierarchy", status: "draft", nodes: layoutTB(nodes, edges), edges, versions: [], createdAt: now, updatedAt: now },
  };
}

/** Node ids under `id` in the hierarchy (via parentNodeId). */
export function descendants(nodes: WorkflowNode[], id: string): string[] {
  const out: string[] = [];
  const walk = (pid: string) => nodes.filter((n) => n.data.parentNodeId === pid).forEach((n) => { if (!out.includes(n.id)) { out.push(n.id); walk(n.id); } });
  walk(id);
  return out;
}

export function depthOf(nodes: WorkflowNode[], id: string): number {
  let d = 0;
  let cur = nodes.find((n) => n.id === id);
  while (cur?.data.parentNodeId && d < 20) { d++; cur = nodes.find((n) => n.id === cur!.data.parentNodeId); }
  return d;
}

/** Ids hidden because an ancestor is collapsed. */
export function hiddenIds(nodes: WorkflowNode[]): Set<string> {
  const hidden = new Set<string>();
  nodes.filter((n) => n.data.collapsed).forEach((n) => descendants(nodes, n.id).forEach((d) => hidden.add(d)));
  return hidden;
}

export interface AddSubResult { ok: true; nodes: WorkflowNode[]; edges: WorkflowEdge[]; agent: Agent } 
export type AddSubOutcome = AddSubResult | { ok: false; reason: string };

/** Adds a child agent under `parentId`, enforcing depth, children and agents-per-workflow limits. */
export function addSubAgent(
  graph: { nodes: WorkflowNode[]; edges: WorkflowEdge[] },
  parentId: string,
  limits: { maxDepth: number; maxChildren: number; maxAgents: number },
  parentAgentId: string | undefined,
  workspaceId = "ws_default",
): AddSubOutcome {
  const parent = graph.nodes.find((n) => n.id === parentId);
  if (!parent || parent.data.kind !== "agent") return { ok: false, reason: "Sub-agents can only be added under an agent." };
  const depth = depthOf(graph.nodes, parentId) + 1;
  if (depth > limits.maxDepth) return { ok: false, reason: `Max sub-agent depth is ${limits.maxDepth}; this would be level ${depth}.` };
  const children = graph.nodes.filter((n) => n.data.parentNodeId === parentId && n.data.kind === "agent").length;
  if (children >= limits.maxChildren) return { ok: false, reason: `This agent already has ${children} sub-agents (limit ${limits.maxChildren}).` };
  const agentCount = graph.nodes.filter((n) => n.data.kind === "agent").length;
  if (agentCount >= limits.maxAgents) return { ok: false, reason: `Workflow already has ${agentCount} agents (limit ${limits.maxAgents}).` };
  const a = makeAgent({ name: `Sub-agent ${children + 1}`, role: "Sub-agent", purpose: "Describe the delegated task.", instructions: "", modelId: "gpt-5-mini", tools: [], knowledge: [] }, workspaceId);
  a.parentAgentId = parentAgentId;
  const node: WorkflowNode = {
    id: uid("node"), type: "mesh",
    position: { x: parent.position.x + children * 40, y: parent.position.y + 170 },
    data: { kind: "agent", label: a.name, description: a.purpose, agentId: a.id, role: "sub", parentNodeId: parentId, orientation: parent.data.orientation },
  };
  const combine = graph.nodes.find((n) => n.data.combine) ?? graph.nodes.find((n) => n.data.kind === "output");
  const edges = [...graph.edges, { id: uid("edge"), source: parentId, target: node.id }];
  if (combine) edges.push({ id: uid("edge"), source: node.id, target: combine.id });
  const parentNodes = graph.nodes.map((n) => (n.id === parentId && !n.data.role ? { ...n, data: { ...n.data, role: "master" as const } } : n));
  return { ok: true, nodes: [...parentNodes, node], edges, agent: a };
}

/** Removes a node and its hierarchy subtree. */
export function removeSubtree(graph: { nodes: WorkflowNode[]; edges: WorkflowEdge[] }, id: string) {
  const gone = new Set([id, ...descendants(graph.nodes, id)]);
  return { nodes: graph.nodes.filter((n) => !gone.has(n.id)), edges: graph.edges.filter((e) => !gone.has(e.source) && !gone.has(e.target)), removed: gone.size };
}
