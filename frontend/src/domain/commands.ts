// Transparent simulation layer for natural-language graph edits.
// Supports a defined set of commands; unknown input returns ok: false with guidance.
import { uid } from "./ids";
import { autoLayout } from "./layout";
import type { NodeKind, WorkflowEdge, WorkflowNode } from "./types";

export interface Graph {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}

export type CommandResult = { ok: true; graph: Graph; message: string } | { ok: false; message: string };

export const SUPPORTED_COMMANDS = [
  "Add human approval before sending emails",
  "Add a validation step after customer lookup",
  "Notify the team in Slack at the end",
  "Remove create ticket",
];

function findNode(nodes: WorkflowNode[], phrase: string): WorkflowNode | undefined {
  const p = phrase.toLowerCase().trim();
  if (!p) return undefined;
  const words = p.split(/\s+/).filter((w) => w.length > 2);
  const emailLike = /email|send|repl|respon/.test(p);
  return (
    nodes.find((n) => n.data.label.toLowerCase() === p) ??
    nodes.find((n) => n.data.label.toLowerCase().includes(p)) ??
    (emailLike ? nodes.find((n) => n.data.tool === "Email send" && n.data.kind !== "agent") ?? nodes.find((n) => /send/i.test(n.data.label)) : undefined) ??
    nodes.find((n) => words.some((w) => n.data.label.toLowerCase().includes(w.replace(/s$/, ""))))
  );
}

function newNode(kind: NodeKind, label: string, description: string, tool?: string): WorkflowNode {
  return { id: uid("node"), type: "mesh", position: { x: 0, y: 0 }, data: { label, kind, description, tool } };
}

export function insertBefore(g: Graph, targetId: string, node: WorkflowNode): Graph {
  const incoming = g.edges.filter((e) => e.target === targetId);
  const edges = g.edges
    .filter((e) => e.target !== targetId)
    .concat(incoming.map((e) => ({ ...e, id: uid("edge"), target: node.id })))
    .concat([{ id: uid("edge"), source: node.id, target: targetId }]);
  const nodes = [...g.nodes, node];
  return { nodes: autoLayout(nodes, edges), edges };
}

export function insertAfter(g: Graph, sourceId: string, node: WorkflowNode): Graph {
  const outgoing = g.edges.filter((e) => e.source === sourceId);
  const edges = g.edges
    .filter((e) => e.source !== sourceId)
    .concat([{ id: uid("edge"), source: sourceId, target: node.id }])
    .concat(outgoing.map((e) => ({ ...e, id: uid("edge"), source: node.id })));
  const nodes = [...g.nodes, node];
  return { nodes: autoLayout(nodes, edges), edges };
}

export function removeNode(g: Graph, id: string): Graph {
  const incoming = g.edges.filter((e) => e.target === id);
  const outgoing = g.edges.filter((e) => e.source === id);
  const bridged: WorkflowEdge[] = [];
  incoming.forEach((i) => outgoing.forEach((o) => bridged.push({ id: uid("edge"), source: i.source, target: o.target, label: i.label })));
  const edges = g.edges.filter((e) => e.source !== id && e.target !== id).concat(bridged);
  const nodes = g.nodes.filter((n) => n.id !== id);
  return { nodes: autoLayout(nodes, edges), edges };
}

export function applyCommand(g: Graph, raw: string): CommandResult {
  const text = raw.trim();
  let m: RegExpMatchArray | null;

  if ((m = text.match(/add (?:a |an )?(?:human )?approval(?: step| gate)? before (.+)/i))) {
    const target = findNode(g.nodes, m[1]!);
    if (!target) return { ok: false, message: `Couldn't find a step matching "${m[1]}".` };
    const node = newNode("approval", "Human approval", `Review before ${target.data.label.toLowerCase()}`);
    return { ok: true, graph: insertBefore(g, target.id, node), message: `Added human approval before "${target.data.label}".` };
  }

  if ((m = text.match(/add (?:a |an )?(?:validation|validate|check)(?: step)? after (.+)/i))) {
    const src = findNode(g.nodes, m[1]!);
    if (!src) return { ok: false, message: `Couldn't find a step matching "${m[1]}".` };
    const node = newNode("transform", "Validate data", `Validate output of ${src.data.label.toLowerCase()}`);
    return { ok: true, graph: insertAfter(g, src.id, node), message: `Added validation after "${src.data.label}".` };
  }

  if (/slack|notify/i.test(text)) {
    const outputs = g.nodes.filter((n) => n.data.kind === "output");
    const target = outputs[0];
    if (!target) return { ok: false, message: "This workflow has no output step to notify after." };
    const node = newNode("tool", "Slack notification", "Post summary to team channel", "Slack notify");
    return { ok: true, graph: insertBefore(g, target.id, node), message: `Added a Slack notification before "${target.data.label}".` };
  }

  if ((m = text.match(/(?:remove|delete) (?:the )?(.+)/i))) {
    const target = findNode(g.nodes, m[1]!);
    if (!target) return { ok: false, message: `Couldn't find a step matching "${m[1]}".` };
    if (target.data.kind === "trigger") return { ok: false, message: "The trigger can't be removed — every workflow needs a start." };
    return { ok: true, graph: removeNode(g, target.id), message: `Removed "${target.data.label}" and reconnected its neighbours.` };
  }

  return { ok: false, message: `Use one of the supported local editing commands, e.g. "${SUPPORTED_COMMANDS[0]}".` };
}
