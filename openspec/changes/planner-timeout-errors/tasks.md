- [x] Add bounded planning-specific timeout configuration without changing runtime timeouts or retries.
- [x] Map SDK timeout/connection/rate/status failures to safe planner errors.
- [x] Normalize generated input combinations and implicit save-field schemas without changing saved workflow semantics.
- [x] Test error envelopes, privacy and timeout propagation.
- [x] Verify the restaurant workflow with the configured live model and record limitations.

## Verification — 2026-10-12

The initial isolated live request reproduced APITimeoutError escaping PlannerService and becoming INVALID_API_DATA. A longer-deadline attempt completed but failed graph validation. Two subsequent captured, secret-checked model responses established the configuration defects: mixed input/input_mapping and omitted closed save-field schemas; the correction response also introduced unsupported dictionary expressions. The first actual model response, replayed through the corrected full generation/save pipeline in temporary storage, returned HTTP-equivalent 200 for both operations. This proves the fix against a real captured response, not a fresh successful post-fix model request or a published/operational workflow.

Artifacts (private/local): `.local/phase1-planner-attempt-1.json`, `.local/phase1-planner-attempt-2.json`, `.local/phase1-normalized-model-draft.json`. No provider credentials are included.

Full Python regression: 226 tests passed. New tests cover SDK errors, deadline propagation, ambiguity rejection, preservation of explicitly open schemas and a published offline domain workflow whose model proposal uses the exact mixed-input/omitted-schema pattern. Existing bounded-correction tests now assert structured error codes/requirements. Shared contracts, generated-client drift and strict OpenSpec passed; diff check passed. Expected prompt-injection/Slack rejection diagnostics remain in negative tests.

No live sheet update, email, publication or credential change occurred. A graceful reload was requested only after confirming no active runs or pending jobs, but execution was rejected by the user; the running backend was not changed. Operator restart is required to load the fix. The live model can still time out or return invalid content; those cases now have safe explicit retryable errors rather than invalid-data claims.
