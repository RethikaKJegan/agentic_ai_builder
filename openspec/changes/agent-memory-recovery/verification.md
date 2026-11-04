# Phase 3 implementation and verification

Implemented locally, backend only. No deployment, service restart, frontend edits, company/source writes, real Google effects, paid model calls or reinforcement learning. Existing uncommitted Phase 1/2 changes were preserved. Shared workflow/agent/tool contracts are unchanged.

## Files changed in this phase

New runtime services: `runtime/memory.py`, `runtime/recovery.py`.
New knowledge adapter/store: `workflow_api/client_packages.py`.
Integration: `runtime/service.py`, `runtime/graph.py`, `runtime/delegation.py`, `runtime/capability_composition.py`, `workflow_api/business_composition.py`, `workflow_api/business_preparation.py`, `workflow_api/business_ontology_routes.py`.
Acceptance: `tests/test_agent_memory_recovery.py`.
Documentation: `docs/simpson-business-ontology/agent-memory-recovery.md`, contributor handoffs, phase guide link and this OpenSpec change.

Other dirty files belong to prior work. No frontend files were edited.

## Architecture and acceptance evidence

- Existing `runtime_runs` is the short-term memory/checkpoint authority. Working-memory views isolate direct dependencies and relevant task context; extra context is bounded and cannot override source/Registry authority. Context overflow fails explicitly.
- `runtime_experiences` stores owner/workspace-scoped candidate/validated/invalidated strategy hints. Promotion requires actual completed matching recovery, exact knowledge pins and reviewed outcome; expiry/version changes reject reuse. No previous case findings or generated business approval becomes reusable authority.
- Failures have stable codes, a typed category, affected task/source, retry eligibility, strategy and human-review indication. Existing bounded output correction remains in use.
- Dependency refs cover mapped observations, mappings, concepts, source collections, version hashes, selected rules/relationships and task outputs. Recovery archives invalidated results, closes the downstream DAG and preserves unaffected checkpoints. It revalidates completed mapped reads outside write transactions and checks optimistic run-state integrity. Fresh read timestamps do not imply changed business data.
- Explicit recovery requires current source/Registry authority, exact approved workflow/knowledge/scenario identity, expired lease and remaining approved call/tool/time/retry allowance. Usage, original inputs/time, effect identity and audit remain. Retry allowance is opt-in at composition preparation and bounded by Registry policy. Existing workflows are not granted extra retries.
- Unknown external effects and completed downstream writes require reconciliation; no blind replay or fabricated receipt. This phase rejects such resume requests. Existing connector journals and explicit reviewed actions remain authoritative.
- Client packages are immutable scoped revisions with concepts/parents, relations, mappings, requirements, capability contracts, rules, resource bindings and validation rules. Packages cannot install code/SQL/tools/permissions. Source adapters are registered by trusted operators and keyed by workspace AND owner. A second owner cannot reuse another owner's provider binding.
- Shared preparation feeds the same capability compiler/factory/Registry/delegation/CrewAI runtime for the retail fixture. Read-only mapped stock values are evaluated against configured numeric thresholds. Both matching and nonmatching records are checked. Missing/invalid values remain gaps; duplicate conflicting identity values remain conflicts.
- Simpson remains on its existing richer ontology/evidence adapter; no source/knowledge republishing occurred. Historical pre-Phase-3 compositions retain their original compilation. An actual saved Phase 2 diagnostic composition was revalidated by the CLI: `composition_5366f6490dce06969e960ec5`, `valid: true`, zero model calls.
- Terminal evaluation records requested/achieved outcome, coverage, business-rule evaluation status, tool receipts/failures, recovery attempts/success, duration, usage/cost and available corrections. Successful workflow execution is separate from business conclusion readiness.

## Final test commands

```bash
cd /home/raf/agentic-ai-builder
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider \
 tests/test_agent_memory_recovery.py tests/test_business_composition.py \
 tests/test_business_preparation.py tests/test_dynamic_delegation.py tests/test_delegated_tools.py
```

**130 passed**, 10 warnings, 264.19 s (`/tmp/phase3-final-clean.log`). This includes **42 Phase 3 acceptance cases** plus Phase 1/2 composition/preparation and existing delegation/tool compatibility. A final dependency-reference/historical-compilation follow-up passed four overlapping tests (`/tmp/phase3-dependency-final.log`).

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider \
 tests/test_runtime.py tests/test_registry.py tests/test_workflow_api.py \
 tests/test_business_planning.py tests/test_business_investigations.py \
 tests/test_business_environments.py tests/test_investigation_jobs.py tests/test_google_tools.py
```

**186 passed, 34 subtests passed**, 174 warnings, 267.21 s (`/tmp/phase3-regression-b.log`). Warnings are existing JSON Schema/FastAPI deprecations. Earlier overlapping runtime/composition acceptance also passed 123 tests; it is not added to the distinct total. The final clean suite supersedes intermediate runs.

The two disjoint final suites total **316 tests plus 34 subtests passed**. Follow-up repeats are not added to that total. After the final missing-revision failure-path guard, `tests/test_runtime.py` passed again: **55 tests and 18 subtests**, 22 warnings, 20.17 s (`/tmp/phase3-runtime-final.log`); these overlap the 316-test total.

Actual CrewAI bridge execution is tested with deterministic fake model transport for both existing Simpson composition and retail. Connector effects use fake transports. No live model-quality or actual second-client system acceptance is claimed.

Additional gates: shared schema/fixture validation, strict scoped OpenSpec validation and `git diff --check`. OpenSpec must run with Node 22 on PATH; the host default Node 18 cannot load its installed CLI.

## Remaining limitations

- New domains need validated knowledge packages, compatible registered capabilities and trusted authorized source adapters; arbitrary unregistered business operations are unsupported.
- Package source projection currently uses flat configured fields and allowlisted scalar comparison rules. Simpson's existing richer evidence resolver remains in place. No automatic migration or republication of company ontology is performed.
- Missing inputs/evidence or mapping/knowledge corrections require the established typed-input/review/new immutable preparation flow. Same-run recovery cannot mutate source evidence, authorize a business action, reset budgets or replace a pin. It may correctly refuse when reviewed allowances are exhausted.
- Uncertain write reconciliation is deliberately an operator/connector-journal responsibility; this phase provides a blocker rather than an automatic remote reconciler.
- Memory is owner/workspace scoped; cross-owner organisational sharing, retention jobs and policy learning/RL are not enabled. Experiences improve task context only after verified promotion, not model weights.
- No UI integration/deployment or live Google/model evaluation. PostgreSQL was not connected for this phase's acceptance; tests use the existing SQLite store implementation.
