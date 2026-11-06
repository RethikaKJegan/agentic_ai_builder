# Simpsons workspace audit — 6 November 2026

## Scope

Live checks used the authenticated Simpsons workspace and read-only source access.
No paid model calls, messages, spreadsheet/calendar writes or live workflow executions
were performed. Workflow execution/approval behavior was exercised through existing
isolated regression fixtures. A copied Simpsons application store was used for
current-source retrieval preparation and a bounded read with a nonexistent identifier.

## Findings corrected

1. Runs and Monitoring unconditionally polled legacy `/cases`, although the isolated
   deployment intentionally has no shared IMAP/customer-reply monitor. This produced
   repeated 503 responses. Session now advertises `reply_monitor_available`; the
   frontend suppresses this optional component/polling when explicitly unavailable.
   Configured operator deployments retain the component. This endpoint is separate
   from the existing business-case and workflow-run features.
2. Dedicated-store startup interpreted `builder_worker_leases.owner` as a tenant user.
   A supervisor lease left after an unclean shutdown could consequently prevent
   restart. Startup now validates the exact coordination-table shape, fixed lease
   name, server process identifier format and numeric expiry before exempting that
   process owner. Other workspace/owner checks remain. A foreign lease owner is
   rejected. Existing supervisor expiry/fencing behavior is unchanged.

## Verification

- Broad backend regression suite: 242 passed, including client isolation, Google
  ownership/scopes, data queries, source browsing, ontology generation/compilation,
  planning, composition, connected action plans, lifecycle UI and release checks.
- Final changed client/Google tests: 12 passed, including restart with process lease,
  foreign lease rejection and optional-monitor availability.
- Final frontend suite: 529 passed across 81 files.
- Production build, TypeScript, lint, shared contract validation, strict OpenSpec
  validation and diff whitespace checks passed.
- Live APIs returned success for session, tools/capabilities, accounts, sources,
  ontology, jobs, workflows, runs, approvals, monitoring and overview.
- Simpsons currently has two connected Google accounts, two connected/profiled
  MongoDB sources and its saved 79-concept ontology. Account identities and values
  are excluded from public audit records.
- Both owned databases returned bounded source records. Actual foreign Subway
  connection IDs were rejected. Active worker components had no current errors.
  Historical stale worker records are retained as history, not current failures.
- Current-schema complaint, inspection and warranty preparations are ready with
  all selected mappings available and zero model calls. A deliberately nonexistent
  engine ID completed a bounded complaints read with zero records. Inspection
  completion evidence, applicable warranty policy, assessment date and exclusion
  findings remain legitimate business evidence requirements, not invented facts.
- Metadata-change warnings reflect baseline/current revision differences. They
  remain visible; current-schema mapped reads and preparation passed. The audit
  did not erase warnings or rewrite the saved ontology baseline.

## Deployment

Restarted both dedicated client backends and frontend after verification. Stored
Google connection rows, ontology versions/workspaces, metadata snapshots, workflow
revisions and runtime rows matched pre-deployment fingerprints for both tenants.
Backups and receipts are private under `.local/simpsons-audit/`.

The first post-restart browser pass overlapped backend startup and observed transient
session 503s on its first two pages. The final browser pass was repeated against the
ready services. Final results are recorded in `browser.json` and `browser-final.log`.

## Limits

This audit does not establish zero defects or guarantee every natural-language goal.
No real model response or outgoing integration effect was tested. Provider outages,
expired/revoked consent, ungranted scopes, unsupported query semantics and missing
business evidence can still affect specific requests. Existing deterministic and
controlled-provider workflow tests cover the corresponding application boundaries.

Final ready-service browser verification passed all 28 desktop/mobile page and
ontology-source checks: zero page errors, failed API responses, unexpected error
screens or horizontal overflow. Runs/Monitoring no longer poll the unsupported
legacy reply monitor. Both client backends and frontend are active.
