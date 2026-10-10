# UI Agent Model to Agent Contract v1

The active Mesh/Next.js UI from `incoming/pixel-perfect-match-latest.zip` is a presentation and local draft editing model. The backend `agent-contract-v1.json` is authoritative for validation and execution. The old `agentt.zip` is historical input.

| Existing UI field | Contract field | Integration rule |
| --- | --- | --- |
| `Agent.id` | `agent_id` | Preserve the stable ID; reject duplicate IDs. |
| `Agent.name` | `name` | Display label only; backend validates length and presence. |
| `Agent.role` | `role` | Runtime responsibility. |
| `Agent.purpose` | `goal` | Map to the contract goal; do not silently replace it with UI copy. |
| `Agent.instructions` | `instructions` | Send for validation; never allow raw credentials. |
| `Agent.modelId` | `model.model_id` | Resolve through the approved model provider configuration. |
| `Agent.tools` | `allowed_tool_ids` | Treat UI selections as requests until Tool Registry authorization succeeds. |
| `Agent.knowledge` | Future knowledge references | Keep as UI metadata until the later knowledge contract is defined. |
| `Agent.maxTokens` | `limits.max_tokens` | Convert and validate against workflow limits. |
| `Agent.guardrails` | `guardrails` | Map the three supported guardrail flags. |
| `fallbackModelId`, `temperature`, `memory`, `version`, `status` | Contract metadata or later contract stage | Do not make these execution-authoritative until the later model/version contract is approved. |

Local settings are draft requests. They must not imply backend authorization or runtime enforcement. Demo/nonworking execution and configuration actions have been removed from the active baseline; backend controls return only when their accepted adapters are implemented.

## New UI integration notes

`WorkflowNode.data.parentNodeId`, hierarchy `role`, collapse state and `position` currently describe the local editor. Map presentation coordinates/collapse into optional layout metadata; never infer execution order or authority from visual nesting. Execution hierarchy semantics need explicit accepted-contract representation before submission.

The local `Workflow` shape (`id`, `workspaceId`, `nodes`, `edges`, `versions`) remains an editor view model. Task 1.2 must add a canonical boundary adapter; task 2.3 must replace browser persistence for backend lifecycle operations. Local `Agent.tools` selections remain requirements, not authorized `allowed_tool_ids`.

Routes are `/`, `/app`, `/app/workflows`, `/app/workflows/[id]`, `/app/agents`, `/app/marketplace`, `/app/integrations`, `/app/knowledge`, `/app/approvals`, `/app/runs`, `/app/monitoring`, `/app/governance`, and `/app/settings`. No backend HTTP routes were introduced by the migration.
