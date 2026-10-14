- [x] Match genuine compliance text across whitespace without allowing paraphrases.
- [x] Revalidate existing compliance-only failures from authenticated complete source records.
- [x] Verify focused regressions, actual stored quotations read-only, contracts and scoped spec.

Six focused tests passed, including wrapped compliance and absent/unsupported/negative statements. Read-only validation of all four actual stored quotation outputs now returns no extraction issues. Contracts, strict scoped OpenSpec and diff checks passed. No live records were modified, emails sent or services started; normal worker recovery after reload retains source hashes, commercial-field equality, latest-quote selection and store qualification guards.
