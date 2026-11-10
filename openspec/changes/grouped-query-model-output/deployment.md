Latest hosted query release: [mixed-numeric HMR fix](../mongodb-mixed-numeric-queries/deployment.md).

# Hosted grouped-query fix — 10 November 2026

Deployed to **https://praxi.bellcorpstudio.com/**.

- Release: `status-group-20261110-e7c7b86a2e82`.
- Source manifest SHA-256: `e7c7b86a2e821fe156cc9dc6e48aa8f2e0339beadb3660682cf76838430fe3bd`.
- Base commit: `36fc5cee6c7abf19107a1563064c72ffceedfad0` plus existing recorded changes and this one-file runtime fix.
- Frontend artifact retained: `73n0K7eciFUQ8gCNaRgsi`.
- Completed: 2026-11-10T13:31:59.216302+05:30 (India time).

Redundant grouping projections are normalized at the generic model-output boundary, before persistence, durable identity and consent. Explicit query validation and existing approved/saved payloads remain unchanged. Trusted report guidance distinguishes grouped metrics from engine-wide matched population and preserves missing/blank status semantics.

126 regression tests, one pagination test and 18 subtests passed. The corrected structured query was also executed read-only against authorized live Simpson data through an isolated application copy: 5,810 tickets, three status groups, complete grouped output with counts summing to 5,810, zero null/absent and zero blank statuses at that snapshot. No paid model calls or real Sheets/email writes occurred. The spreadsheet path was tested with controlled HTTP providers and existing approvals. See [verification](verification.md) for scope and limits.

Fresh verified backups and six baseline/candidate copied-store startup rehearsals preceded the existing backend/worker systemd rollout. Authenticated public checks and six desktop/mobile browser journeys passed; API writes were blocked in browser verification. All five services are active with zero automatic restarts, no critical logs during monitoring, and preservation checks passed for history counts, encrypted credentials and configuration hashes. No frontend switch, shared-contract change, destructive migration or database restore occurred.

Application-only rollback:

```sh
.venv-integrations/bin/python .local/status-group-deploy-20261110/rollback.py
```

It restores the previous runtime/crew.py and restarts existing backend/worker services without restoring databases, journals or frontend artifacts. Baseline source was rehearsed against copied stores. No rollback was needed. Private verified backups and evidence are retained in `.local/status-group-deploy-20261110/`.

Existing failed workflows were not rewritten or retried. Generate a new workflow with the original prompt to use the correction. Historical shared-store audit and other production-readiness limits remain separate.
