## ADDED Requirements
### Requirement: Automatic business grounding
Workflow planning SHALL consult the requesting owner's saved Business Ontology automatically and supply relevant definitions and source-cited policy interpretations to the planning provider, without changing execution authority.

#### Scenario: Relevant warranty objective
- **WHEN** an authorized owner requests a warranty workflow and has relevant saved knowledge
- **THEN** the provider receives a bounded pinned retrieval and the resulting proposal records validated links from actual action steps to retrieved references

#### Scenario: No relevant knowledge
- **WHEN** no saved definition matches the objective
- **THEN** ordinary planning continues and the review explicitly reports no relevant Business Ontology match without claiming incorporation

### Requirement: Inspectable contribution evidence
The review SHALL show the pinned version, source citations, policy basis and workflow steps that use each reference; client or provider assertions SHALL NOT override server-owned evidence.

#### Scenario: Invented reference
- **WHEN** a provider cites a reference outside its retrieved context or an absent workflow step
- **THEN** no workflow with that unsupported contribution claim is returned

#### Scenario: Stable retry
- **WHEN** an identical planning request is retried after ontology changes
- **THEN** the original idempotent proposal retains its original pinned evidence
