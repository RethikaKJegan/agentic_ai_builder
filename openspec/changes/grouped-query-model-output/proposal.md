# Canonical grouped query output and population totals

## Why
Saved Simpson run run_6a9d55ba611c494a943c736f41e160f6 failed because generated fields repeated its group_by key while metrics were present. It also named a duplicate grouped count overall_total, although all grouped metrics remain per-group.

## What Changes
At the generic query model output boundary only, remove redundant projected fields when all are already grouping keys. Persist the canonical model output before query validation, durable identity and recurring consent; never alter explicit query requests or saved/approved payloads. Preserve unsupported fields for rejection. Add trusted query/content guidance for group-key projection, per-group metrics, engine matched_rows as overall matched population and null/missing versus blank statuses.

## Impact
One runtime source file; no engine/schema/shared-contract change. Regression and grouped query-to-spreadsheet tests use controlled providers. Qualify a read-only grouped query against authorized source data without model calls or real Sheets/email writes. Deploy through verified backups and application-only rollback.
