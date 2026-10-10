// Governance: demo roles/permissions, policies with inheritance, and run metrics.
// Pure functions so UI and tests share one implementation.
import type { Agent, Run, Workflow } from "./types";

export type Role = "admin" | "builder" | "approver" | "viewer";
export type Permission = "workflow.edit" | "workflow.publish" | "run.test" | "approval.decide" | "policy.manage" | "settings.manage";

export const ROLES: { id: Role; label: string; description: string }[] = [
  { id: "admin", label: "Organization Admin", description: "Full control, including policies and settings." },
  { id: "builder", label: "Builder", description: "Designs, tests and publishes workflows." },
  { id: "approver", label: "Approver", description: "Reviews paused runs and decides approvals." },
  { id: "viewer", label: "Viewer", description: "Read-only access to workflows, runs and monitoring." },
];

const MATRIX: Record<Role, Permission[]> = {
  admin: ["workflow.edit", "workflow.publish", "run.test", "approval.decide", "policy.manage", "settings.manage"],
  builder: ["workflow.edit", "workflow.publish", "run.test"],
  approver: ["run.test", "approval.decide"],
  viewer: [],
};

export const can = (role: Role, p: Permission) => MATRIX[role].includes(p);
export const roleLabel = (r: Role) => ROLES.find((x) => x.id === r)?.label ?? r;

export type GuardrailKey = "piiRedaction" | "injectionDetection" | "outputValidation";
export type PolicyRule =
  | { type: "require-guardrail"; guardrail: GuardrailKey }
  | { type: "block-model"; modelId: string }
  | { type: "max-run-cost"; usd: number };

export interface Policy {
  id: string;
  scope: "organization" | "workspace";
  name: string;
  description: string;
  rule: PolicyRule;
  enabled: boolean;
}

export interface EffectivePolicy {
  guardrails: Record<GuardrailKey, boolean>;
  blockedModels: string[];
  maxRunCost: number | null;
  /** Which policy produced each effective setting. */
  sources: { setting: string; policy: string; scope: Policy["scope"] }[];
}

/** Workspace policies can only tighten organization policies: guardrails and blocks union, cost caps take the minimum. */
export function effectivePolicy(policies: Policy[]): EffectivePolicy {
  const eff: EffectivePolicy = { guardrails: { piiRedaction: false, injectionDetection: false, outputValidation: false }, blockedModels: [], maxRunCost: null, sources: [] };
  const ordered = [...policies.filter((p) => p.scope === "organization"), ...policies.filter((p) => p.scope === "workspace")];
  for (const p of ordered) {
    if (!p.enabled) continue;
    const r = p.rule;
    if (r.type === "require-guardrail") {
      eff.guardrails[r.guardrail] = true;
      eff.sources.push({ setting: `Guardrail: ${r.guardrail}`, policy: p.name, scope: p.scope });
    } else if (r.type === "block-model") {
      if (!eff.blockedModels.includes(r.modelId)) eff.blockedModels.push(r.modelId);
      eff.sources.push({ setting: `Blocked model: ${r.modelId}`, policy: p.name, scope: p.scope });
    } else if (eff.maxRunCost === null || r.usd < eff.maxRunCost) {
      eff.maxRunCost = r.usd;
      eff.sources.push({ setting: `Max run cost: $${r.usd}`, policy: p.name, scope: p.scope });
    }
  }
  return eff;
}

export function runMetrics(runs: Run[]) {
  const total = runs.length;
  const finished = runs.filter((r) => r.status !== "paused" && r.status !== "running");
  const completed = runs.filter((r) => r.status === "completed").length;
  const cost = runs.reduce((a, r) => a + r.steps.reduce((b, s) => b + s.cost, 0), 0);
  const latency = runs.reduce((a, r) => a + r.steps.reduce((b, s) => b + s.latencyMs, 0), 0);
  return {
    total,
    completed,
    pending: runs.filter((r) => r.status === "paused").length,
    blocked: runs.filter((r) => r.status === "blocked").length,
    failed: runs.filter((r) => r.status === "failed" || r.status === "rejected").length,
    successRate: finished.length ? completed / finished.length : 0,
    cost: +cost.toFixed(4),
    avgLatencyMs: total ? Math.round(latency / total) : 0,
  };
}

// ---------------- Agent controls (organization → workspace → workflow → agent) ----------------

export interface AgentControls {
  executionEnabled: boolean;
  maxAgentsPerWorkflow: number;
  maxRunsPerDay: number;
  maxSpendUsd: number;
  maxDepth: number;
  maxChildren: number;
  /** null = every tool allowed. */
  allowedTools: string[] | null;
  blockedModels: string[];
  approvalForSensitive: boolean;
}

export const SENSITIVE_TOOLS = ["Email send", "ERP ledger"];

export const DEFAULT_CONTROLS: { organization: AgentControls; workspace: AgentControls } = {
  organization: { executionEnabled: true, maxAgentsPerWorkflow: 12, maxRunsPerDay: 200, maxSpendUsd: 25, maxDepth: 3, maxChildren: 6, allowedTools: null, blockedModels: [], approvalForSensitive: false },
  workspace: { executionEnabled: true, maxAgentsPerWorkflow: 10, maxRunsPerDay: 150, maxSpendUsd: 20, maxDepth: 2, maxChildren: 5, allowedTools: null, blockedModels: [], approvalForSensitive: false },
};

const intersect = (a: string[] | null, b: string[] | null) => (a === null ? b : b === null ? a : a.filter((x) => b.includes(x)));

/** Lower levels can only tighten: switches AND, limits MIN, allow-lists intersect, blocks union, approvals OR. */
export function resolveControls(org: AgentControls, ws: AgentControls, wf?: Workflow["controls"]): AgentControls {
  return {
    executionEnabled: org.executionEnabled && ws.executionEnabled,
    maxAgentsPerWorkflow: Math.min(org.maxAgentsPerWorkflow, ws.maxAgentsPerWorkflow, wf?.maxAgents ?? Infinity),
    maxRunsPerDay: Math.min(org.maxRunsPerDay, ws.maxRunsPerDay),
    maxSpendUsd: Math.min(org.maxSpendUsd, ws.maxSpendUsd, wf?.maxSpendUsd ?? Infinity),
    maxDepth: Math.min(org.maxDepth, ws.maxDepth),
    maxChildren: Math.min(org.maxChildren, ws.maxChildren),
    allowedTools: intersect(org.allowedTools, ws.allowedTools),
    blockedModels: [...new Set([...org.blockedModels, ...ws.blockedModels])],
    approvalForSensitive: org.approvalForSensitive || ws.approvalForSensitive,
  };
}

export interface Usage { runsToday: number; spendToday: number; agentSpend: Record<string, number> }

/** Usage over the last 24h from simulated runs, plus lifetime spend per agent. */
export function usageFrom(runs: Run[], now = Date.now()): Usage {
  const day = runs.filter((r) => now - new Date(r.startedAt).getTime() < 86400000);
  const agentSpend: Record<string, number> = {};
  runs.forEach((r) => r.steps.forEach((s) => { if (s.agentId) agentSpend[s.agentId] = (agentSpend[s.agentId] ?? 0) + s.cost; }));
  return { runsToday: day.length, spendToday: day.reduce((a, r) => a + r.steps.reduce((b, s) => b + s.cost, 0), 0), agentSpend };
}

export function ancestorsOf(agent: Agent, agents: Agent[]): Agent[] {
  const out: Agent[] = [];
  let cur = agent.parentAgentId ? agents.find((a) => a.id === agent.parentAgentId) : undefined;
  while (cur && !out.includes(cur)) {
    out.push(cur);
    cur = cur.parentAgentId ? agents.find((a) => a.id === cur!.parentAgentId) : undefined;
  }
  return out;
}

export interface Block { control: string; reason: string }

/** Single enforcement point for an agent step. Returns the first control that blocks, or null. */
export function checkAgentExecution(p: {
  agent: Agent | undefined;
  agents: Agent[];
  controls: AgentControls;
  modelId: string;
  depth: number;
  projectedSpend: number;
  stepCost: number;
  agentSpent: number;
}): Block | null {
  const { agent, controls: c } = p;
  if (!c.executionEnabled) return { control: "Organization execution switch", reason: "Agent execution is disabled for the organization." };
  if (agent?.paused) return { control: "Agent paused", reason: `${agent.name} is paused, so it and any sub-agents cannot run.` };
  const pausedParent = agent ? ancestorsOf(agent, p.agents).find((a) => a.paused) : undefined;
  if (pausedParent) return { control: "Parent agent paused", reason: `Parent agent ${pausedParent.name} is paused; ${agent!.name} cannot run through it.` };
  if (p.depth > c.maxDepth) return { control: "Max sub-agent depth", reason: `Hierarchy depth ${p.depth} exceeds the limit of ${c.maxDepth}.` };
  if (c.blockedModels.includes(p.modelId)) return { control: "Restricted model", reason: `Model ${p.modelId} is restricted by agent controls.` };
  const badTool = agent && c.allowedTools ? agent.tools.find((t) => !c.allowedTools!.includes(t)) : undefined;
  if (badTool) return { control: "Restricted tool", reason: `${agent!.name} uses ${badTool}, which is not on the allowed tool list.` };
  if (p.projectedSpend > c.maxSpendUsd) return { control: "Daily spend limit", reason: `Estimated spend would reach $${p.projectedSpend.toFixed(2)}, above the $${c.maxSpendUsd} limit.` };
  if (agent?.budgetUsd != null && p.agentSpent + p.stepCost > agent.budgetUsd) return { control: "Agent budget", reason: `${agent.name} would exceed its $${agent.budgetUsd} execution budget.` };
  return null;
}

/** Pre-run checks that apply to the whole workflow. */
export function checkRunStart(p: { controls: AgentControls; agentCount: number; runsToday: number }): Block | null {
  if (!p.controls.executionEnabled) return { control: "Organization execution switch", reason: "Agent execution is disabled for the organization." };
  if (p.agentCount > p.controls.maxAgentsPerWorkflow) return { control: "Max agents per workflow", reason: `Workflow has ${p.agentCount} agents; the limit is ${p.controls.maxAgentsPerWorkflow}.` };
  if (p.runsToday >= p.controls.maxRunsPerDay) return { control: "Daily run limit", reason: `Daily limit of ${p.controls.maxRunsPerDay} runs reached.` };
  return null;
}
