# Retrieval limit correction

Production job `plan_76383160b9374d4c86c54b22e08fd176` failed before generation with `KG_RETRIEVAL_LIMIT`. For the supplied prompt, the twelve ranked saved schemas totaled about 105 KB; the joint-inspection schema alone was about 50.6 KB. The previous algorithm rejected this aggregate rather than selecting a useful fitting pool.

The automatic planning branch now packs complete descriptors in rank order into the existing 70,000-byte source budget. It skips descriptors that do not fit, continues considering later candidates, filters technical/semantic relationships and selected flags to supplied sources, and records a visible omission warning. Fields, source identities, hashes and tool authority are not rewritten. Explicit selections retain their oversized-selection error; an entirely oversized automatic pool still reports a specific bounded failure. Four execution sources remain the limit. No frontend build is needed.

## Evidence
- Targeted retrieval, business-planning and provider-error suites: 41 tests and four subtests passed.
- Saved production metadata reproduction: the exact suggested prompt passes with 11 complete candidate descriptors, 54,479 bytes and ontology revision 4. A local fixture provider receives both the actual scoped database catalog and Business Ontology evidence and returns a valid incorporated draft. Cached index sync was bypassed to guarantee read-only reproduction. This is not a new OpenAI generation or a saved live workflow.
- Regression tests cover deterministic packing, preservation of complete fields, skipped oversized candidates, filtered source/relationship scope and retained explicit-selection errors.
- Shared contract validation, Python compilation, strict scoped OpenSpec and diff integrity passed.

Private evidence: `.local/business-ontology/retrieval-limit-20261101/`. Previous backend source bytes are preserved under `rollback/`; the previous full application/config backup remains under the preceding workflow-planning rollout. No schema migration or business-data mutation is required by this fix. The original failed job is retained as history; the client's existing terminal-failure retry behavior issues a new planning key.

Additional database-workflow regressions and live activation are recorded below when complete. The preceding approved model test did not exercise this production metadata path; no full live automatic generation success is claimed for this correction without an actual new model result.

## Activation
34 additional database-workflow/automatic-source/deleted-planning regressions passed (75 scoped tests overall, plus four subtests). Backend and worker restarted with no active jobs. All three Builder services are active; frontend build `8XcKU7N-zHUG4DMKasjp4` is unchanged. Live backend session/ontology/library and HTTPS login checks passed. Four ontology versions and four warranty interpretations remain available, and the reported failed job remains preserved. No additional provider call, company write or workflow execution was made.
