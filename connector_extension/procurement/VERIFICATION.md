# Step 1 verification — 13 October 2026

- Record and policy JSON Schemas pass Draft 2020-12 schema checks.
- 14 fictional records across ten entity types pass, including incomplete extraction states.
- A closed-order representation with explicit confirmation flags and evidence passes.
- 18 invalid cases fail: missing actionable data, zero/float quantity, invalid contact/date, secret field, premature closure, unresolved closure exception, agent/missing approval identity, unverified qualifying quote, negative amount and unauthorized policy changes.
- 60 ordinary transition edges, initial/terminal states, partial/same-state updates and hold/cancellation references are checked.
- Cross-record fixture references and monetary/progress arithmetic pass.
- Original shared contract schemas and fixtures pass.
- Both official cached OpenSpec 1.14.1 strict validator library passes (proposal and delta specs/tasks) return valid, zero issues. The interactive CLI wrapper does not run on default Node 18, so its unchanged validation library was called directly. No Node upgrade or project dependency change.
- All 484 original tracked file hashes remain unchanged.

Run: `.venv-integrations/bin/python connector_extension/procurement/verify_contracts.py`.

Evidence: `.local/connector-extension/verification/procurement-step1-openspec.json` and `procurement-step1-preservation.json`.

This verifies definition artifacts and fixtures, not deployed procurement enforcement. No live provider call, credential update, source-sheet change, service restart or automatic policy activation occurred. Existing connector tests from prior work are not rerun or represented as new evidence for this definition-only step.
