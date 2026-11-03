# Warranty input readiness — chunk 8

The saved source graph now supports explicit input preparation for a selected complaint. This is the next evidence step toward the requested warranty rule. It does not yet execute the rule: complete applicable policy, physical-engine identity and the assessment date basis remain unresolved.

In Business Ontology, select a definition version and saved source graph, then choose one saved complaint under **Warranty input readiness** and click **Prepare warranty inputs**. The report shows **Requires Review · Eligibility not evaluated**, reasons, source observations, invoice candidates and evidence needed next. It supports source-record inspection and JSON export. Selecting another complaint or graph clears the old report; opening a graph or choosing a complaint does not run preparation. Authorized viewers can prepare saved evidence. No tickets means no preparation action, not absence from company systems.

## Inputs and comparisons

| Source observation | Treatment |
| --- | --- |
| `tickets.engineNo` | Recorded complaint serial, without normalization for identity matching |
| `tickets.oem` | Recorded OEM account reference; retained separately from company scope |
| `tickets.oemOrg` | Recorded OEM company reference, compared with invoice OEM company; public comparisons do not reconstruct original BSON types |
| `tickets.complaintRecord.dateOfSale` | Primary complaint sale-date observation, parsed only as ISO date/datetime |
| `tickets.complaintRecord.hmr` | Primary operating-hours input used by the supplied implementation; nonnegative finite decimal parsing, including zero |
| `tickets.hmr` | Separate alternate observation; never substituted for absent complaint hours |
| `tickets.createdAt` | Context only; never silently selected as the assessment timestamp |
| `enginedetails.engineSerialNumber`, `.oem`, `.invoiceDate` | Every saved invoice stays separate, with serial/OEM comparison states and date observations |

Decimal strings retain source text plus a separate plain-decimal normalization. Booleans, negatives, nonfinite numbers, units, grouping commas, exponent-form strings, non-ASCII digits and overlong numeric text are unsupported; no unit conversion or guessing occurs. Numeric source values can already have source-side floating-point precision; normalization cannot restore lost precision. Zero is valid input syntax, not proof of coverage. Complaint and alternate numeric hours differing produce an explicit review reason.

Dates preserve the source value, recorded calendar date and precision (`date`, `datetime`, `local_datetime`). Unsupported/invalid dates remain invalid. Calendar precision and timezone differences do not establish event ordering. No current date, elapsed-month calculation or threshold is used. A parseable value is not a verified event or sufficient policy input.

Since chunk 10 (`simpson-warranty-inputs-v2`), invoice OEM comparisons use `tickets.oemOrg` (company), correcting the earlier account/company namespace comparison. Invoice comparisons use exact saved public scalar values without string/number coercion. They do not establish native BSON equality, ownership, identity, invoice applicability or policy. Missing values, mismatches, multiple invoices, no invoice candidates and unusable invoice dates remain visible. No candidate is selected automatically. Claims and inspection fields do not fill missing complaint inputs; stored warranty booleans and old implementation limits do not determine eligibility.

## Policy and review boundary

Policy-kind sources retained in the immutable definition version are listed by source ID, title and hash. Their authority and completeness are not established by the label or document text. Preparation always retains these requirements:

- Applicable structured policy version, effective dates, OEM/model scope, coverage limits, date basis, boundary conventions and exclusion handling.
- Verified complaint-to-physical-engine and invoice association, including ambiguity/replacement handling.
- Explicit assessment timestamp and the required dated operating-hour, sale and invoice evidence.

No policy is configured by this feature and no Eligible/Not Eligible decision is made. Requires Review is an input-readiness state, not an SME validation workflow, claim denial, operational approval or persisted business decision. Warranty-policy intake and execution remain future work once authoritative information is available. Monitoring evidence and complete business competency answers remain open.

## API

`POST /business-ontology/v1/versions/{version_id}/graphs/{graph_id}/warranty-readiness`

Body: `{"ticket_node_id":"<saved ticket node ID>"}`. No extra fields, input overrides, arbitrary prompt or proposed policy are accepted. The selected node must be a service ticket in that owned saved graph. Existing session/origin protection, tools-read/workspace-read scope and no-store response envelopes apply. Foreign versions/graphs fail scope lookup; invalid or non-ticket selections fail validation.

Response includes readiness version, `requires_review` status, `not_evaluated` eligibility, source observations and hashes, separate invoice candidates/comparisons, unverified policy-source references, review reason codes, relevant saved collection outcomes, limits, next evidence and graph/definition/result hashes. Policy version, assessment timestamp and selected invoice remain null. `company_queries=0`, `model_calls=0`, `rules_executed=false` and `business_policy_verified=false` are explicit.

Preparation checks saved graph/version alignment, record field hashes and edge validity, then performs pure deterministic analysis. It introduces no persistence table or automatic source query. Historical saved cases remain inspectable after connectors disconnect. Repeating the same request against the same saved inputs yields the same report hash; no case state or company record changes.

## Offline real-evidence check

`scripts/check_business_warranty.py` accepts `--database`, `--directory`, `--workspace`, `--owner`, `--graph-id`. It reads the owned graph/version with SQLite mode=ro, prepares each saved service ticket, and writes reports to a fresh private directory. It loads no credentials and makes no company/model calls. It verifies the input store file hash stayed unchanged.

The earlier real ticket snapshot contained two complaints. Both had parseable complaint sale dates/hours, but no saved invoice candidates, no policy-kind documents, unresolved identity and no selected assessment-time basis. Both remained Requires Review with eligibility not evaluated. The earlier invoice-only and two-source QA snapshots had no tickets; no cases were invented. All source stores remained unchanged. Private outputs: `.local/business-ontology/chunk8-chunk6-ticket-check/`, `chunk8-chunk6-connector-check/` and `chunk8-chunk6-quality-valid-anchor/`.
