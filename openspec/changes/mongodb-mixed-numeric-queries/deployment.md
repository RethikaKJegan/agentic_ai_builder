# Hosted mixed-numeric HMR query fix — 10 November 2026

Deployed to **https://praxi.bellcorpstudio.com/**.

- Release: `hmr-numeric-20261110-185991c4e8f4`.
- Source manifest SHA-256: `185991c4e8f406ae66092174651cdce7bbd6a7f6695af93efd490e4a5e67f8d5`.
- Base commit: `36fc5cee6c7abf19107a1563064c72ffceedfad0` plus existing recorded changes and this single query-compiler update.
- Frontend artifact retained: `73n0K7eciFUQ8gCNaRgsi`.
- Completed: 2026-11-10T13:55:52.586151+05:30 (India time).

The valid HMR query previously fell back to the 5,000-row reader because mixed integer/number metadata was not eligible for native Mongo aggregation. It now uses the existing bounded database executor with actual BSON type, decimal-envelope and lossless round-trip checks. No global limit was raised and no partial/sample statistic is presented as complete. The database-source cap remains one million rows; unsupported application shapes and other safety limits remain enforced.

87 regression tests passed; 21 PostgreSQL-dependent tests were skipped without a DSN. Authorized live read-only qualification scanned 5,810 source records and returned 1,588 matches, HMR minimum 0.1, maximum 100, average approximately 33.7464105793. A separate snapshot counted 41 null/absent HMR values. No paid model call, live workflow submission, source write, email or real spreadsheet creation occurred. See [verification](verification.md) for exact evidence and limits.

Fresh verified backups and six offline baseline/candidate startup checks preceded the existing backend/worker systemd rollout. Authenticated public checks, six desktop/mobile browser journeys, history counts and encrypted credential/configuration preservation passed. All five services are active with zero automatic restarts and no critical post-activation backend/worker logs. No frontend switch, shared-contract change, destructive migration or database restore occurred.

Application-only rollback:

```sh
.venv-integrations/bin/python .local/hmr-numeric-deploy-20261110/rollback.py
```

It restores the previous workflow_api/data_query_pushdown.py and restarts the existing backend/worker services, without restoring databases, journals or frontend artifacts. Baseline source was rehearsed against copied stores. No rollback was needed. Private verified backups and evidence are retained in `.local/hmr-numeric-deploy-20261110/`.

Existing failed runs and durable jobs were not rewritten or silently resubmitted. Generate a new workflow with the original prompt. Historical audit and other production-readiness limits remain separate.
