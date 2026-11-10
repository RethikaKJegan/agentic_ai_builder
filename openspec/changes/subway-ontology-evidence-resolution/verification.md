# Verification — 10 November 2026

See `docs/subway-evidence-resolution.md` for scope, checked sources, actual recovery,
conditions and remaining parent-only facts. Private evidence is under
`.local/tenants/subway/reaudit-20261110/`.

- Baseline audit: 225 passed, no failures. All 52 actual reader bindings, collection
  counts, 13 rule cases, 65 definitions and 11 additional paraphrases passed.
- Correction: 12 focused resolution/dump tests and 36 affected ontology/auth/client
  isolation regressions passed (overlapping). Exact original quotes/hashes,
  conditional requirements, usable child facts, unchanged definitions, historical
  versions, wrong owner/client/content and tampered artifact are checked.
- After correction all 13 rule questions and 65 definitions still retrieved with
  original plus separately hashed resolution citations.
- Contracts and strict OpenSpec passed; whitespace check passed.
- No workflow implementation, source record, credentials, immutable ontology/package
  or source permissions changed. Source-code fingerprint records preserve all
  runtime/workflow modules other than the intentionally changed ontology retrieval.
- Subway alone reloaded after checking no active runs/investigations/query jobs and
  confirming all other backend source files predate the previously running process.
  No unrelated newer workflow code was activated.
- Both live client sessions/ontology APIs pass; cross-client source requests denied;
  preservation hashes pass and Simpsons PID unchanged. Current live-store read-only
  ontology retrieval includes all three corrected evidence routes.
- No workflow or external model operation was executed for the correction. The
  earlier private controlled test belonged to the audit before the user's scope
  clarification and never touched production workflows.
