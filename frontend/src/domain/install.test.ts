import { describe, expect, it } from "vitest";
import { applyInstall, type InstallState } from "./install";
import { MARKETPLACE, SEED_CONNECTORS } from "./catalog";
import { makeAgent } from "./templates";

const base = (): InstallState => ({
  workflows: [],
  agents: [makeAgent({ name: "A", role: "r", purpose: "p", instructions: "", modelId: "gpt-5-mini", tools: [], knowledge: [] }, "ws")],
  connectors: SEED_CONNECTORS,
  installed: {},
});
const asset = (id: string) => MARKETPLACE.find((a) => a.id === id)!;

describe("marketplace install", () => {
  it("ships 11 curated assets", () => expect(MARKETPLACE).toHaveLength(11));
  it("workflow template creates an editable workflow with its agents", () => {
    const r = applyInstall(base(), asset("mk_wf_complaint"));
    expect(r.patch.workflows).toHaveLength(1);
    expect(r.patch.workflows![0]!.nodes).toHaveLength(8);
    expect(r.patch.agents).toHaveLength(3);
  });
  it("agent install adds a reusable agent", () => {
    const r = applyInstall(base(), asset("mk_ag_contract"));
    expect(r.patch.agents![0]!.name).toBe("Contract Reviewer");
  });
  it("tool install cannot fabricate a configured connector", () => {
    const r = applyInstall(base(), asset("mk_tl_google"));
    expect(r.patch).toEqual({});
    expect(r.target).toBeUndefined();
    expect(r.message).toContain("backend integration");
  });
  it("guardrail pack turns on guardrails for every agent", () => {
    const s = base();
    s.agents[0]!.guardrails.outputValidation = false;
    const r = applyInstall(s, asset("mk_gr_pii"));
    expect(r.patch.agents!.every((a) => a.guardrails.outputValidation)).toBe(true);
  });
});
