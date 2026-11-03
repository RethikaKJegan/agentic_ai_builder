# Business Ontology in workflow creation

The Overview **Generate workflow** action now automatically retrieves the requesting owner's relevant Simpson Business Ontology definitions and latest saved warranty interpretations before calling the configured planning model. There is no additional ontology-selection model call or source picker.

The planner receives a bounded selection of concepts, relationships, rules and policy interpretations, including exact supporting quotations and source hashes. These inform proposed process steps, required information, responsibilities and business checks. Existing database metadata retrieval still selects actual readable datasets; ontology relationships do not grant database joins, permissions or tool access.

## Try it

1. Open Overview and enter: “Create a read-only Simpson workflow to assess engine complaint warranty eligibility. Retrieve complaint and invoice evidence, check the applicable warranty dates, operating hours and exclusions, and explain the decision.”
2. Generate the workflow. In the editor, find **Business Ontology informed … proposed steps** and select **View ontology evidence**.
3. Inspect a step's explanation, expand its concepts or rules, and read the supporting source quotations. Warranty interpretations retain their application-code or policy-document origin.
4. Expand **Generation provenance** to see the exact definition version and hashes. **Download ontology evidence** exports the entire saved trace, including considered references, policy revisions and step contributions.
5. Reopen the saved workflow. Its original evidence remains attached. A new generation request reads the latest definitions; retrying the original idempotency key preserves its original proposal and evidence.

Existing workflows are not retroactively labelled as ontology-informed. Irrelevant requests continue normally and show a no-match result. Sessions without Business Ontology read access continue ordinary planning without receiving its content.

## How the proof is constructed

`workflow.metadata.business_ontology` follows `shared/contracts/data-sources/business-planning-v1.schema.json`. The server constructs its sources and hashes from owned saved evidence. The provider declares `metadata.business_ontology_step_bindings`, each with an actual action `node_id`, exact retrieved `refs` and an explanation of their application. The server checks those references, requires at least one contribution for a matched retrieval, replaces provider-authored provenance, and removes the intermediate binding field.

A separate owner-scoped `business_planning_provenance` record preserves the trace. Draft saving rejects modified or foreign contribution evidence. The UI describes contributions as recorded at generation; later workflow edits do not turn the original trace into fresh analysis. This trace is evidence of supplied knowledge and declared step-level application, not a model reasoning transcript or proof that a workflow executed.

Retrieval reads the latest immutable definition version and policy heads in one read transaction. Snapshot source hashes, citations and stored policy integrity are checked. Selection is lexical with business module aliases, bounded to three matched modules, 36 references and 70,000 serialized characters. No embeddings, Bedrock, company-record reads or source writes are introduced by retrieval. The ordinary live planner's existing two-attempt correction limit also covers invalid contribution links.

The existing three business-rule handlers, policy assessment safeguards and operational approval requirements remain in force. Code-derived warranty conditions remain descriptive implementation evidence; importing them into a proposal does not establish an official written policy. This integration concerns workflow creation, not every independent free-text data-query endpoint.

## Verification

See `openspec/changes/business-ontology-workflow-planning/verification.md`. Tests cover real scoped stores, automatic context injection, forged client/provider references, API save/get, ownership, exact citations, missing read authority, no-match requests, immutable retry evidence, fresh version selection, stable workflow identity and bounded correction. Browser checks cover creation, save, editor evidence, citations and downloads on desktop and mobile. One explicitly approved configured-model planning test used actual saved definitions and code quotations; it did not query company records, execute a workflow or write business decisions.

Contribution formatting now appears explicitly in the schema supplied to the model. Unambiguous agent-to-action and definition-ID-to-reference normalization is recorded as `binding_normalizations` in the exported trace; unsupported references still fail. Dynamic specialist contributions must target their actual delegating master graph node. The approved real hierarchy diagnostic is saved as draft `planned_d365b41086457927` for inspection; it has not been executed.

For wide database schemas, agent reference metadata now contains exact task-relevant fields and explicit `metadata_coverage` omission counts within the existing task budget. Source identity, hashes and runtime authorization still bind the complete schema. This avoids rejecting a valid inspection source merely because its full schema exceeds the per-agent reference limit. See `openspec/changes/planner-database-binding-reliability/verification.md` for the three approved real generation checks.

The workflow evidence panel now leads with business terms and meanings, how they apply to the linked step, and optional planned responsibilities. Source quotations and technical hashes are nested disclosures. Explicit bounded read-only coverage notes remain under **Investigation scope and limitations**, while actual missing setup still blocks approval. The existing complaint investigation was corrected as revision 2 and is validated/submitted, awaiting the user’s preparation/approval action. See `openspec/changes/business-workflow-review-clarity/verification.md`.
