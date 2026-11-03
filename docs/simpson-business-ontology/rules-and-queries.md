# Rule catalogue and competency queries — chunk 5

Current execution support: the three reference safeguards now have [implemented evidence-based handlers](rule-execution.md). The description below records the original definition-query scope; those queries remain read-only.

The separate Business Ontology tab now provides a read-only candidate-rule catalogue and six fixed competency queries on saved compiled definitions. No model requests, company queries, rule execution or SME approval gate are added by these reads. This is implemented locally; deployment and company-instance graph mapping remain separate.

## Candidate rules

Choose a saved definition version, then filter its catalogue by module, evidence basis or text. Each candidate retains its draft definition, conditions, outcome, direct input concepts/attributes, source kind/hash/origin/quotation, unknowns and module questions. Input availability is explicitly `not_checked`. Required flags describe declared attributes; they do not assert that a company record contains a valid value. Attribute-level evidence is inherited from the concept because the extraction schema has no separate attribute quotations.

The three evidence bases stay distinct:

| Basis | Meaning |
| --- | --- |
| Policy statement | A candidate cites a supplied policy document; completeness, authority, current applicability and business correctness remain unverified. |
| Descriptive implementation | A candidate describes supplied code behavior; existing code is not approved policy. |
| Proposed logic | An illustrative or proposed rule candidate; it is not a verified business rule. |

At chunk 5, every rule remained non-executable, including policy-source candidates. The later rule runner adds exact-definition handler availability separately from the immutable extraction field. Nothing in this chunk silently supplies warranty limits, exclusions, policy versions or complaint data. A foundation has an empty rule catalogue; historical versions expose only their own rules. These are projections of immutable definitions and do not create another editable policy store.

## Runnable definition questions

| Query ID | Returns |
| --- | --- |
| `rule_inputs` | Direct rule input concepts and their declared attributes, datatypes and required flags. Reference target datatypes remain unspecified. |
| `rule_evidence` | Rule basis and source title, kind, hash and exact quotation. |
| `policy_candidates` | Only policy-statement candidates, their outcomes and recorded unknowns. |
| `implementation_candidates` | Only code-description candidates, recorded conditions and outcomes. |
| `concept_relationships` | Declared relationship domain/predicate/range definitions; these are not associations between company records. |
| `unresolved_information` | Definition unknowns and, without focus, module questions. Zero rows does not prove policy completeness. |

Queries use the existing passed compilation for the selected immutable version. Opening the catalogue, changing a question or selecting another version never executes a query. After an explicit successful compilation the catalogue refreshes readiness; the user must still run the selected query explicitly. Historical version, question, focus and catalogue refresh changes discard stale results. The UI fetches 20 rows at a time and shows provenance and explicit empty versus prerequisite/failure states.

These queries use [RDFLib's local SPARQL query API and variable bindings](https://rdflib.readthedocs.io/en/stable/intro_to_sparql/). Only six code-owned SELECT templates are accepted. Caller-authored SPARQL, external IRIs, remote SERVICE requests, graph updates and model-generated queries are not accepted. The implementation does not run inference or use source connectors.

Before parsing local generated Turtle, it checks the compilation/version/compiler IDs, canonical immutable-input hash, passing report/checks and ontology artifact SHA-256. Missing, stale, failed or damaged compilation is a prerequisite failure, never an empty successful result. The current compiler is required; older compiler artifacts are not automatically replaced or recompiled. A successful query is not SHACL validation of instances or business-policy approval.

## Business questions awaiting company data

The 22 supplied blueprint questions are retained with blueprint hash and section provenance in `ontology/business-reference/competency-questions.json`. They cover warranty, service, QA, engineering and management. Each has explicit data/evidence prerequisites and remains `requires_instance_mapping` in this chunk. Source-document instructions about SME review were not adopted as product requirements.

For example, warranty on the failure date needs mapped engine/failure-date observations plus valid required inputs and temporally applicable coverage/exclusion policy. Confirmed recurrence needs comparable confirmed failures, incorporation evidence and exposure. Failure rates need a defensible population denominator. Concept names or the presence of candidate rules do not establish those capabilities.

Company-instance competency query templates and actual business answers follow the later graph-mapping and policy work. This chunk does not claim to retrieve all claims for an OEM, determine eligibility, compare actual inspection findings or calculate failure rates.

## API

Both endpoints use existing read permissions (`tools.read`, `workspace:read`), trusted workspace/owner scope, session/origin transport, no-store envelopes and safe errors. The POST is computationally read-only and permitted for viewers.

| Method and path | Behavior |
| --- | --- |
| GET `/business-ontology/v1/versions/{version_id}/rule-catalogue` | Rules, input/evidence details, evidence-basis counts, six query readiness entries, 22 business questions and source provenance. No compilation or execution. |
| POST `/business-ontology/v1/versions/{version_id}/competency-queries/run` | Execute one fixed query on the owned passed compilation; accepts exactly `query_id`, `focus_id`, `limit`, `offset`. |

Example payload:

```json
{"query_id":"rule_evidence","focus_id":null,"limit":20,"offset":0}
```

Focus must be an existing rule, concept or definition appropriate to that query in the selected version. Limit is an integer from 1 to 50; offset is an integer from 0 to 20,000. Results include ordered columns/cells, actual rows, offset/limit/next page, query version/hash, compiler version, input hash and ontology hash. Optional entity identifiers/labels link returned IRIs to saved definition/source identities. Null cells mean unspecified in the query graph; they do not mean a source database column is absent. Instance scope, company queries, rule execution and policy verification remain explicitly false/not performed.

Foreign versions return 404; invalid requests/focus return 422; missing or unsuitable compilation returns 409; evaluation failure returns safe 503. No additional database table, persisted query history or audit event is created by catalogue/query reads. Existing Ontology, Semantic Intelligence and shared execution contracts remain unchanged.

## Offline evidence

`scripts/check_business_rules.py` reads the earlier isolated chunk-3 store in SQLite read-only mode and the chunk-4 export files. It validates the compilation before running all six templates, then writes a fresh private evidence directory.

The real-model warranty draft contains two candidates: one code-description and one proposed logic, zero policy-statement candidates. The queries returned 11 input rows, two evidence rows, zero policy candidates, four implementation-condition rows, seven relationship rows and 29 unresolved-information rows. All result pages were complete at limit 50. The report at `.local/business-ontology/chunk5-offline-check/report.json` records zero model calls, company queries/writes and input-store writes. The absence of policy candidates is an observation about this draft, not proof that company policy documents do not exist.

Next chunk: knowledge graph mappings and the engine-to-monitoring path using both Simpson databases, retaining unresolved links and policy/data gaps.
