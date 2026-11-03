## ADDED Requirements

### Requirement: Separate business ontology subsystem
The system SHALL preserve the existing Ontology tab and keep the new Business Ontology definitions, storage scope, namespace and versions separate.

#### Scenario: First discovery chunk
- **WHEN** source verification is requested
- **THEN** only bounded read operations SHALL contact company systems
- **AND** existing ontology and company records SHALL remain unchanged

### Requirement: Qualified source evidence
The diagnostic SHALL distinguish source-code declarations from sampled database observations and SHALL export no source records, identifiers, credentials or field values.

#### Scenario: Missing sampled field
- **WHEN** an allowlisted field is missing from all sampled documents
- **THEN** the report SHALL mark it not observed in the bounded sample rather than absent from the schema

#### Scenario: Source unavailable
- **WHEN** connection or query execution fails
- **THEN** the report SHALL retain an unavailable outcome and a safe error type without exposing driver messages

### Requirement: Preserve agreed generation scope
Future generation SHALL use the existing OpenAI configuration and automated technical validation without an SME ontology validation gate.

#### Scenario: Operational approval in source
- **WHEN** a source record describes replacement or quality approval
- **THEN** it SHALL remain a business concept independent of the excluded SME ontology validation workflow

### Requirement: Scoped persistent foundation
The system SHALL persist a separate foundation and immutable foundation snapshot only after explicit initialization with two distinct owned connected sources.

#### Scenario: Read before initialization
- **WHEN** an authorized user opens Business Ontology
- **THEN** the system SHALL return the five-layer twelve-module catalogue without creating workspace records

#### Scenario: Repeated initialization
- **WHEN** an authorized manager initializes using the same source bindings twice
- **THEN** the system SHALL return the same foundation revision without duplicate versions or events

#### Scenario: Cross-owner source
- **WHEN** initialization references a source belonging to another owner or workspace
- **THEN** the system SHALL reject it without creating business ontology records

#### Scenario: Existing ontology preservation
- **WHEN** the business foundation is initialized
- **THEN** existing ontology records and source configuration SHALL remain unchanged

#### Scenario: Foundation navigation
- **WHEN** a user selects a layer or module in the new tab
- **THEN** the view SHALL display its description and actual concept count without implying generation has run

### Requirement: Evidence-backed module extraction
The system SHALL generate draft structured concepts, properties, relationships and non-executable rule candidates using the configured OpenAI model and scoped source documents.

#### Scenario: Valid module result
- **WHEN** a module generation result passes structural and evidence checks
- **THEN** the system SHALL save a new immutable draft version with source hashes, exact quotations, unknowns and provider usage
- **AND** prior versions and unrelated modules SHALL remain unchanged

#### Scenario: Unsupported evidence or relationships
- **WHEN** a result cites an unknown source, invents a quotation or references a missing concept
- **THEN** the job SHALL fail without changing the current draft

### Requirement: Durable authorized generation
Generation jobs SHALL be idempotent and SHALL recheck authority, source generation and expected draft revision before applying results.

#### Scenario: Stale or cancelled job
- **WHEN** sources change, authority is revoked, a newer version exists or cancellation occurs during generation
- **THEN** the late result SHALL NOT replace current definitions

#### Scenario: Provider unavailable
- **WHEN** the configured provider refuses, times out or returns incomplete output
- **THEN** the job SHALL expose a safe failure without a fallback model or automatic retry

#### Scenario: Evidence inspection
- **WHEN** a user selects a generated concept, relationship or rule
- **THEN** the UI SHALL show its draft definition, source quotations and unresolved information without representing it as approved business policy


### Requirement: Deterministic version-bound ontology compilation
The system SHALL compile an owned immutable draft into OWL/RDF and SHACL without model calls, company queries, rule execution or mutation of the source draft.

#### Scenario: Repeat or historical compilation
- **WHEN** a manager compiles the same version again or compiles a historical version
- **THEN** the stored artifact SHALL be idempotent for that input and compiler version
- **AND** current definitions and prior artifacts SHALL remain unchanged

#### Scenario: Faithful schema mapping
- **WHEN** concepts, attributes, relationships and candidate rules are compiled
- **THEN** class inheritance, declared datatypes, required fields and evidence SHALL be preserved
- **AND** candidate rules SHALL remain non-executable without invented policy or unspecified constraints

### Requirement: Honest automated validation and scoped exports
The system SHALL validate generated shapes and ontology definitions offline and SHALL report unresolved mapping limits separately from conformance.

#### Scenario: No instance validation
- **WHEN** a definition compilation passes SHACL checks
- **THEN** the report SHALL explicitly state that company instances were not validated and business policy is unverified

#### Scenario: Invalid definitions or foreign version
- **WHEN** references, citations, hierarchy or shape generation fail validation or a version is not owned
- **THEN** the system SHALL reject or report failure without publishing artifacts as conforming or exposing another scope's data

#### Scenario: Version inspection and export
- **WHEN** an authorized user selects a saved version
- **THEN** the UI SHALL display only that version's actual compilation report and downloadable artifacts
- **AND** viewers SHALL NOT receive compilation mutation controls


### Requirement: Evidence-backed versioned rule catalogue
The system SHALL expose saved non-executable candidate rules with their evidence basis, source quotations, input definitions and unresolved information without claiming business approval or data completeness.

#### Scenario: Policy-source rule
- **WHEN** a draft rule cites a policy document
- **THEN** the catalogue SHALL retain that basis and evidence while business-policy verification and execution remain false

#### Scenario: Historical or empty catalogue
- **WHEN** an authorized user selects an older version or a foundation
- **THEN** the catalogue SHALL reflect only that version, including honest zero rules

### Requirement: Bounded read-only competency queries
The system SHALL execute only predefined definition-level queries on an owned, integrity-checked, conforming compiled artifact using bounded read-only result pages.

#### Scenario: Viewer query
- **WHEN** a viewer runs an allowlisted query with valid focus and bounds
- **THEN** the result SHALL include actual RDF rows, version/artifact provenance and explicit definition-only limits without model calls, source queries or mutations

#### Scenario: Invalid or unavailable query
- **WHEN** a request supplies arbitrary SPARQL, foreign focus, invalid bounds, a missing or failed compilation or a mismatched artifact hash
- **THEN** the system SHALL reject it or expose its prerequisite failure rather than return fabricated answers or an empty success

#### Scenario: Instance question prerequisites
- **WHEN** a supplied business question needs mapped company instances, complete policy, temporal applicability or exposure evidence
- **THEN** the UI SHALL show it as unavailable with those prerequisites rather than infer its answer from concept names

#### Scenario: Query selection changes
- **WHEN** a version, query, focus or result page changes during a request
- **THEN** the UI SHALL discard stale results and SHALL NOT automatically execute another query after a version or question change


### Requirement: Explicit bounded source graph mappings
The system SHALL map reviewed source collections and scalar fields from both owned Simpson sources to explicitly selected saved concepts/attributes without semantic label inference, company writes or model transfers.

#### Scenario: Exact serial engine path
- **WHEN** a manager explicitly builds a bounded engine graph with current mapping-plan hash
- **THEN** both databases SHALL be read with fixed safe projections, bounded operations and explicit zero/unavailable/truncated outcomes
- **AND** current authority and source state SHALL be rechecked before saving an immutable scoped snapshot

#### Scenario: Direct versus candidate association
- **WHEN** a record has an explicit ticket reference or shares an engine serial with another source
- **THEN** unique exact-type same-source references MAY form direct edges
- **AND** serial/scope matches SHALL remain candidates without merged physical-engine identity or confirmed recurrence

#### Scenario: Unresolved records and monitoring limits
- **WHEN** references fail to resolve or exposure/incorporation/policy evidence is absent
- **THEN** records SHALL be preserved with unresolved states and monitoring/warranty conclusions SHALL remain unavailable

### Requirement: Honest mapped-instance validation and graph inspection
The system SHALL validate explicitly mapped RDF attributes against saved shapes, report violations/conversion gaps and expose snapshot provenance and bounded coverage independently of business approval.

#### Scenario: Viewer or historical inspection
- **WHEN** an authorized viewer opens a version or saved graph
- **THEN** the system SHALL NOT query company sources automatically and SHALL expose only that scope/version's saved records and graph artifacts

#### Scenario: Source drift or revoked access
- **WHEN** source configuration/metadata/generation or authority changes during retrieval
- **THEN** the result SHALL NOT be committed or returned as a successful graph


### Requirement: Grounded remaining-module reference drafts
The system SHALL provide exact-source-cited curated draft definitions for all twelve modules and SHALL add only absent modules to a new immutable owned version after an explicit manager request.

#### Scenario: Preserve existing module work
- **WHEN** reference drafts are added to a partially populated version
- **THEN** existing concepts, rules, relationships, earlier versions and source graphs SHALL remain unchanged
- **AND** the new version SHALL label the added source as curated reference drafts without claiming model generation or verified policy

#### Scenario: Stale, foreign or repeated import
- **WHEN** revision/source/authority is unsuitable or the source bindings do not match the supplied reference
- **THEN** no partial version SHALL be saved
- **AND** an identical completed request key SHALL return its prior version without duplicate events

### Requirement: Source-qualified saved-graph intelligence
The system SHALL answer only fixed bounded snapshot questions with record/field citations and explicit gaps, using an owned immutable graph without new source queries, model calls, company writes or policy execution.

#### Scenario: Recorded observations
- **WHEN** a reader requests claim, inspection, quality, service or dated-observation information
- **THEN** results SHALL preserve literal source statuses, potential-versus-confirmed distinctions, value states, association qualification, graph bounds and provenance

#### Scenario: Unsupported business conclusion
- **WHEN** policy, identity, confirmed causality, incorporation or exposure evidence is absent
- **THEN** the report SHALL retain unavailable/not-evaluated conclusions rather than fabricate eligibility, rejection reasons, recurrence or rates

#### Scenario: Stale or invalid graph input
- **WHEN** a graph is foreign, belongs to another version, has damaged record hashes or invalid edge endpoints
- **THEN** the request SHALL fail safely rather than return a fabricated or empty success

### Requirement: Source-qualified warranty input readiness
The system SHALL prepare inputs for one explicitly selected ticket in an owned saved graph, retaining literal field states and provenance. It SHALL keep complaint and alternate hours separate, preserve numeric zero and expose missing/invalid dates and hours without imputation. Invoice records SHALL remain separate candidates with saved-value serial/OEM comparisons and no automatic identity resolution.

#### Scenario: Missing complaint hours with alternate ticket hours
- **WHEN** a ticket has top-level hours but no complaint-hour observation
- **THEN** readiness SHALL retain the missing primary input and show alternate hours separately without substitution

#### Scenario: Multiple or scope-mismatched invoices
- **WHEN** a saved graph contains several invoice records or different OEM references
- **THEN** each candidate and comparison SHALL remain visible without selection or reference-type coercion

### Requirement: Warranty readiness does not infer authoritative policy
The system SHALL return Requires Review and eligibility not_evaluated until an applicable complete structured policy, confirmed identity and explicit assessment-time basis are supplied by later work. Policy-kind documents, draft candidates, implementation code and stored warranty booleans SHALL NOT be treated as executable authority. Preparation SHALL make no company/model calls or source/live-application writes.

#### Scenario: Complete-looking inputs and a policy-kind document
- **WHEN** a saved ticket has parseable hours and dates and its definition version cites a policy-kind document
- **THEN** the system SHALL show the document as evidence only and retain policy applicability/completeness, identity and time-basis review requirements

#### Scenario: Explicit historical readiness and isolation
- **WHEN** an authorized reader prepares an owned historical ticket after a connector disconnects
- **THEN** readiness SHALL use that saved graph/version without external calls
- **AND** foreign graphs, non-ticket nodes and extra policy/input payload keys SHALL be rejected

### Requirement: Versioned source-cited warranty policy drafts
The system SHALL save bounded immutable policy draft revisions from owned warranty policy documents with per-clause exact quotations, explicit unknowns and unverified business authority. Existing ontology, source graph and policy history SHALL remain unchanged.

#### Scenario: Missing policy clauses
- **WHEN** a manager saves an incomplete cited policy draft
- **THEN** unknown clauses SHALL remain visible and SHALL NOT acquire defaults or executable authority

#### Scenario: Stale or duplicate policy submission
- **WHEN** a submission repeats a completed request key
- **THEN** the same revision SHALL be returned without duplicate audit
- **AND** conflicting revisions, changed-key payload reuse and foreign/non-policy evidence SHALL fail without partial writes

### Requirement: Source-qualified policy scope and date comparisons
The system SHALL compare one selected owned policy revision and saved complaint using an explicit assessment timestamp, declared scope/date basis and optional saved invoice. Results SHALL remain Requires Review with eligibility not_evaluated and non-executed limits/exclusions.

#### Scenario: Complete-looking policy and matching scalar evidence
- **WHEN** scope and effective-date observations match a saved draft
- **THEN** results SHALL describe candidate comparisons only and retain unverified policy authority and unresolved physical-engine identity

#### Scenario: Invoice date basis without a selected invoice
- **WHEN** the draft uses invoice date and no invoice candidate is explicitly selected
- **THEN** the date comparison SHALL be unavailable without choosing or inferring an invoice

#### Scenario: Read-only historical comparison
- **WHEN** a reader compares saved evidence after a connector disconnects
- **THEN** no source query, model call or company/decision write SHALL occur
- **AND** foreign or extra-input requests SHALL be rejected

### Requirement: Typed OEM account and company references
New source graphs SHALL distinguish ticket OEM accounts from OEM companies, preserve native identifier tokens in hashed field evidence and annotate explicit same-source reference fields. Company searches SHALL remain bounded with clipped search-domain coverage reported.

#### Scenario: Invoice company differs from ticket account identifier
- **WHEN** ticket.oem and invoice.oem refer to different namespaces
- **THEN** invoice scope SHALL use ticket.oemOrg and explicit account-to-company paths rather than equating the two oem fields

#### Scenario: Legacy graph without native identifier tokens
- **WHEN** a reader resolves associations in an older saved graph
- **THEN** equal public values SHALL NOT be presented as newly verified native-type equality

### Requirement: Evidence-backed saved engine associations
The system SHALL resolve only supported saved record references and report invoice/claim/QA candidates, conflicts, missing evidence and replacement context separately. It SHALL retain unresolved physical identity and non-evaluated eligibility without automatic invoice selection or entity merging.

#### Scenario: Single scoped invoice candidate
- **WHEN** serial type/value and explicit company paths support one saved invoice
- **THEN** it SHALL be labelled a scope-supported candidate, not confirmed physical-engine identity

#### Scenario: Conflicting company references or replacement serial
- **WHEN** company paths disagree or a linked dispatch records another engine serial
- **THEN** the conflict/context SHALL remain visible without silently selecting a company or merging engines

#### Scenario: Historical source-qualified report
- **WHEN** an authorized reader explicitly resolves an owned saved ticket
- **THEN** no company/model call or persisted source/identity mutation SHALL occur
- **AND** foreign/non-ticket/extra-input requests SHALL fail safely

### Requirement: Deterministic warranty decision with unknown precedence
The system SHALL return Warranty Eligible only with verified prerequisites and all required checks passing, Requires Review when required evidence or authority is missing, and Warranty Not Eligible only when verified prerequisites and complete evidence establish a failed condition. Caller-supplied verification flags SHALL NOT be accepted.

#### Scenario: Failure plus missing policy or exclusion information
- **WHEN** one limit fails but policy/identity or required exclusion evidence is unavailable
- **THEN** the final classification SHALL be Requires Review, not a denial

#### Scenario: Supported complete synthetic prerequisites
- **WHEN** trusted test inputs supply verified policy/identity and complete checks
- **THEN** the deterministic kernel SHALL distinguish eligible and not eligible without implying that such verified real evidence currently exists

### Requirement: Explicit cited calculation conventions
New policy drafts SHALL retain nullable cited coverage-mode, date/period convention, separate boundaries and exclusion interpretation parameters. Missing legacy parameters SHALL remain unknown without inferred defaults. Draft calculations SHALL be distinguished from final eligibility and business authority.

#### Scenario: Zero hours and a month-end anniversary
- **WHEN** the recorded primary hours are zero or a declared monthly anniversary falls beyond the target month's final day
- **THEN** the system SHALL preserve zero and use only the explicitly declared clamping/boundary convention

#### Scenario: Unknown exclusion findings
- **WHEN** a policy requires exclusion checks without mapped evidence
- **THEN** those findings SHALL remain unknown, without interpreting raw status flags or accepting caller overrides

### Requirement: Scoped saved-case warranty assessment
The system SHALL assess only explicitly selected owned saved policy/case/invoice evidence and an explicit assessment timestamp, with source/provenance hashes and read-only no-store transport. No company/model call, policy publication or case-decision mutation SHALL occur.

#### Scenario: Draft policy with seemingly passing calculations
- **WHEN** calculations pass but the policy is unverified and physical identity unresolved
- **THEN** the UI SHALL show draft calculations alongside Requires Review and exact blockers

#### Scenario: Explicit assessment without a policy
- **WHEN** a reader selects an owned saved complaint and explicit timestamp with policy_id null
- **THEN** the result SHALL be Requires Review with missing-policy evidence and null policy/source identifiers
- **AND** no placeholder policy or final eligibility SHALL be created

### Requirement: Source-qualified monitoring readiness
The system SHALL inspect an owned saved graph using an explicit inclusive calendar-date window and optional supported saved change record. It SHALL expose source observations and unmet identity/applicability/incorporation/comparability/population/exposure/coverage prerequisites. It SHALL NOT infer serial ordering, failure counts, recurrence, rates or effectiveness from source labels or bounded records.

#### Scenario: Complete-looking cut-in and claim observations
- **WHEN** change and claim fields exist without verified incorporation, comparable failures or exposure
- **THEN** metrics SHALL remain null/unavailable and source observations SHALL remain unverified

#### Scenario: Missing or invalid failure dates
- **WHEN** raw failure-date observations cannot be placed in the explicit window
- **THEN** missing/invalid states SHALL remain visible without date defaults or zero-failure claims

### Requirement: Explicit historical monitoring report
The system SHALL provide a scoped no-store read-only report with bounded pages, source hashes, explicit run/export actions and stale-result clearing. No company/model call, source mutation or monitoring schedule SHALL occur.

#### Scenario: Foreign graph, unsupported change or extra overrides
- **WHEN** inputs exceed the exact owned saved-evidence contract
- **THEN** the request SHALL fail safely without producing a monitoring conclusion

### Requirement: Evidence-qualified release audit
An explicit offline audit SHALL report artifact integrity, code/reference hashes and all 22 competency questions with their unmet production prerequisites. Available evidence tools SHALL NOT imply accepted business answers. Current production authentication admission failures and unverified operational checks SHALL remain release blockers.

#### Scenario: Passing artifact checks with unresolved business and authentication prerequisites
- **WHEN** owned saved artifacts pass the offline checks
- **THEN** public release readiness SHALL remain not_ready while production authentication and business acceptance are unmet

### Requirement: Isolated ontology-artifact recovery verification
The audit SHALL read explicit owned SQLite artifacts consistently and restore only allowlisted Business Ontology tables/columns to a fresh private database using fixed schemas. It SHALL preserve artifact/job contents without running services or replaying model calls and verify restored hashes/reports and unchanged inputs.

#### Scenario: Foreign scope, corrupt data or pre-existing output
- **WHEN** requested scope is absent, integrity fails or output already exists
- **THEN** the audit SHALL fail safely without modifying input or overwriting output

### Requirement: Existing shared-workspace functional activation
With explicit owner authorization, the system SHALL support a backed-up rollout to the existing shared-workspace environment while preserving its access controls and private backend. Such activation SHALL NOT claim individual-user production authentication or accepted business semantics.

#### Scenario: Owner defers individual login for functional verification
- **WHEN** the existing Builder services are updated for the requested test
- **THEN** complete backup/restored configuration checks and live Business Ontology verification SHALL precede a completion claim
- **AND** original ontology, connector settings and histories SHALL be preserved without new model calls or company writes

### Requirement: Executable reference evidence checks
The system SHALL provide deterministic handlers for the three exact supported reference safeguards, independently of immutable definition executability flags. It SHALL reject unsupported edited definitions and arbitrary code. Complete, contradicted and missing inputs SHALL produce explicit source-qualified outcomes; zero failures with valid denominators SHALL be calculable.

#### Scenario: Complete cited cohort evidence
- **WHEN** a reader selects an owned immutable complete-cohort evidence revision with valid counts, at-risk exposure and period
- **THEN** the rate handler SHALL calculate the failed-engine percentage and first-failure incidence per 1000 engine-hours with evidence/provenance

#### Scenario: Missing or contradicted recurrence prerequisites
- **WHEN** required evidence is unknown or complete evidence fails a condition
- **THEN** the handler SHALL distinguish insufficient evidence from recurrence not established and explain each check

### Requirement: Scoped cited rule evidence and explicit execution
Managers SHALL save bounded immutable case/change/rule-bound evidence with exact source quotations and revision/idempotency protection. Readers SHALL run checks on saved owned graphs and evidence without source/model calls or source/decision writes. Results SHALL include inputs, checks, source qualifications, hashes and export; input changes SHALL discard stale results.

#### Scenario: Foreign or mismatched input evidence
- **WHEN** evidence belongs to another owner, graph, subject, change or rule
- **THEN** execution SHALL reject it without overriding or merging evidence

### Requirement: Source-qualified warranty knowledge
The system SHALL import the reviewed supplied application warranty branches as immutable implementation-derived interpretations with exact source citations, source-hash and selector provenance. It SHALL keep written-policy authority, effectivity, scope identifiers and exclusions distinct and unknown when not supplied. Import SHALL be atomic, idempotent and owner/manager-scoped without model or company-source calls.

#### Scenario: Existing code answers a limit question
- **WHEN** the supplied reviewed source is imported
- **THEN** the library SHALL show its four OEM-name branches and invoice/sale/hour limits as code-derived knowledge, with inspectable saved revisions and without asserting contractual eligibility

### Requirement: Stable warranty revision selection
Revision selection SHALL persist the selected identifier while immutable detail loads, show loading and ignore stale responses. Empty selectors SHALL be disabled. Saved/imported revisions SHALL refresh case-comparison choices.

#### Scenario: Rapid selection during a slow response
- **WHEN** a reader selects a second revision before the first read finishes
- **THEN** the second selection and detail SHALL remain current when the first response arrives
