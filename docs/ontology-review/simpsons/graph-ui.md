# Business ontology graph — 2026-10-30

**31 October extension:** the [source-backed record explorer](object-explorer.md) is now deployed alongside this concept graph. Select a concept, choose Browse records and open a permitted record for underlying values and relationship navigation. This document retains the original concept-graph release evidence.

The ontology now opens as an interactive connected concept graph in [Data Intelligence → Ontology](https://praxi.bellcorpstudio.com/app/data-intelligence). This replaces the default technical record-management presentation. The initial diagram shows six Simpsons service concepts and nine stored relationships. **Show all concepts** exposes the organization model; **All three layers** exposes the 72 common/domain/organization concepts and their mappings/dependencies.

The diagram uses the existing ontology API and records. It does not create company record instances or invent relationships to connect isolated concepts. Candidate serial associations, possible creators and physical-engine interpretations use dashed links. Definition dependencies are labelled as dependencies rather than asserted as new business predicates. Ordinary reciprocal relationships are preserved.

Select a concept to read its definition, fields, rules, relationships and mapped source names. Select a relationship label to inspect its meaning and endpoints. Search can locate a field and show its surrounding concept context. Zoom, fit and drag-to-pan are supported; mobile opens at a readable zoom with an additional concept picker. Review, publication, history, export and task selection remain under **Review & manage**. Raw definition JSON is an optional advanced editor, not the default inspector.

The former nulls had different meanings: uncalibrated scores lacked representative reviewed examples; an organization record's optional domain label was not its separate domain mapping; unresolved field bindings had no confirmed source identifier or datatype. They did not mean the Simpsons company data was empty. The new default view explains pending bindings and confidence limits in words and does not manufacture values to fill those gaps. Seven unresolved bindings remain visible as **Needs verification**.

## Verification and deployment

- **19 UI tests passed**, covering graph projection, preserved reciprocal edges, real labels/source paths, readable pending states, graph-first presentation, search/layers, viewer behavior and existing review/API compatibility.
- TypeScript, scoped ESLint, full production build, shared schemas/fixtures, generated-contract drift checks, strict OpenSpec and diff checks passed. The existing framework build notice was handled through the ordinary retry; dependencies and the previously recorded security-advisory status were not changed.
- The exact production build was checked with the captured current Simpsons ontology on desktop and 390px mobile. Readable node/edge inspection, seven pending bindings, all 72 concepts across layers, search, zoom/fit and management access passed. The existing isolated accept → publish → select management flow also passed on both viewports.
- Live authenticated desktop/mobile checks passed concept and relationship clicks, readable field/rule/source inspection, pending-field explanations, all-layer selection, search, zoom/fit, dragging and management access. No raw JSON appeared in the default business view; no page errors, horizontal page overflow or backend mutation requests occurred.
- Activated frontend build `zCmmvYM2O8OO6XuTavX-9`, retaining 85 previous static assets. Only the frontend service restarted. Backend/worker PIDs remained unchanged. Before/after database hashes, including after browser verification, confirm unchanged ontology records/versions/events/selections/approvals, observation evidence, connector credentials, saved workflows and runtime runs. No company records or schemas were changed.

Private evidence and screenshots: `.local/ontology-foundation/graph-release/`. Live diagram images: `live-desktop-diagram.png` and `live-mobile-diagram.png`. Rollback frontend: `.local/ontology-foundation/graph-release/previous.next`. The isolated preview server was stopped after verification.

The ontology still contains 416 records: 409 approved and seven unresolved drafts. Current published version remains `ov_d633a24f73d20898769885f779fe39c4fb929723`. This correction changes how the existing model is presented, not its business authority, calibration status, source permissions or execution contracts.
