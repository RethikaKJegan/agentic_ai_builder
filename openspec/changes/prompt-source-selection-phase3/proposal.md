# Complete original-plan Phase 3 source selection

Connect confirmed, current business entity mappings to the metadata-only Questions
planner. Return a server-derived source preview from each validated plan, with
qualified datasets, field purposes, eligible join pairs and review status. Show
that selected graph subset and explain each source's contribution before reads.
Retain strict read validation, source isolation, freshness, jobs and legacy plans.

The query response contract gains optional metadata; workflow/agent/tool contracts
and the model query-intent schema stay unchanged. No writes, arbitrary query text,
new join semantics, live review edits or deployment are included. Unsupported
questions still require clarification or fail validation. Verify source selection
for MongoDB only, PostgreSQL only, and both, plus irrelevant-source exclusion.
