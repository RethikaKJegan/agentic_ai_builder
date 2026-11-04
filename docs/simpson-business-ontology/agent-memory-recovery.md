# Phase 3: memory, recovery and client packages

Backend only. No deployment, frontend edits, live company writes, live Google actions, paid model evaluation or reinforcement learning.

## Execution memory

`RuntimeService.working_memory` builds master/task views from existing `runtime_runs`. The master receives the objective, task dependency graph, completed/pending identifiers, verification classifications, recent errors/recovery summaries and knowledge pins. Children receive their own task, direct dependencies, exact allowed tool candidates, completion criteria and relevant attempts. The existing composition guard supplies task-specific ontology and mapped evidence. Full source envelopes remain separate from model context. The new memory view has a byte bound and a conservative UTF-8-byte token bound; existing model token accounting/usage policies still apply. Required context is rejected with `WORKING_CONTEXT_LIMIT` rather than silently truncated.

Verified child outputs persist under `runtime_runs.document.task_checkpoints` immediately on completion. They include task, agent and invocation-node identity, completion time and actual verified output. Restart/resume restores these checkpoints instead of delegating unaffected completed tasks again. Model/tool usage, effect identities, inputs, original creation time, workflow digest and audit events remain on the same run.

## Experience schema and lifecycle

The same workflow database contains `runtime_experiences(workspace, owner, experience_id, document)`. Documents contain domain, capability, failure category, an allowlisted recovery strategy code, evidence references, validation state, version pins, creation/expiry, invalidation conditions, optional agent scope and verified outcome. Experiences contain strategy hints, never previous business conclusions or reusable approval authority.

Candidate creation requires current execution permission. Promotion requires an approver/admin with `workflow.approve`, provenance referencing an actual completed recovered run, matching capability/knowledge pins and a matching strategy/category whose recovery was verified. Candidates do not enter agent context. Retrieval checks workspace AND owner, domain, capability, optional agent scope, category, expiry and ontology/mapping/package versions. Expired or version-mismatched entries become invalidated. Explicit invalidation accepts operator correction, withdrawn source or contradicted outcome. The user/Registry/source authority remains current; a hint never changes executable controls.

## Failure taxonomy and recovery

`runtime/recovery.py` maps stable error codes to invalid model output, missing evidence, invalid values, stale metadata, bad mappings, connector timeout/authentication, revoked authorization, conflicting evidence, unsupported capabilities, tool failure, uncertain external effects and dependency failure. Unknown errors require review. Error records identify task/tool, retry eligibility, recovery strategy and need for intervention.

Recovery is explicit, using `runtime.recovery.resume(run_id, auth, changed_dependencies=[...])`. It requires the original owner, expired worker lease, current approved revision/grants, unchanged digest and remaining deadline/retry budget. Source checks happen outside write transactions; an optimistic run-state check prevents applying recovery to concurrently changed state. Completed mapped reads are revalidated; changed observations invalidate their task and dependency descendants. Unchanged checkpoints remain completed. Typed refs cover concepts, record IDs, mapping IDs, source collections, selected rule/relationship IDs, knowledge hashes and task outputs. Invalidated results are archived in recovery history; the existing graph coordinator/output descendants are cleared and queued through the normal worker. No separate scheduler is introduced.

New compositions can explicitly request `recovery_max_retries` (0–3, bounded by current Registry policy). The approved workflow includes that allowance and enough bounded child call/tool capacity where Registry policy permits. Default remains zero; old workflows gain no new retry allowance. Every retry uses existing runtime reservation checks and retains prior charges. Existing model-output correction remains the first bounded correction mechanism.

Uncertain external writes are blocked with `RECOVERY_RECONCILIATION_REQUIRED`; this phase does not blindly replay or fabricate a reconciliation receipt. Existing connector effect journals/remote reconciliation must be inspected before an operator prepares a fresh explicit action. Completed downstream writes also prevent upstream replay. Missing input/evidence, mapping correction and changed knowledge require the existing typed-input/review/new immutable preparation lifecycle; resume does not mutate inputs or republish ontology.

## Client knowledge packages

`workflow_api/client_packages.py` stores immutable owner/workspace-scoped versions in `client_knowledge_packages`. A package contains client/domain identity, ontology version, concepts/parents, relationships, source mappings, evidence requirements, registered capability contracts, declarative scalar-comparison rules, resource bindings and validation requirements. Structural validation rejects unknown concepts/mappings/dependencies, inheritance/task cycles, malformed contracts and unsupported rules. Same ID/revision cannot be overwritten. Old versions remain available.

The shared preparation boundary accepts a package adapter; `BusinessComposition.prepare` accepts `client_package_id` and `client_package_revision`. The existing planner selects registered operations (or explicit typed operations in offline diagnostics). The same task compiler, temporary agent factory, Registry matching, canonical workflow lifecycle, delegation, CrewAI adapter, memory and recovery are reused. Package-defined tools are restricted to authorized mapped reads; package data cannot install code, SQL, connectors, permissions or approvals. Source adapters are operator-registered current-auth callables, bound to workspace and owner; arbitrary new clients still need real authorized adapters and knowledge configuration.

The `client_package_read` connector is workflow-bound to the exact package hash/version. It projects only configured source fields, evaluates allowlisted numeric comparisons (`lt`, `lte`, `eq`, `gt`, `gte`) and emits normal mapped evidence/coverage. Missing/invalid values remain gaps. Contradictory values for the same source identity remain conflicts. No procurement or stock-change write is implemented by the inventory fixture.

The isolated retail acceptance fixture defines Store, Product, Inventory, Supplier and ReplenishmentRequest. Two records deliberately produce one below-threshold and one above-threshold result. It executes through the same composition and actual CrewAI adapter with deterministic model transport. Simpson continues using its existing richer ontology/evidence adapter; its knowledge is not republished or replaced by the retail fixture.

## Outcome evaluation

Terminal runs persist `outcome_evaluation`: requested/achieved outcome, evidence coverage, business-rule evaluation status, tool receipts/failures, recovery count/success, duration, model usage/cost and available corrections. A completed workflow is distinct from supported business conclusions. Recovery success requires affected tasks to return completed results. These are evaluation records, not training or automatic policy release.

## Backend interfaces

Existing authenticated session transport applies:

- `POST /business-ontology/v1/client-packages` — validate/persist an immutable package.
- `GET /business-ontology/v1/client-packages/{package_id}/{revision}` — read an owned version.
- Existing `POST /business-ontology/v1/compositions` — accepts package selection and optional `recovery_max_retries`.
- `POST /business-ontology/v1/experiences/{candidate|relevant|validate|invalidate}` — structured memory lifecycle.
- `POST /business-ontology/v1/recovery/{run_id}/resume` — body `{}` or `{"changed_dependencies":["mapping:ticket_id"]}`; queues eligible recovery, does not approve anything.
- `GET /business-ontology/v1/run-memory/{run_id}` — bounded owner-scoped master working view.
- `GET /business-ontology/v1/run-outcomes/{run_id}` — persisted evaluation.

Candidate example body (use actual pinned versions and a real recovered run for validation):

```json
{"domain":"configured_business_ontology","capability":"business.read.inspection","category":"connector_timeout","strategy":"retry_read","evidence_references":[{"run_id":"YOUR_RUN_ID"}],"pins":{},"expires_at":1900000000}
```

Empty pins in that illustrative body do not satisfy promotion for a version-pinned run. Copy its exact knowledge pins. Validation body: `{"experience_id":"YOUR_EXPERIENCE_ID","run_id":"YOUR_RECOVERED_RUN_ID"}`.

## Exact local tests

```bash
cd /home/raf/agentic-ai-builder
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider tests/test_agent_memory_recovery.py
```

This performs isolated store/Registry/workflow execution, interruption/resumption, checkpoint/context isolation, dependency invalidation, memory validation/expiry/isolation, stale/revoked causes, retry budgets, model correction, uncertain writes and Simpson/retail acceptance. Actual CrewAI is exercised with fake model responses. No real provider side effects.

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider \
 tests/test_business_composition.py tests/test_business_preparation.py \
 tests/test_dynamic_delegation.py tests/test_delegated_tools.py
```

Verified: 42 Phase 3 cases; 316 distinct backend tests plus 34 subtests across the final regression suites. Detailed final counts and limitations are in `openspec/changes/agent-memory-recovery/verification.md`.

## Boundaries

No autonomous ontology correction/publication, learned policies, model-weight training, automatic write reconciliation, arbitrary input mutation on an existing run, UI integration or deployment. Current policy may refuse recovery if call/tool/token/time allowances are exhausted. Source revalidation reads can incur source latency. Strategy memory is intentionally scoped to owner/workspace; cross-owner organisational sharing is not enabled. A new domain needs validated package data, registered tools and authorized source adapters; supported comparison rules do not replace an arbitrary policy engine. Source/knowledge drift that cannot preserve the pin needs a new reviewed preparation. Historical pre-Phase-3 compositions retain their original compilation and permissions.
