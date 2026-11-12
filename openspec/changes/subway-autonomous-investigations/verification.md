# Phase 2 implementation and verification

Local repository implementation; no deployment, production restart, external
communication, business-record write or live paid model call was performed.
Phase 1 changes already present in the working tree were retained.

## Implementation

Normal Subway Overview requests classified as read-only `investigation` now
compile an explicitly reviewed `workflow-investigation` control declaration.
Ordinary population queries, knowledge explanations, previously persisted plans,
other tenants and business-case workflows retain their existing execution path.
No Subway business case, stage or Simpsons lifecycle is created.

The existing worker calls GraphRunner. For eligible runs, GraphRunner invokes
run-owned adaptive control before dispatching work. The controller reserves a
reasoning turn, persists an exclusive claim, calls the existing OpenAI evaluator,
validates its structured assessment, and grants one ready action. GraphRunner
alone executes that action through existing CrewAI and Registry boundaries.
Another evaluation follows execution; the final output node is gated until the
objective assessment is eligible and required actions have completed.

The controller supports continue, retrieve-more, replan, typed business-input
waits, qualified completion and explicit blockers. Existing runtime failures,
cancellation and approval mechanisms remain authoritative. Input waits are
run metadata/events while the existing runtime status remains queued/running;
no incompatible new runtime status was added. Read-only continuation never
grants a new external write or bypasses an exact-payload approval.

## Revisions, ownership and budgets

Revisions use the existing action binder, canonical orchestration-plan-v2
validation, compiler and DAG validation. The immutable approved workflow is
revalidated on execution. A validated effective DAG is persisted in that run,
with its digest and revision history; it does not rewrite the approved revision.
Registry-reviewed agent definitions, tools, grants, execution policy, scope,
original objective and constraints remain pinned.

Completed actions are immutable and retained with their receipts, outputs,
provenance, checkpoints and input bindings. Revised edges are reconstructed
from stable completed nodes. Failed/retired actions remain in execution history;
retired identifiers cannot be reused. Correlation IDs and cumulative usage stay
on the same run. Serial database transactions and claim tokens prevent competing
workers from committing conflicting evaluator decisions.

Default controller ceilings: 16 reasoning turns, 4 plan versions, 4 retrieval
rounds, 2 consecutive decisions without progress, 2 recoverable action-validation
failures, and 2 retries after explicit provider 429/503 rejection. Time, tool and
model-call limits also respect initial plan constraints. Evaluator requests reserve
bounded input/output usage before provider calls. Successful CrewAI calls settle
confirmed usage; failed or uncertain calls retain their reservations. Existing
provider capacity controls are consulted. An expired unknown evaluation claim
blocks rather than silently repeating a potentially paid request.

Revisions are intentionally limited to capabilities with exact agent/tool
authority already included in the initial reviewed workflow. New connectors,
write capabilities or increased allowances require another review. Business
input waits retain the original workflow deadline; input cannot reset budgets
or overwrite an existing execution input.

## Evidence and reports

The additive `investigation-assessment-v1` contract leaves evaluator-decision-v1
and the existing workflow/agent/tool contracts unchanged. It records objective,
stable requirements, findings, gaps, source limitations, invalid assumptions,
recoverable failures, rule classifications, completion eligibility and optional
numeric calculations.

Subway evidence checks compare the actual stored receipt, query hash, output
fingerprint, ontology version, owner/workspace, source authority, coverage and
join checks. A successful HTTP response or model-generated report is not business
evidence. Incomplete detail, missing currency and invalid receipts cannot support
a verified requirement. Findings must copy an exact value at a cited source
location. Difference/ratio calculations are recomputed with Decimal arithmetic;
incorrect arithmetic is rejected. Arithmetic alone establishes neither comparable
business scope nor a currency, policy, payment, approval or causal explanation.

Company-specific policy cannot be inferred from code, filenames or a model's
confidence. Missing policy and explicit user analytical thresholds have separate
classifications. No new authoritative company policy or executable policy
definition was installed. Contradictory sources remain separate source receipts;
the evaluator is instructed to retain unresolved conflicts as gaps and cannot
invent source precedence or verified cross-system identities.

`subway_documents` is a bounded read-only Registry tool over existing owned
BusinessDocuments text and hash-checked saved Subway ontology/resolution sources.
It returns actual passages, document identity, content/excerpt hashes, character
offsets, scope and ontology version. It reuses existing text ingestion and source
storage. There is no new OCR, PDF parser, external download or claim that attachment
metadata proves indexed bytes. Keyword passage selection is bounded to eight
records and 12,000 characters. Unavailable attachment bytes remain a limitation.

The existing connected Overview workspace and builder execution view show
objective, evaluation status, plan revision, requirements, findings, calculations,
gaps, blockers and typed input continuation. Composition graphs/steps project the
effective revised plan. Existing Knowledge Map usage remains attached to exact
executed actions; each adaptive action also records its plan revision/fingerprint,
and document reads record exact passage provenance. Generated report prose is
explicitly qualified as interpretation; the assessment controls completion.

## Memory and agent boundaries

Existing WorkingMemory, bounded context, experience recommendations, account
knowledge pins and persisted checkpoints are reused. Continuation uses the current
scoped run's results; historical strategy guidance grants no data or execution
authority and is not promoted to a current company fact. Cross-run business-result
caching is not added without proof of current source freshness.

OpenAI interprets objectives, plans and evaluates gaps. Existing CrewAI executes
registered analysis/query/report tasks. Registry enforces current tool schemas,
grants, credentials and tenant permissions. GraphRunner owns dispatch, leases,
checkpoints, action outcomes and recovery. No second execution engine or mandatory
new agent classes were introduced.

## Phase 2 file inventory

New:

- `runtime/adaptive_context.py`
- `workflow_api/workflow_adaptive.py`
- `workflow_api/subway_documents.py`
- `shared/contracts/investigation-assessment-v1.json`
- `tests/test_subway_autonomy.py`
- `frontend/src/api/adaptive.ts`
- `frontend/src/features/builder/AdaptiveProgress.tsx`
- `frontend/src/features/builder/AdaptiveProgress.test.tsx`
- This OpenSpec change's proposal, tasks, requirements and verification report.

Extended:

- `planner/provider.py`
- `runtime/action_plans.py`, `runtime/adaptive_control.py`, `runtime/graph.py`,
  `runtime/service.py`
- `workflow_api/action_plans.py`, `workflow_api/adaptive_orchestration.py`,
  `workflow_api/composition_presentation.py`, `workflow_api/live_providers.py`,
  `workflow_api/main.py`, `workflow_api/subway_queries.py`
- `scripts/generate_ui_contracts.py`
- `frontend/src/api/client.ts`, `frontend/src/api/compositions.ts`,
  `frontend/src/api/contracts.generated.ts`
- `frontend/src/features/builder/ExecutionView.tsx`,
  `frontend/src/features/builder/useWorkflowTrace.ts`
- `frontend/src/features/investigations/ConnectedPlan.tsx`
- `frontend/e2e/subway-intelligence.spec.ts`

Other dirty files belong to the pre-existing work and Phase 1, not this inventory.

## Verification record

Observed before final consolidated rerun:

- Phase 1 acceptance baseline: 15 passed.
- Compatibility packet: 168 passed, 18 subtests passed. Included existing adaptive
  orchestration, runtime, connected plans, Subway query/authentication and Simpsons
  isolation tests.
- Initial adaptive acceptance: 12 passed. Subsequent expanded checks found a
  progress-accounting issue during rejected-query correction; it was fixed to
  recognize new completed actions/failures as progress. The correction plus budget
  and invoice scenario follow-up passed (3 tests).
- Stronger restart check clears process-local Registry caches and constructs a
  new RuntimeService/GraphRunner over saved state. It and arithmetic rejection
  passed (2 tests).
- Frontend first complete run: 604 passed across 90 files.
- Desktop/mobile production-build browser journeys: 14 passed, including normal
  Overview, adaptive input resume, reports and multi-tenant Knowledge Map behavior.
- Types, lint, isolated production build, generated contract drift, shared contract
  fixtures and strict scoped OpenSpec validation passed at their recorded stages.

These counts overlap and must not be added. Two later backend reruns and one
frontend rerun encountered root-filesystem exhaustion (`ENOSPC`); they are not
reported as passing. Only this task's temporary test directories were moved to
shared memory, preserving artifacts. The final consolidated rerun uses shared
memory for test databases and temporary files.

Final observed results (11 November 2026):

| Check | Result | Evidence log |
| --- | --- | --- |
| Consolidated backend packet below | 317 passed, 0 failed, 0 skipped; 18 subtests passed; 210 warnings | `/tmp/subway-phase2-final.log` |
| Autonomous acceptance plus existing adaptive orchestration, including refreshed business input and shared helper extraction | 44 passed, 0 failed, 0 skipped; 82 warnings | `/tmp/subway-phase2-acceptance-complete.log` |
| Final quota exhaustion, revoked source scope and completion with commit-time evidence revalidation | 3 passed, 0 failed, 0 skipped | `/tmp/subway-phase2-boundaries.log` |
| Actual OpenAI evaluator adapter with controlled transport and additive schema | 1 passed, 0 failed, 0 skipped | `/tmp/subway-phase2-provider.log` |
| Complete frontend suite | 604 passed in 90 files | `/tmp/subway-phase2-frontend-verified.log` |
| Final production-build desktop/mobile browser journeys | 14 passed | `/tmp/subway-phase2-browsers-final.log` |
| Final types | Passed | `/tmp/subway-phase2-types-complete.log` |
| Final lint | Passed | `/tmp/subway-phase2-lint-final.log` |
| Final isolated production build | Passed | `/tmp/subway-phase2-build-final.log` |
| Shared contract fixtures, generated drift, whitespace, strict OpenSpec | Passed | Commands recorded here |

The autonomous module contains 23 distinct tests across the consolidated packet
and follow-ups. Counts in the table overlap. The focused follow-ups verify the
last controller changes; do not add the table's counts as distinct coverage.
Simpsons isolation and its existing adaptive/lifecycle behavior passed in the
backend compatibility checks. Existing FastAPI/jsonschema deprecation warnings
were retained rather than broadening this change into a framework migration.

Final source-capacity checks ensure exhausted provider deferrals and revoked
source scope persist a blocker. Receipt/source authority is revalidated again
when an evaluator decision commits. New business input refreshes query context
instead of leaving the planner with its original pre-wait snapshot.

The production build used `/dev/shm/subway-phase2-build-h6t8eo_w/frontend`.
The active repository `.next` build was not overwritten. Logs and shared-memory
artifacts are local verification evidence and can be transient; this report and
the tests preserve the reproducible implementation record.

## Reproduction

From `/home/raf/agentic-ai-builder`, use the existing integration environment:

```bash
env -u BUILDER_DATABASE_URL -u BUILDER_AUXILIARY_DATABASE_URL \
    -u BUILDER_CLIENT_ID -u BUILDER_TEST_POSTGRES_DSN \
    TMPDIR=/dev/shm/subway-phase2-tmp \
    CREWAI_TESTING=true CREWAI_TRACING_ENABLED=false OTEL_SDK_DISABLED=false \
    PYTHONDONTWRITEBYTECODE=1 \
    .venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider \
    --basetemp=/dev/shm/subway-phase2-pytest-final \
    tests/test_subway_autonomy.py tests/test_subway_intelligence.py \
    tests/test_subway_full_queries.py tests/test_connected_action_plans.py \
    tests/test_adaptive_orchestration.py tests/test_runtime.py \
    tests/test_simpsons_client_isolation.py tests/test_subway_client_auth.py \
    tests/test_composition_presentation.py tests/test_overview_automation.py \
    tests/test_overview_automation_integration.py \
    tests/test_workflow_ontology_usage.py tests/test_agent_memory_recovery.py

.venv-integrations/bin/python scripts/validate_contracts.py
.venv-integrations/bin/python scripts/generate_ui_contracts.py --check
git diff --check
```

Create the TMPDIR directory first. Use a fresh `--basetemp` for any concurrent
test run; pytest owns and cleans that directory. Frontend checks are `npm test`,
`npm run typecheck`, `npm run lint` and an isolated `npm run build`. Browser checks
use `playwright.subway-intelligence.config.ts` with `BUILDER_E2E_FRONTEND_DIR`
pointing to the isolated production build.

The final follow-up commands used the same Python/environment prefix and separate
shared-memory base directories:

```bash
# Complete autonomous module plus unchanged case-owned adaptive compatibility:
.venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider \
    tests/test_subway_autonomy.py tests/test_adaptive_orchestration.py

# Latest account/source boundary checks and normal completion:
.venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider \
    tests/test_subway_autonomy.py::test_exhausted_provider_capacity_persists_a_blocker_instead_of_polling_forever \
    tests/test_subway_autonomy.py::test_revoked_source_scope_blocks_before_evaluation \
    tests/test_subway_autonomy.py::test_overview_runs_actual_crewai_and_checks_goal_before_completion

# Existing OpenAI adapter, controlled transport; no paid live provider call:
.venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider \
    tests/test_subway_autonomy.py::test_existing_openai_evaluator_transport_uses_additive_investigation_schema
```

## Qualification and remaining limits

The operational rows, budget baselines, invoice differences and provider decisions
in acceptance tests are isolated synthetic fixtures. Real Registry, CrewAI,
GraphRunner, source-query evaluation, persisted receipts and UI components execute;
provider reasoning and browser API transports are controlled fixtures. This does
not establish live OpenAI answer quality or production business-source coverage.

The budget scenario verifies numeric differences and supported budget references,
then blocks the unsatisfied business objective because actual budget meaning,
period and cause are not established. The invoice scenario preserves an unmatched
invoice and validates its supported numeric comparison without inventing currency
equivalence, tolerance policy or cause. Such partial outcomes are intentional.

Live provider quality, full production worker/process rollout, PostgreSQL-specific
concurrency behavior and inaccessible operational document contents remain
unqualified. Interrupted unknown provider calls or uncertain action outcomes
block for reconciliation; they are not silently replayed. Existing business-rule
execution is not converted into a new policy engine. Recurring schedules, external
events, notifications, delivery integrations and deployment remain outside Phase 2.
