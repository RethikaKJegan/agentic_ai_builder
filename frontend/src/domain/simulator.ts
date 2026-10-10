// Deterministic run simulator. Walks the graph from triggers, following condition
// branches, pausing at approvals without a decision. Re-running with decisions resumes.
import { getModel } from "./models";
import type { Agent, NodeKind, RunStatus, RunStep, Workflow } from "./types";
import { checkAgentExecution, checkRunStart, SENSITIVE_TOOLS, type AgentControls, type EffectivePolicy, type Usage } from "./governance";

export interface ControlContext { controls: AgentControls; usage: Usage }

export const CRITICAL_PATTERN = /critical|urgent|lawsuit|legal|furious|unacceptable|cancel|over \$?10,?000|\$\d{2},\d{3}|high[- ]fit|enterprise/i;
export const INJECTION_PATTERN = /ignore (all |previous |prior )?instructions|system prompt|jailbreak/i;
export const FAIL_PATTERN = /#fail/i;

export interface SimResult {
  status: RunStatus;
  steps: RunStep[];
  branch: "critical" | "standard";
}

function hash(s: string) {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return Math.abs(h);
}

const baseLatency: Record<NodeKind, number> = { trigger: 40, agent: 1400, tool: 320, condition: 25, approval: 0, transform: 60, output: 260 };

export function simulateRun(
  wf: Pick<Workflow, "nodes" | "edges">,
  agents: Agent[],
  input: string,
  decisions: Record<string, "approved" | "rejected"> = {},
  policy?: EffectivePolicy,
  ctx?: ControlContext,
): SimResult {
  let spent = 0;
  const nodeById = new Map(wf.nodes.map((n) => [n.id, n]));
  const depthOf = (id: string) => {
    let d = 0;
    let cur = nodeById.get(id);
    while (cur?.data.parentNodeId && d < 20) { d++; cur = nodeById.get(cur.data.parentNodeId); }
    return d;
  };
  if (ctx) {
    const agentCount = wf.nodes.filter((n) => n.data.kind === "agent").length;
    const b = checkRunStart({ controls: ctx.controls, agentCount, runsToday: ctx.usage.runsToday });
    if (b) {
      const first = wf.nodes.find((n) => n.data.kind === "trigger") ?? wf.nodes[0];
      return { status: "blocked", branch: "standard", steps: first ? [{ nodeId: first.id, label: first.data.label, kind: first.data.kind, status: "blocked", output: "Run not started.", latencyMs: 0, tokens: 0, cost: 0, guardrail: `Control: ${b.reason}`, control: b.control }] : [] };
    }
  }
  const agentSpent: Record<string, number> = { ...(ctx?.usage.agentSpend ?? {}) };
  const branch: "critical" | "standard" = CRITICAL_PATTERN.test(input) ? "critical" : "standard";
  const injection = INJECTION_PATTERN.test(input);
  const forceFail = FAIL_PATTERN.test(input);
  const hasIncoming = new Set(wf.edges.map((e) => e.target));
  const queue = wf.nodes.filter((n) => !hasIncoming.has(n.id)).map((n) => n.id);
  const visited = new Set<string>();
  const steps: RunStep[] = [];
  let failedOnce = false;
  let deferrals = 0;
  const preds = (id: string) => wf.edges.filter((e) => e.target === id).map((e) => e.source);
  const reachable = (from: string, to: string, avoid: string) => {
    const seen = new Set<string>([avoid]);
    const stack = [from];
    while (stack.length) {
      const x = stack.pop()!;
      if (x === to) return true;
      if (seen.has(x)) continue;
      seen.add(x);
      wf.edges.filter((e) => e.source === x).forEach((e) => stack.push(e.target));
    }
    return false;
  };
  const waitsOnPending = (id: string) =>
    preds(id).some((p) => !visited.has(p) && queue.some((q) => q !== id && !visited.has(q) && reachable(q, p, id)));

  while (queue.length) {
    const id = queue.shift()!;
    if (visited.has(id)) continue;
    // Join: wait while an unvisited predecessor is still reachable from pending work.
    if (deferrals < 500 && waitsOnPending(id)) { deferrals++; queue.push(id); continue; }
    visited.add(id);
    const node = nodeById.get(id);
    if (!node) continue;
    const { kind, label } = node.data;
    const parent = node.data.parentNodeId ? nodeById.get(node.data.parentNodeId) : undefined;
    const sensitiveTool = (kind === "tool" || kind === "output") && node.data.tool && SENSITIVE_TOOLS.includes(node.data.tool) ? node.data.tool : undefined;
    const nodeAgent = kind === "agent" ? agents.find((a) => a.id === node.data.agentId) : undefined;
    const agentSensitive = nodeAgent?.requireApproval || (ctx?.controls.approvalForSensitive && nodeAgent?.tools.some((t) => SENSITIVE_TOOLS.includes(t)));
    if ((ctx?.controls.approvalForSensitive && sensitiveTool) || agentSensitive) {
      const d = decisions[id];
      const what = sensitiveTool ?? `${nodeAgent?.name} actions`;
      const gate: RunStep = { nodeId: id, label: `Approval · ${label}`, kind: "approval", status: d ?? "paused", output: d ? (d === "approved" ? "Sensitive action approved by reviewer" : "Sensitive action rejected") : `Approval required before ${what}`, latencyMs: 0, tokens: 0, cost: 0, control: "Require approval for sensitive actions" };
      steps.push(gate);
      if (!d) return { status: "paused", steps, branch };
      if (d === "rejected") return { status: "rejected", steps, branch };
    }
    const seed = hash(id + input);
    const step: RunStep = { nodeId: id, label, kind, status: "success", output: "", latencyMs: Math.round(baseLatency[kind] * (0.8 + (seed % 40) / 100)), tokens: 0, cost: 0, delegatedBy: parent?.data.label };

    if (kind === "agent") {
      const agent = agents.find((a) => a.id === node.data.agentId);
      const model = getModel(agent?.modelId ?? "gpt-5-mini");
      step.modelId = model.id;
      step.tokens = 600 + (seed % 900);
      step.latencyMs = Math.round(step.latencyMs * model.speed);
      step.cost = +((step.tokens / 1000) * model.costPer1k).toFixed(4);
      step.agentId = agent?.id;
      if (ctx) {
        const b = checkAgentExecution({ agent, agents, controls: ctx.controls, modelId: model.id, depth: depthOf(id), projectedSpend: ctx.usage.spendToday + spent + step.cost, stepCost: step.cost, agentSpent: agent ? agentSpent[agent.id] ?? 0 : 0 });
        if (b) {
          step.status = "blocked";
          step.tokens = 0;
          step.cost = 0;
          step.guardrail = `Control: ${b.reason}`;
          step.control = b.control;
          step.output = "Execution blocked by agent controls before model call.";
          steps.push(step);
          return { status: "blocked", steps, branch };
        }
        if (agent) agentSpent[agent.id] = (agentSpent[agent.id] ?? 0) + step.cost;
      }
      if (policy?.blockedModels.includes(model.id)) {
        step.status = "blocked";
        step.tokens = 0;
        step.cost = 0;
        step.guardrail = `Policy: ${model.name} is not allowed in this workspace`;
        step.output = "Execution blocked by policy before model call.";
        steps.push(step);
        return { status: "blocked", steps, branch };
      }
      if (injection && ((agent?.guardrails.injectionDetection ?? true) || policy?.guardrails.injectionDetection)) {
        step.status = "blocked";
        step.guardrail = "Prompt-injection pattern detected in input";
        step.output = "Execution blocked by guardrail before model call.";
        steps.push(step);
        return { status: "blocked", steps, branch };
      }
      if ((agent?.guardrails.piiRedaction || policy?.guardrails.piiRedaction) && /\b[\w.]+@[\w.]+\.\w+\b|\b\d{3}[- ]\d{3}[- ]\d{4}\b/.test(input)) {
        step.guardrail = "PII redacted from prompt (simulated)";
      }
      const kids = wf.nodes.filter((n) => n.data.parentNodeId === id && n.data.kind === "agent");
      step.output = node.data.role === "master" && kids.length
        ? `Delegated ${kids.length} tasks: ${kids.map((k) => k.data.label).join(", ")}`
        : branch === "critical" && /analy|classif|audit|research/i.test(label)
        ? "Severity: critical · sentiment: negative · escalation recommended"
        : `${agent?.name ?? "Agent"} completed: ${node.data.description ?? "task done"}`;
      if (parent) step.output = `${step.output} → returned to ${parent.data.label}`;
    } else if (kind === "tool") {
      if ((forceFail || node.data.simulateFailure) && !failedOnce) {
        failedOnce = true;
        step.status = "failed";
        step.output = `${node.data.tool ?? "Tool"} returned 503 (simulated outage)`;
        steps.push(step);
        return { status: "failed", steps, branch };
      }
      step.output = `${node.data.tool ?? "Tool"}: ok`;
    } else if (kind === "condition") {
      step.output = `Branch → ${branch}`;
    } else if (kind === "approval" && node.data.onlyCritical && branch === "standard") {
      step.status = "skipped";
      step.output = "Approval not required for a standard case";
    } else if (kind === "approval") {
      const d = decisions[id];
      if (!d) {
        step.status = "paused";
        step.output = "Waiting for human approval";
        steps.push(step);
        return { status: "paused", steps, branch };
      }
      step.status = d;
      step.output = d === "approved" ? "Approved by reviewer" : "Rejected by reviewer";
      if (d === "rejected") {
        steps.push(step);
        return { status: "rejected", steps, branch };
      }
    } else if (node.data.combine) {
      const results = steps.filter((x) => x.delegatedBy && x.kind === "agent").length;
      step.output = `Combined ${results} sub-agent results`;
    } else if (kind === "output") {
      step.output = node.data.description ?? "Delivered";
    } else {
      step.output = node.data.description ?? "Done";
    }
    spent += step.cost;
    if (policy?.maxRunCost != null && spent > policy.maxRunCost) {
      step.status = "blocked";
      step.guardrail = `Policy: run cost cap $${policy.maxRunCost} exceeded`;
      steps.push(step);
      return { status: "blocked", steps, branch };
    }
    steps.push(step);

    const out = wf.edges.filter((e) => e.source === id);
    const next = kind === "condition" ? out.filter((e) => !e.label || e.label === branch) : out;
    const chosen = kind === "condition" && next.length === 0 ? out.slice(0, 1) : next;
    chosen.forEach((e) => queue.push(e.target));
  }
  return { status: "completed", steps, branch };
}

export function runTotals(steps: RunStep[]) {
  return steps.reduce(
    (acc, s) => ({ latencyMs: acc.latencyMs + s.latencyMs, tokens: acc.tokens + s.tokens, cost: +(acc.cost + s.cost).toFixed(4) }),
    { latencyMs: 0, tokens: 0, cost: 0 },
  );
}
