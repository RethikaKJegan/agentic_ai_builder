// Core domain models. Stable IDs; workflow nodes reference agents by ID.

export type NodeKind = "trigger" | "agent" | "tool" | "condition" | "approval" | "transform" | "output";

export interface WorkflowNodeData {
  label: string;
  kind: NodeKind;
  description?: string | undefined;
  agentId?: string | undefined;
  tool?: string | undefined;
  /** For tool nodes: force a simulated failure. */
  simulateFailure?: boolean | undefined;
  /** Hierarchy role for master/sub-agent orchestration. */
  role?: "master" | "sub" | undefined;
  /** Parent node in the agent hierarchy (sub-agents, and tasks under a sub-agent). */
  parentNodeId?: string | undefined;
  /** Collapsed master/sub node hides its descendants on the canvas. */
  collapsed?: boolean | undefined;
  /** Node that merges sub-agent results. */
  combine?: boolean | undefined;
  /** Approval only pauses critical cases. */
  onlyCritical?: boolean | undefined;
  /** Top-to-bottom handles for hierarchy layouts. */
  orientation?: "tb" | undefined;
  [key: string]: unknown;
}

export interface WorkflowNode {
  id: string;
  type: "mesh";
  position: { x: number; y: number };
  data: WorkflowNodeData;
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  /** Branch label for condition outputs, e.g. "critical" / "standard". */
  label?: string | undefined;
}

export interface WorkflowVersion {
  id: string;
  version: number;
  publishedAt: string;
  nodeCount: number;
}

export type WorkflowStatus = "draft" | "validated" | "approved" | "published" | "archived";

export interface Workflow {
  canonical?: import("@/api/contracts.generated").CanonicalWorkflow | undefined;
  serverVersion?: number | undefined;
  remote?: import("@/api/contracts.generated").CanonicalWorkflow | undefined;
  tabConflict?: boolean | undefined;
  id: string;
  workspaceId: string;
  name: string;
  description: string;
  prompt: string;
  scenario: string;
  status: WorkflowStatus;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  versions: WorkflowVersion[];
  /** Workflow-level limits; can only tighten workspace/org controls. */
  controls?: { maxAgents?: number | undefined; maxSpendUsd?: number | undefined } | undefined;
  createdAt: string;
  updatedAt: string;
}

export interface Agent {
  origin?: "backend" | undefined;
  canonicalId?: string | undefined;
  capabilities?: string[] | undefined;
  declaredPermissions?: string[] | undefined;
  id: string;
  workspaceId: string;
  name: string;
  role: string;
  purpose: string;
  instructions: string;
  modelId: string;
  fallbackModelId: string;
  temperature: number;
  maxTokens: number;
  tools: string[];
  knowledge: string[];
  memory: "none" | "session" | "long-term";
  outputSchema: string;
  guardrails: { piiRedaction: boolean; injectionDetection: boolean; outputValidation: boolean };
  version: number;
  status: "active" | "draft";
  updatedAt: string;
  /** Agent-level controls (all optional so older saved agents still load). */
  paused?: boolean | undefined;
  parentAgentId?: string | undefined;
  budgetUsd?: number | null | undefined;
  requireApproval?: boolean | undefined;
}

export type StepStatus = "success" | "paused" | "approved" | "rejected" | "failed" | "blocked" | "skipped";
export type RunStatus = "running" | "paused" | "completed" | "rejected" | "failed" | "blocked";

export interface RunStep {
  nodeId: string;
  label: string;
  kind: NodeKind;
  status: StepStatus;
  output: string;
  latencyMs: number;
  tokens: number;
  cost: number;
  modelId?: string | undefined;
  guardrail?: string | undefined;
  agentId?: string | undefined;
  /** Label of the parent agent that delegated this step. */
  delegatedBy?: string | undefined;
  /** Which control blocked or paused this step. */
  control?: string | undefined;
}

export interface Run {
  id: string;
  workflowId: string;
  workflowName: string;
  input: string;
  status: RunStatus;
  steps: RunStep[];
  decisions: Record<string, "approved" | "rejected">;
  startedAt: string;
  finishedAt?: string | undefined;
  simulated: true;
}

export interface ActivityEvent {
  id: string;
  at: string;
  kind: "workflow.created" | "workflow.published" | "agent.updated" | "run.completed" | "run.paused" | "run.failed" | "approval.decided";
  message: string;
  workflowId?: string | undefined;
}

export type ConnectorStatus = "available" | "demo-connected" | "needs-config" | "error";
export interface Connector {
  id: string;
  name: string;
  category: "Communication" | "CRM" | "Storage" | "Databases" | "HTTP/API" | "Productivity";
  description: string;
  /** Tool names (from the tool catalog) this connector powers. */
  tools: string[];
  status: ConnectorStatus;
  account?: string | undefined;
}

export interface KnowledgeSource {
  id: string;
  name: string;
  collection: string;
  fileType: "PDF" | "DOCX" | "Markdown" | "Web" | "CSV";
  sizeKb: number;
  status: "ready" | "processing" | "failed";
  updatedAt: string;
}

export type AssetKind = "agent" | "workflow" | "tool" | "guardrail";
export interface MarketplaceAsset {
  id: string;
  kind: AssetKind;
  name: string;
  domain: string;
  publisher: string;
  description: string;
  dependencies: string[];
  /** workflow: template id; tool: connector id */
  ref?: string | undefined;
  agent?: { name: string; role: string; purpose: string; instructions: string; modelId: string; tools: string[]; knowledge: string[] } | undefined;
  guardrails?: Partial<{ piiRedaction: boolean; injectionDetection: boolean; outputValidation: boolean }> | undefined;
  orgOwned?: boolean | undefined;
}
