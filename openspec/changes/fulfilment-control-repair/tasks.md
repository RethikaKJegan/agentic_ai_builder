- [x] Align control transport with runtime shape and task limits.
- [x] Recover only one side-effect-free failed fulfilment extraction.
- [x] Verify focused protocol/recovery tests and scoped validation.

Six offline protocol/recovery tests, contracts and strict OpenSpec pass. The
actual failure is recorded as MODEL_OUTPUT_SCHEMA_INVALID on the first master
turn before any external tools or business events; raw invalid output was not
persisted, so its exact rejected field is unknown. A synthetic live-model check
through the actual bounded CrewAI adapter passes with fictional acceptance data.
No private email content was sent to the model during diagnostics, no historical
runs rewritten and no servers started. The active project's Activity target is
149kG_XIXcpMZNkm-RktjLVoTHm_0n4QOeNRaWxGsGNM, distinct from the older workbook
in the user's screenshot. Loading the runtime fix enables one pure extraction
recovery; any second failure remains stopped for review.
