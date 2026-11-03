# Source-cited warranty policy drafts — chunk 9

This chunk adds a separate policy draft library and saved-case scope/date comparisons within Simpson Business Ontology. No real policy is seeded: existing code thresholds, warranty flags and blueprint examples are not imported as authoritative policy. Draft saving and matching quotations do not verify policy authority or business meaning. There is no SME validation or policy approval workflow, and no claim decision is executed.

## Policy intake and immutable revisions

Managers can add a warranty policy source document, create a draft, select the source, record known clauses with exact source quotations, and explicitly save a revision. Unknown values remain blank/null; at least one cited clause is required. The source text can be read while editing. Every revision embeds its source text/hash, clauses/quotations and provenance and remains inspectable/downloadable. A new revision preserves all previous policy versions, ontology definitions and source graphs. An old revision remains readable; a stale base cannot silently overwrite the latest series revision.

The draft contains:

| Clause group | Recorded values |
| --- | --- |
| Identity/effectivity | Source policy version, effective start/end, effective-date basis and boundary convention |
| Declared scope | Exact OEM reference values and engine model values, one per line |
| Coverage interpretation | Sale/invoice coverage months, operating-hour limit, boundary notes and exclusion/handling text |

Clause values are user-supplied interpretations, not machine-verified translations of the quotations. Source documents must be owned, policy-kind and tagged for Warranty. The existing source intake remains available; no model transfer is involved. A source-kind label is not an authority assertion. Each non-null clause needs a nonblank exact quotation (whitespace normalized, at least four substantive characters). Unknown clauses have null value and quote, never inferred defaults.

Structured validation rejects invalid/reversed ISO effectivity dates, duplicate/wildcard scope values, invalid choices, boolean/negative/nonfinite numeric inputs, extra fields and unmatched citations. Month inputs are bounded integers 0–1200 for input/storage validation; this range is not a business coverage rule. Hour limits are bounded plain-decimal strings including zero. The comparison operation executes no coverage limit or exclusion text. Chunk 11 separately supports explicit draft arithmetic using [cited conventions](warranty-assessment.md). Unknown effective end is unknown, not automatically unlimited duration.

Writes require current manager/write authority, an expected per-series revision and stable request key. Concurrent identical requests save one revision/event; changed payload reuse and stale revisions fail without partial changes. Additive policy heads/versions are scoped by trusted workspace and owner; source text/hash is captured immutably. Storage is bounded to twelve series, eighty total revisions and forty revisions per series. Historical inspection does not require connected source databases.

## Saved-case comparisons

A graph reader explicitly selects an exact policy revision, saved complaint, assessment date/time and timezone offset, and optionally a saved invoice. Nothing runs on selection alone. Scope values compare exactly against the complaint's saved `oem` and `engineModal` values, without aliases, string/number coercion or native BSON reconstruction. An exact public-value match is not confirmed physical-engine identity, scope mapping or policy applicability.

Effective-date comparison uses the draft's declared basis:

- `assessment_date`: the explicitly entered timestamp's recorded calendar date, retaining the entered timezone.
- `sale_date`: that complaint's parseable `complaintRecord.dateOfSale` observation.
- `invoice_date`: the parseable invoice date from the explicitly selected saved service invoice. No invoice is selected automatically.

The declared start/end and inclusive/exclusive convention determine only a fixed calendar-date comparison. Unknown basis, bound, endpoint or required observation yields unavailable. No current-date fallback, timezone conversion, claim/alternate-input substitution or month/hour threshold calculation occurs. An invoice selection identifies a candidate only. Source graph truncation remains visible in review reasons.

Results show match/different/unavailable for OEM/model/effective dates, supporting observations, exact saved clause values/quotations, source/graph/definition/policy/result hashes and review reasons. **Requires Review; eligibility not evaluated** remains explicit even when every observed comparison matches. Policy authority and meaning, physical-engine identity and selected-invoice applicability remain unresolved; coverage limits/exclusions are not executed. A differing scope comparison does not deny a claim. Chunk-8 input preparation remains independent and unchanged.

Changing any policy/case/invoice/time or graph/version input clears the old comparison and discards late results. Readers can export the exact report. Empty libraries and graphs without complaints offer honest unavailable guidance rather than fabricated results. Managers can save drafts; authorized viewers can inspect/download historical revisions and run read-only comparisons. None of these actions publishes policy, changes company records or starts a source query/model call.

## API

All paths below use `/business-ontology/v1`, existing session/origin protection and no-store response envelopes.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/warranty-policies` | Bounded revision summaries, owned policy-source summaries and clause specifications |
| POST | `/warranty-policies` | Save immutable draft with `{request_key, expected_revision, policy}` |
| GET | `/warranty-policies/{policy_id}` | Owned immutable revision with embedded evidence and integrity hash |
| POST | `/versions/{version_id}/graphs/{graph_id}/policy-comparison` | Explicit comparison with `{policy_id, ticket_node_id, assessment_at, invoice_node_id}` |

The save `policy` object contains exactly `policy_key`, `title`, `source_id`, `clauses`. New saves use schema v2 with all nineteen clause keys required (the original twelve plus the seven [explicit assessment interpretation parameters](warranty-assessment.md)); each has exactly `{value, quote}`, null together if unknown. `expected_revision=0` creates a new series. Subsequent revisions require the latest series number. No caller-supplied scope/owner/status/authority/executable fields are accepted. The exact selected policy revision can be used with an owned historical graph without regenerating ontology definitions.

Assessment time must be a timezone-qualified ISO datetime; date-only/local timestamps are rejected. `invoice_node_id` is null or an existing saved service invoice ID. Arbitrary prompts, SQL, policy overrides and additional comparison inputs are rejected. Readiness/comparison never writes claim decisions or company records. Policy persistence adds local draft/audit records only. Policy, graph field and source hashes are checked; hashes identify the inputs and do not establish external authority.

## Actual evidence and remaining work

`scripts/check_business_policy_evidence.py` reads an explicitly owned existing private graph store in SQLite mode=ro and reports policy evidence availability without initializing new tables or seeding a policy. It records zero comparisons when no saved policy exists. It loads no credentials, makes no company/model calls and verifies the input-store file hash stayed unchanged.

All three earlier real invoice/ticket/QA stores had zero owned warranty-policy documents and zero saved policy revisions. The ticket store contains two complaints; the others have none. No real policy comparison or eligibility decision was claimed. Private reports are in `.local/business-ontology/chunk9-chunk6-{connector-check,ticket-check,quality-valid-anchor}/`. Populated policy comparisons in unit/browser tests are explicitly synthetic fixtures.

This chunk completes draft intake and candidate comparisons only. Authoritative source content/acceptance, verified policy-to-identifier mappings, confirmed physical-engine/invoice identity, structured executable exclusion handling and final eligibility are still required. Monitoring/incorporation/confirmed-failure/exposure/population evidence and production competency acceptance also remain open. Nothing is deployed by this chunk.

## Warranty knowledge follow-up — 1 November 2026

The library now contains both written-policy interpretations and explicitly **implementation-derived** warranty drafts. The supplied `src/services/warranty.service.js` code is an existing source of knowledge, even though no written policy document was supplied. **Import existing warranty logic** creates four immutable, source-cited implementation drafts; the live owned workspace has been initialized with these four references. An empty written-policy collection no longer hides the known code logic.

| Supplied code OEM-name branch | Invoice months | Sale months | Operating hours |
| --- | ---: | ---: | ---: |
| Tractors and Farm Equipments Ltd | 27 | 24 | 2,000 |
| CNH Industrial (India) Private Ltd. | 24 | 21 | 2,000 |
| TEREX Equipment (P) LTD / Manitou Group | 24 | 18 | 2,000 |
| Other names (the code's else branch) | 15 | 12 | 1,500 |

All three comparisons must pass in the supplied calculation; its limits are inclusive and its month difference ignores the day of month. These are facts about supplied code, not confirmation of what version runs in Simpson's live application or of contractual terms. The source uses substring name conditions, which are not database OEM account IDs. The importer therefore leaves scope IDs, model scope, effective dates, source-policy version and exclusions unknown. It does not treat missing exclusion logic as a no-exclusions policy. Legacy missing-input, date and identity limitations remain qualified rather than reproduced as business truth.

For “What limits does the supplied application use for CNH?”, the answer is the cited 24/21/2000 branch above. For “Is this engine contractually covered?”, use its source-record facts, a genuinely applicable policy and exclusion/identity evidence; the code limits alone do not establish a final approval or denial. The existing fixed assessment can calculate the interpreted checks and explain missing evidence, and still returns Requires Review where final prerequisites are absent. No SME workflow is introduced.

Every imported clause has an exact quotation. `interpretation_basis: descriptive_implementation` and `implementation_reference` (branch, selector, source hash and reference version) keep code provenance explicit. Manually supplied application-code interpretations get the same descriptive basis; policy-source interpretations retain policy-statement basis. Both remain drafts/unverified, with immutable source snapshots and hashes. This extends the earlier source-kind restriction; it does not relabel code as policy.

POST `/business-ontology/v1/warranty-policies/import-implementation` accepts `{}` under existing manager/session/origin checks. The reviewed source hash is pinned to `621995136ad5360339474d9234e72879b25d791babf440d76e77859120d72870`. The four revisions, heads and audit events commit atomically; re-import is idempotent and retains subsequent history. No model or company-source call occurs. Other/modified source content is not silently parsed as the reviewed code. This adds metadata to existing policy tables and no schema migration or new policy-authority capability.

Revision selection now commits the selected ID before the detail request, shows loading, ignores stale responses and disables an empty list. Source reading/history/download still work, and saved/imported drafts refresh the case-comparison list immediately. Choose a source-labelled code-derived revision to inspect its clauses and provenance. The importer does not invent unknown policy clauses or require the user to type limits already present in the supplied source.
