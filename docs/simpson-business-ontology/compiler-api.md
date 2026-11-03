# OWL/RDF and SHACL compilation — chunk 4

Implemented locally in the separate Business Ontology subsystem. This compiles an existing immutable draft without a model request, company query or company-data write. It does not initialize or publish the live workspace.

## Use in the UI

In Data Intelligence → Business Ontology, choose a saved definition version. For a generated draft, a workspace manager can select **Compile & validate version**. The panel displays the persisted result for that exact version, unresolved information, mapping limits and downloadable files. Viewers can inspect and download existing results but cannot start compilation. Foundation-only versions require a generated module first.

A passed result means the structured draft, generated RDF syntax, SHACL shape definitions and compiled ontology definitions passed their technical checks. Company instances have not been validated, OWL reasoning has not run, and business-policy correctness is not established. Candidate rules stay non-executable. No SME ontology approval gate is introduced; operational business approvals remain concepts in the model.

Compilation does not alter the selected draft or the current workspace revision. Historical versions compile independently of current source connectivity. Repeating a request returns the same saved artifact for that version/compiler. A newer compiler uses a different compiler version rather than overwriting earlier artifacts.

## Mapping

| Draft input | Compiled representation |
| --- | --- |
| Concept | `owl:Class` with definition, label and draft provenance annotations |
| Declared parent | `rdfs:subClassOf` |
| Relationship | Separate `owl:ObjectProperty` per relationship ID, with domain and range; predicate text is preserved as an annotation |
| String/integer/decimal/boolean/date/datetime attribute | Concept-scoped `owl:DatatypeProperty` with explicit XSD range and matching SHACL datatype |
| Required attribute | `sh:minCount 1`; no undeclared maximum cardinality |
| Reference attribute | `owl:ObjectProperty` and `sh:nodeKind sh:IRI`; unknown target class is reported |
| Enumeration attribute | String datatype and an unresolved-values warning; no invented allowed-values list |
| Relationship target | IRI and declared target-class constraint; relationship presence is not required unless declared in a future schema |
| Candidate rule | Annotated non-executable rule resource with inputs, conditions, outcome and evidence basis |
| Evidence | Source identity/hash/kind/origin and exact quotation, linked to the definition |
| Unknowns/questions | Preserved annotations and report warnings |

All entity IRIs use the existing owned namespace plus escaped internal IDs. Labels, definitions, predicate text and source text are literal values. They never become external IRIs or executable SPARQL. Attributes inherit concept-level source evidence; the current draft schema does not provide attribute-level quotations. No policy limits, joins, inverses, class equivalence or engineering causality are inferred.

The implementation uses [RDFLib's graph construction API](https://rdflib.readthedocs.io/en/stable/intro_to_creating_rdf/) and [pySHACL](https://github.com/RDFLib/pySHACL), following the [W3C SHACL specification](https://www.w3.org/TR/shacl/). Validation runs offline with remote imports, JavaScript, advanced features, custom SPARQL, SHACL rules and inference disabled. Source RDF is not accepted through this API.

## Export files

- `ontology.ttl`: deterministic Turtle in N-Triples-compatible syntax.
- `ontology.rdf`: equivalent deterministic RDF/XML.
- `instance-shapes.ttl`: constraints for later mapped company instances.
- `definition-shapes.ttl`: constraints used to validate compiled ontology definitions and evidence annotations.
- `validation-report.ttl`: actual definition SHACL validation report.
- `validation-report.json`: check results, counts, issues, warnings and explicit validation limits.

The response includes each file's SHA-256, canonical input hash, compiler version, draft version ID and compilation timestamp. The empty graph used while meta-validating instance shapes is not reported as successful company-instance validation. Invalid source structure, broken references, cycles or unmatched evidence prevent compilation. Definition SHACL failures are reported as failures, with issues; exporting those reports does not publish a conforming ontology.

## API and persistence

| Method and path | Behavior |
| --- | --- |
| GET `/business-ontology/v1/versions/{version_id}/compilation` | Return `{compilation: null}` or the actual scoped artifact for the current compiler; never compiles on read. |
| POST `/business-ontology/v1/versions/{version_id}/compilation` | Compile the owned immutable draft; accepts exactly `{}` and requires manager/write permissions. |

Existing session/origin transport, safe errors, no-store envelopes and workspace/owner checks apply. Foreign versions return 404; insufficient permissions return 403; a foundation returns 409; malformed requests or invalid drafts return 422. Missing compiler dependencies return a safe 503. Additive `business_ontology_compilations` storage is keyed by workspace, owner, version and compiler version. The input hash is rechecked before committing; an idempotent audit event accompanies the first saved result. Existing ontology tables and shared execution contracts remain unchanged.

Install the updated root `requirements.txt` in the backend environment before a later deployment: this chunk pins RDFLib 7.6.0 and pySHACL 0.40.2. They were installed and checked in the local integration virtual environment only. No service restart or deployment was performed.

## Offline real-draft verification

`scripts/check_business_compilation.py` opens a supplied SQLite application store in read-only mode, selects an explicitly scoped saved draft and writes a fresh private artifact directory. It does not load `.env`, credentials or company records, instantiate application services, send model requests or write the input store.

The previously approved chunk-3 OpenAI warranty draft passed this offline check: 14 concepts, seven relationships, two non-executable candidate rules, 525 ontology triples and 182 instance-shape triples. Its 31 warnings retain unresolved policy/source information and mapping limitations; they are not silently resolved. Evidence is at `.local/business-ontology/chunk4-offline-check/manifest.json` and `validation-report.json`.

Next chunk: source-backed rule catalogue and competency queries. Company-instance mapping, populated knowledge graph and intelligence remain subsequent work.
