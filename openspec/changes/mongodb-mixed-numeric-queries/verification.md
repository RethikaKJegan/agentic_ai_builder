# Mixed-numeric Mongo query verification — 10 November 2026

## Confirmed failure
Saved Simpson run run_4ab9593a0f88401a955a746422546469 contains a valid inclusive direct-HMR range query. Its job failed with DATA_QUERY_LIMIT and the message that the source exceeded 5,000 rows. Physical planning rejected the field's integer/number metadata as unsupported for database pushdown, falling back to application reads of the full 5,810-row source. Display limit one did not change the source scan.

## Correction and bounds
Mongo numeric type families, including integer/double mixtures, now select the existing database executor. The compiler checks actual BSON types, rejects numeric strings/booleans/objects, retains the existing magnitude-at-most-1e16 and maximum-eight-fractional-digits envelope, and rejects doubles whose conversion to decimal and back changes the binary operand. Exact averages retain the production sum/count finalizer. Unsupported mixed text types and PostgreSQL floats remain on the prior strict path.

No global cap was raised: database sources remain bounded at one million rows, application fallback at 5,000, result rows at the existing API limit, transfer/result bytes and average-group/intermediate limits unchanged. Filters and aggregates cover the full matching population; display pagination is never a denominator. Invalid/oversized sources fail without partial results. No schema, shared contract, Registry/consent or frontend artifact changed.

## Tests
Final scoped suite: 87 passed, 21 PostgreSQL-dependent cases skipped without a configured DSN. The 18 mixed-numeric cases also passed separately against an isolated real Mongo replica. More than 6,000 integer/double records with null/missing values and inclusive 0/100 boundaries match the application engine and independent Decimal statistics. Precision-loss, excessive fractional precision, NaN/infinity, strings, booleans and objects fail closed. Existing compiler, query, restart, recurrence and clarification checks pass.

The initial large-average test directly invoked Mongo's average rather than the production sum/count finalization path. The test was corrected to use execute_average and 38-digit Decimal expectations; application average logic was not weakened or changed. The complete scoped suite then passed.

## Authorized live read-only qualification
Using the exact saved HMR plan and verified copied Simpson application state, with planner calls and Mongo mutation APIs blocked, the existing query engine performed a live read-only aggregate. It scanned 5810 source records and returned 1588 matching records, minimum 0.100000000000000, maximum 100, average 33.746410579345088161209068010075566751. limited=false; strategy=mongodb. A separate read counted 41 null or absent HMR values. Each query uses its own snapshot; no shared snapshot across the two queries is claimed. Application persistence was verified to use the isolated copy. No paid model call, live workflow submission, source mutation or real email/Sheets write occurred. Evidence is private in live-readonly.json.

## Rollout qualification
Fresh online main/Simpson/Subway snapshots passed quick_check. Fifty-three credential/configuration files, nine provider-state files, source and active frontend were verified. Only owned disposable rehearsal copies from the previous task were removed to retain disk headroom; verified backups, logs and all live stores were preserved. Six offline baseline/candidate startup/auth/API rehearsals passed with networking/workers disabled and protected records unchanged. Contracts, strict OpenSpec and whitespace checks passed.

Authenticated public checks, six read-only desktop/mobile browser journeys and history/credential/configuration preservation passed after deployment. All five services remain active with zero automatic restarts and no critical backend/worker log entries during monitoring. No database was restored or destructively migrated. Old failed runs/jobs remain unchanged; create a new workflow for retry. Historical shared-store audit, intermittent SQLite contention and other unsupported-query limits remain separate.
