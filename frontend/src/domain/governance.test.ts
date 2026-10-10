import { describe, expect, it } from "vitest";
import { can, effectivePolicy, type Policy } from "./governance";
import { generateWorkflow, TEMPLATES } from "./templates";
import { simulateRun } from "./simulator";

const pol = (p: Partial<Policy> & Pick<Policy, "rule">): Policy => ({ id: Math.random().toString(), scope: "organization", name: "p", description: "", enabled: true, ...p });

describe("roles", () => {
  it("viewer cannot publish or approve", () => {
    expect(can("viewer", "workflow.publish")).toBe(false);
    expect(can("viewer", "approval.decide")).toBe(false);
  });
  it("approver can decide approvals but not publish", () => {
    expect(can("approver", "approval.decide")).toBe(true);
    expect(can("approver", "workflow.publish")).toBe(false);
  });
  it("only admin manages policies", () => {
    expect(can("admin", "policy.manage")).toBe(true);
    expect(can("builder", "policy.manage")).toBe(false);
  });
});

describe("policy inheritance", () => {
  it("workspace cost cap can only tighten the organization cap", () => {
    const e = effectivePolicy([pol({ rule: { type: "max-run-cost", usd: 1 } }), pol({ scope: "workspace", rule: { type: "max-run-cost", usd: 5 } })]);
    expect(e.maxRunCost).toBe(1);
    const t = effectivePolicy([pol({ rule: { type: "max-run-cost", usd: 1 } }), pol({ scope: "workspace", rule: { type: "max-run-cost", usd: 0.2 } })]);
    expect(t.maxRunCost).toBe(0.2);
  });
  it("disabled policies are ignored", () => {
    expect(effectivePolicy([pol({ enabled: false, rule: { type: "block-model", modelId: "gpt-5" } })]).blockedModels).toEqual([]);
  });
});

describe("policy enforcement in runs", () => {
  const { workflow, agents } = generateWorkflow(TEMPLATES[0]!.examplePrompt);
  it("blocked model stops the run at the first agent using it", () => {
    const modelId = agents[0]!.modelId;
    const r = simulateRun(workflow, agents, "My parcel was late", {}, effectivePolicy([pol({ rule: { type: "block-model", modelId } })]));
    expect(r.status).toBe("blocked");
  });
  it("cost cap blocks a run that exceeds it", () => {
    const r = simulateRun(workflow, agents, "My parcel was late", {}, effectivePolicy([pol({ rule: { type: "max-run-cost", usd: 0.0001 } })]));
    expect(r.status).toBe("blocked");
  });
});
