// Model catalog. No provider is connected in this prototype — every model is demo-only.

export interface ModelOption {
  id: string;
  provider: "OpenAI" | "Anthropic" | "Google";
  name: string;
  capabilities: string[];
  costTier: "$" | "$$" | "$$$";
  /** Simulated USD per 1K tokens. */
  costPer1k: number;
  /** Simulated latency multiplier. */
  speed: number;
  configured: boolean;
}

export const MODELS: ModelOption[] = [
  { id: "gpt-5", provider: "OpenAI", name: "GPT-5", capabilities: ["Reasoning", "Tools", "Vision"], costTier: "$$$", costPer1k: 0.012, speed: 1.4, configured: false },
  { id: "gpt-5-mini", provider: "OpenAI", name: "GPT-5 mini", capabilities: ["Fast", "Tools"], costTier: "$", costPer1k: 0.002, speed: 0.6, configured: false },
  { id: "claude-sonnet-4-5", provider: "Anthropic", name: "Claude Sonnet 4.5", capabilities: ["Reasoning", "Long context", "Tools"], costTier: "$$", costPer1k: 0.009, speed: 1.1, configured: false },
  { id: "claude-haiku-4-5", provider: "Anthropic", name: "Claude Haiku 4.5", capabilities: ["Fast", "Classification"], costTier: "$", costPer1k: 0.0025, speed: 0.5, configured: false },
  { id: "gemini-2-5-pro", provider: "Google", name: "Gemini 2.5 Pro", capabilities: ["Reasoning", "Multimodal", "1M context"], costTier: "$$", costPer1k: 0.007, speed: 1.2, configured: false },
  { id: "gemini-2-5-flash", provider: "Google", name: "Gemini 2.5 Flash", capabilities: ["Fast", "Multimodal"], costTier: "$", costPer1k: 0.0015, speed: 0.45, configured: false },
];

export const getModel = (id: string) => MODELS.find((m) => m.id === id) ?? MODELS[0]!;

export const TOOL_CATALOG = [
  "CRM lookup",
  "Ticketing",
  "Email send",
  "Slack notify",
  "Web search",
  "Document parser",
  "ERP ledger",
  "HRIS",
  "Calendar",
] as const;

export const KNOWLEDGE_CATALOG = [
  "Support playbook",
  "Refund policy",
  "Brand voice guide",
  "Finance approval matrix",
  "Vendor master list",
  "Ideal customer profile",
  "Employee handbook",
] as const;
