# Subway-only deployment — 12 November 2026

Target: https://praxi.bellcorpstudio.com/

- Active source: `/home/raf/agentic-ai-builder/.local/subway-persistent-demo-release-20261112/app`
- Release SHA-256: `40d14a49d2c8d6d892ccef8ac8c5ead212ba4054e385f4ef1f4d6f140b62b491`
- Persistent dataset: `subway-demonstration-v1`, revision 1, 192 records in 18 collections.
- Dataset/policy SHA-256: `e29d250b172a64701e3af577a8fa4c5db77d5662e68f3c1ddfd1bfeda128f80c`
- Explicit ontology: `bov_subway_demonstration_v1`, revision 0. The historical ontology remains the default.
- Service: `agentic-builder-subway`, port 8021. Only its backend configuration enables `BUILDER_SUBWAY_DEMO_ENABLED=1`.
- Dedicated override: `/etc/systemd/system/agentic-builder-subway.service.d/zzzzzz-subway-persistent-demo-release.conf`.
- Previous isolated Subway source remains available at `.local/subway-procurement-release-20261112-r2/app`.

Activation and health/preservation checks passed at 12:49 UTC. The candidate was copied from the previous isolated Subway release, with only 12 scoped runtime/API files changed and five demo/test files added. The existing deployed provider wrapper and shared service source were preserved. No frontend assets were rebuilt.

Use the existing Subway Overview with:

> Use Subway demonstration dataset v1. Investigate purchase orders against invoices, receipts, approvals and budgets under the modeled policy and prepare an evidence-backed report.

Review, approve and execute the generated workflow normally. The same explicit context works with ordinary count/sum queries and reviewed scheduled workflows. Model-generated reports are labeled as modeled demonstration evidence; record-level deterministic outcomes and dataset/knowledge hashes remain in actual receipts.

The real historical source records and connectors are retained. Existing records and credential/configuration hashes were checked immediately after restart; only housekeeping source-profile timestamps are normalized, as documented in `verification.md`. Other services and source hashes are unchanged.

Private deployment evidence and the consistent compressed backup are under `.local/subway-persistent-demo-20261112/`. Rollback restores its `backend-before.env`, removes only the dedicated persistent-demo systemd override, reloads systemd and restarts only Subway. The previous procurement override remains available. Existing data and the added demo evidence should be retained when rolling back; disabling selection requires no destructive database cleanup.

Hosted public HTTPS acceptance completed at 12:51 UTC using the deployed service and its existing background workers. [Open the completed report](https://praxi.bellcorpstudio.com/app/workflows/investigate?connected=1&composition=composition_4cc7e4a157a5b8cf4faf834f&run=run_4362cc5339b24d10aa32934c7406356b) after signing in as Subway. The run contains the selected demo dataset/hash, native query receipt, 470 deterministic outcomes, eight invoice reconciliations, actual Knowledge Map usage and a labeled report. Final existing-row, credential/key, shared-source and unrelated-PID preservation checks passed after this run. No live schedule was created by hosted acceptance.
