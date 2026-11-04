# Executed Phase 5 verification

Executed locally on 4 November 2026. No paid provider call, live external write,
database deployment, service restart or frontend change was used for this phase.
Application runtime, Registry, SQLite and CrewAI are real; external model/tool
transports and source records are controlled fixtures.

## Commands and results

From `/home/raf/agentic-ai-builder`:

```bash
.venv-integrations/bin/python -m pytest tests/test_simpson_lifecycle.py -q --basetemp /tmp/simpson-phase5-final
# 14 passed, 10 deprecation warnings, 185.17s

.venv-integrations/bin/python -m pytest tests/test_business_cases.py tests/test_business_case_runtime.py -q
# 51 passed, 10 deprecation warnings, 79.59s

.venv-integrations/bin/python -m pytest tests/test_business_investigations.py tests/test_business_composition.py tests/test_business_preparation.py tests/test_agent_memory_recovery.py tests/test_investigation_recovery_details.py -q
# 128 passed, 14 deprecation warnings, 365.50s

.venv-integrations/bin/python -m pytest tests/test_simpson_lifecycle.py::test_twelve_stage_end_to_end_actual_crewai_event_restart_and_report -q --basetemp /tmp/simpson-phase5-report-final
# 1 passed, 2 deprecation warnings, 44.46s

.venv-integrations/bin/python scripts/validate_contracts.py
# Shared contract schemas and fixtures are valid.

/home/raf/.nvm/versions/node/v22.23.3/bin/node /home/raf/.nvm/versions/node/v22.23.3/lib/node_modules/@fission-ai/openspec/bin/openspec.js validate simpson-lifecycle-phase5 --strict
# Change 'simpson-lifecycle-phase5' is valid

git diff --check
# exit 0

.venv-integrations/bin/python scripts/business_cases.py --help
# exit 0; includes simpson-create, drive and inspect
```

The final single-test run followed the report-order correction and asserts exact
process order. The 14-test suite preceded that presentation correction. Total
distinct tests: 193; the additional end-to-end run repeats one. Warnings concern
existing jsonschema RefResolver and FastAPI on_event deprecations.

An earlier run found repair/rejection descendants left CREATED after canonical
JSON reordered keys. Dependency-order refresh fixed this; focused branch tests
and the complete suite subsequently passed. Failed runs are not passing evidence.

## Actual persisted execution

Latest full-path case: `case_0c3ededc6c7b54490baa8247`.
Process: `simpson_warranty_lifecycle`, version 1. All twelve stages persisted
COMPLETED_PROVISIONALLY. Execution: COMPLETED; case: COMPLETED_PROVISIONALLY;
business outcome: PROVISIONAL.

Five driver invocations stopped four times at real authorization/work boundaries,
then reached terminal analysis. They used 2, 3, 4, 7 and 1 commands. Normal workflow
approvals were explicit test actions between invocations; the driver approved
nothing. The report retains 67 timeline entries, composition/run IDs, resolved
input/output provenance, assumptions and conflicts.

Mapped complaint, inspection and QA fixtures used existing preparation/retrieval.
Tool records persisted on complaint (one), warranty (one), field diagnosis (two).
CrewAI used a controlled model transport. Ticket reference is DERIVED, complaint
ID ACTUAL, policy fallback SYNTHETIC and model narrative INFERRED. Original source
fixture rows remained unchanged.

A wrongly correlated schedule event was rejected; matching event and duplicate
exercised durable deduplication. The schedule wait records
REPORTED_BY_AUTHENTICATED_SOURCE and a late-evidence reassessment conflict. An
independent CLI subprocess inspected the same SQLite case; reopened case/runtime
services continued without replacing completed work or changing process pins.

Unresolved actual waits: inspection_findings, commercial_authorization,
shipment_confirmation, qa_results, engineering_change_evidence and
monitoring_observations, all PENDING. Replacement remains UNVERIFIED and monitoring
effectiveness remains `unverified`.

Repair-only acceptance skipped replacement/logistics, QA, corrective engineering
and monitoring. Warranty rejection skipped stages 4–12. Both persisted qualified
terminal reports. A blocking Simpson variant demonstrated genuine event
pause/resume with pinned version 2. Other tests cover crash takeover, durable
budgets, idempotency, uncertain-write non-replay, protected authorization inputs
and authenticated API/workspace boundaries.

Optional registered mail/calendar variants each used normal workflow and action
approvals before a single fake connector call. ACTUAL receipts correlate to
downstream pending findings/reply waits. No real message or calendar event was sent.

## Artifacts and limits

`docs/simpson-business-ontology/phase5-acceptance-trace.json` projects actual case,
report and driver outputs, retaining original artifact SHA-256 values, twelve
ordered results, full input/output provenance, actual waits, timeline, branch
outcomes and driver stop reasons. Repeated raw tool packets are represented by
tool ID, inputs and output digest.

Full local artifacts (temporary; regenerate with pytest):

```
/tmp/simpson-phase5-report-final/test_twelve_stage_end_to_end_a0/phase5-report.json
/tmp/simpson-phase5-report-final/test_twelve_stage_end_to_end_a0/phase5-case.json
/tmp/simpson-phase5-report-final/test_twelve_stage_end_to_end_a0/phase5-timeline.json
/tmp/simpson-phase5-report-final/test_twelve_stage_end_to_end_a0/phase5-driver-receipts.json
/tmp/simpson-phase5-final/test_repair_only_and_warranty_0/branch-report.json
/tmp/simpson-phase5-final/test_repair_only_and_warranty_1/branch-report.json
```

This demonstrates controlled existing-backend execution, not live provider
quality, live PostgreSQL deployment, commercial authority or physical completion.
The implementation report documents per-stage behavior, backend commands,
dispatch budget semantics and remaining limits.
