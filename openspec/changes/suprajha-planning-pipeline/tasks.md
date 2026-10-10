# Tasks

## 1. Contract-boundary setup

- [x] 1.1 Create the planner request/response adapter using `api-payloads-v1`, `error-format-v1`, and `auth-permissions-v1`; verify valid, missing-objective, and unauthorized requests produce accepted payloads.
- [x] 1.2 Load the workflow, agent, tool, branching, approval, run-status, and versioning schemas from `shared/contracts/`; verify the planner has no duplicate local contract definitions.
- [x] 1.3 Add workspace-scoped idempotency handling with request fingerprints and contract-version metadata; verify repeated keys do not create duplicate planning results.

## 2. Structured planning

- [x] 2.1 Implement the OpenAI structured-output adapter behind a replaceable provider boundary; verify a model response is parsed without exposing the API key or provider payload.
- [x] 2.2 Implement objective decomposition into ordered workflow nodes, dependencies, agent requirements, deterministic steps, and unresolved requirements; verify generic support, onboarding, procurement, and reporting examples.
- [x] 2.3 Implement explicit capability and tool-reference extraction without permission grants or fabricated tools; verify unknown external operations remain unresolved.
- [x] 2.4 Implement condition, branch, approval-gate, rejection-path, and timeout representation; verify risky side effects cannot bypass an approval requirement.

## 3. Validation and safety

- [x] 3.1 Implement normalized workflow validation, including duplicate IDs, missing references, invalid transitions, graph bounds, and required fields; verify malformed model output is rejected before persistence.
- [x] 3.2 Add secret and sensitive-data redaction/rejection checks for prompts, logs, drafts, and errors; verify fixtures contain no credentials or provider secrets.
- [x] 3.3 Map planner failures to stable error codes with request and correlation IDs; verify field paths and retryability match `error-format-v1`.

## 4. Tests and handoff

- [x] 4.1 Add unit and contract tests for valid planning, invalid model output, unresolved tools, approval gates, idempotency, and authorization; verify the planner test suite passes.
- [x] 4.2 Add a planner handoff document listing capability identifiers, agent requirements, unresolved requirements, API examples, and downstream notes for Aravind, Harihar, and Rethika; verify each consumer has a named input.
- [x] 4.3 Run `python3 scripts/validate_contracts.py` and strict OpenSpec validation; verify the planner change is complete without modifying the existing Praxi or fire-detection projects.
- [ ] 4.4 Perform Suprajha's acceptance review: run the full planner test suite, contract validation, strict OpenSpec validation, and three generic example flows; record pass/fail evidence and obtain Aravind's review of the planner handoff before marking the segment ready.

## Workflow follow-up

- Apply this change only when Suprajha begins implementation.
- After implementation and review, notify Aravind, Harihar, and Rethika using the contributor handoff files.
- Archive the change only after all tracked tasks and downstream handoffs are complete.
