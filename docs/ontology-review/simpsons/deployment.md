# Simpsons ontology deployment — 2026-10-30

**31 October release:** the [source-backed record explorer](object-explorer.md) is live. Frontend build `Luy8ChhV-XPO0tJlhuS7D`; ontology version `ov_3c9e855088f5ac678e11127661eae182b5189707`. It extends the [concept graph](graph-ui.md) with permitted source values and linked records. Existing approved meanings remain unchanged: 409 approved records, seven drafts. Native technical revalidation adds revision/history entries and a new publication. Earlier release details below are retained as history.

The owner approved deployment and publication of the reviewed descriptive ontology. Open [Data Intelligence](https://praxi.bellcorpstudio.com/app/data-intelligence) and select **Ontology**. Refresh the page and sign in again if the backend restart invalidated an older browser session.

The running application contains **416 Simpsons records: 409 approved and seven unresolved drafts**. The approved records include the common/domain/organization concepts, supported typed attributes, provisional mappings, relationships and documented constraints. Approval covers these descriptions with their stated uncertainty; it does not make undocumented business policies executable or establish independent SME calibration.

Current version: `ov_d633a24f73d20898769885f779fe39c4fb929723` (409 records). Frontend build: `tWVmsTzo3PodyiFlIgA72`. Backend, frontend and scheduled worker were restarted through the existing systemd services and are active.

## What is visible

- Three ontology layers, searchable definitions, source catalogue and bounded profile evidence.
- Per-record source references, constraints, dependencies, assessment availability and correction history, including the preserved review hashes and targeted field evidence.
- Explicit owner acceptance and the seven remaining unresolved field bindings. The original evidence classifications remain separate from approval status.
- Published version history, export and bounded concept/dependency selection. Seven unresolved attributes are excluded from approved task context. Selecting the Service ticket concept produced 42 records on the live API.
- Unavailable calibrated precision/false-positive values rather than invented scores. The review counter counts review actions, including 58 evidence revalidations; it is not a count of independently calibrated relationships.

## Verification and root-cause correction

The staged publication used the existing review and publication services before promotion into the application store. The [owner approval](owner-approval.json) records the actual instruction and scope. No expert identity or business policy answer was fabricated.

Live checks found that a subsequent bounded metadata sample could omit the two targeted ticket fields. This was genuine evidence drift in the first published version, so it was retained in history rather than overwritten. Added ontology-owned source-observation persistence and sample reconciliation: confirmed fields remain prior observations when later samples omit them, with explicit warnings. Freshly observed types and declared-schema prohibitions remain authoritative. Evidence is bound to the same connection and credential fingerprint; credential replacement disables its reuse. Public metadata retains the existing `sampled`/`declared` field contract, with no shared contract change.

Revalidated 58 affected records without changing their business definitions and published the current version. The older version remains inspectable and stale; its stale context cannot silently authorize current selection. A real resumed-worker metadata refresh then completed with **zero stale records**, and both live source metadata payloads passed the shared metadata contract after removing the common response-envelope annotations.

Authenticated live desktop and 390px mobile checks passed: layers, owner history, technical evidence, unresolved-field display, version export and approved dependency selection. Both had zero page errors and no horizontal overflow. Browser verification permitted only the intended ontology selection POSTs and no workflow/source/tool mutations. Screenshots and machine evidence are retained under `.local/ontology-foundation/deployment/`.

Validation:

- Backend/API/runtime regression: **227 passed**, 24 subtests, one previously reproduced baseline tools-list assertion excluded. Log: `/tmp/ontology-deploy-backend-tests.log`.
- Import-history fix: **32 passed**. Log: `/tmp/ontology-deploy-history-tests.log`.
- Observation persistence/construction/source/ontology checks after the final fix: **86 passed**. Log: `/tmp/ontology-deploy-drift-fix-tests.log`.
- Final source/database-workflow/retrieval/runtime regressions: **131 passed**, 18 subtests. Log: `/tmp/ontology-deploy-drift-regressions.log`.
- Final isolated PostgreSQL adapter suite: **27 passed**. Log: `/tmp/ontology-deploy-postgres-final.log`. The temporary cluster was stopped afterward.
- Frontend review/API compatibility: **13 passed**; TypeScript and changed-file lint passed. Isolated desktop/mobile lifecycle: **2 passed**; live desktop/mobile checks also passed.
- Shared schemas/fixtures, generated UI contract drift checks, strict OpenSpec validation and diff checks passed.
- Full production build completed with exit zero on the ordinary retry and the exact tested artifact was activated, retaining 64 existing static assets. The first attempt emitted the installed Next.js security-upgrade notice. This deployment did not upgrade dependencies or claim that the advisory was remediated. Logs: `/tmp/ontology-deploy-build.log`, `/tmp/ontology-deploy-build-retry.log`.

An initial activation guard detected changed connection timestamps while source revisions/content remained identical. The check was narrowed to actual source scope, credential generation and snapshot content while preserving the newest connection status. The first backend readiness request also carried an invalidated pre-restart backend session; a fresh authenticated session verified readiness before frontend activation. These intermediate checks did not fabricate publication success or alter source authority.

## Preservation and remaining work

No company records or source schemas were modified. Connector identifiers/encrypted credentials, existing reviews, saved workflow revisions and runtime runs compared unchanged. No company workflow was created or executed by verification. The source refresh checks performed bounded reads only. Local metadata, ontology records, review events, versions and selection manifests were updated as authorized.

Seven bindings still need authoritative schema/model evidence. Independent business-rule review and representative calibration remain pending. Full Simpsons business acceptance is not inferred from owner-approved descriptive publication.

Application backup: `.local/ontology-foundation/deployment/application-before-ontology.sqlite3`, owner-only permissions. Previous frontend artifact: `.local/ontology-foundation/deployment/previous.next`; previous tracked backend sources and base commit are recorded beside it. Rollback can restore the previous frontend/backend code while retaining additive ontology tables and audit history. Coordinate any whole-database restore with current activity rather than erasing subsequent application work.
