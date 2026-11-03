# Binding reliability and actual hierarchy diagnostic

The reported job `plan_dd75fbc4cc774ce88017c562325001b7` failed with PLANNER_OUTPUT_INVALID / BUSINESS_ONTOLOGY_BINDING_INVALID. Rejected drafts were not persisted by that earlier job, so its exact malformed binding cannot be reconstructed and is not asserted here.

The user explicitly approved one new full-path diagnostic planning test. It used cached real source-schema metadata, ontology revision 4 and the same hierarchy/automatic-input planning mode as Overview, through LivePlannerProvider and PlannerService. No company records were sent. The configured model returned a valid draft on its first call: three graph nodes, a master and four specialist definitions, one master-node contribution with eight retrieved references. It passed canonical validation, database-source binding, ontology binding and the live wrapper's checks. This demonstrates intermittency, not proof that every generation will succeed. Schema discovery/source reads were bypassed in the diagnostic to preserve the saved metadata-only transfer scope.

## Changes
- The canonical schema supplied in the model request now explicitly requires the contribution array when relevant business evidence is present, with exact retrieved reference enums and bounded fields. Transport remains the existing JSON output mode; no claim of API-enforced strict structured output is made.
- Hierarchy prompting identifies the actual master graph node as the contribution target for specialists without graph nodes. It explicitly excludes specialist IDs in node_id.
- Safe normalization resolves an agent ID to exactly one existing action node and a saved definition ID to exactly one retrieved reference. It merges bounded repeated contributions to the same action. Every normalization is recorded in the server-owned trace. Unknown/ambiguous references, missing specialist graph nodes, trigger/output targets and fabricated citations still fail.
- Validation feedback now identifies the failed binding/index and provides exact valid action node IDs and retrieved references within the existing two-attempt limit. No extra automatic model pass is introduced.
- The optional normalization audit is documented in the versioned metadata contract. It is included in downloaded original traces; no UI build is needed.

## Checks and live result
77 scoped backend tests plus four subtests passed, including normalization integrity, missing-node rejection, exact failed-constraint feedback, provider request schema enumeration and prior retrieval/planner regressions. The captured actual model response was replayed through the updated full wrapper without additional model calls and passed. Shared contracts, Python compilation, strict OpenSpec and diff checks passed.

Backend and worker restarted after verifying no active jobs; frontend remained on build `8XcKU7N-zHUG4DMKasjp4`. The approved diagnostic result was recorded as server-owned evidence and saved through the normal workflow API as **Simpson Warranty Complaint Assessment**, draft v1 `planned_d365b41086457927`. It is not approved, published or executed. This is the real captured model result, not an authored substitute or a claim that the earlier failed job succeeded. Original failed job history is preserved.

Private evidence: `.local/business-ontology/binding-diagnostic-20261101/` contains the exact permitted provider context, actual first draft, canonical response, offline replay, scoped test logs, source rollback, saved-draft reference and browser checks. No credentials or company rows were printed. Only one real diagnostic provider call occurred.
