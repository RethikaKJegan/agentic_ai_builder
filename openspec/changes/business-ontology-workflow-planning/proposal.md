# Automatic Business Ontology workflow planning

## Why
The separate Simpson Business Ontology is not consulted by the workflow planner. A user asking for a warranty or investigation workflow needs its definitions and cited business knowledge to shape the proposal, with inspectable evidence linked to the resulting steps.

## What Changes
- Automatically retrieve relevant owned definitions and latest policy interpretations before planning; retain the existing metadata/source selection and authorization boundaries.
- Pin the exact definition version, policy revisions, evidence quotations and hashes in the workflow proposal. Validate model-declared step references against the retrieved evidence and actual workflow nodes; never trust model-authored provenance.
- Show step-level ontology contributions and downloadable evidence in the existing plan review, including explicit not-matched/not-configured states.
- Test isolation, forgery, irrelevant objectives, version changes, idempotency, source integrity, and proposal persistence. No new SME gate, model provider, company-data writes or automatic workflow execution.

## Impact
Planner context, workflow metadata extensions, existing review UI, fixture-based integration tests and documentation. Canonical execution fields and tool authority stay unchanged. Production model behavior requires a separately identified real-model acceptance run; fixture evidence must not be represented as such.
