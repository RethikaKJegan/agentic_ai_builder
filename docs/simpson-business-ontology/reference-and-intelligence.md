# Reference modules and saved evidence intelligence

Chunk 7 adds curated blueprint drafts for all twelve modules and six fixed reports over an owned, immutable source graph. It remains separate from the original Ontology and Semantic Intelligence tabs. No SME validation workflow is introduced.

## Reference drafts

`ontology/business-reference/module-drafts.json` contains 67 concepts, 14 relationships and three non-executable proposed rules, tied to the exact sanitized source bundle hash. Every item passes the same structural, reference and exact-quotation checks as generated drafts. Diagram groupings are not treated as inheritance; parent concepts remain unspecified. The kit contains definitions, optional attributes and explicit information gaps, not approved warranty policy.

The UI shows selected-version module counts, reference origin, source-document counts and unresolved questions. A manager can explicitly **Add missing reference drafts** on the latest version with the original two connected Simpson bindings. This saves a new cumulative version, preserves existing module definitions and history, and makes no model calls. Existing modules are not replaced. Cross-module relationships requiring absent existing concept IDs are omitted with an explicit binding question; labels are not used to guess identity. Empty or sparse source collections do not prevent reference definitions, and draft coverage does not imply populated/validated business instances.

API additions, using existing authenticated envelopes and `Cache-Control: no-store`:

| Method | Path under `/business-ontology/v1` | Meaning |
| --- | --- | --- |
| GET | `/versions/{version_id}/module-coverage` | Owned historical module coverage; local metadata/documents only |
| POST | `/reference-modules` | Explicit manager import, `{expected_revision, request_key}` |
| GET | `/versions/{version_id}/graphs/{graph_id}/intelligence` | Six available fixed report questions |
| POST | `/versions/{version_id}/graphs/{graph_id}/intelligence/run` | `{question_id, limit, offset}`; limit 1–50, offset 0–20000 |

Imports check current authority, original source binding, connection state, revision and active generation jobs. Retries use the same request key and return the saved version; changed-key payload reuse and stale revisions fail without committing. Curated origin is recorded per item and version, with no fabricated model/token metadata.

## Fixed saved-graph reports

| Question ID | Scope |
| --- | --- |
| `service_path` | Tickets, inspection/replacement/logistics and participating organization records |
| `claim_fields` | Separate manual and SAP claim values and missing-field states |
| `inspection_findings` | Inspection observations and possible causes |
| `quality_changes` | QA, cut-in and CAPA observations |
| `dated_observations` | Recorded calendar dates with precision/timezone qualifications |
| `evidence_gaps` | Missing fields, coverage/truncation, mapping issues and unresolved questions |

Reports require explicit execution. They read only the saved graph and its exact definition version, verify projected-record hashes and edge identities, and make zero company/model calls. Historical reports remain available when a source disconnects. Graph reads retain owner/workspace isolation. No arbitrary prompts, SQL, SPARQL or executable rules are accepted.

Each row retains record ID, collection, projected field, literal value/state, source-reference/candidate association classes, qualification and record hash. Pagination is bounded; page exports retain totals, limits and provenance. The UI can open the corresponding saved record. Graph and definition hashes, source metadata revisions, report version and report hash identify the result inputs. Export is a report page, not an assertion that every result fits that page.

Claim status/reason values are not interpreted as approved eligibility/rejection semantics. Potential causes remain possible causes. Dates are grouped by recorded calendar day, without inferring within-day order across timezone/precision differences. Invalid dates remain invalid; missing fields are not filled. Direct references establish record association, while candidate links remain unverified. Neither establishes physical-engine identity or business approval. Zero rows means no observations in this bounded saved graph, not absence from company systems.

Warranty eligibility and confirmed root cause are not evaluated. Recurrence, failure rates and change effectiveness remain unavailable pending authoritative policy, identity, comparable confirmed failures, incorporation and population/exposure evidence. Module coverage is a draft inventory, not production readiness.

## Offline verification

`scripts/check_business_intelligence.py` takes `--database`, `--directory`, `--workspace`, `--owner` and `--graph-id`. It opens the supplied SQLite store in read-only mode, checks an expanded draft in memory, runs all six report questions on the original graph/version and writes first-page evidence plus totals to a fresh private directory. It does not load connector credentials or change input stores. Private outputs are not source-controlled.

The previously saved real invoice, ticket and two-source QA graphs all passed. The original 14 warranty concepts were retained and eleven modules added in memory for 73 total concepts; all expanded drafts compiled. The QA graph retained one service invoice and one quality analysis as separate records: seven quality-field report rows, three dated-field rows and 28 gap rows. All three graphs had zero claim observations. No matching claim, root cause, recurrence or eligibility result was invented.
