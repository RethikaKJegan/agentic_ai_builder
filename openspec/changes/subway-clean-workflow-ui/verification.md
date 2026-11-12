# Verification — 12 November 2026

Subsequent backend follow-up: [actual delivery content cleanup](../subway-clean-delivery-content/verification.md) now applies the cleanup before approval and delivery. The frontend-only rollout evidence below is retained.

This follow-up is frontend-only. It supersedes the visible Demo data marker introduced by the earlier presentation change. Backend generation of actual email, Calendar and spreadsheet payloads is unchanged; existing deliveries are not edited.

## Presentation

Removed the workspace badge and demonstration prefixes in Subway report previews, supplier display names, workflow node summaries, graph relationship labels, concept definitions, tooltips and technical detail panels. Supplier names display as Supplier 1/2/3. Repeated known provenance/policy boilerplate is omitted from presentation. Evidence headings use Notes; actual currency separation, source coverage, missing evidence, blocking gaps and numerical results remain visible. Background knowledge/recovery and adaptive-progress text use the same scoped presentation.

Canonical objects and submitted execution contracts retain their original identifiers, source relationships and provenance. Opaque reference names are abbreviated only in rendered technical text, after serialization/model identity resolution; those display aliases are never submitted as workflow or action authority. Array positions, table dimensions, monetary amounts and currency codes are unchanged. Non-Subway presentation remains unchanged.

## Verification

- **116 frontend tests passed**, covering presentation, Knowledge Map, ontology usage/context, node inspectors, reports, query tables, background/recovery, lifecycle and builder/adaptive UI. Tests verify unchanged input objects, numeric/currency values, IDs and exact saved payload references.
- **Eight browser journeys passed**: existing desktop/mobile journeys for three tenants plus Subway-specific desktop/mobile checks across Workflow, Steps, Reports, Knowledge Map, Background, clicked workflow nodes and expanded technical details. Controlled API fixtures; no external actions.
- TypeScript, changed-file ESLint, isolated production build, strict scoped OpenSpec and whitespace checks passed.
- An initial test command used the repository root rather than frontend cwd and collected no tests; it is not counted as passing evidence. The final run used the correct frontend directory.

## Actual hosted acceptance

Read-only checks of the retained completed Subway workflow `composition_e5cbf556af5e5316bf38b593`, run `run_7f73974c485643e1980dd5fcc141eda8`, passed on the public site. The Knowledge Map rendered 16 nodes. Workflow, Steps, Reports, Background, a clicked content-preparation node, expanded details/diagnostics and the Knowledge Map contained no demonstration wording or limitation headings. Desktop and mobile checks passed without browser errors. Evidence facts remained visible. No response fixture replaced the hosted API.

The first hosted attempt referenced an older acceptance workflow that had subsequently been deleted; the API correctly returned 410. It is not counted as passing evidence, and no deleted workflow was restored. The successful check selected a retained completed workflow through the ordinary read-only listing API.

## Deployment

Only the frontend restarted, at **20:34 IST**. Isolated release: `.local/subway-clean-ui-release-20261112/frontend`. Build ID: `6csstwFbPIsnB_HGLFB-X`.

The candidate was copied from the active frontend and overlaid with exactly nine UI source/test files. No backend file or configuration was changed. Before/after checks verified all four backend service PIDs and Python source hashes unchanged, including Subway and Simpson. Existing static assets were retained for already-open browser sessions. The preceding frontend release and systemd override are retained for rollback.

Private evidence: `.local/subway-clean-ui-20261112/` contains source manifest, type/lint/build/test logs, browser evidence and deployment verification. No paid model call, workflow execution, source write or email/Calendar/spreadsheet action was submitted by this change.
