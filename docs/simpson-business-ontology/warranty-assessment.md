# Deterministic warranty assessment — chunk 11

Implemented locally in the separate Simpson Business Ontology tab. Select a saved graph, complaint, explicit assessment date/time and timezone; optionally select a policy revision and invoice candidate. Click **Assess saved warranty case**. Changing an input clears the result and discards late responses. Reports include check explanations, source inspection, cited parameters, blockers, provenance hashes and JSON export.

## Decision and evidence

The internal decision kernel implements three outcomes:

| Evidence | Classification |
| --- | --- |
| Verified policy authority/applicability and physical identity; every required check passes | Warranty Eligible |
| Missing/unverified prerequisites or any unknown required check, including alongside a failed limit | Requires Review |
| Verified prerequisites and complete required evidence; at least one required check fails | Warranty Not Eligible |

**Current saved policies are drafts and physical identity remains unresolved. Current application assessments therefore return Requires Review, including when draft calculations pass or fail.** There is no public verification override or SME approval workflow. The eligible/ineligible branches are verified with trusted synthetic kernel tests; no real Simpson approvals or denials are claimed. Authoritative policy, identifier applicability and verified exclusion findings remain dependencies.

## Explicit draft calculations

New policy revisions use `simpson-policy-draft-v2`. The original twelve clauses remain; seven nullable cited interpretation clauses are added:

| Clause | Supported values |
| --- | --- |
| `coverage_mode` | `sale_and_hours`, `invoice_and_hours`, `sale_invoice_and_hours` |
| `coverage_date_basis` | `assessment_date` only |
| `period_method` | `calendar_month_anniversary_clamped`, `calendar_month_difference` |
| `period_boundary` | `inclusive`, `exclusive` |
| `hours_boundary` | `inclusive`, `exclusive` |
| `exclusion_mode` | `checks_required`, `none_declared` |
| `exclusion_checks` | Null or an explicit list of required lower-case underscore codes |

Every known value requires an exact quotation from the owned policy source. Quotes prove provenance, not authority or correct interpretation. Legacy revisions remain unchanged and readable; missing new parameters yield unknown checks. New saves require all nineteen keys, with unknown value/quote pairs null. A no-exclusions declaration cannot also list required checks.

Sale calculations use primary `complaintRecord.dateOfSale`. Invoice calculations require an explicitly selected saved invoice/date; no invoice is automatically selected. Calendar anniversaries clamp to month end, including leap years. Calendar-month difference deliberately ignores the day of month. Inclusive/exclusive equality follows the separately declared boundary. Future start dates, unsupported conventions and calendar overflow yield unknown. Coverage currently uses the entered assessment calendar date, preserving its timezone; failure/complaint-date coverage bases are not implemented or inferred.

Hours use only primary `complaintRecord.hmr`, strict nonnegative decimal parsing and decimal arithmetic. Zero is retained. Alternate, claim or invoice hours are not substituted. Required exclusions without verified mapped findings remain unknown; raw flags/statuses and free text are not executed. Explicit draft `none_declared` can pass the draft exclusion calculation but cannot establish authoritative absence of exclusions.

`draft_calculation` describes only the arithmetic evidence: `within_declared_limits`, `outside_declared_limits` or `incomplete_evidence`. It is separate from final classification. OEM/model/effectivity comparisons remain candidate scope observations, not verified applicability. Truncation and company conflicts remain blockers. No company/model calls or persisted claim decisions occur.

## API and verification

`POST /business-ontology/v1/versions/{version_id}/graphs/{graph_id}/warranty-assessment`

Body contains exactly `{policy_id, ticket_node_id, assessment_at, invoice_node_id}`. Policy and invoice IDs may be null; timestamp must be an explicit timezone-qualified ISO datetime. A null policy returns Requires Review with `POLICY_MISSING`, unknown checks and null policy/source evidence. It creates no placeholder policy. Policy comparison still requires a policy ID.

Existing session/origin/no-store transport, owned immutable graph/version/policy integrity checks and reader authority apply. Foreign/non-ticket/invalid invoice selections, observation overrides and extra authority fields fail safely. Historical assessment remains available after connector disconnection. No new assessment table is added.

`scripts/check_business_assessment.py` reads an explicitly owned SQLite graph store in `mode=ro`, requires `--assessment-at`, and writes a fresh private report directory. It loads no credentials and verifies the input-store hash. The earlier real ticket snapshot produced two Requires Review cases with missing policy and unresolved identity; the invoice/QA snapshots had no tickets. No policy or final eligibility was fabricated. Diagnostic timestamps are explicit test inputs, not verified claim dates. Private evidence: `.local/business-ontology/chunk11-chunk6-{connector-check,ticket-check,quality-valid-anchor}/`.

See the chunk-11 section of `openspec/changes/simpson-business-ontology/verification.md` for final regression and browser evidence. Nothing is deployed by this chunk. Monitoring/incorporation/confirmed-failure/exposure/population and production acceptance remain open.
