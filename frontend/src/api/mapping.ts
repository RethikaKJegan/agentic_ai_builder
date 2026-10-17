import { CanonicalWorkflowSchema, type CanonicalWorkflow } from "./contracts.generated";
import type { Agent, Workflow, WorkflowNode } from "@/domain/types";
import { InputError } from "./feedback";
import { MODELS } from "@/domain/models";

export function fromCanonical(document: CanonicalWorkflow): { workflow: Workflow; agents: Agent[] } {
  const canonical = structuredClone(CanonicalWorkflowSchema.parse(document));
  const timestamp = typeof canonical.metadata["updated_at"] === "string" ? canonical.metadata["updated_at"] : new Date().toISOString();
  const workspaceId = String(canonical.metadata["workspace_id"] ?? "server");
  const agents: Agent[] = canonical.agents.map((a) => ({
    id: `${canonical.workflow_id}::${a.agent_id}`, canonicalId: a.agent_id, capabilities: a.capabilities, declaredPermissions: a.permissions, workspaceId, name: a.role, role: a.role, purpose: a.goal,
    instructions: a.instructions, modelId: a.model.model_id, fallbackModelId: a.model.model_id,
    temperature: a.model.temperature ?? 0, maxTokens: a.limits.max_tokens, tools: a.allowed_tool_ids,
    knowledge: [], memory: "none", outputSchema: JSON.stringify(a.output_schema, null, 2),
    guardrails: { piiRedaction: true, injectionDetection: true, outputValidation: true },
    parentAgentId: a.parent_agent_id ? `${canonical.workflow_id}::${a.parent_agent_id}` : undefined,
    version: canonical.version, status: "draft", updatedAt: timestamp, origin: "backend",
  }));
  const nodes: WorkflowNode[] = canonical.nodes.map((n, index) => ({
    id: n.node_id, type: "mesh", position: { x: n.layout?.x ?? 80 + index * 240, y: n.layout?.y ?? 120 },
    data: { ...structuredClone(n.configuration?.["ui"] as Record<string, unknown> | undefined),
      kind: n.kind, label: n.label, agentId: n.agent_id ? `${canonical.workflow_id}::${n.agent_id}` : undefined, tool: n.tool_id,
      conditionId: n.condition_id, approvalGateId: n.approval_gate_id,
      condition: structuredClone(canonical.conditions.find((c) => c.condition_id === n.condition_id)),
      approval: structuredClone(canonical.approval_gates.find((g) => g.approval_gate_id === n.approval_gate_id)),
      description: typeof n.configuration?.["description"] === "string" ? n.configuration["description"] : "" },
  }));
  return { workflow: { id: canonical.workflow_id, workspaceId, name: canonical.name, description: canonical.description,
    prompt: canonical.description, scenario: "custom", status: canonical.status, nodes,
    edges: canonical.edges.map((e) => ({ id: e.edge_id, source: e.source, target: e.target, label: e.outcome })),
    versions: [], createdAt: timestamp, updatedAt: timestamp, canonical, serverVersion: canonical.version }, agents };
}

const limits = { max_llm_calls: 0, max_tool_calls: 0, max_tokens: 1000, max_retries: 0, timeout_seconds: 60 };
/** Includes delegated templates even when they have no execution graph node. */
export function olderDocument(incoming: CanonicalWorkflow, baseline?: CanonicalWorkflow) {
  const rank={draft:0,validated:1,approved:2,published:3,archived:4};
  return !!baseline && (incoming.version<baseline.version || (incoming.version===baseline.version && rank[incoming.status]<rank[baseline.status]));
}
export function ownsAgent(workflow: Workflow, agent: Agent) {
  return workflow.nodes.some(node => node.data.agentId === agent.id) || !!workflow.canonical?.agents.some(definition => agent.id === `${workflow.id}::${definition.agent_id}`);
}
export function stableSnapshot(value: unknown): string {
  const normalize = (item: unknown): unknown => Array.isArray(item) ? item.map(normalize) : item && typeof item === "object" ? Object.fromEntries(Object.entries(item).filter(([,v])=>v!==undefined).sort(([a],[b])=>a.localeCompare(b)).map(([k,v])=>[k,normalize(v)])) : item;
  return JSON.stringify(normalize(value));
}
export function workflowEditSnapshot(workflow: Workflow, agents: Agent[]) {
  return stableSnapshot({name:workflow.name,description:workflow.description,nodes:workflow.nodes,edges:workflow.edges,
    agents:agents.filter(a=>ownsAgent(workflow,a)).map(a=>({id:a.id,role:a.role,purpose:a.purpose,instructions:a.instructions,modelId:a.modelId,temperature:a.temperature,maxTokens:a.maxTokens,outputSchema:a.outputSchema,capabilities:a.capabilities,declaredPermissions:a.declaredPermissions,parentAgentId:a.parentAgentId})).sort((a,b)=>a.id.localeCompare(b.id))});
}
export function hasWorkflowEdits(workflow: Workflow, agents: Agent[]): boolean {
  if (!workflow.canonical || !workflow.serverVersion) return true;
  const baseline=fromCanonical(workflow.canonical);
  return workflowEditSnapshot(workflow,agents)!==workflowEditSnapshot(baseline.workflow,baseline.agents);
}
export function toCanonical(workflow: Workflow, agents: Agent[], nextVersion = (workflow.serverVersion ?? 0) + 1): CanonicalWorkflow {
  const base = workflow.canonical;
  const agentIds = new Set(workflow.nodes.flatMap((n) => n.data.agentId ? [agents.find((a) => a.id === n.data.agentId)?.canonicalId ?? n.data.agentId] : []));
  // Retain original unreferenced definitions too; graph validation decides validity.
  base?.agents.forEach((a) => agentIds.add(a.agent_id));
  const definitions = [...agentIds].map((id) => {
    const original = base?.agents.find((a) => a.agent_id === id);
    const agent = agents.find((a) => a.id === `${workflow.id}::${id}`) ?? agents.find((a) => a.canonicalId === id && workflow.nodes.some((n) => n.data.agentId === a.id)) ?? agents.find((a) => a.id === id);
    if (!agent) { if (original) return original; throw new InputError(`Agent ${id} needs a configuration.`, "agents"); }
    if (!original && agent.tools.length) throw new InputError("Local tool names need registry resolution before saving.", "tools");
    let outputSchema: unknown;
    try { outputSchema = JSON.parse(agent.outputSchema); } catch { throw new InputError("Enter valid JSON in the agent output schema.", `agents.${id}.output_schema`); }
    return { ...(original ?? { agent_id: id, capabilities: [], allowed_tool_ids: [], permissions: ["workflow.read_input"], limits: { ...limits }, approval_requirements: [] }),
      role: agent.role, goal: agent.purpose, instructions: agent.instructions,
      capabilities: agent.capabilities ?? original?.capabilities ?? [], permissions: agent.declaredPermissions ?? original?.permissions ?? ["workflow.read_input"],
      ...(agent.parentAgentId ? {parent_agent_id: agents.find(parent=>parent.id===agent.parentAgentId)?.canonicalId ?? agent.parentAgentId} : {}),
      model: { ...(original?.model ?? { provider: "openai" }), provider: original && agent.modelId === original.model.model_id ? original.model.provider : MODELS.find((model) => model.id === agent.modelId)?.provider.toLowerCase() ?? original?.model.provider ?? "openai", model_id: agent.modelId, temperature: agent.temperature },
      input_schema: original?.input_schema ?? { type: "object" }, output_schema: outputSchema,
      limits: { ...(original?.limits ?? limits), max_tokens: agent.maxTokens } };
  });
  const conditions = [...(base?.conditions ?? [])];
  const approvals = [...(base?.approval_gates ?? [])];
  const nodes = workflow.nodes.map((n) => {
    const original = base?.nodes.find((item) => item.node_id === n.id);
    const node = { ...original, node_id: n.id, kind: n.data.kind, label: n.data.label,
      layout: { ...n.position }, configuration: { ...original?.configuration, description: n.data.description ?? "",
        ui: { ...(original?.configuration?.["ui"] as Record<string,unknown> | undefined), role: n.data.role, parentNodeId: n.data.parentNodeId, collapsed: n.data.collapsed, combine: n.data.combine, orientation: n.data.orientation } },
      ...(n.data.agentId ? { agent_id: agents.find((a) => a.id === n.data.agentId)?.canonicalId ?? n.data.agentId } : {}), ...(n.data.tool ? { tool_id: n.data.tool } : {}) };
    if (n.data.kind === "condition") {
      const condition = n.data["condition"] as CanonicalWorkflow["conditions"][number] | undefined;
      const id = condition?.condition_id ?? String(n.data["conditionId"] ?? `condition_${n.id}`);
      const value = condition ?? { condition_id: id, expression: "", outcomes: [] };
      const index = conditions.findIndex((c) => c.condition_id === id);
      if (index >= 0) conditions[index] = value; else conditions.push(value);
      return { ...node, condition_id: id };
    }
    if (n.data.kind === "approval") {
      const gate = n.data["approval"] as CanonicalWorkflow["approval_gates"][number] | undefined;
      const id = gate?.approval_gate_id ?? String(n.data["approvalGateId"] ?? `gate_${n.id}`);
      const value = gate ?? { approval_gate_id: id, approver_roles: ["approver"], on_reject: "stop" as const };
      const index = approvals.findIndex((g) => g.approval_gate_id === id);
      if (index >= 0) approvals[index] = value; else approvals.push(value);
      return { ...node, approval_gate_id: id };
    }
    return node;
  });
  const parsed = CanonicalWorkflowSchema.safeParse({ ...(base ?? {}),
    workflow_id: workflow.id, version: nextVersion, name: workflow.name, description: workflow.description, status: "draft",
    inputs: base?.inputs ?? [], outputs: base?.outputs ?? [], stakeholders: base?.stakeholders ?? [],
    agents: definitions.map((a) => ({ ...a, allowed_tool_ids: [] })),
    tools: (base?.tools ?? []).map((tool) => ({ tool_id: tool.tool_id, capability: tool.capability })), nodes,
    edges: workflow.edges.map((e) => ({ edge_id: e.id, source: e.source, target: e.target, ...(e.label ? { outcome: e.label } : {}) })),
    conditions, approval_gates: approvals,
    execution_policy: base?.execution_policy ?? { limits, requires_review_before_execution: true, allow_external_writes: false },
    error_policy: base?.error_policy ?? { on_validation_error: "reject", on_runtime_error: "stop", max_retries: 0 },
    metadata: { ...base?.metadata, updated_at: workflow.updatedAt } });
  if (!parsed.success) {
    const issue = parsed.error.issues[0];
    throw new InputError(`Complete the workflow configuration at ${issue?.path.join(".") || "workflow"}. ${issue?.message ?? ""}`, issue?.path.join(".") || "workflow");
  }
  for (const key of ["approved_by", "validation_state", "approval_submission"]) delete parsed.data.metadata[key];
  return structuredClone(parsed.data);
}
