# Running the three reference rules

Business Ontology has implemented handlers for the three reference rules shown in its rule count. They run against a selected saved source graph and optional saved, source-cited input revision. They do not need an OpenAI call or an SME approval step.

In **Data Intelligence → Business Ontology**, select a definition version and a **Saved source graph**, then find **Run business rule checks**. Select a rule and, for a case rule, its subject record. Recurrence also needs a saved change record. **Run selected business rule** explains missing inputs immediately. To supply evidence, choose **Record source-cited rule inputs**, add/select a document, enter its supported facts and exact supporting quotations, and save a revision. Select that revision and run again. Unknown facts stay blank. Evidence history, source text, check-by-check explanations, provenance and JSON downloads are available in the same panel.

These inputs are assertions recorded by a workspace manager from source documents. The application validates their types, citations, ownership and case/change binding; it does not independently investigate whether a document is true or whether the selected quotations substantiate the manager's interpretation. Results state that qualification. A genuine inspection report or cohort report must be supplied before treating a supported result as evidence for a business decision. No source ticket, diagnosis, claim or company database is changed.

## 1. Root-cause evidence

Rule: `failure:unconfirmed_similarity`.

Known facts are a suspected/documented cause, finding basis (similarity, inspection or test), current-case diagnosis (confirmed, inconclusive or ruled out), and finding details. Every known fact needs a quotation.

- Similarity alone, or an inconclusive diagnosis, returns **hypothesis only**.
- Missing necessary evidence returns **insufficient evidence**.
- A source-cited confirmed diagnosis supported by inspection/test findings returns **documented root cause**.
- A source-cited ruled-out diagnosis with inspection/test findings returns **cause ruled out**.

Example: “A similar previous engine had a gasket leak” remains a hypothesis. A current engine report stating that an inspection and pressure test identified a gasket leak can support a documented root-cause result when those findings are explicitly entered and cited. The result reports the document's assertion; it does not turn LLM similarity into a diagnosis.

## 2. Post-change recurrence

Rule: `effectivity:recurrence_needs_evidence`.

Select a saved case and change. Required source-cited facts cover the same-engine identity link, applicability, actual changed-component incorporation, matching failure mechanism and root cause, comparable investigation conclusion, incorporation/failure dates, observed post-change hours and required exposure. Actual failure must occur on or after incorporation, and recorded hours must meet the stated minimum. Dates have calendar-day precision. The application supplies no default exposure threshold.

- All conditions met: **recurrence supported**, qualified by the supplied evidence.
- Complete evidence with a failed condition: **recurrence not established**.
- Any required fact missing: **insufficient evidence**; the result shows each failed/unknown condition separately.

Example: an incorporated change on 1 January followed by the same confirmed mechanism on 1 June, after 100 hours against a documented 100-hour requirement, supports recurrence when identity, applicability and the other conditions are documented. A complaint merely occurring after a serial cut-in does not. At 99 hours against that requirement the exposure check fails. A bare serial match never supplies an identity or incorporation finding automatically.

## 3. Failure rates

Rule: `monitoring:rate_requires_exposure`.

Supply a defined monitored cohort and common start/end period, complete follow-up coverage, a numerator counting distinct engines with confirmed first failures, the at-risk engine count, and total at-risk engine-hours. The cohort may come from a separate authoritative report; it is not assumed to be the bounded records in the saved graph. The subject can remain “External cohort specified in evidence.”

- Missing inputs: **insufficient evidence**.
- Complete inputs with incomplete follow-up, unsuitable counting basis, nonpositive denominator/exposure, failures exceeding the population, or reversed dates: **rate not calculable**.
- Valid inputs: **rate calculated**, with both formulas and denominators shown.

Example: five confirmed failed engines out of 100 engines with 10,000 total at-risk operating hours gives **5% failed engines** and **0.5 first failures per 1,000 engine-hours**. A documented zero failures with those valid denominators gives zero for both. Zero observed rows, a single complaint's hour meter, or unknown follow-up cannot establish zero cohort failures. Outputs use exact decimal arithmetic rounded to six decimal places, half-even. This handler does not calculate repeat-event intensity or corrective-action effectiveness.

## API and persistence

All paths start `/business-ontology/v1` and retain existing scoped sessions, no-store envelopes and origin checks.

| Method and path | Behavior |
| --- | --- |
| GET `/versions/{vid}/graphs/{gid}/rule-execution` | Available handlers, typed input specifications, owned evidence sources and this graph's revision metadata. |
| POST `/documents` with `kind: "evidence"` | Manager adds a source for the selected rule module. |
| POST `/versions/{vid}/graphs/{gid}/rule-evidence` | Manager saves an immutable, cited input revision with `expected_revision` and `request_key`. |
| GET `/rule-evidence/{evidence_id}` | Read the owned saved revision, embedded source and integrity hash. |
| POST `/versions/{vid}/graphs/{gid}/rules/execute` | Read-only execution, accepting exactly `rule_id`, `subject_node_id`, `change_node_id`, `evidence_id` (nullable selections). |

`business_rule_evidence_heads` and `business_rule_evidence_versions` are additive application tables included in the scoped backup/restore audit. Revisions use optimistic concurrency and retry keys; previous revisions remain readable. A scope may contain at most 24 case/rule series, 200 revisions total and 32 revisions per series. Evidence cannot be reused for a different graph, version, rule, subject or change. Every execution checks saved definition/graph/evidence integrity, returns all checks and pins provenance to hashes. Execution makes zero model calls, company queries or source writes and does not persist a result until the user downloads it.

Dispatch matches the saved rule's semantic definition to a fixed implemented handler (`simpson-reference-execution-v1`). A model-generated or edited rule does not become executable because it happens to reuse a familiar ID. Historical immutable definition documents retain their original `executable: false` extraction field, which prohibits treating arbitrary generated text as code. The catalogue's separate **execution** availability reflects the implemented handler. No old version is rewritten to hide that history.

This completes execution for the three displayed reference rules. It does not establish all 22 blueprint business answers, automatically confirm company evidence, add individual production login, or supply missing warranty policy, physical identity or cohort data. The existing monitoring-readiness panel still describes what the bounded graph itself establishes; the new runner additionally evaluates explicitly supplied evidence.
