// Pure marketplace install logic. Returns the state changes an install produces.
import { generateWorkflow, makeAgent, TEMPLATES } from "./templates";
import type { Agent, Connector, MarketplaceAsset, Workflow } from "./types";

export interface InstallState {
  workflows: Workflow[];
  agents: Agent[];
  connectors: Connector[];
  installed: Record<string, string>;
}

export interface InstallResult {
  patch: Partial<InstallState>;
  message: string;
  /** Created entity to navigate to, if any. */
  target?: { type: "workflow" | "agent" | "connector"; id: string } | undefined;
}

export function applyInstall(s: InstallState, asset: MarketplaceAsset): InstallResult {
  const installed = (id: string) => ({ ...s.installed, [asset.id]: id });
  switch (asset.kind) {
    case "workflow": {
      const t = TEMPLATES.find((x) => x.id === asset.ref);
      const { workflow, agents } = generateWorkflow(t?.examplePrompt ?? asset.description);
      workflow.name = asset.name;
      return {
        patch: { workflows: [workflow, ...s.workflows], agents: [...agents, ...s.agents], installed: installed(workflow.id) },
        message: `"${asset.name}" added to Workflows as a draft`,
        target: { type: "workflow", id: workflow.id },
      };
    }
    case "agent": {
      const a = makeAgent(asset.agent!, "ws_default");
      return { patch: { agents: [a, ...s.agents], installed: installed(a.id) }, message: `${a.name} is now in Agents and the builder's step picker`, target: { type: "agent", id: a.id } };
    }
    case "tool": {
      return { patch: {}, message: "Connector configuration requires backend integration." };
    }
    case "guardrail": {
      const agents = s.agents.map((a) => ({ ...a, guardrails: { ...a.guardrails, ...asset.guardrails } }));
      return { patch: { agents, installed: installed(asset.id) }, message: `${asset.name} applied to ${agents.length} agents` };
    }
  }
}
