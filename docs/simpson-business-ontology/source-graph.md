# Bounded engine source graph — chunk 6

The separate Business Ontology tab supports explicit concept/field mappings and saved source-record graphs using both bound Simpson databases. This is implemented and verified locally, without deployment or company-data writes. It is a bounded investigation path, not a complete population graph or an eligibility engine.

## Build and inspect

Choose a saved draft and compile it first. In **Engine source graph**, a manager chooses a record concept and attribute-to-source-field mappings under **Configure source mappings**, then enters one exact serial and selects **Build & save source graph**. Bindings are never inferred from concept labels. The selected generated concept must belong to a permitted module for that collection; attributes and source fields must exist in that version/current metadata.

The mapping catalogue contains the 21 reviewed collections from both databases. Only allowlisted, currently observed/declared scalar fields with one supported non-null type are available. Unsupported arrays, documents, attachments, credential fields and nested objects are excluded. Supported nested scalar paths are flattened with missing/null states preserved. Reference-valued ontology attributes require a resolved target mapping; they produce conversion issues rather than invented IRIs.

Managers explicitly trigger company-source reads and a local immutable graph save. Opening the panel, changing versions, loading the metadata plan or selecting a saved snapshot does not query company databases. Viewers inspect saved graphs and exports without build controls.

The interactive graph uses solid edges for direct source references and dashed edges for candidates. Select nodes or use the source-record list to inspect projected fields, value states and source hashes. Coverage cards, collection outcomes, truncation, unresolved references, conversion/SHACL issues, read times and source metadata revisions remain visible. RDF and instance-validation reports are downloadable. Phone layouts stack the source groups and support zoom/pan.

## Exact bounded path

| Step | Retrieval and qualification |
| --- | --- |
| Serial anchors | Exact scalar search in db1 engine invoices and tickets, and db2 manual claims, SAP claims and failed-engine analyses. |
| Service references | Matching ticket keys drive joint inspection, engine/part replacement, dispatch and FOC reads. Ticket OEM/account/organization references are retrieved by native keys. |
| Engineering/CAPA candidates | Observed list numbers drive bounded cut-in/CAPA retrieval. An invoice edge additionally requires exact typed equality on OEM, engine model and list number. It remains a candidate; plant, approval, serial boundary and incorporation applicability are not established. |
| Other reviewed collections | Shown as `not_in_serial_path` rather than scanned or fabricated into the engine history. |

Each queried collection returns at most 20 retained records plus one truncation probe. The overall build has a 25-second deadline, Mongo operations have time limits, connections are reused per source, and the saved response is capped at 2 MB. No automatic source retry or unlimited scan runs. Source absence, missing scalar metadata, unusable search inputs, no matches, out-of-path collections and truncation are distinct outcomes. Source execution errors fail the build without saving partial results.

The current exact-serial protocol accepts a nonempty trimmed identifier of at most 80 characters using letters/digits, spaces, slash, underscore, dot and hyphen. Unsupported stored formats are not normalized or treated as evidence of a different engine; they require a deliberate identifier-format extension. The diagnostic's rejected-anchor count describes this protocol, not business validity.

## Identity and meaning

Every node uses the source connection, collection and native BSON-typed `_id`. Equal serials and equal-looking keys in different collections/databases remain separate. A string ID and ObjectId with identical text cannot become a direct reference through coercion. The graph is a record-level projection; physical-engine identity remains unresolved.

Direct edges require a unique observed same-source target and exact native type/value equality. Unresolved references are retained as such. A bounded targeted search cannot recover every orphan replacement record, and an unlinked replacement is never assigned to an engine by guesswork. The two replacement gaps accepted during discovery remain a data-quality qualification, not a build blocker or a repair action.

Serial edges use a bounded invoice-anchored star (or one observed serial record when no invoice is found). They are candidate associations, including cross-database matches, with no `sameAs` or physical-engine merge. Claims and QA records gain no invented direct ticket link. Scope matches are not proof of a change being incorporated, a confirmed failure mechanism or recurrence.

## Mapped RDF and validation

Explicit bindings project source records into the selected draft classes and concept-scoped attribute IRIs. Supported datatype conversions are explicit; failed conversions are reported, and missing mapped required values can fail the saved SHACL shapes. Unbound source records remain source records and are not counted as successfully validated business instances.

The result reports mapped-record count, SHACL conformance/violations, conversion issues, and false business-policy/mapping-meaning verification flags. With zero matching bound records, validation is `not_run`, even if the shape engine sees no violations. A technically conforming projection does not prove that a chosen mapping means the correct business thing or that a claim is eligible. Inference, remote imports, rule execution and model transfers are disabled.

The stage path covers observed engine, complaint, inspection, replacement, claim, quality, engineering-change and CAPA record presence. Monitoring remains unavailable until change applicability/incorporation, comparable confirmed failures and exposure/population denominators exist. Warranty evaluation remains `not_run`. No failure rate, policy threshold, exclusion decision or change-effectiveness conclusion is invented.

## API and persistence

| Method and path | Behavior |
| --- | --- |
| GET `/business-ontology/v1/versions/{version_id}/graph-plan` | Metadata-only mappings, current plan hash, readiness and saved snapshot summaries. |
| POST `/business-ontology/v1/versions/{version_id}/graphs` | Explicit manager build with exactly `plan_hash`, `serial`, `bindings`, `request_key`. |
| GET `/business-ontology/v1/versions/{version_id}/graphs/{graph_id}` | Read an owned immutable version-bound snapshot, with no company query. |

Example binding:

```json
{"enginedetails":{"concept_id":"warranty:engine_instance","attributes":{"serial_number":"engineSerialNumber"}}}
```

Existing session/origin transport, no-store envelopes and workspace/owner permissions apply. Builds require existing write/manager authority, both owned connected MongoDB sources, usable current metadata and a passing integrity-checked compilation. Viewer reads require existing read authority. Source credentials are decrypted only in memory. The canonical mapping plan includes source metadata/generation/configuration fingerprints, and stale plans fail before reads. Current authority, source state and definition version are rechecked after retrieval and before commit.

`business_ontology_graphs` is additive scoped storage. Same-key identical completed requests return the saved snapshot, while reused keys with different input fail. One build per scope and at most two local concurrent builds are admitted. Saved graph inspection is historical and does not imply that current company rows are unchanged. Source projection never writes to company databases. Existing Ontology, Semantic Intelligence, source configurations and shared execution contracts remain independent.

## Real-source evidence

`scripts/check_business_graph.py` reads live application connection/metadata rows with SQLite `mode=ro`, decrypts credentials in memory and clones only safe metadata plus the earlier real-model draft into a fresh private isolated store. It explicitly maps the known Engine Instance serial attribute for the diagnostic. No connector secret is copied to that store or an output file, and no live Business Ontology workspace is initialized.

- Invoice anchor: one db1 invoice, no ticket/claim/QA match; one mapped record passed structural instance validation.
- Ticket anchor: two tickets and two OEM records, four direct references and one candidate serial edge; no bound invoice matched, so mapped-instance validation correctly stayed `not_run`.
- QA anchor: one db1 invoice and one db2 failed-engine analysis, one candidate serial edge; one mapped invoice record passed structural instance validation. Of eight bounded QA serial candidates, four did not meet the current diagnostic anchor format and were not normalized.

All checks used both bound sources, found no matching claim records for those serials, left monitoring unavailable and preserved connector configuration. Company writes, model calls, live application writes and copied connector secrets were zero. Private reports are under `.local/business-ontology/chunk6-connector-check/`, `chunk6-ticket-check/` and `chunk6-quality-valid-anchor/`. Initial QA diagnostic failures were retained; the diagnostic's source-role choice was corrected and bounded usable-anchor selection added. Those failures do not count as successful QA verification.

Next chunk: complete remaining modules and evidence-backed intelligence on top of these qualified mappings. Full business-instance competency answers, broader identifier formats, complete identity/applicability resolution and monitoring rates remain dependent on suitable data and policy.

## Chunk 10 graph update

New builds use `simpson-source-graph-v2`, retain native identifier tokens and source-field annotations, and resolve company records from ticket company, invoice company and account-company references with one bounded deduplicated query. Clipped search domains are marked truncated. Existing v1 snapshots stay immutable/readable. See [typed association evidence and OEM correction](engine-associations.md). No physical-engine merge is inferred.
