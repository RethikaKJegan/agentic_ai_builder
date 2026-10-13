- [x] Normalize discovered bounded ranges and decimal limits without inventing mappings.
- [x] Preserve precise validation codes in exhausted planner errors.
- [x] Run focused offline tests and scoped contract/spec checks.

Four offline planner tests pass, covering range/limit recovery, precise policy
errors, unknown-header rejection and out-of-capacity rejection. Shared contracts
and strict OpenSpec validation pass. The failed live draft was not persisted, so
its exact invalid field cannot be confirmed. Automatic approval review rejected
the live Sheets/model diagnostic due to private-data egress; no external
diagnostic, workflow execution or server restart occurred.

Follow-up: a live model reproduction using exclusively fictional fixture
headers/objective emitted `INR 100000` twice and reproduced
PROCUREMENT_PHASE2_SETUP_INVALID. Matching currency labels now normalize without
changing the amount; conflicting currencies remain rejected. The model schema
and instructions require a bare decimal. Six offline tests, contracts and strict
OpenSpec pass. A fresh synthetic live-model generation passed after the fix.
No private spreadsheet was accessed/shared, and no workflows were saved,
published or executed by these diagnostics.
