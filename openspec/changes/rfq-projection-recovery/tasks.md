- [x] Categorize Sheets HTTP failures without exposing provider bodies.
- [x] Reconcile a sent-RFQ projection once from exact stored intent and current table values.
- [x] Preserve sent receipts and failed runs; test recovery and denial cases.
- [x] Run focused checks and report what remains live-unverified.

24 focused recovery, fulfilment-guard and Sheets connector tests passed. Shared contracts, strict scoped OpenSpec and diff checks passed. Read-only live Sheet inspection and dry-run confirmed the failed row equals its known prior revision; all four Gmail submissions have persisted receipts. Original provider details were suppressed, so the exact HTTP/timeout cause is unknown. Generic recovery is restricted to one sent-RFQ projection, verifies its immutable intent and current row, and never retries sends. Loaded into existing API/worker services after confirming no running invocations. Live resume result is recorded separately below. Other concurrent repository changes were retained.

Live result: original project resumed STOPPED → RFQS_SENT with issues=[], projection_read and sync_sent_*_reconcile1 completed. Original four send run IDs remain unchanged and completed. Additional no-mail-replay test passed (25 focused tests total). No RFQ email was resubmitted by recovery. Awards/fulfilment remain dependent on new valid replies and are not claimed live-verified by this repair.
