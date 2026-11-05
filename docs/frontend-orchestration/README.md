# Business Investigation frontend — Phase 4

Open **Workflow → Business investigations → New connected investigation**. This extends `/app/workflows/investigate`; the existing investigation, dynamic composition and persistent lifecycle views remain available.

Describe the business goal, choose an owned Google connection, supply the authorized recipient and any required resource values, and request a plan. The backend planner selects actions; the frontend contains no prompt-keyword workflow templates. Planning creates no external effects. Review each action's dependencies, capability, agent, selected tools, typed bindings, evidence requirements, expected output schema, approval requirements and completion criteria. Save, validate and approve the workflow before running it.

Consequential actions expose their own persisted exact payload and digest. Approve or reject the specific gate. Changing inputs requires a new backend plan/revision and fresh authorization. Completed actions show saved findings, source references, assumptions, provider identifiers and receipts. Clickable artifact URLs come only from completed actions marked as verified connector results; the UI never constructs Gmail, Sheet or Calendar URLs. Research evidence and generated content remain inspectable as saved outputs. ACTUAL, DERIVED, INFERRED and SYNTHETIC values retain their distinctions. Provider confirmation does not prove physical/business completion.

## Adaptive cases

Use the existing persistent lifecycle case form to select an installed process or client package, enter the original goal and actual inputs, choose the account and create/prepare the case. Open an idle READY stage, then enable adaptive planning with explicit recipient/resource values. The stage must support the desired actions, tool allowlist, output bindings and completion predicates. Enabling adaptive control does not rewrite installed Simpson or retail process definitions.

The five-state display reads the persisted `UNDERSTAND`, `PLAN`, `GATHER_AND_ASSESS`, `EXECUTE`, `EVALUATE` state. Continue uses a bounded backend driver turn. Plans remain inspectable and require workflow/Registry review; each consequential action still needs its own exact-payload decision. Typed missing-input waits expose the backend field names and schemas. Supply exactly the requested actual values. Revisions, evaluator decisions, evidence gaps, usage, errors and wait history are preserved. Unknown effects and interrupted evaluator intents stay blocked for operator reconciliation; this UI grants no new reconciliation authority.

A saved case URL (`?case=...`) or connected plan/run URL (`?connected=1&composition=...&run=...`) restores persisted state. Read polling submits no execution commands. Owner/workspace changes remount scoped panels; stale reads are discarded. Commands use stable owner/workspace/operation/payload digests with opaque session-storage keys. No prompt, recipient, content, credentials or source records are stored by that mechanism. Duplicate clicks are locked. Unknown command outcomes require explicit identical-key retry or inspecting saved state; they are never automatically replayed.

## Replies, timers and recurrence

Open **Background continuation & recurring automation** in a case or connected investigation.

- A Gmail reply subscription binds the current case/wait/stage, selected account, actual completed-send thread/message/RFC identifiers, expected sender addresses, expected information, typed payload paths, deadline and an approved thread-reading workflow revision. Review the complete request before confirming. It resumes the same case/run. Email content grants no permission.
- A timer references a current case wait and a purpose/deadline. It creates an observation for reevaluation; it does not authorize a reminder.
- Recurring business consent requires an authorized approver, the selected account, registered tool IDs with local input schemas, explicit `const`/`enum` identity/destination restrictions, purpose, content scope, cron/timezone, occurrence/action ceilings and expiry. The advanced scope editor exposes the exact backend schema, including authorized recipients; it does not broaden policy.
- A recurring schedule selects an independent approved workflow revision and saved consent ID, exact cron/timezone, missed-run/overlap policy and explicit execution inputs. Adaptive case-owned revisions cannot be scheduled. Each occurrence creates a distinct execution with fresh mapped reads.

Records show actual state, due time, latest occurrence visible on the current bounded page, full saved history/error/receipt references and recent worker jobs/health. Pagination is explicit. Use the existing run inspector for an occurrence's recorded inputs, results and effects. Pause/resume/cancel controls apply to active records; consent can be revoked. Provider revocation and scope/expiry changes are enforced by the backend at execution.

## Integration points

All requests reuse `WorkflowClient` and the existing same-origin authenticated proxy, session recovery, origin protection, error envelope and backend authorization. Local permission checks only disable controls; the backend remains authoritative.

| API | Integration |
| --- | --- |
| POST/GET `/business-ontology/v1/action-plans[/{composition_id}]` | Goal planning and immutable plan inspection |
| POST `/business-ontology/v1/compositions/{id}/workflow`, GET `/{id}/view?run_id=...` | Existing canonical workflow, assignments, persisted action results and exact approval payloads |
| Existing workflow save/validate/approve/execute APIs | Review and authorized execution through the existing lifecycle |
| Existing approval decision and composition cancellation APIs | Exact gate approve/reject and cancellation |
| Existing case/process/package/create/prepare/drive/cancel APIs | Original case workflow and bounded adaptive continuation |
| POST `/business-ontology/v1/cases/{id}/adaptive[/supply]` | Enable adaptive planning and supply typed missing information |
| GET `/business-ontology/v1/automation`, GET `/{id}` | Scoped record pages, history, jobs and health |
| POST `/automation/subscriptions`, `/authorizations`, `/schedules`, `/timers`, `/{id}/control` | Reviewed durable continuation and recurring operations |
| Existing Google connection listing | Actual selected account/status; no silent account substitution |
| Existing `/app/runs?run=...` inspector | Canonical occurrence event and effect history |

The API client also provides the existing adaptive revision endpoint for explicit backend proposals. The UI observes evaluator-driven replanning and immutable history; it does not offer an unvalidated client plan editor.

## Validation and deployment

See [verification.md](verification.md) for exact commands/results and controlled browser evidence, and [live-provider-checklist.md](live-provider-checklist.md) for separately authorized live acceptance. No deployment or live readiness is implied by local controlled tests.
