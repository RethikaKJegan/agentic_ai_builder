# First procurement slice — Step 4

The opt-in coordinator connects the case repository to the existing canonical Registry, graph runtime, source reads, approvals and connectors. It prepares **requirements + supplied contacts → BOQ/RFQs → tracking spreadsheet → Sheet projections → Gmail drafts**. It stops at drafts. No email is sent, quotation monitored, order awarded, PO released or Calendar event created by this slice.

The source workflow registers separate Requirements, Vendors and Preparation specialists. Their explicit tool nodes exchange actual mapped outputs through the runtime and preserve handoff traces. Preparation is deterministic table extraction, validation, section grouping and templated RFQ drafting; it does not make LLM calls or perform free-text/PDF/OCR extraction. Existing configured agents can use the scoped procurement status tool. Ingestion is restricted to the registered source-read graph so an agent cannot submit fabricated source rows as verified evidence.

## Enable separately

Add these settings to the extension's private configuration, preserving existing provider settings:

```json
{
  "enabled_providers": ["google_sheets", "gmail"],
  "sheet_creation_enabled": true,
  "procurement_enabled": true,
  "procurement_currency_precision": {"INR": 2}
}
```

Keep Calendar in `enabled_providers` if already configured. Currency precision must reflect the actual project's comparison currency; the example does not set it for every project. No additional credentials or Google scopes are requested. Restart only the isolated extension backend after changing configuration. Without procurement opt-in, the existing 19-tool catalog stays unchanged; enablement adds two internal tools and the procurement routes. No project is seeded or read on startup.

## Generalized project setup

Copy `setup.example.json` to a private file and replace the example URLs, bounded ranges and header mappings with your selected requirements/vendor tables. Field mappings use actual column titles, so arbitrary accessible spreadsheets and tab names are supported without server configuration changes. Discovery remains available through the existing Sheets connector to find those headers/ranges. The setup helper does not guess ambiguous tabs or headers.

Each source has at most 100 data rows, 100 columns and one header row. Requirements need stable item IDs. Map section, description, quantity, unit, specifications and delivery details when present. Project delivery location/deadline can fill missing row-level delivery fields. Missing values remain explicit; they do not receive invented business defaults. Quantity, specifications, complete project context and a matching vendor category are required before any external write.

Vendor categories are a comma-separated list matched to requirement sections without case. Each supplied vendor receives a separate RFQ per matching section, grouping that section's items. Four-item simulation example: two Piping vendors each receive one grouped pipes/valves RFQ; Equipment and Safety vendors each receive their respective item. This slice does not infer supplier suitability from web results. Invalid contacts and unmatched categories stop preparation for clarification. A selected vendor table is the operator's supplied recipient authority; its row data is still reviewed at the exact Gmail action gate.

Submit the plan through the existing isolated UI proxy using the local helper:

```sh
.venv-integrations/bin/python -m connector_extension.procurement.client setup \
  --plan .local/connector-extension/my-procurement-plan.json
```

The authenticated local-development session must have edit, validate, review, publish and execute permissions. The service creates/reviews/publishes derived workflows under that current operator authority. **It never calls the runtime approval-decision operation.** Every spreadsheet creation, row upsert and Gmail draft pauses at a dedicated human gate in the existing [Approvals UI](http://127.0.0.1:3002/app/approvals). Review the exact destination, headers, row fields or recipient/body before approving.

With normal extension workers enabled, the coordinator checks a bounded set of registered projects every three seconds and progresses after confirmed approvals/results. With workers disabled, explicitly advance it:

```sh
.venv-integrations/bin/python -m connector_extension.procurement.client advance --project-id project_demo
.venv-integrations/bin/python -m connector_extension.procurement.client status --project-id project_demo
```

Status includes phase, clarification issues, exact workflow/run/approval references, records, resource links and sync state. Existing workflow/trace/approval pages show those canonical workflows; no new frontend source or procurement dashboard was added. The setup plan is immutable per workspace/project ID. An identical resubmission observes the same project. Changed context, mappings or sources require a separately reviewed new setup/project; in-place amendments and clarification resumption are future work.

## Durability and confirmation

Plans, source snapshots/proofs, phases and workflow/run IDs are persisted in the separate procurement database. Source transactions, resource adoption and draft acknowledgements use stable keys. Original source rows are never edited. Tracking creation returns verified actual IDs; exact row-write targets are bound into the separately published upsert workflows. Case revisions and initial projections commit transactionally, while Google writes remain separate approved effects. Confirmed projections are acknowledged only from completed canonical run outputs. Rejection marks the target and stops the project; failed/uncertain projections require reconciliation.

After restart, the coordinator restores only its already-published exact workflow Registry evidence, under the same current authorized publisher. Runtime action approval is still pending until a human decision. No actor or grant is borrowed from a different project. Run references are reused instead of creating another invocation. This coordinator supports one extension process per state directory; its in-process lock is not a multi-server lease.

Gmail draft output is stored as resource metadata (`draft_id`, message/thread ID, run/workflow ID, `sent: false`). RFQ records remain READY. Draft creation never fills the sent-message fields or claims delivery. The RFQs Sheet therefore still shows READY. Draft references are available in project status and Gmail Drafts.

Unknown effects and terminal run failures are frozen; the worker does not silently retry a send/create or decide approval. Step 2's read-only spreadsheet reconciliation helper remains available, but automatic recovery of a stopped coordinator, Gmail draft reconciliation and operator-approved amendments are later work. A missing-configuration or budget failure is surfaced in project status. No self-approved automatic write policy is enabled.

## Extension routes

All routes reuse the existing loopback/Origin/session protection and canonical response envelope. Their operations are extension-local and do not alter shared API schemas:

| Route | Operation |
| --- | --- |
| `POST /procurement/projects` | `procurement_setup`, with the setup plan as payload |
| `GET /procurement/projects/{project_id}` | Read scoped project status |
| `POST /procurement/projects/{project_id}/advance` | `procurement_advance`, payload `{ "project_id": "..." }` |

Mutation requests use `request_id`, `operation`, `idempotency_key` and `payload`. Stable project/action identities provide durable effect idempotency. Caller-supplied workspace, auth, roles or credentials are not accepted. No generic record-write, approval-minting or direct Google endpoint is exposed.

## Verification

```sh
.venv-integrations/bin/python -m unittest connector_extension.tests.test_procurement_slice -v
```

Integration tests exercise actual extension Registry/runtime/SQLite/connector code with stateful offline Google responses, including all four-item rows, approved projections/drafts, source preservation, specialist handoffs, worker advancement, restart recovery, missing data, changed setup, source-graph tampering, rejection and unknown draft outcomes. Live account acceptance still requires a selected real setup plan and its exact action approvals. Production source authentication is the connected Google account; reading the vendor table does not verify buyer identity, physical delivery or compliance certificates.

## Operator tracking recovery

`POST /procurement/projects/{project_id}/retry-tracking`, operation `procurement_retry_tracking`, accepts the exact `project_id`, `expected_run_id` and boolean `absence_confirmed`. A current authorized approver is required. An absence-based retry requires the operator's explicit external check. With `absence_confirmed: false`, a scoped journal-confirmed HTTP 400 rejection of that exact create is required instead. Neither path is allowed when a returned resource ID has been recorded; verify that resource read-only. At most two fresh recovery attempts are allowed. Old runs, reported basis and original effect intents are retained; nothing is erased or automatically replayed. A new exact runtime gate still governs the new creation action.

Transport failures now retain bounded HTTP categories and secret-checked messages privately in the effect journal. Complete provider bodies, headers and URLs are not retained. The actual live create exposed a metadata placement rule: spreadsheet ownership metadata belongs in the root container, while each sheet's metadata belongs in that sheet's container. The payload and offline provider fixture now enforce that rule. The corrected create was verified live on 13 October 2026.
