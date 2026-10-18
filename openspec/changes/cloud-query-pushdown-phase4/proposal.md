# Phase 4: bounded database pushdown

Compile the reviewed, validated logical plan into trusted PostgreSQL queries or MongoDB pipelines when equivalence with the existing scalar engine can be established. Keep the bounded application executor for unsupported operations, with the chosen strategy and reason visible before execution. Never execute model-generated database programs.

Preserve ownership, expiring plans, metadata freshness, explicit execution, TLS and complete strict join checks. Add execution evidence without changing workflow, agent or tool contracts. No contributor signoff is inferred.
