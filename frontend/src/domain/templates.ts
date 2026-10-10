// Deterministic workflow generation from structured templates.
// This is simulated generation — no live LLM inference happens here.
import { uid } from "./ids";
import { autoLayout } from "./layout";
import type { Agent, NodeKind, Workflow, WorkflowEdge, WorkflowNode } from "./types";

interface AgentSpec {
  name: string;
  role: string;
  purpose: string;
  instructions: string;
  modelId: string;
  tools: string[];
  knowledge: string[];
}

interface StepSpec {
  key: string;
  kind: NodeKind;
  label: string;
  description: string;
  tool?: string;
  agent?: AgentSpec;
}

export interface TemplateSpec {
  id: string;
  name: string;
  match: RegExp;
  examplePrompt: string;
  steps: StepSpec[];
  edges: [string, string, string?][];
}

export const TEMPLATES: TemplateSpec[] = [
  {
    id: "complaint",
    name: "Customer complaint resolution",
    match: /complain|support|ticket|customer (issue|feedback)/i,
    examplePrompt:
      "Whenever a customer complaint arrives, analyze severity, look up customer information, create a support ticket, draft a response, and escalate critical cases for manager approval.",
    steps: [
      { key: "trigger", kind: "trigger", label: "Complaint received", description: "New message in support inbox" },
      {
        key: "analyze", kind: "agent", label: "Complaint analysis", description: "Classifies severity, sentiment and intent",
        agent: { name: "Complaint Analyst", role: "Classifier", purpose: "Assess severity, sentiment and intent of inbound complaints.", instructions: "Read the complaint. Return severity (low, standard, critical), sentiment, and a one-line summary. Treat legal threats, safety issues and churn signals as critical.", modelId: "claude-haiku-4-5", tools: [], knowledge: ["Support playbook"] },
      },
      { key: "lookup", kind: "tool", label: "Customer lookup", description: "Fetch account, plan and history", tool: "CRM lookup" },
      { key: "ticket", kind: "tool", label: "Create ticket", description: "Open a ticket with classification", tool: "Ticketing" },
      { key: "router", kind: "condition", label: "Severity router", description: "Route by analysed severity" },
      {
        key: "respond", kind: "agent", label: "Response drafting", description: "Drafts an on-brand reply",
        agent: { name: "Response Writer", role: "Writer", purpose: "Draft empathetic, policy-compliant customer replies.", instructions: "Write a concise reply in the brand voice. Acknowledge the issue, state the next step, never promise refunds above policy limits.", modelId: "claude-sonnet-4-5", tools: ["Email send"], knowledge: ["Brand voice guide", "Refund policy"] },
      },
      { key: "approval", kind: "approval", label: "Manager approval", description: "Required for critical cases" },
      { key: "output", kind: "output", label: "Send response", description: "Reply sent and ticket updated", tool: "Email send" },
    ],
    edges: [
      ["trigger", "analyze"], ["analyze", "lookup"], ["lookup", "ticket"], ["ticket", "router"],
      ["router", "respond", "standard"], ["router", "approval", "critical"], ["approval", "respond"], ["respond", "output"],
    ],
  },
  {
    id: "invoice",
    name: "Invoice review and approval",
    match: /invoice|payable|bill|vendor payment/i,
    examplePrompt: "When an invoice is emailed, extract its fields, match it to the purchase order, flag anomalies, and route invoices over $10,000 to finance approval before posting to the ledger.",
    steps: [
      { key: "trigger", kind: "trigger", label: "Invoice received", description: "PDF arrives in AP inbox" },
      { key: "parse", kind: "tool", label: "Extract fields", description: "Vendor, amount, line items", tool: "Document parser" },
      {
        key: "match", kind: "agent", label: "PO matching", description: "Three-way match and anomaly check",
        agent: { name: "Invoice Auditor", role: "Reviewer", purpose: "Match invoices to POs and flag anomalies.", instructions: "Compare invoice lines to the purchase order and receipt. Flag price variance above 2% and unknown vendors.", modelId: "gpt-5-mini", tools: ["ERP ledger"], knowledge: ["Vendor master list", "Finance approval matrix"] },
      },
      { key: "router", kind: "condition", label: "Amount router", description: "Route by invoice total" },
      { key: "approval", kind: "approval", label: "Finance approval", description: "Required above $10,000" },
      { key: "post", kind: "output", label: "Post to ledger", description: "Booked in ERP", tool: "ERP ledger" },
    ],
    edges: [["trigger", "parse"], ["parse", "match"], ["match", "router"], ["router", "approval", "critical"], ["router", "post", "standard"], ["approval", "post"]],
  },
  {
    id: "lead",
    name: "Lead research and qualification",
    match: /lead|prospect|sales|qualif/i,
    examplePrompt: "When a new lead signs up, research the company, score fit against our ideal customer profile, enrich the CRM record, and alert the account owner in Slack for high-fit leads.",
    steps: [
      { key: "trigger", kind: "trigger", label: "New lead", description: "Form submission or CRM create" },
      {
        key: "research", kind: "agent", label: "Company research", description: "Size, industry, tech stack",
        agent: { name: "Lead Researcher", role: "Researcher", purpose: "Research inbound leads from public sources.", instructions: "Summarise the company's size, industry, recent news and likely buying committee. Cite sources.", modelId: "gemini-2-5-pro", tools: ["Web search"], knowledge: ["Ideal customer profile"] },
      },
      { key: "score", kind: "transform", label: "Fit scoring", description: "Score 0–100 against ICP" },
      { key: "enrich", kind: "tool", label: "Enrich CRM", description: "Write fields to record", tool: "CRM lookup" },
      { key: "router", kind: "condition", label: "Fit router", description: "High fit vs nurture" },
      { key: "notify", kind: "output", label: "Alert owner", description: "Slack message to AE", tool: "Slack notify" },
      { key: "nurture", kind: "output", label: "Add to nurture", description: "Marketing sequence" },
    ],
    edges: [["trigger", "research"], ["research", "score"], ["score", "enrich"], ["enrich", "router"], ["router", "notify", "critical"], ["router", "nurture", "standard"]],
  },
  {
    id: "onboarding",
    name: "Employee onboarding",
    match: /onboard|new hire|employee|joiner/i,
    examplePrompt: "When a new hire is confirmed, create their accounts, assemble a personalised first-week plan, schedule intro meetings, and get manager sign-off on access permissions.",
    steps: [
      { key: "trigger", kind: "trigger", label: "Hire confirmed", description: "Status change in HRIS" },
      { key: "accounts", kind: "tool", label: "Provision accounts", description: "Email, chat, core tools", tool: "HRIS" },
      {
        key: "plan", kind: "agent", label: "First-week planner", description: "Personalised onboarding plan",
        agent: { name: "Onboarding Guide", role: "Planner", purpose: "Assemble personalised onboarding plans.", instructions: "Build a five-day plan from the role, team and handbook. Include owners for each session.", modelId: "gpt-5-mini", tools: ["Calendar"], knowledge: ["Employee handbook"] },
      },
      { key: "approval", kind: "approval", label: "Manager sign-off", description: "Confirm access levels" },
      { key: "schedule", kind: "tool", label: "Schedule intros", description: "Book calendar slots", tool: "Calendar" },
      { key: "output", kind: "output", label: "Welcome pack sent", description: "Plan emailed to new hire", tool: "Email send" },
    ],
    edges: [["trigger", "accounts"], ["accounts", "plan"], ["plan", "approval"], ["approval", "schedule"], ["schedule", "output"]],
  },
];

const GENERIC: TemplateSpec = {
  id: "generic",
  name: "Custom process",
  match: /.*/,
  examplePrompt: "",
  steps: [
    { key: "trigger", kind: "trigger", label: "Process starts", description: "Incoming request or event" },
    {
      key: "understand", kind: "agent", label: "Understand request", description: "Extracts intent and key fields",
      agent: { name: "Intake Agent", role: "Analyst", purpose: "Understand incoming requests and extract structured fields.", instructions: "Read the request, extract the key entities and classify urgency.", modelId: "gpt-5-mini", tools: [], knowledge: [] },
    },
    { key: "validate", kind: "transform", label: "Validate data", description: "Check required fields" },
    {
      key: "act", kind: "agent", label: "Execute task", description: "Performs the core work",
      agent: { name: "Operator Agent", role: "Executor", purpose: "Carry out the requested task using approved tools.", instructions: "Complete the task described. Ask for approval before any irreversible action.", modelId: "claude-sonnet-4-5", tools: ["Email send"], knowledge: [] },
    },
    { key: "output", kind: "output", label: "Deliver result", description: "Notify requester" },
  ],
  edges: [["trigger", "understand"], ["understand", "validate"], ["validate", "act"], ["act", "output"]],
};

export function pickTemplate(prompt: string): TemplateSpec {
  return TEMPLATES.find((t) => t.match.test(prompt)) ?? GENERIC;
}

function titleFrom(prompt: string) {
  const words = prompt.replace(/[^\w\s]/g, "").split(/\s+/).filter(Boolean).slice(0, 5).join(" ");
  return words ? words.charAt(0).toUpperCase() + words.slice(1) : "Untitled workflow";
}

export function makeAgent(spec: AgentSpec, workspaceId: string): Agent {
  return {
    id: uid("agt"),
    workspaceId,
    ...spec,
    fallbackModelId: "gpt-5-mini",
    temperature: 0.3,
    maxTokens: 1200,
    memory: "session",
    outputSchema: '{ "result": string, "confidence": number }',
    guardrails: { piiRedaction: true, injectionDetection: true, outputValidation: false },
    version: 1,
    status: "active",
    updatedAt: new Date().toISOString(),
  };
}

export function generateWorkflow(prompt: string, workspaceId = "ws_default"): { workflow: Workflow; agents: Agent[] } {
  const t = pickTemplate(prompt);
  const agents: Agent[] = [];
  const idByKey: Record<string, string> = {};
  const nodes: WorkflowNode[] = t.steps.map((s) => {
    const id = uid("node");
    idByKey[s.key] = id;
    let agentId: string | undefined;
    if (s.agent) {
      const a = makeAgent(s.agent, workspaceId);
      agents.push(a);
      agentId = a.id;
    }
    return { id, type: "mesh", position: { x: 0, y: 0 }, data: { label: s.label, kind: s.kind, description: s.description, tool: s.tool, agentId } };
  });
  const edges: WorkflowEdge[] = t.edges.map(([a, b, label]) => ({ id: uid("edge"), source: idByKey[a]!, target: idByKey[b]!, label }));
  const now = new Date().toISOString();
  return {
    agents,
    workflow: {
      id: uid("wf"),
      workspaceId,
      name: t.id === "generic" ? titleFrom(prompt) : t.name,
      description: prompt,
      prompt,
      scenario: t.id,
      status: "draft",
      nodes: autoLayout(nodes, edges),
      edges,
      versions: [],
      createdAt: now,
      updatedAt: now,
    },
  };
}
