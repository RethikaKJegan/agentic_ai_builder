# Conjunctive filter semantics verification

The saved receipt for query `subway_query_3bf9eea3dfb443f9b9c4a6d07adaea60` contains `availableAmount < 0` and `availableAmount is_null` on the same field. The executor combines flat filters with AND. Its live historical receipt records a complete 22,550-row scan and zero matches, which does not establish that both requested alternative categories are absent.

The fix preserves the query grammar and AND meaning. Generic validation now rejects provable null/non-null contradictions, incompatible equalities, equality exclusions, impossible compatible-type ordered intervals and equalities outside their bounds before source dispatch. It compares native scalar keys; date/timezone and ObjectId equivalent representations retain their native meaning. It does not change, drop, coerce or reinterpret predicates. Unknown source/field/relationship, currency, deadline, population and arithmetic checks remain enforced. Legitimate empty results and compatible conjunctions retain their behavior.

Connected workflow planning and query-agent guidance now explicitly require separate query-plan/read branches for alternatives, repeating common constraints and passing all relevant receipts to reporting. Query agents implement the assigned branch rather than folding the whole goal into one conjunction. Reports retain individual branch counts/coverage and cannot invent a distinct union count for overlapping branches.

An exact saved-query replay on 22,550 synthetic records reproduced the archived executor's zero result even though the synthetic workload contained both categories. The new executor rejected that same conjunction. Separate supported aggregate branches returned complete synthetic counts of 5,638 negative records and 11,275 missing/null records. These figures are test data, not live business findings.

Tests exercise rejection before source connection, valid zero matches, compatible interval/equality/null conditions, native date/ObjectId equivalence and actual CrewAI/GraphRunner execution through two independent reads to a report. The runtime fixture preserves a common exclusion filter and verifies two matching records in each category, all-source coverage and both receipts in report inputs.

No live provider replay, tenant source read or email delivery was performed. Contracts, generated UI contracts, OpenSpec strict validation and whitespace checks passed. Private backup, exact rollback and replay records: `.local/subway-filter-semantics-20261112/`.

Validation completed: 131 unique tests passed (42 predicate/native-query tests and 89 prior routing, business-resolution, dataset-selection, model, pagination, reporting, demo and Simpsons isolation tests), plus the exact historical-query replay. Existing framework deprecation warnings remain.

Deployment verified: only agentic-builder-subway restarted. Hosted authenticated checks passed across operator, Simpsons and Subway, including source isolation and native tools. Source/Google credentials, bindings, ontology/packages, automations, configuration and histories were preserved. Other service process IDs and the frontend build remained unchanged. The previous completed false-zero report was preserved as historical output; generate a fresh workflow for the third prompt to apply new planning and validation.
