# Simpsons ontology evidence review

**Current UI:** the [deployed record explorer](object-explorer.md) connects reviewed concepts to permitted source values. The supplied evidence classification below and the remaining business-policy/calibration gates are preserved. Technical source revalidation does not establish new SME approval.

## Status and provenance

The user explicitly supplied the attached answers as **documented current application behaviour**, not business-confirmed policy. This classification applies to both source documents retained here. No business approver has been identified, no blanket SME sign-off is inferred, and these notes do not approve or publish ontology records.

- [Initial code-review answers](initial-code-review.txt): the original 50-question response.
- [Follow-up code-review answers](follow-up-code-review.txt): the latest clarification, including warranty thresholds and cross-connection behaviour.
- [Evidence manifest](evidence-manifest.json): original attachment paths, SHA-256 hashes and classification flags. Copies preserve the original bytes.

These are user-supplied reports of code inspection, not an independent inspection of `simpcare-admin-console` in this session or proof of actual record-level consistency. Earlier conversational hypotheses must not override this more specific clarification. Future corrections should retain these originals and add new evidence rather than overwrite their contents.

## Accepted interpretation of the supplied evidence

| Area | Documented application behaviour | Ontology treatment |
| --- | --- | --- |
| Engine identity | Invoice records are unique by billed-to OEM company plus serial. Lookups use serial alone and select the first match. | Represent invoice-record identity separately from physical-engine identity. Storage permitting repeated serials does not establish that distinct physical engines legitimately share serials. Serial-only resolution can be ambiguous. |
| OEM company and account | `oemnames` represents companies; `oems` represents email login accounts connected by `oemNameId`. Accounts can change company; tickets retain their original copied company. | Keep Company, OEMAccount and Person distinct. Do not identify an account as a person, plant or branch without additional evidence. Preserve ticket-company history separately from current account-company membership. |
| Engine/company association | `enginedetails.oem` is the billed-to company, not a login account. | Model billed-to association, not current engine ownership or a direct engine-to-person association. |
| Ticket references | OEM account, copied company and actual creator are distinct. Engine serial is free text, not a guaranteed invoice-record reference. | Retain typed source mappings and an ambiguous actor reference where `createdBy` can identify either a staff or OEM account. Do not merge accounts by email alone. |
| Serial matching | Exact text; case-insensitive search is an exception. | Record endpoint-specific matching behaviour. No approved normalization or physical identity rule is established. |
| Cut-in ordering | Text comparison, inconsistent compared fields across paths, and first-plant bulletin handling. | Record as implementation observations/defects. Do not promote lexical ordering or first-plant selection to approved engine applicability rules. |
| Ticket state | Four status values; stage is workflow position, state is geography, phase is unused. | Separate these attributes. The 27 supplied labels comprise 14 ticket workflow-stage labels, 11 timeline-only labels and two unused labels, not 27 sequential workflow steps. Do not infer a complete allowed-transition graph from the grouped list. |
| Open-ticket restriction | Serial-only submission check, bypassable by concurrency/admin submission/reopening. Resolved and closed tickets permit new submissions. | Record a currently attempted restriction with enforcement gaps, not a guaranteed uniqueness invariant. Reopen/resolve/close business policy remains unconfirmed. |
| Inspections and repairs | One JIR per ticket, overwritten on edit; multiple replaced parts; repeat repair uses a new ticket. | Retain current cardinality and lack of report revisions as documented behaviour. Do not invent inspection history. |
| Replacement lineage | Old serial is on the ticket; new serial is on float-engine dispatch. Invoice master is not updated. | Link the dispatch and original complaint through the documented ticket reference. Do not assert that later ticket serials or free-text work-order references resolve reliably. |
| Unregistered engine | Ticket can enter `ENTER_ENGINE_DETAILS` and generate an alert. | Record this explicit application path without treating missing invoice data as proof that an engine does not exist. |
| Claims and code lists | Manual and SAP claims are separate and not reconciled; dashboards use SAP claims. `simpsoncodes` is the active code source. | Do not deduplicate claims without a validated matching rule. Distinguish active source authority in the application from business-approved source authority. |
| Money and measurements | No explicit currency; some money values are text. Several quantities have no defined units/formula. | Keep currency, tax interpretation, units and unsupported formulas unresolved. Do not invent INR, totals, conversions or metric semantics. MTTR/MTTC fields are documented per-ticket whole-day durations, not automatically verified mean statistics. |
| Reporting | Financial year is derived from ticket creation, April–March. Sales denominators in MIS are hardcoded. | Record current period selection. Do not represent hardcoded sales as live company data or trust derived MIS output as verified performance evidence. |
| Documents and knowledge | Manuals use archive, release order and approval status; FAQs have no approval workflow. | Do not equate newest with approved/effective, or editable FAQ content with validated guidance. |
| Empty/operational collections | Some active schemas have no sampled rows; counters/import trackers/JIR submission logs are operational. | Empty coverage is not a nonexistent schema. Keep operational provenance separate from business facts. Preserve still-undefined terms such as FOC, ICA/CAPA and Wcl as unresolved labels. |
| Freshness and review | Polling schedules exist; no acceptable-staleness policy or ontology approver is supplied. | Collection timestamps are observations. Neither the implementation's heuristic freshness window nor existing application approval flows establish business-approved ontology governance. |

## Documented warranty implementation

The supplied code review reports that all three conditions are required, evaluated to ticket creation rather than failure date, with depot/dealer-stock engines bypassing the check:

| OEM label in supplied review | Maximum months since Simpson invoice | Maximum months since machine sale | Maximum HMR |
| --- | ---: | ---: | ---: |
| TAFE | 27 | 24 | 2,000 |
| CNH | 24 | 21 | 2,000 |
| TEREX / Manitou | 24 | 18 | 2,000 |
| Other labels | 15 | 12 | 1,500 |

Classification: **documented implementation, business approval unconfirmed**. Exact boundary operators, month arithmetic, treatment of missing/invalid dates or HMR, and company-label matching are not specified by the supplied table. Do not encode these as an executable approved warranty policy by guessing. Serial-first-match ambiguity also affects the underlying invoice used by this calculation.

## Cross-database clarification

The earlier claim that these references "cannot be resolved" is superseded: the supplied follow-up says target data and matching UUID strings exist, while default same-connection Mongoose population does not implement the lookup. Explicit cross-connection resolution is therefore a candidate implementation path, subject to authorized source access and actual reference validation. Matching identifier formats alone are not a record-level integrity check.

Export tracking reportedly already uses an explicit lookup. Wcl and the old code lists are a separate case: their connection is not opened by the application, so availability and authority must not be assumed.

## Permissions and defects

The supplied role visibility matrix can be retained as documented role behaviour for review. It is not final business authorization policy under the user's explicit classification. Unauthenticated endpoints and cross-company past-history exposure are defects, not access entitlements. Existing ontology API permission checks must not be loosened to reproduce them.

Keep access defects, hardcoded sales, text cut-in ordering and enforcement races separate from ontology business rules. This review did not fix those upstream application behaviours.

## What remains unconfirmed

There are no further general code-behaviour questions needed to continue a descriptive ontology draft. Business unknowns stay explicit: physical engine identity, serial normalization/ordering, intended lifecycle and visibility rules, account types, terminology, currency/units, warranty approval, effective-document rules, freshness limits, always-review decisions and final ontology approver.

Exact implementation details may need targeted verification if a later task consumes a rule, especially warranty boundary arithmetic. This does not require inventing answers or reopening the entire questionnaire.

Source descriptions can support draft concepts, relationships and documented-behaviour assertions. They do not constitute numerical calibration labels or authority to approve desired business policy. Task 7.3 remains incomplete until reviewed publication and its required acceptance evidence actually exist.

## Earlier documentation-only update

Only local documentation/evidence files and the verification cross-reference were updated. No company database, local ontology database, production application, workflow, approval, credential or permission was changed. No company data was queried during this documentation update.


## Subsequent descriptive draft

The [Simpsons draft and three question previews](draft/README.md) now represent these definitions in native common/domain/organization records and a separate local ontology database. All assertions retain the evidence boundaries above; no business policy was approved. See [validation.json](draft/validation.json) for counts, missing sampled bindings and isolation evidence. The running application's ontology has not been replaced or deployed by this draft construction.


## Targeted technical follow-up

[Read-only technical verification](technical-verification.md) observed four of the eleven originally unresolved fields and retained seven unresolved bindings. The [current revised draft](draft-v2/README.md) preserves the original draft and records the new evidence without business approval, reference-target verification or publication. An application schema/model can resolve empty-collection field questions; an expert is required for intended business policy, not for obtaining those technical definitions.


## Owner-approved deployment

The owner subsequently explicitly approved publication and deployment. [Deployment evidence](deployment.md) records the live UI, 409 approved descriptions, seven unresolved drafts, actual source-evidence revalidation and desktop/mobile checks. The original code-review documents remain preserved with their original classification; owner approval is recorded separately and is not represented as independent SME calibration or executable policy approval.
