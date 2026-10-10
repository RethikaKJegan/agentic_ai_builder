import { describe, expect, it } from "vitest";
import { DEFAULT_CONTROLS, resolveControls, type AgentControls } from "./governance";
import { addSubAgent, descendants, hiddenIds, planHierarchy, removeSubtree } from "./hierarchy";
import { insertPattern } from "./patterns";
import { simulateRun } from "./simulator";

const org = DEFAULT_CONTROLS.organization;
const ws = DEFAULT_CONTROLS.workspace;
const usage = { runsToday: 0, spendToday: 0, agentSpend: {} };
const ctx = (patch: Partial<AgentControls> = {}) => ({ controls: { ...resolveControls(org, ws), ...patch }, usage });
const PROMPT = "Research customer complaints, analyze issues, draft responses, and escalate critical cases.";

describe("agent controls inheritance", () => {
  it("workspace cannot loosen organization limits", () => {
    const r = resolveControls({ ...org, maxDepth: 2, maxSpendUsd: 10 }, { ...ws, maxDepth: 5, maxSpendUsd: 50 });
    expect(r.maxDepth).toBe(2);
    expect(r.maxSpendUsd).toBe(10);
  });
  it("disabling execution at any level disables it", () => {
    expect(resolveControls({ ...org, executionEnabled: false }, ws).executionEnabled).toBe(false);
    expect(resolveControls(org, { ...ws, executionEnabled: false }).executionEnabled).toBe(false);
  });
  it("tool allow-lists intersect and model blocks union", () => {
    const r = resolveControls({ ...org, allowedTools: ["CRM lookup", "Ticketing"], blockedModels: ["gpt-5"] }, { ...ws, allowedTools: ["Ticketing", "Email send"], blockedModels: ["gemini-2-5-pro"] });
    expect(r.allowedTools).toEqual(["Ticketing"]);
    expect(r.blockedModels.sort()).toEqual(["gemini-2-5-pro", "gpt-5"]);
  });
  it("workflow limit tightens agents per workflow", () => {
    expect(resolveControls(org, ws, { maxAgents: 3 }).maxAgentsPerWorkflow).toBe(3);
  });
});

describe("master/sub-agent hierarchy", () => {
  it("plans a support orchestrator with four child agents", () => {
    const { workflow, agents } = planHierarchy(PROMPT);
    const master = workflow.nodes.find((n) => n.data.role === "master")!;
    expect(master.data.label).toBe("Customer Support Orchestrator");
    const kids = workflow.nodes.filter((n) => n.data.role === "sub").map((n) => n.data.label);
    expect(kids).toEqual(["Research Agent", "Analysis Agent", "Response Agent", "Escalation Agent"]);
    expect(agents.filter((a) => a.parentAgentId === agents[0]!.id)).toHaveLength(4);
  });
  it("simulated run delegates from master to every child and combines results", () => {
    const { workflow, agents } = planHierarchy(PROMPT);
    const r = simulateRun(workflow, agents, "Package arrived late", {}, undefined, ctx());
    expect(r.status).toBe("completed");
    expect(r.steps.filter((s) => s.delegatedBy === "Customer Support Orchestrator")).toHaveLength(4);
    const combine = r.steps.find((s) => s.label === "Combined result")!;
    expect(r.steps.indexOf(combine)).toBeGreaterThan(r.steps.findIndex((s) => s.label === "Human approval"));
    expect(r.steps.find((s) => s.label === "Human approval")!.status).toBe("skipped");
  });
  it("critical cases pause at the escalation approval", () => {
    const { workflow, agents } = planHierarchy(PROMPT);
    expect(simulateRun(workflow, agents, "Customer furious, threatening to cancel", {}, undefined, ctx()).status).toBe("paused");
  });
  it("pausing the parent blocks its children", () => {
    const { workflow, agents } = planHierarchy(PROMPT);
    agents[0]!.paused = true;
    const r = simulateRun(workflow, agents, "Package late", {}, undefined, ctx());
    expect(r.status).toBe("blocked");
    expect(r.steps.filter((s) => s.delegatedBy).length).toBe(0);
  });
  it("a sub-agent whose parent agent is paused cannot run", () => {
    const { workflow, agents } = planHierarchy(PROMPT);
    const sub = agents[1]!;
    const master = agents[0]!;
    const masterNode = workflow.nodes.find((n) => n.data.agentId === master.id)!;
    const trig = workflow.nodes.find((n) => n.data.kind === "trigger")!;
    const r = simulateRun({ nodes: workflow.nodes.filter((n) => n.id !== masterNode.id && n.id !== trig.id), edges: workflow.edges.filter((e) => e.source !== masterNode.id && e.target !== masterNode.id) }, agents.map((a) => (a.id === master.id ? { ...a, paused: true } : a)), "x", {}, undefined, ctx());
    expect(r.status).toBe("blocked");
    expect(r.steps.at(-1)!.control).toBe("Parent agent paused");
    expect(sub.parentAgentId).toBe(master.id);
  });
  it("enforces the maximum sub-agent depth during execution", () => {
    const { workflow, agents } = planHierarchy(PROMPT);
    const r = simulateRun(workflow, agents, "x", {}, undefined, ctx({ maxDepth: 0 }));
    expect(r.status).toBe("blocked");
    expect(r.steps.at(-1)!.control).toBe("Max sub-agent depth");
  });
  it("addSubAgent respects depth and children limits", () => {
    const { workflow } = planHierarchy(PROMPT);
    const master = workflow.nodes.find((n) => n.data.role === "master")!;
    const sub = workflow.nodes.find((n) => n.data.role === "sub")!;
    expect(addSubAgent(workflow, master.id, { maxDepth: 2, maxChildren: 4, maxAgents: 10 }, undefined).ok).toBe(false);
    expect(addSubAgent(workflow, sub.id, { maxDepth: 1, maxChildren: 5, maxAgents: 10 }, undefined).ok).toBe(false);
    const ok = addSubAgent(workflow, sub.id, { maxDepth: 2, maxChildren: 5, maxAgents: 10 }, undefined);
    expect(ok.ok).toBe(true);
  });
  it("collapse hides descendants and removeSubtree deletes them", () => {
    const { workflow } = planHierarchy(PROMPT);
    const master = workflow.nodes.find((n) => n.data.role === "master")!;
    const kids = descendants(workflow.nodes, master.id);
    const collapsed = workflow.nodes.map((n) => (n.id === master.id ? { ...n, data: { ...n.data, collapsed: true } } : n));
    expect(hiddenIds(collapsed).size).toBe(kids.length);
    const sub = workflow.nodes.find((n) => n.data.role === "sub")!;
    expect(removeSubtree(workflow, sub.id).removed).toBe(1 + descendants(workflow.nodes, sub.id).length);
  });
});

describe("run limits", () => {
  const { workflow, agents } = planHierarchy(PROMPT);
  it("disabled execution blocks before any step", () => {
    const r = simulateRun(workflow, agents, "x", {}, undefined, ctx({ executionEnabled: false }));
    expect(r.status).toBe("blocked");
    expect(r.steps).toHaveLength(1);
  });
  it("daily run limit blocks new runs", () => {
    const r = simulateRun(workflow, agents, "x", {}, undefined, { controls: { ...resolveControls(org, ws), maxRunsPerDay: 5 }, usage: { ...usage, runsToday: 5 } });
    expect(r.steps[0]!.control).toBe("Daily run limit");
  });
  it("max agents per workflow blocks oversized workflows", () => {
    const r = simulateRun(workflow, agents, "x", {}, undefined, ctx({ maxAgentsPerWorkflow: 3 }));
    expect(r.steps[0]!.control).toBe("Max agents per workflow");
  });
  it("spend limit blocks when exceeded", () => {
    const r = simulateRun(workflow, agents, "x", {}, undefined, { controls: { ...resolveControls(org, ws), maxSpendUsd: 1 }, usage: { ...usage, spendToday: 1 } });
    expect(r.steps.at(-1)!.control).toBe("Daily spend limit");
  });
  it("agent budget blocks that agent", () => {
    const a = agents.map((x, i) => (i === 0 ? { ...x, budgetUsd: 0 } : x));
    const r = simulateRun(workflow, a, "x", {}, undefined, ctx());
    expect(r.steps.at(-1)!.control).toBe("Agent budget");
  });
  it("restricted tools block agents that use them", () => {
    const r = simulateRun(workflow, agents, "x", {}, undefined, ctx({ allowedTools: ["Ticketing"] }));
    expect(r.steps.at(-1)!.control).toBe("Restricted tool");
  });
  it("sensitive actions pause for approval and resume after approval", () => {
    const sens = planHierarchy(PROMPT);
    const r = simulateRun(sens.workflow, sens.agents, "late parcel", {}, undefined, ctx({ approvalForSensitive: true }));
    expect(r.status).toBe("paused");
    const gate = r.steps.at(-1)!;
    expect(gate.control).toBe("Require approval for sensitive actions");
    const r2 = simulateRun(sens.workflow, sens.agents, "late parcel", { [gate.nodeId]: "approved" }, undefined, ctx({ approvalForSensitive: true }));
    expect(r2.status).toBe("completed");
  });
});

describe("patterns", () => {
  it("supervisor pattern creates connected master and sub-agents", () => {
    const p = insertPattern("supervisor", { x: 100, y: 50 });
    expect(p.nodes).toHaveLength(5);
    expect(p.edges).toHaveLength(6);
    expect(p.agents.filter((a) => a.parentAgentId === p.agents[0]!.id)).toHaveLength(3);
    expect(p.nodes[0]!.position).toEqual({ x: 100, y: 170 });
  });
  it("every pattern's edges reference its own nodes", () => {
    for (const k of ["sequential", "parallel", "conditional", "approval", "supervisor"] as const) {
      const p = insertPattern(k, { x: 0, y: 0 });
      const ids = new Set(p.nodes.map((n) => n.id));
      expect(p.edges.every((e) => ids.has(e.source) && ids.has(e.target))).toBe(true);
    }
  });
});
