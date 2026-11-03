# Database source binding correction

## Reported failure and reproducible defect
The reported job `plan_ce342f0bd9c24b3db352be0dfc4e39b3` failed after model generation with PLANNER_OUTPUT_INVALID / KG_SOURCE_BINDING_INVALID. The old wrapper collapsed distinct ValueError reasons into that generic code and did not retain rejected drafts, so the original rejected field cannot be reconstructed exactly.

A deterministic defect exists on the reported inspection path: the actual cached inspection source contains 355 fields and a projected descriptor of 48,322 characters. Retrieval accepts it within the 70 KB candidate pool, but `bind_generated` previously appended the complete descriptor to each specialist and rejected anything over 16,000 characters. No source assignment or retry could make that complete schema fit.

## Implementation
`bounded_agent_reference` is generic across owned catalogs. Small references are unchanged. Wide references retain exact source identity, label, engine, operations, identity/write policy and source hash binding. The server packs existing catalog fields fairly across assigned sources, prioritizing explicit identity/write/join fields and words relevant to each agent's role/goal/instructions. It records field and relationship coverage omissions. It invents no fields and does not infer grants or joins. Runtime source/field validation still uses the complete saved schema. If the required source identity/policy skeleton itself cannot fit, a specific error remains.

`SourceBindingError` distinguishes dataset selection, unknown source, wrong agent-key namespace, missing specialist assignment and scope violation. The existing bounded correction receives the actual safe failed constraint, valid owned dataset IDs and current proposed agent IDs. Model request metadata schema enumerates actual candidate source IDs and the specialist assignment shape. This is an instruction schema in existing JSON output mode, not a new strict-output API guarantee.

No domain/prompt recognition template, extra automatic provider pass, hardcoded Simpson workflow, guessed source mapping, permission bypass, record write or execution was added.

## Tests
- 74 targeted retrieval/business-planning/planner/provider-error tests passed, plus four subtests.
- 59 disjoint database-workflow/automatic-source/deleted-planning/live-provider regressions passed. Total 133 scoped backend tests.
- Shared contract validation, generated UI contract consistency, Python compilation, strict scoped OpenSpec and whitespace checks passed.
- Read-only actual saved-metadata reproduction for the reported investigation objective includes inspection/ticket/workorder/FOC schemas. The 355-field inspection source binds in 15,993 characters using 107 exact task-relevant fields; ticket and smaller source metadata remain complete. No model or source database calls occurred in this reproduction.
- Regression coverage checks exact trusted field preservation, unchanged input catalogs and source hashes, fair multi-source coverage, deterministic output, unknown-source rejection, model request source-ID enums and specific correction feedback.

## Approved actual model checks
The user explicitly approved up to three fresh generation checks. Exactly three configured OpenAI provider calls occurred. All returned valid drafts on the first attempt through `LivePlannerProvider` and `PlannerService`, including canonical validation, database binding, ontology contribution binding and hierarchy/automatic-input mode:
1. Exact reported investigation prompt: three graph nodes, four agents, three selected sources (tickets, inspection reports, workorders), ontology incorporated.
2. Earlier warranty prompt: three graph nodes, two agents, one selected source, ontology incorporated.
3. Rephrased investigation prompt: three graph nodes, four agents, three selected sources, ontology incorporated.

Requests used actual saved owned database schema metadata and ontology citations, without company records or credentials. Schema-index sync and external spreadsheet discovery were not invoked; there were no spreadsheet URLs in these prompts. This is actual configured-model planning and validation evidence, not a claim of workflow execution, complete case data, automatic official policy approval or universal generation reliability. No prepared workflow was substituted into the user's failed job or saved as its result.

## Activation and preservation
Backend and worker restarted after checking that no jobs were queued/running; frontend build remains `8XcKU7N-zHUG4DMKasjp4`. Scoped source rollback files are preserved. Existing saved business versions/documents/graphs/generation history/policy revisions and backed-up configuration/key hashes are unchanged. The reported failed job stays in history. Normal explicit Retry generation creates a new planning key; no uncertain request was automatically replayed.

Private evidence: `.local/business-ontology/database-binding-20261101/`, including reproduction, three provider request/output/result files, model report, test logs, baseline, rollback and deployment report. Sensitive context stays local; no credentials or company rows were printed.
