# Scope generated reports to their execution action

The live inventory run passed research/ranking and spreadsheet approval, then
failed on create_report. Sheet setup identity uses workspace/project/creation_key;
the compiler uses a constant report_v1 key, so fresh reports with different live
findings collide with an earlier completed spreadsheet. Provisioning identity is
appropriate for permanent setup but not per-run reports.

Give report exports an immutable identity from workflow namespace and the runtime
action reference (run:node), retaining project/key and input fingerprint checks.
Same action retries reuse one verified spreadsheet; a fresh action produces a
fresh report. Keep setup connector identity unchanged. Preserve old journal rows,
approval gates and uncertain-effect protection. Reconciliation must accept the
exact report action reference. Verify changed-input and cross-run cases offline
through the actual connector and native runtime before deployment.
