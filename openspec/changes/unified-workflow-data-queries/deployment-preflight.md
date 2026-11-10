> **Superseded:** the user subsequently directed proceeding. The hosted release was deployed; see [deployment.md](deployment.md). The initial stop below remains historical evidence.

# Controlled deployment preflight — 9 November 2026

Decision: STOPPED BEFORE DEPLOYMENT. No application release was activated.

The user authorized a controlled application deployment to
https://praxi.bellcorpstudio.com/ subject to verified target access, backups,
rollback readiness and preservation of existing business data, workflow history,
credentials and scheduled jobs. The instruction explicitly requires stopping if a
critical prerequisite fails. It does not authorize destructive migrations, repairs
of historical production data or external tool actions.

## Verified target and active services

- HTTPS /login returned 200; unauthenticated /api/backend/session returned 401.
- nginx server_name is praxi.bellcorpstudio.com with its existing TLS certificate.
- nginx forwards this host to the frontend on 127.0.0.1:3001.
- Frontend uses the main backend on 127.0.0.1:8002 and existing selected-tenant
  endpoints on 127.0.0.1:8020 (Simpsons) / 8021 (Subway).
- agentic-builder-backend, agentic-builder-worker, agentic-builder-frontend,
  agentic-builder-simpsons and agentic-builder-subway are active.
- Main backend and worker started 5 November 2026; the frontend started 7 November.
  Service working directories point into the current repository, rather than an
  immutable versioned backend release directory.
- Existing frontend build observed: `KQHhQpTBedkYc5z5IxDWh`. This identifies the current artifact;
  no matching complete source-release manifest was established by this inspection.
- Checkout: branch agentic_ai_builder, HEAD `36fc5cee6c7abf19107a1563064c72ffceedfad0`, with uncommitted unified-query
  implementation and pre-existing unrelated changes. HEAD alone does not identify
  the pending release or all code loaded by the running services.
- Privileged service-control access is available. No service-control action was taken.
- Main application store: .local/workflows.sqlite3 (4,244,287,488 bytes observed).
  Isolated tenant configurations reference their respective
  .local/tenants/simpsons/workflows.sqlite3 and .local/tenants/subway/workflows.sqlite3.
  Credentials/configuration values were not printed or changed.

## Critical failed prerequisite

The independent follow-up investigation still explicitly records:

> Historical shared-store impact remains BLOCKED for independent operator audit.

Evidence:

- openspec/changes/final-platform-validation/verification.md
- openspec/changes/final-platform-validation/evidence/bootstrap-audit.json
- openspec/changes/release-blocker-remediation/verification.md (read-only bootstrap investigation)
- openspec/changes/release-blocker-remediation/evidence/bootstrap-investigation.json

The import-time initializer defect has subsequently been fixed in source, but
that preventive fix does not establish the historical incident's record/schema
impact. Available November 3 backup/schema information and later service logs
cannot attribute intervening changes to the incident. No immediate pre-incident
fingerprint or transaction audit establishes data equivalence. This deployment
preflight did not repair or restore any business records.

Accordingly the requested shared-data preservation assurance could not be
established under the current deployment conditions. Creating a fresh backup
would preserve today's state; it would not resolve the documented historical
integrity uncertainty. This is an evidence gap, not a claim that corruption or
record loss has been proven.

## Actions deliberately not reached after the stop gate

- No new release-specific backup set was created or verified.
- Existing rollback artifacts were located, including prior frontend builds and
  earlier source/database snapshots. Complete rollback readiness for all active
  backend/worker/tenant services was not established, and is not claimed.
- No new production build activation, migration, backend startup rehearsal against
  live data, service restart or nginx change occurred.
- No read-only business workflow was submitted on the live system, no paid model
  call was made, and no email, Sheets write or other external effect was triggered.
- Business Investigation/CrewAI/query/tool execution was not verified on the live
  site. Previous controlled integration results remain in verification.md.
- Data Intelligence Questions and existing scheduled services were left running;
  their end-to-end behavior was not requalified in this blocked attempt.

## Required evidence before another deployment attempt

An independent operator must resolve the shared-store incident assessment against
available authoritative backup/audit evidence and record the integrity decision
and any outstanding limitations. Then establish a consistent verified backup set
for the main/tenant stores and credential/job state, identify and rehearse the
backend/frontend rollback release, run copied-store startup/migration checks, and
complete the authorized application rollout with read-only smoke tests. Application
rollback must not blindly restore databases or erase intervening work.

No additional deployment version is reported because nothing was deployed.
Recorded at 2026-11-09T16:52:58.467086+00:00.
