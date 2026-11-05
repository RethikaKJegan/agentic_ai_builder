# Verification

Observed saved workflow `composition_11ba61503ad3a859497c2fe2` was unsupported
solely for `tool.extension_mail_draft` / `SIDE_EFFECT_MISMATCH`. Complaint reads,
inspection reads, comparison and reporting were ready. Explicit recipient, subject,
body, authorized `extension_recipients` destination and selected Google connection
were already saved; the recipient also satisfied the operator restriction.

Cause: deployment enables automatic procurement actions. The shared unbound Gmail
connector then reports `external_write=False`; its existing standalone workflow
binding restores `external_write=True` and requires exact action approval. Business
planning checked the unbound flag and incorrectly rejected the standalone draft.

Changed `workflow_api/procurement.py` to share its existing standalone-write rule
with a side-effect classification method. `workflow_api/business_composition.py`
uses that trusted standalone classification while matching. Destination/schema/
credential/permission checks and runtime approval gates remain in place. Existing
procurement project binding retains lazy extension metadata access, including for
legacy Sheets row connectors without an extension definition.

Tests: `tests/test_business_draft_binding.py`; existing installation helper in
`tests/test_business_composition.py` gains an optional automatic-mode parameter.
Five targeted tests pass (6.50s): deployed false-default/true-bound behavior; missing
destination; missing body; exact action approval before any connector invocation;
legacy row connector compatibility.

The initial broad run caught a compatibility regression in the first patch:
eager extension-definition access on a legacy row connector. Four procurement
tracking tests failed with INVALID_EXECUTION_DATA. A separate process loaded the
original two production modules from HEAD in memory; all four tests passed
(104.37s). This established the failures were introduced, not pre-existing. The
patch restored lazy access and added a regression test. The final affected-suite
rerun passed: **65 passed**, 166 existing jsonschema/FastAPI deprecation warnings,
237.13s. Command:

```text
.venv-integrations/bin/python -m pytest tests/test_business_draft_binding.py tests/test_business_composition.py tests/test_google_tools.py tests/test_integrated_procurement.py tests/test_procurement_start_readiness.py tests/test_procurement_communication_selection.py -q
```

Contracts, Python syntax, strict OpenSpec and `git diff --check` pass. No shared
contract, database migration, frontend, credential or operator-policy changes.
Multi-action forms and web-search integration remain outside this fix.

Deployed through existing `agentic-builder-backend` and `agentic-builder-worker`
services; both verified active. Frontend/build unchanged. The online SQLite backup
and exact before/after fingerprints preserve **170,591 rows across 32 tables**.
Previous source copies and the database backup are retained privately.

Authenticated public verification passed using normal workspace login/session:
unauthenticated access denied, worker active, and a fresh offline plan using the
user's saved explicit inputs is **ready**, including its Gmail draft task. Model
calls: **0**; external actions: **0**. Verification composition:
`composition_fc05fa3245fca8902fbd8b82`. Original unsupported composition remains
unchanged. User should use Workflow details → Generate updated workflow to create
a new version; Refresh alone does not rewrite immutable saved planning results.
Normal workflow review and exact Gmail action approval are still required.

No live Gmail draft/send, source mutation or paid model calls were performed.
This verifies setup readiness; actual Gmail creation remains the user's approved
execution test. Private rollout material and receipts:
`.local/gmail-draft-binding-release-20261104/`.
