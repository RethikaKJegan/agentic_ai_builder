# Whole-envelope routing budget: verification and release

## Confirmed failure

The saved failed job `plan_3ec22e448cc34fbab775ffb41988ebc0` retains
`OVERVIEW_CONTEXT_LIMIT`, HTTP 422, with request reference
`a1ec7877-832a-48f2-a805-eeb2c6f91297`. The terminal job's request body has been
cleared by existing retention behavior; the exact objective was recovered from
the user's screenshot, not guessed from the error.

The preceding discovery correction bounded that component independently. It did
not bound the combined intent-preparation envelope. Source-cited knowledge,
account/recipient inputs, tool capabilities and event-source metadata are added
before the router enforces 220,000 bytes. Thus discovery can satisfy its 180,000
byte ceiling and still cause the complete request to fail before a provider call.

## Scoped correction

Two production files changed:

- `workflow_api/overview_automation.py`: name the existing total ceiling and
  allocate discovery capacity from the actual serialized envelope after every
  sibling component is present. Account for replacing an empty JSON object with
  the discovery object. Keep the final guard as defense in depth.
- `workflow_api/subway_queries.py`: accept an internal caller allowance for
  discovery, capped at its existing component ceiling. Existing field-suggestion
  ranking and returned/total metadata counts remain; all authorized source
  descriptors and supported relationships stay available.

No prompt phrase, supplier, recipient, record identity or business metric is
hardcoded by this fix. No ceiling was raised. Knowledge, account context,
permissions, query execution and source completeness semantics are unchanged.
Unrelated application source hashes match the preceding deployed baseline.

## Full copied-store replay

A consistent online snapshot of the actual Subway store was used with the actual
owned connected account and current source metadata. Network connections were
disabled, workers were not started, and only the intent interpretation response
was controlled. All protected copied-store records remained unchanged.

| Request | Old combined bytes | New combined bytes | Source descriptors |
| --- | ---: | ---: | ---: |
| Exact screenshot procurement/email prompt | 256,604 | 218,897 | 52 |
| Biggest orders and supplier-ranking variant | 256,433 | 218,941 | 52 |
| Procurement/vendor/currency summary variant | 256,375 | 218,882 | 52 |
| Explicit demo-profile variant | 256,288 | 218,896 | 52 |

All four completed full intent preparation while retaining the selected account,
resolved recipient, knowledge and relationship identities. This establishes the
specific size-bound correction, not live model interpretation or email delivery.

## Regression checks

98 final passing cases across disjoint module selections:

- Four new checks exercise different business wording, varying knowledge sizes,
  multibyte Unicode, event metadata, owned Google account validation, complete
  source/relationship descriptor preservation, and the unchanged component cap.
- 51 existing Overview and Subway intelligence checks passed.
- 43 additional Simpsons-isolation, Overview integration, native full-query and
  demo-definition checks passed. Existing email/Sheets paths are included.

The initial new fixture used a placeholder Google ID and was correctly rejected
by existing account validation. It was corrected to provision an owned synthetic
connection through the established Google fixture. No authorization check was
removed. The repeated component-limit case is counted once above.

Shared contracts, strict OpenSpec validation and whitespace checks passed.
No frontend files or shared execution contracts changed, so no frontend rebuild
or repeat UI suite was required for this backend-only fix.

## Hosted deployment

Activated at **12:15 AM India time on 12 November 2026**
(`2026-11-11T18:45:24.290477+00:00`). Only the Subway backend restarted.
Frontend build `qoJwzCx2UyYB22_4MK4xe`, its process, the operator and Simpsons
backends and shared operator worker were preserved.

Authenticated public session, workflow page, tools, worker-health and query routes
passed for all three accounts. Native Subway tools are registered. Foreign source
access is denied both ways. All five application services are active with zero
automatic restarts at verification.

History counts, Google connection records, ontology/package records and automation
records were preserved. Subway source credentials/bindings match the consistent
backup, excluding only normal `updated_at`/`last_profiled_at` profiling timestamps.
Credential/configuration file hashes are unchanged. No database restore,
destructive migration, live workflow submission, model call or provider action
was used for deployment verification. Historical failed jobs remain preserved.

Private rollback sources, verified SQLite backup, configuration hashes, complete
replay results, manifests and public checks are under
`.local/overview-routing-context-budget-20261112/`. The two rollback files were
recovered from the exact preceding deployed source archive and verified against
its manifest before activation.

Refresh and explicitly retry generation with the same business prompt. No demo
prefix, field names or narrower business objective is required for this fix.
