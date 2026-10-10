// Local presentation drafts persisted to browser storage.
// Shared contracts remain authoritative at the future API boundary.
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { uid } from "./ids";
import type { ActivityEvent, Agent, Connector, ConnectorStatus, KnowledgeSource, MarketplaceAsset, Run, Workflow, WorkflowEdge, WorkflowNode } from "./types";
import { SEED_CONNECTORS } from "./catalog";
import { applyInstall, type InstallResult } from "./install";
import { makeAgent } from "./templates";
import { DEFAULT_CONTROLS, resolveControls, usageFrom, type AgentControls, type Policy, type Role } from "./governance";
import type { ControlContext } from "./simulator";
import { fromCanonical } from "@/api/mapping";
import type { CanonicalWorkflow } from "@/api/contracts.generated";

export interface AuditEvent { id: string; at: string; actor: string; role: Role; action: string; target: string }

export const SEED_POLICIES: Policy[] = [
  { id: "pol_inj", scope: "organization", name: "Prompt-injection screening", description: "Every agent screens inputs for injection attempts.", rule: { type: "require-guardrail", guardrail: "injectionDetection" }, enabled: true },
  { id: "pol_pii", scope: "organization", name: "PII redaction", description: "Personal data is redacted before any model call.", rule: { type: "require-guardrail", guardrail: "piiRedaction" }, enabled: true },
  { id: "pol_cost", scope: "organization", name: "Run cost cap", description: "Stop any single run that exceeds the cost cap.", rule: { type: "max-run-cost", usd: 1 }, enabled: true },
  { id: "pol_model", scope: "workspace", name: "No GPT-5 in Acme Ops", description: "Workspace restricts the most expensive model.", rule: { type: "block-model", modelId: "gpt-5" }, enabled: false },
];

interface MeshState {
  acceptWorkflow: (document: CanonicalWorkflow) => void;
  workflows: Workflow[];
  agents: Agent[];
  runs: Run[];
  activity: ActivityEvent[];
  connectors: Connector[];
  knowledge: KnowledgeSource[];
  installed: Record<string, string>;
  installAsset: (asset: MarketplaceAsset) => InstallResult;
  createAgent: () => string;
  createBlankWorkflow: (name: string, description?: string) => string;
  controls: { organization: AgentControls; workspace: AgentControls };
  setControls: (scope: "organization" | "workspace", patch: Partial<AgentControls>) => void;
  setAgentPaused: (id: string, paused: boolean) => void;
  controlContext: (workflowId?: string) => ControlContext;
  updateGraph: (id: string, nodes: WorkflowNode[], edges: WorkflowEdge[]) => void;
  renameWorkflow: (id: string, name: string) => void;
  duplicateWorkflow: (id: string) => string | undefined;
  deleteWorkflow: (id: string) => void;
  updateAgent: (id: string, patch: Partial<Agent>) => void;
  log: (e: Omit<ActivityEvent, "id" | "at">) => void;
  role: Role;
  policies: Policy[];
  upsertPolicy: (p: Policy) => void;
  removePolicy: (id: string) => void;
  audit: AuditEvent[];
  audited: (action: string, target: string) => void;
}

function seed() {
  return {
    workflows: [] as Workflow[], agents: [] as Agent[], runs: [] as Run[],
    controls: DEFAULT_CONTROLS,
    connectors: SEED_CONNECTORS.map((c) => ({ ...c, status: "needs-config" as const, account: undefined })),
    knowledge: [] as KnowledgeSource[], installed: {} as Record<string, string>,
    role: "builder" as Role,
    policies: [] as Policy[], audit: [] as AuditEvent[], activity: [] as ActivityEvent[],
  };
}

export const useMesh = create<MeshState>()(
  persist(
    (set, get) => ({
      ...seed(),
      acceptWorkflow: (document) => {
        const mapped = fromCanonical(document);
        set((s) => ({ workflows: [mapped.workflow, ...s.workflows.filter((w) => w.id !== mapped.workflow.id)],
          agents: [...mapped.agents, ...s.agents.filter((a) => !mapped.agents.some((incoming) => incoming.id === a.id))] }));
      },
      createBlankWorkflow: (name, description = "") => {
        const at = new Date().toISOString();
        const trigger = uid("node");
        const output = uid("node");
        const workflow: Workflow = {
          id: uid("wf"), workspaceId: "local", name: name.trim(), description,
          prompt: description, scenario: "custom", status: "draft", versions: [],
          createdAt: at, updatedAt: at,
          nodes: [
            { id: trigger, type: "mesh", position: { x: 80, y: 120 }, data: { kind: "trigger", label: "Start" } },
            { id: output, type: "mesh", position: { x: 420, y: 120 }, data: { kind: "output", label: "Output" } },
          ],
          edges: [{ id: uid("edge"), source: trigger, target: output }],
        };
        set((state) => ({ workflows: [workflow, ...state.workflows] }));
        get().log({ kind: "workflow.created", message: `Created local draft "${workflow.name}"`, workflowId: workflow.id });
        return workflow.id;
      },
      log: (e) => set((s) => ({ activity: [{ ...e, id: uid("evt"), at: new Date().toISOString() }, ...s.activity].slice(0, 50) })),
      updateGraph: (id, nodes, edges) =>
        set((s) => ({ workflows: s.workflows.map((w) => (w.id === id ? { ...w, nodes, edges, updatedAt: new Date().toISOString() } : w)) })),
      renameWorkflow: (id, name) =>
        set((s) => ({ workflows: s.workflows.map((w) => (w.id === id ? { ...w, name, updatedAt: new Date().toISOString() } : w)) })),
      duplicateWorkflow: (id) => {
        const w = get().workflows.find((x) => x.id === id);
        if (!w) return;
        const copyId = uid("wf");
        const copy: Workflow = { ...w, id: copyId, canonical: w.canonical ? { ...w.canonical, workflow_id: copyId, version: 1, status: "draft" } : undefined, serverVersion: undefined, name: `${w.name} (copy)`, status: "draft", versions: [], createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() };
        set((s) => ({ workflows: [copy, ...s.workflows] }));
        return copy.id;
      },
      deleteWorkflow: (id) => set((s) => ({ workflows: s.workflows.filter((w) => w.id !== id) })),
      updateAgent: (id, patch) => {
        const prev = get().agents.find((a) => a.id === id);
        if (prev && patch.modelId && patch.modelId !== prev.modelId) get().audited("Changed agent model", `${prev.name} → ${patch.modelId}`);
        set((s) => ({ agents: s.agents.map((a) => (a.id === id ? { ...a, ...patch, updatedAt: new Date().toISOString() } : a)) }));
      },
      setControls: (scope, patch) => {
        if (scope === "workspace") {
          // Workspace can only tighten organization controls.
          const org = get().controls.organization;
          for (const k of ["maxAgentsPerWorkflow", "maxRunsPerDay", "maxSpendUsd", "maxDepth", "maxChildren"] as const) {
            if (patch[k] != null && patch[k]! > org[k]) patch = { ...patch, [k]: org[k] };
          }
        }
        set((s) => ({ controls: { ...s.controls, [scope]: { ...s.controls[scope], ...patch } } }));
        const desc = Object.entries(patch).map(([k, v]) => `${k} = ${Array.isArray(v) ? v.join(", ") || "none" : v === null ? "all" : v}`).join("; ");
        get().audited(`Changed ${scope} agent control`, desc);
      },
      setAgentPaused: (id, paused) => {
        const a = get().agents.find((x) => x.id === id);
        set((s) => ({ agents: s.agents.map((x) => (x.id === id ? { ...x, paused, updatedAt: new Date().toISOString() } : x)) }));
        if (a) get().audited(paused ? "Paused agent" : "Resumed agent", a.name);
      },
      controlContext: (workflowId) => {
        const s = get();
        const wf = workflowId ? s.workflows.find((w) => w.id === workflowId) : undefined;
        return { controls: resolveControls(s.controls.organization, s.controls.workspace, wf?.controls), usage: usageFrom(s.runs) };
      },
      installAsset: (asset) => {
        const r = applyInstall(get(), asset);
        set(r.patch);
        get().log({ kind: "workflow.created", message: `Installed ${asset.name} from marketplace`, workflowId: r.target?.type === "workflow" ? r.target.id : undefined });
        return r;
      },
      upsertPolicy: (p) => {
        const exists = get().policies.some((x) => x.id === p.id);
        set((s) => ({ policies: exists ? s.policies.map((x) => (x.id === p.id ? p : x)) : [...s.policies, p] }));
        get().audited(exists ? (p.enabled ? "Updated policy" : "Disabled policy") : "Created policy", p.name);
      },
      removePolicy: (id) => {
        const p = get().policies.find((x) => x.id === id);
        set((s) => ({ policies: s.policies.filter((x) => x.id !== id) }));
        if (p) get().audited("Deleted policy", p.name);
      },
      audited: (action, target) =>
        set((s) => ({ audit: [{ id: uid("aud"), at: new Date().toISOString(), actor: "Local editor", role: s.role, action, target }, ...s.audit].slice(0, 300) })),
      createAgent: () => {
        const a = makeAgent({ name: "New Agent", role: "Assistant", purpose: "Describe what this agent does.", instructions: "", modelId: "gpt-5-mini", tools: [], knowledge: [] }, "ws_default");
        set((s) => ({ agents: [a, ...s.agents] }));
        return a.id;
      },
    }),
    {
      name: "mesh-local-drafts-v1",
      version: 1,
      storage: createJSONStorage(() => localStorage),
      skipHydration: true,
      partialize: (s) => ({ workflows: s.workflows.filter((w) => w.serverVersion === undefined), agents: s.agents.filter((a) => a.origin !== "backend"), runs: s.runs, activity: s.activity, connectors: s.connectors, knowledge: s.knowledge, installed: s.installed, role: s.role, policies: s.policies, controls: s.controls, audit: s.audit }),
    },
  ),
);
