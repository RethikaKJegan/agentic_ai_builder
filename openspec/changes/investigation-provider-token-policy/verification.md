# Provider-managed investigation tokens — 3 November 2026

## Root cause and request

Saved run `investigation_run_fff8ee9943c3dabd580565f2` completed complaint, inspection, replacement retrieval and comparison, then failed at final summary with `MODEL_OUTPUT_TRUNCATED`. Reconstructing the exact saved evidence/prior-analysis packet through actual CrewAI with a local provider reproduced a **2,264-token** completion allowance from the application's 14,000-token combined budget. Strict response schemas validate shape but cannot guarantee a response finishes within that allowance. The original provider incomplete reason was not retained, so its exact internal reason is not independently recoverable; the reproduced application bottleneck is verified.

The user explicitly requested no hard input/output token limit. Investigations now opt into a server-owned provider-managed policy instead of replacing the old ceiling with a larger arbitrary number. Model/service context limits still exist. Official guidance: [Responses token behavior](https://developers.openai.com/api/docs/guides/reasoning) and [Responses create](https://developers.openai.com/api/reference/python/resources/responses/methods/create).

## Implementation

- `runtime/model.py`: explicit factory/bridge `token_policy`, default `bounded`. Provider-managed mode omits `max_output_tokens`, imposes no application token/cost ceiling, and records actual provider usage, including available usage on incomplete/invalid responses. Call-count, elapsed-time, injection, secret and schema checks remain. Content-filter incompleteness is distinguished from truncation.
- `workflow_api/investigation_agents.py`: all investigation model analyses opt into provider mode with strict citation-constrained schemas. Final-summary truncation compiles an evidence-only result with no invented findings and no additional model call. Prerequisite analysis errors, invalid citations/schema and content filtering still fail visibly.
- `workflow_api/investigation_planning.py`: removes the separate 10,000-token planning output cap; graph schema and deterministic validation remain.
- `workflow_api/business_investigations.py`: exposes effective model usage policy, preserves failure usage accounting, and reports evidence-only narrative recovery in both structured metadata and the existing visible qualification. Full retrieved sources, prior validated interpretations, task requirements and gaps remain available.

Shared contract shapes, catalogue fingerprint and immutable saved plans remain unchanged. Legacy finite values in generic agent templates are not enlarged: the explicit server-owned investigation usage policy supersedes token/cost enforcement for this path only. Generic automation retains its existing default budgets. Call/time and source/record/byte limits remain; these are not input/output token ceilings. Existing saved workflows can start new runs without regeneration.

## Verification

- Affected provider policy, report schema, model protocol, generic runtime, investigations and jobs: **130 passed, 28 subtests passed**, 26 warnings, 107.01 seconds (`/tmp/investigation-provider-tokens-tests.log`).
- Final provider-focused checks after content-filter distinction: **7 passed**, 2 warnings, 1.91 seconds (`/tmp/investigation-provider-tokens-final.log`). Counts overlap.
- Tests cover provider mode with 50,000 input / 80,000 output tokens despite a one-token/zero-dollar template, no output-cap parameter, accurate costs, denied second calls, default budget preservation, incomplete response accounting, strict schemas and final-report recovery. These are local fixtures, not billed provider usage.
- Shared contracts/fixtures, generated UI contract drift, strict scoped OpenSpec and diff checks passed.
- Actual failed run's saved evidence replay through the real CrewAI/OpenAI adapter with a local provider passed both complete and truncated scenarios: one call each, no output-cap parameter, nine packet records retained, strict schema, response storage disabled, and source-backed recovery without approval/identity fabrication. Receipt: `.local/investigation-provider-token-rollout/saved-evidence-check.json`.

No new paid model evaluation or external evidence transfer was performed. Original failed run is preserved; the user can explicitly start a new run in the website. Remaining provider context limits, refusal/filtering, connection failures and timeouts cannot be eliminated by removing application token ceilings.

## Deployment

Backend-only rollout recovery artifacts are under `.local/investigation-provider-token-rollout/`. Background queues are checked before restarting compatible backend/worker; frontend and knowledge versions are unchanged. Final rollout receipts and preservation checks are recorded there.

Automatic approval review initially rejected deployment without explicit approval of uncapped paid usage/interruption. The command did not execute. The user then explicitly approved: “Yes, deploy without application token/cost ceilings.” Backend/worker restarted after idle checks. Authenticated public HTTPS capabilities now report null application input/output token and monetary ceilings, provider token policy and retained call/time controls. Anonymous session returned 401; normal session and worker health passed. The original failed run and workflow remain accessible with the failed state preserved; existing workflows can start fresh runs without regeneration. Receipt: `public-check.json` in the rollout directory.

Original knowledge version, plan and run documents compared byte-identical after deployment. Frontend build `A8GKRkwv5mpFqeJJ5XTSx` is unchanged. A consistent SQLite backup and prior source archive are retained. No live model replay was started automatically, and no company records changed.
