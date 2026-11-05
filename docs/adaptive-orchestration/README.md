# Adaptive orchestration (Phase 2)

Backend continuation of connected action plans. `AdaptiveOrchestration` validates decisions and changes case state; `LifecycleDriver` supplies bounded continuation and `GraphRunner` remains the only executor. CrewAI, Registry checks, connector journals, case/run persistence and memory remain in place. Existing Phase 1 requests keep `orchestration-plan-v1` behavior.

## Contracts and flow

`shared/contracts/evaluator-decision-v1.json` defines `continue`, `gather_context`, `revise_plan`, `request_input`, `wait_for_event` and `complete`. Decisions cite current observation IDs, action IDs and exact completion criteria. The backend rejects invented observations, stale revisions, unknown capabilities, invalid bindings, inferred authority and premature completion.

The persistent case moves through `UNDERSTAND` → `PLAN` → `GATHER_AND_ASSESS` → `EXECUTE` → `EVALUATE`. Understanding retains the original goal, constraints and proposed completion criteria. Planning uses a supplied proposal or the existing OpenAI planner. Evaluation receives actual results and can choose any of the six decisions. One selected action, including its existing approval/condition nodes, may execute before evaluation resumes. Direct runtime workers also enforce this case permission. The final runtime output node runs only after validated completion. Conditional skips retain Phase 1 graph semantics.

`orchestration-plan-v2` adds a stable plan ID, revision number, previous composition/revision/fingerprint, rationale and triggering observations. Frozen v1 contracts are unchanged. Successors are separately compiled immutable compositions/workflows, using existing storage. Completed action definitions, outputs, receipt identities and usage are carried forward from persisted runtime records. The old run is superseded, pending approvals become unusable, and new actions require normal workflow/Registry review and exact-payload approval. No approval is copied as authority for an unfinished action. Content changes after generation use a new content action and revised unfinished consumers.

## API

All commands use the existing authenticated business-ontology API and workspace/owner scope:

- `POST /business-ontology/v1/cases/{case_id}/adaptive`: `request_key`, `expected_revision`, `stage_instance_id`, `plan_request`, optional `limits`. Select one idle ready stage of an already prepared case; the request uses Phase 1 connected-plan fields. Original goal/client/account/preparation pins come from the case.
- `POST /business-ontology/v1/cases/{case_id}/drive`: existing bounded driver contract (`request_key`, optional `max_commands`, `max_stage_executions`, `max_seconds`). Approval waits still use existing workflow/Registry and runtime approval APIs.
- `POST /business-ontology/v1/cases/{case_id}/adaptive/revise`: `request_key`, `expected_revision`, `expected_plan_revision`, `proposal`, `rationale`, `observation_ids`. Requires current scoped observations and an idle, reconciled run.
- `POST /business-ontology/v1/cases/{case_id}/adaptive/supply`: `request_key`, `expected_revision`, `wait_id`, plus exactly `inputs` or `event`. Inputs must match saved schemas and cannot overwrite existing input pins. Event reports require `events.ingest`, matching source/type and valid payload; authenticated reports do not prove physical completion.
- `GET /business-ontology/v1/cases/{case_id}/sections/adaptive`: inspect phase, revision history, decision records, waits, reservations and failures. Full records also remain on the existing case/run endpoints.
- Existing case `cancel` remains available. Other ordinary stage commands are rejected while this case is under adaptive control.

A stage's existing output bindings, schema, completion predicates and provisional policy still apply. The plan must be compatible with those bindings. Enabling adaptive control does not rewrite an installed Simpson or retail process. Acceptance fixtures use compatible stage definitions; the retail test uses native retail package contracts, mappings and registered source adapter.

## Evidence, memory and budgets

Each evaluator context contains the original goal, scope, constraints, current actions, ontology/mapping pins, available evidence, actual action observations and output digests, verified receipts, pending waits and remaining budgets. It uses `WorkingMemory.case_view` and existing validated ExperienceMemory recommendations. Projections are bounded; complete outputs remain in immutable composition/run records. Receipt references replace large payload duplication in memory. Evidence text and memory never grant authority.

Additional registered read/reasoning actions may expand retrieval tasks using the same ontology, mapping, provider, source-connection and identifier pins. Existing executable capability contracts remain pinned; newly expanded preparation carries the additional mapped facts. Native package reads must match the pinned package, revision and capability. ACTUAL source/connector reports and INFERRED model content keep their existing provenance rules.

Server ceilings/defaults are 16 reasoning turns, four plan revisions, 1,000,000 conservatively reserved tokens, 32 tool calls, 64 total model calls and 600 seconds. Evaluator output allowance is 2,000 tokens per call and can be reduced. Planner/evaluator input bytes conservatively reserve token capacity before calls; actual bounded planning context includes the catalogue and evidence. Runtime usage carries across successors and combines with reasoning reservations. Narrower existing plan/runtime deadlines and limits still apply. Context is capped at 96,000 bytes; oversized context blocks instead of silently losing mandatory fields.

Case CAS, command receipts, evaluation intents, run checkpoints and connector effect journals prevent automatic duplicate work. Definite failures can return to evaluation; uncertain effects block revision until existing runtime/connector reconciliation establishes their outcome. An interrupted evaluator call retains its charged intent and requires operator review rather than automatic model replay. Expired waits or exhausted budgets remain inspectable and require an operator decision; this phase adds no background scheduler.

## Verification and limits

See [verification.md](verification.md) for exact commands/results and trace hashes. Controlled providers exercise actual case/Registry/GraphRunner/CrewAI/connectors with disposable persistence. These tests do not establish live model quality, live account consent, physical repair, warranty eligibility or commercial authority.

Phase 3 remains: scheduled/recurring continuation, Gmail reply workers and the separately authorized event-processing integrations. Frontend changes, deployment and live external writes are outside this phase.
