# Release audit and deployment preparation — chunk 13

**Later owner instruction:** individual login is deferred and the existing shared-workspace functional rollout is now active. See [chunk 14 access and verification](functional-rollout.md). The production-authentication findings below still apply to individual-user production readiness.

This prepares a reviewable release audit and recovery drill. It does not deploy Business Ontology, initialize the live workspace, restart services or change authentication/configuration. The original Ontology release is independent.

## Current release decision

**Public production release is not ready.** Current `workflow_api/security.py:deployment_mode` rejects `production` because trusted production login is deferred. The frontend workspace access cookie does not establish individual backend production identity, roles or tenant isolation. Do not bypass the rejection by exposing development authentication or changing the environment label.

All 22 blueprint business competencies remain **not accepted**. Source-qualified inspection, candidate rules and draft arithmetic are implemented, but those tools do not establish complete populations, authoritative policies, verified identity, confirmed failures or accepted production answers. In particular, current warranty coverage arithmetic uses the entered assessment date; it does not answer the first competency's verified failure-date question. Raw rejection/status fields do not establish rejection decisions. Bounded serial graphs do not retrieve all claims for an OEM. Cost rankings need verified cause/replacement links and comparable currency/valuation.

## Reproducible offline audit

Use a quiescent saved SQLite snapshot and explicit owned scope. The period is a diagnostic calendar window, not an accepted production monitoring period.

```bash
.venv-integrations/bin/python scripts/check_business_release.py \
  --database /absolute/path/to/private-snapshot.sqlite3 \
  --directory /absolute/path/to/fresh-private-audit \
  --workspace '<owned-workspace>' --owner '<owned-owner>' \
  --period-start 2026-01-01 --period-end 2026-12-31
```

Exit **2** means the audit completed and public release is not ready. Exit **1** means the audit was unavailable or integrity failed. Neither exit authorizes deployment. The command emits a small metadata summary; full results stay private.

The audit reads only ten allowlisted Business Ontology tables and exact known columns in one read-only SQLite transaction. It rejects absent owner scope, unexpected columns, over 2,000 rows per table or over 64 MiB of selected serialized artifacts. Optional absent artifact tables are reported explicitly, not invented. This is a bounded audit; larger production stores need a reviewed streaming/backup procedure.

It checks source text hashes, draft structure/evidence, compilation input/export hashes, graph/version/projected-record integrity and saved policy hashes/identities. It records saved compilation/instance-validation statuses; passing byte integrity does not mean every stored validation passed or business meaning is verified. Every graph's monitoring report is recomputed over the explicit period.

Outputs:

| Artifact | Contents |
| --- | --- |
| `report.json` | Owned row counts/hashes, integrity observations, release gates, all 22 exact questions/prerequisites with tool/gap mappings, source/dependency manifest, recovery checks and input-unchanged evidence |
| `ontology-artifacts.sqlite3` | Only owned allowlisted ontology artifacts, preserving original immutable documents and job states |

The fresh directory is mode 0700; files are mode 0600. The source manifest hashes relevant working-tree backend/frontend/reference/test/docs files and records the Git commit/dirty state and installed dependency versions. It excludes environment/key files. It identifies reviewed bytes; it is not a committed release package, frontend build attestation or vulnerability scan. No credentials are loaded and no network/company/model calls occur.

## Recovery drill boundary

The audit rebuilds fixed known table schemas and the one-active-generation-job unique index in a fresh private database. Owned row hashes and recomputed monitoring report hashes must match the original. The input file hash and a second consistent owned snapshot must remain unchanged; concurrent changes require a new quiescent snapshot/audit.

The recovery database contains no connector credential tables, encryption keys, login configuration, other owners or unrelated application tables. It preserves queued/running/terminal job records verbatim. **Keep this database offline; do not point a running application or generation worker at it.** Preserving an uncertain job record is not authorization to send it again. No worker is started or job replayed by the drill.

This verifies ontology-artifact recovery only. A full application recovery must separately back up and restore consistent application state, encrypted connector credentials, encryption-key custody, authentication/session configuration and any external artifacts; validate that complete restoration in an isolated target before release. This chunk does not claim that test passed.

## Deployment sequence to complete after blockers are resolved

1. Establish trusted production login, individual identities, workspace/role mapping, session expiry/revocation and origin/CSRF enforcement. Confirm backend production admission succeeds for the intended reason. Re-run viewer/manager/foreign-owner HTTP acceptance over actual HTTPS.
2. Record the target environment/storage, approved code revision/working-tree bundle hashes, frontend build identifier, dependency inventory and source bindings. Existing SQLite checks do not establish PostgreSQL or multi-replica acceptance. Keep backend listeners private behind the authenticated frontend/proxy.
3. Take a consistent full application backup with separately protected encryption keys/configuration, and complete the isolated full restoration described above. Preserve the independent original ontology, connector configuration and audit history.
4. In isolated staging, install the reviewed backend dependencies (including pinned RDFLib/pySHACL), build the frontend and run the relevant contract/backend/frontend/browser checks. Import no live model jobs. Verify owned empty/existing Business Ontology startup, historical artifacts, policy revisions, graph/report exports and expected safe errors.
5. Verify generation worker authority and interruption/cancellation behavior on the target. Inventory queued/running jobs before any restart; preserve uncertain outcomes and investigate rather than automatically resubmitting. Do not start runtime workflows, source builds or new OpenAI calls as incidental deployment checks.
6. Complete actual competency acceptance with authoritative source evidence. Policy authority/applicability/exclusions, stable physical identity/crosswalks, confirmed failure/incorporation, cohorts/exposure, status vocabularies and cost/currency gaps remain open. Sparse modules and unavailable metrics stay explicit.
7. Prepare the exact service promotion/restart plan and rollback artifacts for the chosen deployment. Perform authenticated HTTPS smoke tests and verify both ontology tabs, permissions, exports and worker state after promotion. Record real results rather than inferring them from local builds.

No target service promotion/restart command is executed or prescribed with assumed live service names here. The concrete target and authentication work must be resolved first.

## Rollback preparation

Retain the prior backend/frontend bundle and full backup. Revert the code/routing through the reviewed target deployment process while retaining additive Business Ontology tables and immutable/audit history. Do not delete the old ontology, reset connector settings, erase policy revisions or replay generation requests. A destructive data rollback requires a separately reviewed full restoration; this scoped recovery archive cannot replace the application database.

## Local evidence

The three earlier real invoice/ticket/QA private stores passed artifact recovery and reproduced graph/monitoring hashes, with one/four/two source records respectively, zero owned policy revisions and zero accepted business answers. All original input hashes/snapshots remained unchanged; company/model calls and company/input writes were zero. Public release stayed not ready. Final private reports and regression results are recorded in the chunk-13 verification section.

Frontend/runtime product code is unchanged in this chunk. The previous chunk's frontend/build/browser results remain prior local evidence; they are not live deployment acceptance.


The rule-execution follow-up extends scoped recovery to **twelve tables**, adding immutable `business_rule_evidence_heads` and `business_rule_evidence_versions`. Restore inspection checks cited evidence hashes/types, definition/graph binding, series identity and history/head consistency. Three-rule execution is implemented; the real company evidence required for the 22 competency answers is still assessed separately. See [rule execution](rule-execution.md).
