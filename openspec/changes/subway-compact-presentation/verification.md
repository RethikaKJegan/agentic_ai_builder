# Verification — 12 November 2026

## Implemented behavior

Subway demonstration content uses the brief **Demo data** indicator. New prepared summaries, message bodies, Calendar descriptions, subjects/titles and spreadsheet tab titles are normalized before downstream payload review. Report tables retain their numbers, currency groups, record references and column structure. Existing Subway workflow reports, inspectors, graph labels, Knowledge Map details and expanded diagnostics use display copies; canonical source documents, policy provenance, receipts, dataset manifests and saved workflows are not rewritten. Other tenants receive their original presentation data. Exact saved approval payloads remain execution authority and are never silently rewritten.

The Knowledge Map failure was reproduced against authenticated public HTTPS responses: both endpoints returned 200, but the ontology list contained the valid demonstration ontology at revision 0, which positive-only frontend list validation rejected. The frontend accepts nonnegative registered revisions and loads the workflow's authorized pinned snapshot independently of optional workspace module labels. A missing Subway demonstration pin cannot silently substitute another version. Existing other-tenant fallback behavior remains covered by regression tests.

## Automated results

| Verification | Result | Boundary |
| --- | --- | --- |
| Final affected backend acceptance | 26 passed | Exact isolated deployment source; normal Overview/workflow/automation runtime with controlled models and external transports |
| Wider regressions | 119 passed | Isolated candidate; lifecycle, ontology usage, Simpson isolation/ontology, adaptive evaluator, usage and conditional/paginated evidence |
| Frontend domain/components | 80 passed | Knowledge Map, reports, inspectors, orchestration and tenant-specific compact presentation |
| Browser journeys | 6 passed | Desktop/mobile for three tenants, isolated production frontend, controlled API fixtures |
| Genuine hosted ontology response parsing | 1 passed | Actual authenticated public ontology list and revision-zero snapshot |
| Final content-field normalization | 2 passed | Calendar descriptions, titles/subjects, spreadsheet tab titles/cells, idempotency and unchanged arithmetic/citations |

Counts overlap and must not be added together. TypeScript, changed-file ESLint, production build, canonical contract validation, generated UI-contract comparison, strict scoped OpenSpec validation and whitespace checks passed. Initial isolated build failures from missing shared test-import paths were corrected before the successful build. Initial browser attempts lacked the configured headless binary; the successful run used the installed Chromium executable.

## Genuine execution and deployment

An ordinary investigation completed using the configured OpenAI provider, normal Overview/save/validate/approve/execute APIs, existing Registry and deterministic assessment engine in a consistent isolated Subway application-store copy: `run_76d30985ae524df0922ccb793042ddb2`. Prepared report content used the concise marker while assessment receipts retained modeled provenance. No company write, production application write or external action occurred in this rehearsal.

The deployed backend is `.local/subway-presentation-release-20261112/app`; frontend is the sibling `frontend` directory. Only Subway backend and frontend restarted. Deployment health/preservation verification completed at **20:04 IST**. Frontend build ID: `rdAkVLyxq_5vug08JkGqd`. Release SHA-256: `4aacde1ae0d31e7b93449203e24eb553a280e0775820419862469785030ead28`.

Actual public desktop/mobile browser acceptance loaded the existing saved run's Knowledge Map with 28 graph nodes and the revision-zero saved ontology. Existing report content and expanded execution diagnostics contained no verbose banner; the workspace showed Demo data. Screenshot evidence is private. No API fixture replaced these hosted browser responses. The same desktop/mobile map, report and diagnostics checks also passed against the newly completed hosted report.

The first new hosted investigation executed query planning and the deterministic assessment but was blocked before report preparation by `ADAPTIVE_FALSE_COMPLETION`, because its evaluator decision conflicted with required completion evidence. This is not passing end-to-end evidence. Its saved workflow/run and block are retained, and no evaluator validation was weakened. A fresh execution of that same reviewed workflow completed through the deployed workers: `run_1e538caed0234316ad882d9f5d42d027`. All normal HTTPS compilation/save/validate/approve/execute steps returned 200. Its report uses Demo data, the assessment retains full provenance, and source selection remains automatic. [Open the report](https://praxi.bellcorpstudio.com/app/workflows/investigate?connected=1&composition=composition_e86910623ce5bbaaddc45af4&run=run_1e538caed0234316ad882d9f5d42d027) after signing in as Subway. The final protected-row comparison passed after this acceptance.

## Preservation and boundaries

A consistent compressed Subway backup and rollback service overrides were prepared before rollout. Original source and ontology definitions, 192 demonstration records, manifest, credentials, prior workflows/runs/receipts and schedules are preserved. Source-profile timestamps are normalized for comparison; the lifecycle registry's stored value is identical and only its startup updated_at timestamp refreshed. Shared backend source and unrelated service PIDs, including Simpson, remain unchanged. The shared frontend restart serves tenant-scoped rendering changes; no Simpson accounts, records, connections or workflows were edited.

Previously delivered emails, Calendar events and spreadsheets are not retrospectively rewritten. No real email/Calendar/spreadsheet delivery was submitted during verification. Full audit provenance remains available internally; this change does not relabel demonstration records as actual operational evidence.

Private evidence: `.local/subway-presentation-20261112/`, including release manifest, tests, actual-source schema responses, provider/hosted runs, browser screenshots, backup, deployment and preservation records. Credentials and operational payloads are omitted from this document.
