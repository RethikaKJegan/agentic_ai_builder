# Hosted scalar-binding correction — 10 November 2026

Deployed to https://praxi.bellcorpstudio.com/ as `scalar-binding-20261110-9a9ac6fa551f`.

Completed 2026-11-10T11:28:31.685738+05:30 (India). Base commit `36fc5cee6c7abf19107a1563064c72ffceedfad0` plus the frozen 19-file manifest `9a9ac6fa551f7b2f821f3d0b547d8619326c4349f46e681a54ed9a9d1e52591d`. Frontend build remains `C038xXGULZ07Dhwu_uq7R`; this rollout changed two backend files only.

## Failure and correction

Reported request/correlation: `64e3f8ea-94f8-4885-a9b6-7436c8327700`. The available journal does not include that correlation ID on its binding diagnostics. Simpson logs at 05:49:54 and 05:50:05 UTC show the matching error path: email_findings initially references context.recipient with path [recipient]; the bounded model correction changes it to literal/user_values.recipient but retains path [recipient]. The supplied recipient is already a scalar string, so traverse rejects treating it as an object. The corrected proposal was otherwise using data.plan_query -> workflow_data_query -> content.prepare -> email, and no external execution occurred.

workflow_api/goal_inputs.py now normalizes an exact redundant scalar self-path. A context key absent from validated_context may reference an existing explicit user value only when the path is empty or the exact self-path and that value is scalar. Existing context values take precedence. No recipients, accounts, case IDs or unknown values are invented. Dictionaries/arrays and other paths retain strict validation. Exact-payload email approval remains mandatory.

workflow_api/action_bindings.py now attaches namespace/key/path/target diagnostics to literal/context traversal failures, so the existing bounded correction receives the actual invalid path instead of a null binding issue. Shared contracts and runtime authorization were not changed.

## Evidence

- `.venv-integrations/bin/python -m pytest tests/test_scalar_input_bindings.py tests/test_workflow_query_integration.py tests/test_goal_planning.py::test_unstated_recipient_becomes_a_business_question_not_technical_setup tests/test_goal_planning.py::test_email_me_resolves_only_the_owned_selected_account tests/test_goal_planning.py::test_model_authority_binding_gets_one_correction_without_relaxing_validation tests/test_goal_planning.py::test_redundant_known_research_namespace_is_normalized_without_masking_real_child -xq`: **20 passed**. Tests cover both observed recipient bindings, one-call generation with the selected owned account, genuinely missing recipient clarification, preserved nested paths and authority rejection, plus existing query/report/durability tests. All providers/model transports are controlled; no real emails or Sheets writes. Initial new unit-fixture failures lacked normal goal/contract metadata; fixtures were completed without changing production validation.
- `scripts/validate_contracts.py`: schemas/fixtures valid. Strict OpenSpec and diff whitespace validation passed.
- Fresh verified online backups: all three stores passed quick_check; 53 configuration/credential files, current source/frontend and nine auxiliary provider files/journals preserved.
- Baseline and candidate startup/rollback compatibility: **six copied-store account rehearsals passed**, with network/workers disabled and existing protected rows unchanged.
- Rollout gate verified no in-flight runs/jobs or active schedules. Existing worker and three backend services restarted through existing units. No frontend restart/build change, nginx/login/unit change or database restore.
- Post-deployment authenticated public HTTPS: **all three accounts passed** for Business Investigation, Questions, session scope, registered query tool and worker health.
- Public desktop/mobile UI: **six journeys passed**, zero page errors, all API mutations blocked.
- Existing histories/jobs, encrypted Google/source credentials and configuration hashes preserved. All five services active, zero automatic restarts; no error-priority journal entries since activation.

No paid/live OpenAI generation was performed. These checks establish the reported binding regression with controlled model output and hosted application health; unrestricted live-language/source execution remains unqualified. Earlier business-field ambiguity, recurrence and historical audit limitations remain as documented in verification.md.

## Rollback

Verified private artifacts: `.local/scalar-binding-deploy-20261110/`.

```
.venv-integrations/bin/python .local/scalar-binding-deploy-20261110/rollback.py
```

Restores the two prior backend files and restarts affected backend/worker services. Databases, provider journals and the frontend artifact are not restored. No rollback was needed.
