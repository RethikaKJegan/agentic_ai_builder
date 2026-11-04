# Phase 5 Simpson lifecycle

Phase 6 extends these same backend components with generic packages, memory,
feedback and reviewed reassessment: see [Phase 6](generic-lifecycle-phase6.md).
The Simpson process definition below remains version 1 and unchanged.

Implemented locally on the Phase 4 backend. No deployment or frontend change is
included. The process is `simpson_warranty_lifecycle`, version **1**, defined in
`ontology/business-processes/simpson-warranty-v1.json`. Every case pins its complete
immutable definition, ontology, mappings, capability contracts and configuration.
This is an illustrative executable process, not an official Simpson policy.

## How the twelve stages execute

| Stage | Execution and evidence | Real-world boundary |
|---|---|---|
| 1. OEM complaint initiation | `business.read.complaints` agent; mapped ticket ID and complaint symptom, or actual supplied ID. Missing symptom has a case-local synthetic fallback. | Reads existing evidence; does not create a company complaint. |
| 2. Ticket registration and validation | Deterministically derives the ticket reference from stage 1; evidence-grounded registration analysis. | Analytical registration artifact; no ticket-system write. |
| 3. Warranty assessment | `business.assess_warranty` agent; upstream complaint evidence and configured policy, with explicitly synthetic nonauthoritative policy fallback. Actual supplied assessment controls the rejection branch. | No commercial approval or official warranty policy is generated. |
| 4. Investigation initiation | Grounded investigation proposal; nullable synthetic engineer reference when absent. | No invented assignment to a real engineer. |
| 5. Joint inspection scheduling | Scheduling proposal by default; optional exact registered mail/calendar action described below. | Schedule confirmation remains an authenticated correlated wait. |
| 6. Field inspection and diagnosis | `business.compare` agent; mapped inspection potential cause, otherwise grounded inference or qualified synthetic diagnosis. | Inspection findings remain unverified until an authenticated source reports them. |
| 7. Technical disposition | Grounded disposition proposal; actual user analytical route (`repair_only`, `replacement`, `undetermined`) and CAPA/monitoring flags, with synthetic conservative defaults. | A disposition proposal grants no replacement authority. |
| 8. Commercial and authorization decision | Qualified commercial proposal and explicit `not_granted_by_analysis` value. | Real commercial authorization remains pending and requires existing approval authority. |
| 9. Replacement and logistics | Provisional logistics proposal on the replacement branch. | No shipment is dispatched; shipment confirmation remains pending. |
| 10. QA investigation | Mapped QA defect when available, otherwise grounded inference or qualified synthetic QA hypothesis; replacement branch only. | Real QA results remain pending. |
| 11. Corrective engineering action | Grounded engineering proposal only when CAPA is requested. | No engineering change is applied; implementation evidence remains pending. |
| 12. Post-change monitoring | `business.report` agent only when monitoring is requested; monitoring plan with effectiveness explicitly unverified. | Observation evidence and proof of effectiveness remain pending. |

Stages 1, 3, 6 and eligible stage 12 invoke the existing dynamic composition,
master/specialist and runtime path. Their registered retrieval tools use the normal
Registry assignments. Other default stages resolve structured analytical artifacts
through Phase 4 bindings, deterministic derivation and evidence completion.
No logistics, QA or engineering connector is invented.

An actual assessment of `rejected` skips stages 4–12. A repair-only case skips
replacement/logistics and QA. CAPA and monitoring are independently conditional.
Known false branch predicates skip immediately even when another predicate is
unavailable. Eligibility now follows dependency order after JSON persistence.

`ACTUAL`, `DERIVED`, `INFERRED` and `SYNTHETIC` values retain their source references,
methods, assumptions and limitations. Actual user assertions identify their origin;
they are not independent physical verification. Company source records are unchanged.

## Driver, waits and approvals

`workflow_api/lifecycle_driver.py` calls existing prepare/start/advance/resume commands.
It persists request progress in the existing command receipt table, reserves budgets
before dispatch and reuses the exact saved command after interruption. Finished
request keys replay the saved response; use a fresh key for a later continuation.
Existing revision checks, run reconciliation and uncertain-write recovery guards apply.

Defaults are 32 commands, 120 seconds and 64 reserved stage executions. Maximums
are 64 commands, 600 seconds and 256 reserved executions, with at most four stage
dispatches per underlying command. Reservations conservatively count capacity,
including attempts that pause at approval. The time budget stops new dispatch;
already approved in-flight provider work remains subject to existing runtime limits.
There is no new background daemon. An authorized caller invokes another bounded
drive when external infrastructure or an operator makes progress possible.

The driver stops at genuine input/event/workflow/action waits, blocked work, active
execution, exhausted budgets or no eligible progress. Recovery requires explicit
`resume: true`; uncertain writes still need existing reconciliation. The driver never
validates or approves a workflow, action, business authorization or event on its own.

The optional backward-compatible event field `blocking: false` permits analytical
continuation only on provisional analytical/read stages. The real wait remains
PENDING, and required protected approval/activity inputs cannot be generated.
Existing definitions default to blocking waits. Late events preserve downstream
reassessment conflicts; they do not silently rewrite completed conclusions.

`coordination_tool_id` on creation selects an existing registered `send_email` or
`calendar_create` tool. This pins a distinct immutable process ID containing the
tool-definition digest and retains all twelve stage names. Stage 5 then becomes a
normally approved write with exact tool input schemas and actual caller values in
`inputs.coordination_inputs`. Supply actual recipients/calendar IDs/time slots,
required resources/engineer and connection through existing configuration. No
account, recipient or calendar is generated. The verified `message_id`/`event_id`
receipt becomes an actual correlation key for the field reply/findings wait.
A connector receipt proves connector acceptance, not that an inspection occurred.

## Backend commands

Run the controlled end-to-end acceptance without a server, paid model or live write:

```bash
cd /home/raf/agentic-ai-builder
.venv-integrations/bin/python -m pytest \
  tests/test_simpson_lifecycle.py::test_twelve_stage_end_to_end_actual_crewai_event_restart_and_report \
  -vv --basetemp /tmp/my-simpson-acceptance
```

That test uses actual CrewAI with a controlled model transport, mapped database
fixtures, registered test tools, normal workflow approvals, a correlated event,
a separate CLI process and reopened runtime state. It writes the case, report,
timeline and driver receipts inside the selected temporary directory. Additional
mail/calendar tests exercise normal action approval with fake transports.

For an already configured backend running this code, put your existing session
Cookie header in a private file. Create `/tmp/simpson-case.json`, replacing the ID
with an actual accessible complaint ID:

```json
{
  "request_key": "simpson-create-001",
  "original_user_goal": "Analyse this complaint through the warranty lifecycle, retaining uncertainty.",
  "inputs": {
    "complaint_id": "REPLACE_WITH_ACTUAL_COMPLAINT_ID",
    "resolution_path": "replacement",
    "capa_required": true,
    "monitoring_required": true
  }
}
```

These flags request analytical branches; they grant no operational authority.
Create `/tmp/simpson-drive.json`:

```json
{"request_key":"simpson-drive-001","max_commands":32,"max_seconds":240,"max_stage_executions":64}
```

Then run, substituting the backend URL, private cookie file and returned case ID:

```bash
.venv-integrations/bin/python scripts/business_cases.py \
  --api-url https://YOUR_BACKEND/api/backend --cookie-file /path/to/existing-session-cookie \
  simpson-create --json /tmp/simpson-case.json

.venv-integrations/bin/python scripts/business_cases.py \
  --api-url https://YOUR_BACKEND/api/backend --cookie-file /path/to/existing-session-cookie \
  drive --case-id RETURNED_CASE_ID --json /tmp/simpson-drive.json

.venv-integrations/bin/python scripts/business_cases.py \
  --api-url https://YOUR_BACKEND/api/backend --cookie-file /path/to/existing-session-cookie \
  inspect --case-id RETURNED_CASE_ID --section report
```

Inspect stage workflow/run IDs when the driver pauses. Use the existing authenticated
workflow validation/approval and action-approval interfaces with their normal
envelopes and permissions, then invoke drive with a fresh request key. Events use
the existing `/business-ontology/v1/cases/{id}/events` command and exact saved wait
correlation keys. No unattended command bypasses these approval boundaries.
The isolated `--database` CLI cannot install live models or connectors; use the
configured backend path for agent execution.

New routes under `/business-ontology/v1` are GET `/simpson-lifecycle/process`,
POST `/simpson-lifecycle/cases`, POST `/cases/{id}/drive`, and the existing section
interface now accepts GET `/cases/{id}/sections/report`. All retain authenticated
workspace/owner isolation, origin checks and standard no-store envelopes.

## Executed evidence and limits

See [verification](../../openspec/changes/simpson-lifecycle-phase5/verification.md)
for exact executed commands/results and
[acceptance trace](phase5-acceptance-trace.json) for a projection of actual persisted
case/report/timeline data, including all twelve stages and branch outcomes.
The full-path acceptance ends with execution COMPLETED, case
COMPLETED_PROVISIONALLY and business outcome PROVISIONAL. Real authorization,
inspection, shipment, QA, engineering and monitoring waits remain pending; the
received scheduling event is recorded as an authenticated source report.

Live provider quality, live PostgreSQL deployment and live mail/calendar/company
writes were not exercised. Tests use real local stores and existing runtime code
with controlled external transports. No authoritative Simpson policy, completed
physical activity, approval or corrective-action effectiveness is asserted.
No Phase 6 feature, deployment or frontend change is included.


The existing Workflow → Business Investigation interface now exposes these
persistent cases, pinned stages, approval gates, evidence, waits, memory and
reports. See [UI integration and verification](business-lifecycle-ui.md).
