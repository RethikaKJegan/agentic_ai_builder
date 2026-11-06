# Verification — 6 November 2026

## Completed implementation

- Analyzed and fingerprinted both supplied local archives, extracted all BSON and
  metadata privately, counted records and sampled up to 200 records per included
  collection. Original compressed archives and extracted BSON remain available.
- Restored 52 selected business collections (1,218,822 records) into a separate
  authenticated Subway MongoDB service. Preserved exclusions, metadata, encoding
  repair counts and reference probes in private onboarding reports.
- Seeded a five-layer, nine-module Subway draft with 54 concepts, 11 qualified
  candidate references and zero invented policy rules. Definition citations/hashes,
  OWL/RDF output and SHACL definition/shape validation passed.
- Connected the existing source browser, ontology planner and workflow pipeline.
  Server-selected package revision 1 supplies 12 bounded read capabilities;
  runtime rechecks owner, source, metadata and pinned bindings.
- Staged all mapped reads against the actual restored reader. A bounded store read
  completed through the existing action-plan compiler, Registry and graph runtime.
  This smoke run used a disposable application-store clone, not the deployed store.
  Zero external model calls or company writes occurred.

## Regression checks

- Initial affected backend suite: 146 passed, covering authentication/isolation,
  ontology, compiler, planning, sources, action plans and generation.
- Final changed backend/security suite: 113 passed, including new archive traversal,
  endpoint substitution, source revocation and package isolation tests, plus existing
  Simpsons/Subway authentication, generation, source and runtime-memory regressions.
- Frontend original suite: 521 passed. Two additional Subway contract/UI tests pass.
- Type checking, lint, production build, shared contract validation and strict
  OpenSpec change validation passed. Existing dependency deprecation warnings remain.

## Deployment and preservation

The dedicated Subway service now uses the prepared snapshot and full business-only
runtime configuration. Its systemd unit depends on the dedicated Subway MongoDB
service. Frontend changes were built and the existing frontend service restarted.
The existing frontend service remains on its previously configured Next dev command;
this onboarding did not change its process mode.

Private release evidence and rollback inputs:
`.local/tenants/subway/onboarding/release-20261106/`.
This includes the auth-only database backup, prior/new backend env and service unit,
credential/config hashes, live HTTP results, browser receipts and screenshots.
The active manifest references the private `prepared-v5/restored-sources.json`.
Preserve this directory and the live MongoDB data directory.

Public HTTP verification confirms both original login credentials authenticate to
separate workspaces, each has its own two sources and ontology, wrong-audience
assertions are denied and foreign source IDs return not-found. Subway's two business
source roles and bounded source-record reads work through the ordinary public proxy.

Simpsons retained the same running backend PID. Its saved ontology, source metadata
snapshots, workflow revisions, knowledge rows, config/credential files and source
count matched the pre-deployment fingerprints. Its original worker continues to
update normal connection profiling timestamps; connection documents are consequently
not claimed byte-for-byte unchanged. No Simpsons service restart was performed.

## Practical limits

These are read-only archive snapshots, not live production synchronization. Source
schema and bounded native-ID matches establish descriptive candidates, not policy,
confirmed joins or complete semantic interpretation. Approval-stage references had
11 unmatched IDs in the 200-record probe. Eight derived records needed UTF-8
replacement. No source instance conformance or OWL reasoning is claimed.

Package reads are bounded to 25 projected rows, without arbitrary filters or
population aggregates. Readiness refers to that bounded retrieval only. Existing
source browsing supports paging. Subway-specific operational case templates,
external integrations and approved business rules require additional authoritative
requirements. The user's live AI chat test remains deliberately unperformed; the
user explicitly chose to perform that test themselves.

Final browser verification passed four actual public sessions: Subway and Simpsons
on desktop and mobile. Both ontology pages load, Subway shows both source roles and
store browsing controls, with zero page errors and no horizontal overflow. The final
frontend suite passed all 523 tests across 79 files. Screenshots and receipts are in
the private release directory. Additional direct backend checks used the actual
foreign connection IDs and received 404 in both directions.

Normal chat planning also receives authenticated, version-pinned Subway concept,
mapping and cited ontology context alongside the eligible capability catalogue.
This path is verified locally with a controlled planner response and actual source
reader/runtime; it does not constitute a live model response test.

The final planning/context changes passed 62 additional focused backend tests.
The controlled normal-chat request (automatic inputs and empty business-request
context, with a local planner response) completed its real Subway source-read run.
The final Subway backend was restarted with those changes; public login, source
reads and isolation checks were repeated successfully. Simpsons remained running.
