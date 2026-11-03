# Provider-managed investigation token usage

The saved A-2025-9-070 replacement/comparison run failed at report synthesis with MODEL_OUTPUT_TRUNCATED. Reconstructing its actual CrewAI request with a local provider reproduced a 2,264-token completion cap: the existing 14,000-token combined application ceiling subtracted evidence/schema/prior-analysis input. Strict schema did not prevent provider truncation.

The user explicitly requests no application input/output token ceiling. Opt investigation model generation into provider-managed tokens/cost, omit max_output_tokens for planning and analysis, retain call-count/time/authorization/schema controls and record actual usage. General runtime agents keep existing budgets. If optional final narrative still truncates at the provider, compile the retrieved evidence and registered gaps with an explicit qualification instead of losing the report. No automatic paid replay or fabricated conclusion.
