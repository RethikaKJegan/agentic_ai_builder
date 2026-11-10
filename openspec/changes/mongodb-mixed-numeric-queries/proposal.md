# Bounded mixed-numeric MongoDB aggregation

## Why
The saved HMR query is valid but its integer/number metadata is not recognized by physical planning. It falls back to full application reads and hits the 5,000-row cap on a 5,810-record source. Reducing display limits would not change the source scan and must not change statistical denominators.

## What Changes
Recognize reviewed Mongo numeric families, including integer/double mixtures, for the existing database aggregate executor. Check actual BSON types, existing numeric magnitude/fraction/row limits, and lossless double-to-decimal-to-double round trips. Preserve unsupported/mixed text types and PostgreSQL float behavior. No arbitrary coercion, sampling, raised global caps or dropped records.

## Impact
One query compiler source file. Real isolated Mongo precision/equivalence tests, existing engine/runtime regressions and authorized live read-only qualification. Existing verified backup, startup rehearsal, rollback and hosted rollout process; no real email/Sheets writes or paid model calls.
