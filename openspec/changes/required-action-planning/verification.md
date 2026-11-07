# Required action planning — 7 November 2026

The reported `ACTION_BINDING_INVALID` message means a completion criterion named an optional action. The validator rejects that contradiction before execution. The historical diagnostic did not retain optional/when fields; the precise original condition cannot be reconstructed, and no live paid-model replay was made.

Generated proposals with `optional=true, when=null` are now normalized to unconditional required execution. This is unambiguous because optional status must equal condition presence. Explicit caller proposals and genuine non-null conditions remain strictly validated. Conditional completion rejection now supplies structured action IDs and precise guidance to the existing one-correction planner boundary. Planner instructions explicitly require requested work to remain unconditional and missing business identities to be requested through missing_inputs. No completion criterion, recipient, business record, approval, real condition or execution budget is invented or removed.

Controlled verification (all commands use `PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider`):

| Modules / selector | Result |
| --- | --- |
| `tests/test_connected_action_plans.py tests/test_planner.py tests/test_planner_provider_errors.py --basetemp /tmp/required-actions-qualified` | 72 passed, 0 failed/skipped; 4 passing subtests; 106.56s |
| `tests/test_goal_planning.py tests/test_connected_action_plans.py -k 'completion_flag or optional_completion or precise_correction or hide_missing or unstated_recipient or email_me_resolves' --basetemp /tmp/required-actions-final-focused` | 6 passed, 0 failed/skipped, 95 deselected; 13.67s |
| `tests/test_connected_action_plans.py -k repeated_conditional_completion --basetemp /tmp/required-actions-bounded` | 1 passed, 0 failed/skipped, 44 deselected; 3.85s |

Counts overlap and are not summed. Logs are corresponding `/tmp/required-actions-*.log`. Five new regressions cover normalized persisted completion/approval, unchanged explicit rejection, real-condition correction, missing recipient, and repeated invalid proposals stopping after one correction. Initial focused run had one fixture failure because automatic mode requires a selected Google account; the correction fixture was narrowed to read/analysis actions, retaining the real condition and correction assertions. Final checks above pass. No permission check or success assertion was weakened.

Startup qualification used a read-only backup of the tenant database, blocked network and outside-clone SQLite access, started no workers, and found no schema changes. First invocation lacked PYTHONPATH; rerun with `PYTHONPATH=.` passed. Contract validation, generated UI contract drift, regenerated SQL source inventory (1,194 calls, 123 tables), whitespace and strict scoped OpenSpec validation pass. Inventory regeneration updates source locations and is not database qualification.

Only the idle Simpsons backend service was restarted under the existing deployment authorization. Authenticated session returned 200 and SQLite schema definitions were unchanged; see `evidence/activation.json`. No configuration or frontend build was changed, no workflow replayed and no message/event/spreadsheet created. Existing workflows and provider receipts were not rewritten. New planning requests receive the fix.

A vague complaint comparison can still legitimately require complaint ID/serial and recipient clarification. Supported evidence readers do not become unrestricted multi-record queries through this fix. Genuine conditional contradictions still fail safely if the model cannot correct them. This is scoped planning qualification, not a promise of error-free arbitrary model proposals or full production readiness. Prior release/staging/live-delivery/monitoring/backup/scaling blockers remain separate.
