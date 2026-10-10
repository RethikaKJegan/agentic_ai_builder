// Seeded demo catalog: marketplace assets, connectors and knowledge documents.
import type { Connector, KnowledgeSource, MarketplaceAsset } from "./types";

export const MARKETPLACE: MarketplaceAsset[] = [
  { id: "mk_wf_complaint", kind: "workflow", ref: "complaint", name: "Customer complaint resolution", domain: "Customer support", publisher: "MESH", description: "Triage, look up, ticket, draft and escalate critical complaints for approval.", dependencies: ["CRM lookup", "Ticketing", "Email send"] },
  { id: "mk_wf_invoice", kind: "workflow", ref: "invoice", name: "Invoice review & approval", domain: "Finance operations", publisher: "MESH", description: "Extract invoice fields, three-way match against POs and route large amounts to finance.", dependencies: ["Document parser", "ERP ledger"] },
  { id: "mk_wf_lead", kind: "workflow", ref: "lead", name: "Lead research & qualification", domain: "Sales", publisher: "MESH", description: "Research inbound leads, score fit against your ICP and alert the owner.", dependencies: ["Web search", "CRM lookup", "Slack notify"] },
  { id: "mk_wf_onboarding", kind: "workflow", ref: "onboarding", name: "Employee onboarding", domain: "HR", publisher: "Acme Ops", description: "Provision accounts, plan the first week and get manager sign-off on access.", dependencies: ["HRIS", "Calendar", "Email send"], orgOwned: true },
  {
    id: "mk_ag_contract", kind: "agent", name: "Contract clause reviewer", domain: "Document processing", publisher: "MESH", description: "Flags non-standard indemnity, liability and termination clauses against your playbook.", dependencies: ["Document parser"],
    agent: { name: "Contract Reviewer", role: "Reviewer", purpose: "Identify risky or non-standard contract clauses.", instructions: "Compare each clause to the playbook. Return clause, risk level and suggested redline.", modelId: "claude-sonnet-4-5", tools: ["Document parser"], knowledge: [] },
  },
  {
    id: "mk_ag_research", kind: "agent", name: "Market research analyst", domain: "Research", publisher: "MESH", description: "Builds sourced briefs on companies, markets and competitors.", dependencies: ["Web search"],
    agent: { name: "Research Analyst", role: "Researcher", purpose: "Produce concise, cited research briefs.", instructions: "Answer the research question with 5 key findings and cite every source.", modelId: "gemini-2-5-pro", tools: ["Web search"], knowledge: [] },
  },
  {
    id: "mk_ag_refund", kind: "agent", name: "Refund eligibility checker", domain: "Customer support", publisher: "Acme Ops", description: "Checks requests against refund policy and order history before any money moves.", dependencies: ["CRM lookup"], orgOwned: true,
    agent: { name: "Refund Checker", role: "Classifier", purpose: "Decide refund eligibility under policy.", instructions: "Return eligible, ineligible or needs review with the policy clause that applies.", modelId: "claude-haiku-4-5", tools: ["CRM lookup"], knowledge: ["Refund policy"] },
  },
  {
    id: "mk_ag_expense", kind: "agent", name: "Expense policy auditor", domain: "Finance operations", publisher: "MESH", description: "Reviews expense claims for policy breaches, duplicates and missing receipts.", dependencies: ["Document parser"],
    agent: { name: "Expense Auditor", role: "Reviewer", purpose: "Audit expense claims against policy.", instructions: "Flag duplicates, out-of-policy items and missing receipts. Summarise per claim.", modelId: "gpt-5-mini", tools: ["Document parser"], knowledge: ["Finance approval matrix"] },
  },
  { id: "mk_tl_slack", kind: "tool", ref: "con_slack", name: "Slack", domain: "Communication", publisher: "MESH", description: "Post messages and approval requests to channels.", dependencies: [] },
  { id: "mk_tl_hubspot", kind: "tool", ref: "con_hubspot", name: "HubSpot", domain: "Sales", publisher: "MESH", description: "Read and update contacts, companies and deals.", dependencies: [] },
  { id: "mk_gr_pii", kind: "guardrail", name: "PII protection pack", domain: "Governance", publisher: "MESH", description: "Turns on PII redaction and output validation for every agent in the workspace.", dependencies: [], guardrails: { piiRedaction: true, outputValidation: true } },
  { id: "mk_gr_injection", kind: "guardrail", name: "Prompt-injection shield", domain: "Governance", publisher: "MESH", description: "Enables injection detection on every agent so manipulated inputs are blocked.", dependencies: [], guardrails: { injectionDetection: true } },
];

export const SEED_CONNECTORS: Connector[] = [
  { id: "con_slack", name: "Slack", category: "Communication", description: "Messages and approval requests", tools: ["Slack notify"], status: "available" },
  { id: "con_gmail", name: "Gmail", category: "Communication", description: "Send and read email", tools: ["Email send"], status: "demo-connected", account: "ops@acme.example" },
  { id: "con_salesforce", name: "Salesforce", category: "CRM", description: "Accounts, contacts and cases", tools: ["CRM lookup", "Ticketing"], status: "demo-connected", account: "acme.my.salesforce.example" },
  { id: "con_hubspot", name: "HubSpot", category: "CRM", description: "Contacts, companies and deals", tools: ["CRM lookup"], status: "available" },
  { id: "con_gdrive", name: "Google Drive", category: "Storage", description: "Files and documents", tools: ["Document parser"], status: "needs-config" },
  { id: "con_postgres", name: "PostgreSQL", category: "Databases", description: "Query operational data", tools: ["ERP ledger"], status: "error" },
  { id: "con_webhook", name: "Webhook", category: "HTTP/API", description: "Call any HTTP endpoint", tools: ["Web search", "HRIS"], status: "available" },
  { id: "con_gcal", name: "Google Calendar", category: "Productivity", description: "Schedule and read events", tools: ["Calendar"], status: "available" },
];

const d = (days: number) => new Date(Date.now() - days * 86400000).toISOString();
export const SEED_KNOWLEDGE: KnowledgeSource[] = [
  { id: "kn_playbook", name: "Support playbook", collection: "Customer support", fileType: "PDF", sizeKb: 842, status: "ready", updatedAt: d(12) },
  { id: "kn_refund", name: "Refund policy", collection: "Customer support", fileType: "DOCX", sizeKb: 96, status: "ready", updatedAt: d(30) },
  { id: "kn_brand", name: "Brand voice guide", collection: "Marketing", fileType: "Markdown", sizeKb: 38, status: "ready", updatedAt: d(4) },
  { id: "kn_matrix", name: "Finance approval matrix", collection: "Finance", fileType: "CSV", sizeKb: 12, status: "ready", updatedAt: d(60) },
  { id: "kn_vendors", name: "Vendor master list", collection: "Finance", fileType: "CSV", sizeKb: 204, status: "processing", updatedAt: d(0) },
  { id: "kn_icp", name: "Ideal customer profile", collection: "Sales", fileType: "Web", sizeKb: 22, status: "ready", updatedAt: d(9) },
  { id: "kn_handbook", name: "Employee handbook", collection: "HR", fileType: "PDF", sizeKb: 1630, status: "failed", updatedAt: d(2) },
];
