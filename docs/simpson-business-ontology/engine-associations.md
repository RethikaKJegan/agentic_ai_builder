# Typed record associations and engine candidates — chunk 10

This chunk corrects the OEM reference path and adds explicit saved-complaint association checks. It resolves supported record references and identifies candidate conflicts; it does not invent a permanent physical-engine identity or evaluate warranty eligibility.

## Source-backed OEM correction

The supplied backend models declare different namespaces:

| Field | Declared target |
| --- | --- |
| `tickets.oem` | OEM account (`Oem`) |
| `tickets.oemOrg` | OEM company (`OemName`) |
| `oems.oemNameId` | OEM company (`OemName`) |
| `enginedetails.oem` | OEM company (`OemName`) |

Thus comparing invoice `oem` directly with ticket `oem` mixes company/account references. Warranty input readiness now compares invoice company with `tickets.oemOrg` and exposes both ticket fields separately. Its report version is `simpson-warranty-inputs-v2`. Earlier read-only reports are not rewritten. The new association resolver additionally checks whether the ticket company and its account's company agree.

`ontology/business-reference/identity-basis.json` retains exact model excerpts and supplied-file hashes, including the declared unique invoice index `(oem, engineSerialNumber)`. These are supplied archive declarations, not proof of deployed schema/index enforcement, business correctness or permanent engine identity. The resolver report includes the reference-basis file hash. Policy-draft v1 OEM scope comparisons remain literal comparisons against the declared ticket account observation; no policy scope is silently reinterpreted or approved by this change.

## New graph evidence

New explicit graph builds use mapping version `simpson-source-graph-v2`. They preserve hashed native scalar identifier tokens in allowlisted projected fields, covered by the existing record hash, so string/ObjectId/number distinctions survive public-value serialization. Direct reference edges retain their source field. Tokens identify exact typed values, not physical engines, and are not OWL sameAs assertions.

One bounded company lookup combines ticket-company, invoice-company and fetched-account-company references. Typed search values are deduplicated before the twenty-value limit. Clipped search domains and truncated returned rows both mark coverage truncated. Per-collection twenty records plus probe, overall time/result bounds, current source/authority checks, explicit manager action, source isolation and zero company writes remain unchanged. New direct same-source account-to-company and invoice-to-company edges are checked without coercing native references. No extra collection or unbounded join is introduced.

Legacy snapshots remain readable. Their saved source edges can be retained as existing evidence, but absent native tokens are not reconstructed from equal public strings. The report labels these `saved_reference_unverified_types`. New comparisons with matching retained native evidence are labelled `native_reference_checked`; this checks identifier equality, not external semantic authority.

## Saved-ticket resolver

Select one complaint in a saved graph and click **Resolve saved associations**. The resolver checks owned graph/version/record integrity and allows only the supplied same-source reference paths. Unsupported paths, wrong source fields and conflicting values are rejected. It reports:

- Ticket serial/model and separate account/company source observations.
- Ticket-to-account/company paths, account-to-company consistency and disagreement/ambiguity.
- Direct source associations, unresolved references and exact source hashes/tokens.
- Separate invoice/manual-claim/SAP-claim/QA candidates with serial/model type-aware checks and company alignment.
- Linked replacement dispatch serials as separate observations, without original/replacement engine merging or inferred chronology.
- Candidate count, no invoice/multiple scoped invoices, truncation and legacy-type limitations.

A scope-supported invoice candidate requires matching retained native serial evidence, a shared saved company record, no observed model difference and no company-path conflict. One such candidate is still not auto-selected or declared the same physical engine. Missing account-company paths are not fabricated. Manual claims declare account references in supplied code, while SAP OEM strings and QA's commented/list-valued fields do not establish a verified cross-source identity contract. Cross-source candidates are never promoted solely on matching identifiers.

Every report retains **Requires Review**, `physical_engine_identity=unresolved`, `eligibility=not_evaluated`, `selected_invoice_node_id=null`, zero identity merges and no executed rules. This feature does not create a manual SME gate, identity approval record or canonical engine table. Confirmed physical-engine mapping still requires authoritative identifier/crosswalk and replacement/history evidence.

The UI supports explicit selection/run, source-record inspection, company/reference/candidate/replacement details and JSON evidence export. Changing case or graph/version clears stale results. Graphs without tickets offer no resolution action. No report runs automatically. Existing warranty preparation, policy comparisons and original ontology tabs remain independent.

## API and offline checks

`POST /business-ontology/v1/versions/{version_id}/graphs/{graph_id}/associations`

Body contains exactly `{"ticket_node_id":"<saved service ticket node>"}`. Owner/workspace/read authority, existing session/origin/no-store transport and saved graph/version/record/token checks apply. No identity overrides, arbitrary prompts, foreign/non-ticket selections, company/model calls, source writes or identity-table mutations are accepted. Historical reads work after source disconnection. Outputs retain resolver/reference-basis/graph/definition/result hashes and source revisions.

`scripts/check_business_associations.py` opens an explicitly owned prior private graph store in SQLite mode=ro, resolves each saved service ticket and writes a fresh private report directory. No credentials or live application services are loaded; it verifies input-store hashes remain unchanged.

The earlier ticket graph contained two complaints. Each retained two legacy saved reference associations, zero invoice candidates and unresolved physical identity. Native verification counts were correctly zero because the old snapshot did not preserve typed tokens. The invoice-only and two-source QA graphs contained no tickets and produced no invented cases. All stores stayed unchanged, with zero company/model calls, company/input writes and identity merges. Private reports: `.local/business-ontology/chunk10-chunk6-{connector-check,ticket-check,quality-valid-anchor}/`.

New typed reference/candidate behavior is tested with explicit fixtures, including account/company disagreement, ObjectId/string distinctions, multiple invoices, search-domain clipping, replacements and unsupported edge fields. These tests do not establish that a new live typed graph was built. No new live company reads or deployment were performed in this chunk.
