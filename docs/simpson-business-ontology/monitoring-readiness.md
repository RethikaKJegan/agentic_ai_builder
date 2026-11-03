# Monitoring evidence and prerequisites — chunk 12

The separate Business Ontology graph view now offers **Monitoring evidence readiness**. Select a saved graph, optionally select a cut-in/QA/CAPA source record, enter an explicit start/end date and click **Inspect monitoring readiness**. No report runs on opening the panel. Readers can inspect sources, page observations and export the exact report page. Changing any input or graph/version clears prior results and discards late responses.

This implements the supplied blueprint's monitoring evidence boundary: a cut-in label or complaint is insufficient to establish a confirmed recurrence. It adds evidence inspection and prerequisite reporting, not a populated reliability program or background monitoring schedule.

## What the report establishes

- The explicitly declared inclusive calendar-day window and source failure-date observations before, within and after it. Missing/invalid/unprojected values retain their state; dates retain recorded calendar days and precision without timezone conversion or current-date defaults.
- Separate saved invoice/ticket identity observations, primary complaint/claim hours, inspection/claim failure dates and literal findings/status/reason fields, plus cut-in/quality/CAPA change fields. Each observation includes role, connection, record/field/hash and direct/candidate association qualifications. Claims and inspections may describe the same event; neither records nor date fields become a deduplicated failure count.
- A prerequisite matrix for stable physical identity, scoped applicability, actual incorporation, comparable confirmed failures, eligible population, longitudinal exposure, source/follow-up coverage and declared period. Usable observations remain unverified. Individual hour readings do not establish longitudinal exposure or sufficient exposure. Even fully matched bounded source searches do not prove population completeness.

Supported optional change records are service `internalcutins` and quality `failedengineanalyses`, `failedpartanalyses`, `icacapas`. Selecting a change identifies one source record for inspection. It does not make other saved records an applicable cohort or automatically select a physical engine. Serial ordering, retrofits, component incorporation and confirmed equivalent root causes are not inferred. Raw `POST_CUT_IN`, approver and approval/status values never confirm recurrence.

## Unavailable metrics

Confirmed recurrence, failure rate, change effectiveness, monitored population and operating exposure remain **null**, with unmet prerequisites shown. Zero failure-date observations does not mean zero failures. No real numerator, denominator, monitoring alert or effectiveness conclusion is fabricated. These metrics need authoritative cohort/identity/applicability/incorporation, confirmed comparable event and longitudinal exposure mappings before calculation.

## API

`POST /business-ontology/v1/versions/{version_id}/graphs/{graph_id}/monitoring-readiness`

Exact body:

```json
{
  "change_node_id": null,
  "period_start": "2026-01-01",
  "period_end": "2026-12-31",
  "limit": 20,
  "offset": 0
}
```

Dates must be valid `YYYY-MM-DD`, start no later than end. Limit is an integer 1–50 and offset 0–20000; booleans are rejected. Optional change ID must identify a supported record/role in the owned graph. Arbitrary queries, extra fields, caller-supplied incorporation/population/rates and foreign graph/version selections fail safely.

Existing read authority, session/origin/no-store transport and immutable saved evidence checks apply. Historical reports work after connector disconnection. Outputs include report version/hash, graph/definition hashes, source metadata revisions, prerequisite states, full-snapshot observation counts and one bounded page. Exports are labelled by page offset; a page is not a complete dataset export. No new monitoring table, company/model call, source write or schedule is added.

## Actual saved evidence

`scripts/check_business_monitoring.py` takes explicit owned SQLite graph coordinates, fresh output directory, start/end dates and optional `--change-node-id`. It opens the database in `mode=ro`, reads all report pages, loads no credentials and verifies the input-file hash remains unchanged. This checks saved evidence, not current company-wide availability.

Earlier real snapshots: invoice-only graph retained five monitoring observations; ticket graph twelve; two-source QA graph fifteen. None contained projected failure-date observations. The QA graph retained one change candidate; explicitly selecting it changed applicability evidence to observed/unverified, without confirming incorporation, comparable failures, population or exposure. Every metric stayed null. All input hashes were unchanged with company/model calls, company/input writes and schedules zero.

Private evidence: `.local/business-ontology/chunk12-chunk6-{connector-check,ticket-check,quality-valid-anchor}/` and `chunk12-qa-selected-change/`. The diagnostic 2026 calendar window is an explicit test input, not a verified production monitoring period.

Final checks are recorded in `openspec/changes/simpson-business-ontology/verification.md`. Production competency/deployment acceptance and the authoritative data dependencies remain open. Nothing is deployed by this chunk.
