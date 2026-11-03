# Business Ontology extraction — chunk 3

Implemented and verified locally, without deployment, live workspace initialization or company-data writes. This extends the separate Business Ontology tab; existing Ontology and Semantic Intelligence remain independent.

## Source evidence and generation

After initializing both source bindings, a manager can explicitly import the sanitized Simpson blueprint/backend reference bundle or add bounded source text for selected modules. Documents are immutable, scoped to the workspace/owner, hashed and inspectable. The supplied archive remains reference evidence; correspondence with the deployed Simpson backend is not asserted. The bundled warranty service excerpt excludes unrelated credential-bearing portions.

Generation uses the application's configured OpenAI integration and model, strict Responses JSON Schema and `store=False`. Inputs contain relevant source excerpts and saved collection/field names/types from both bound sources. They contain no company record values or connector credentials. Adding source text and clicking Generate are explicit actions; opening the tab does not send a model request. User-supplied document text is included when relevant, so source forms should contain only material intended for extraction.

Persistent jobs enforce ownership, current authorization, an expected workspace revision, idempotency and one active job per workspace/owner. Source revision/generation changes, stale workspace versions, invalid evidence or broken references prevent a draft from being committed. Cancellation discards late results; it cannot undo a request already sent to the provider. Interrupted/expired running jobs fail without automatic provider replay. The existing local worker and worker supervisor process these jobs.

The response validator checks structure, ID uniqueness, references, parent cycles and quoted evidence against supplied text. Policy statements and implementation descriptions require their corresponding evidence kinds. These checks do not prove that extracted business meaning or policy is correct. Documents are treated as evidence, never as instructions to execute.

Each success atomically saves an immutable draft version and an audit event. Regenerating one module retains other modules and rejects removals that would break their references. Rules retain their evidence basis and are always non-executable. Missing policy/exclusion evidence and questions remain visible. No SME approval gate is introduced; operational business approvals remain business concepts.

## Additive API

All paths below are relative to `/business-ontology/v1`, use the existing authenticated transport and no-store envelope, and enforce workspace/owner access. Read access uses the existing read permissions; mutations require manager/write permissions.

| Method and path | Purpose |
| --- | --- |
| POST `/documents` | Add an immutable text source with title, kind and module IDs. |
| GET `/documents/{document_id}` | Inspect an owned source and provenance. |
| POST `/import-reference` | Import the verified bundled reference once; requires the matching current source bindings and `{}`. |
| GET `/jobs` | Read owned jobs and provider availability. |
| POST `/jobs` | Queue one module with `module_id`, `expected_revision` and `request_key`. |
| GET `/jobs/{job_id}` | Read current state and safe failure details. |
| POST `/jobs/{job_id}/cancel` | Cancel a pending/running owned job using `{}`. |
| GET `/versions/{version_id}` | Inspect an immutable foundation or generated draft version. |

The workspace view now exposes actual generated counts, module counts, source summaries, unresolved questions and version summaries. The UI provides source inspection, explicit generation/cancellation, polling, concept/relationship/rule details, quoted evidence and historical versions. Viewer access permits browsing without mutation controls.

## Verification and next chunk

The owner approved exactly one real-provider smoke test using the prepared warranty payload. It succeeded on configured model `gpt-5.6-luna`: 14 concepts, seven relationships, two candidate rules; 7,306 input and 3,717 output tokens. It used an isolated application store populated with sanitized saved metadata. There were zero company queries/writes, copied connector secrets or live application mutations. Its drafts were not published into the live workspace. Private evidence is in `.local/business-ontology/chunk3-payload-review/report-real.json`.

Automated backend, worker, frontend, build and desktop/mobile browser checks passed; full evidence is in `openspec/changes/simpson-business-ontology/verification.md`. The smoke proves the extraction path and structural/evidence checks work with the configured provider. It does not establish policy completeness or business correctness.

Next chunk: compile draft definitions to OWL/RDF and SHACL and run automated validation. Rule execution, competency queries, populated graph and intelligence remain later work.

## Generation controls update — 1 November 2026

The generation panel shows the latest attempt for the selected module separately from expandable history. A successful attempt exposes **View generated draft**, which selects that attempt's exact immutable revision and the correct module, even when a historical version was selected previously. **Refresh generation status** reads saved state without submitting a model request. **Retry selected module** explicitly submits a new request after a failure; there is no automatic paid retry. Existing successful revisions remain readable. Cancellation prevents a late result from applying; it does not promise that an already submitted provider request can be unbilled.

Source import/save now confirms its result; source inspection reads the actual owned document and lists its module scope. Importing the same supplied reference reuses its saved source IDs. Old failures retain their historical state and are not displayed as the selected module's current success/failure. The older organization error did not retain a detailed diagnostic or raw model response; its exact cause cannot now be established from that record alone.

Regeneration now sends the existing target-module concepts required by other modules as `required_concepts` alongside the retained cross-module concept catalogue. The prompt requests preservation of those IDs/meanings with exact source evidence. Validation still rejects omissions, invalid citations, incorrect identifiers, broken references and cycles. Known validation messages are preserved through an allowlist rather than replaced with one generic error; arbitrary exception/model text is not exposed. This addresses a reproduced regeneration-context defect, not a promise that every future model response must pass semantic validation. The configured model, structured output schema and no-replay provider boundary are unchanged; prompt version is `simpson-evidence-v2`.

This follows the [official OpenAI structured-output guidance](https://developers.openai.com/api/docs/guides/structured-outputs): schema-conforming output can still contain mistakes, so application citation and reference validation remains necessary.

## Source-classification reliability update — 1 November 2026

Two later engine attempts failed on unsupported policy/code classifications. Generation now builds its rule-basis enum from the actual supplied document kinds: proposed logic is always allowed; code descriptions require an application-code source; policy statements require a policy source. A second deterministic check uses each rule's actual cited documents and conservatively changes an unsupported policy/code label to `proposed_logic`. It never promotes a proposed rule or swaps in an unrelated policy citation. Existing meaning, source IDs and quotations are preserved. The normalized result must pass all original schema, citation, identifier, dependency, hierarchy and secret checks.

The immutable version's extraction metadata and job usage retain `classification_adjustments` with rule ID, original/final basis and reason. The result card explains the adjustment, and the version inspector lists individual corrections. These remain unverified proposed rules, not business-policy authority or executable generated code. The strict saved-draft/compiler validator still rejects an unsupported authority label in an already stored document; only the generation preparation boundary performs this correction.

This prevents the observed metadata mismatch from failing an otherwise valid first attempt, without a second model call, paid retry, fabricated evidence or silent substitution of an older draft. Prompt version is `simpson-evidence-v3`; configured model and transport/no-replay limits are unchanged. Real invalid quotations/references and provider failures still retain honest failure states. Earlier failed jobs are historical and are not rewritten as successes.
