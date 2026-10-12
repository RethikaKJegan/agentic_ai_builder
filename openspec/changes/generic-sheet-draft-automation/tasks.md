## Implementation
- [x] Register restricted record upserts and live planner capability context.
- [x] Implement identity resolution, bounded locking, sparse literal writes and error handling.
- [x] Validate generated/publication mappings and document prompt-driven setup.
- [x] Verify restaurant/manufacturing publication, polling, delegation and saved drafts with offline transports.
- [x] Verify authorization, duplicates, concurrent writes, sorted rows and restart behavior.
- [x] Run regression tests, contract/client drift and strict OpenSpec validation.

## Verification — 2026-10-12

- `PYTHONWARNINGS=ignore .venv-integrations/bin/python -m unittest discover -s tests -q`: 217 tests passed. Expected prompt-injection rejection diagnostics and the Slack acknowledgment rejection diagnostic appear in negative tests.
- Final planner metadata adjustment: published restaurant/manufacturing and default-action-approval focused checks passed (2 test methods, 3 domain/configuration runs).
- `scripts/validate_contracts.py`: passed, including the new tool fixture; existing versioned schemas unchanged.
- `scripts/generate_ui_contracts.py --check`: passed.
- `openspec validate generic-sheet-draft-automation --type change --strict --json`: valid, zero issues.
- `git diff --check`: passed.

The new file contains 18 test methods. End-to-end cases run actual structured planner parsing, Registry, publication, durable polling, bounded CrewAI and Google connector code with offline model/HTTP/OAuth transports. They cover initial baseline, matching evidence, missing/ambiguous evidence, draft/status saves, default approval pauses, restart deduplication and partial-write failure without replay. Connector cases cover sorted/offset rows, sparse preservation, literal formula-looking drafts, concurrent separate connector instances, bounded locks, policy/schema/identity rejection, capacity and provider failures.

No real model request, Google Sheet change, email, credential modification, workflow publication against the user's database, or backend restart occurred. Live rollout requires operator-approved target settings, Google write consent, restart and a reviewed generated workflow. External editors/separate hosts are outside local file-lock coordination; multiple target writes are not atomic. Existing launcher Gmail configuration remains required. See docs/sheet-drafts-phase1.md.
