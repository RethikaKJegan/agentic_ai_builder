## ADDED Requirements

### Requirement: Unambiguous worksheet recovery
The Sheets reader SHALL recover a missing named worksheet only when one actual worksheet exists, and SHALL report invalid or ambiguous ranges with SHEETS_RANGE_INVALID. It SHALL preserve source identity and baseline semantics.

#### Scenario: Spreadsheet title differs from its sole worksheet title
- **WHEN** a named range is rejected and the requested worksheet does not exist in a single-tab spreadsheet
- **THEN** the reader retries the same cell range against the sole actual worksheet

#### Scenario: Multiple worksheets exist
- **WHEN** the requested worksheet does not exist
- **THEN** the reader reports SHEETS_RANGE_INVALID without selecting a different worksheet

### Requirement: Safe trigger paths and live governance visibility
Trigger mappings SHALL accept dot paths and literal bracket paths and reject executable expressions before publication. Monitoring and Governance SHALL show scoped source failures, published agent guardrails and runtime audit records. Usage SHALL count workflow reservations once.

#### Scenario: Published priority mapping uses brackets
- **WHEN** a new row is mapped with row["priority"]
- **THEN** its priority reaches the workflow and the retained checkpoint advances only after successful ingestion

#### Scenario: Source fails before a run starts
- **WHEN** polling fails with a stable error code
- **THEN** Monitoring and Governance show that source error even if no run was created

### Requirement: Assignment-free planner drafts
The planner SHALL check raw provider output for sensitive data and remove model-proposed executable tool assignments before returning or caching a draft. Client draft saves SHALL continue to reject executable assignments.

#### Scenario: Model supplies assigned tools in a draft
- **WHEN** an otherwise valid model draft contains agent allowed_tool_ids or tool configuration_reference
- **THEN** planning returns empty agent assignments and no tool configuration references, and the UI can save the draft for Registry review

#### Scenario: Client forges an assignment on save
- **WHEN** a client saves a draft containing executable assignments
- **THEN** the API rejects it with UNTRUSTED_ASSIGNMENT

### Requirement: Explicit direct-email policy
The server SHALL permit smtp_send_email without a per-action approval only when operator direct-send mode is enabled, the exact Registry grant does not require approval, the published workflow permits external writes, and the recipient is allowlisted. Default connectors and runners SHALL require action approval.

#### Scenario: Operator enables direct email and the workflow has no approval gate
- **WHEN** a published matching-row workflow reaches its authorized allowlisted email action
- **THEN** it sends directly and completes without a pending approval

#### Scenario: UI reaches an unrelated upstream service
- **WHEN** the upstream returns JSON outside the canonical API envelope
- **THEN** the proxy returns a canonical API_WRONG_SERVICE error rather than an invalid envelope

### Requirement: Workflow-owned live execution
The server SHALL provide configured Sheets, OpenAI and Gmail adapters without creating a business workflow. Published workflows SHALL determine conditions, agent handoffs and email content. External email SHALL retain operator recipient restrictions and action approval unless explicit operator direct-email policy permits the action.

#### Scenario: UI workflow reaches an email action
- **WHEN** a published workflow processes a newly observed complete row through two configured model agents
- **THEN** it pauses for action approval before the allowlisted SMTP submission

### Requirement: Stable row-created polling
The source SHALL use the workflow-configured stable identity field for row.created events, retain observed identifiers, and wait for required fields before dispatching new incomplete rows. A current-only baseline SHALL exclude existing identities.

#### Scenario: The published source contains a spreadsheet URL
- **WHEN** a published Sheets trigger references an HTTPS Google Sheets URL instead of a bare ID
- **THEN** the provider extracts the spreadsheet ID for the API request and event identity without requiring workflow recreation

#### Scenario: Rows are reordered or edited
- **WHEN** already observed identities move or change and the server restarts
- **THEN** polling does not emit new row-created events for those identities

#### Scenario: A new partial row becomes complete
- **WHEN** a new identity initially lacks a required field and that field is later populated
- **THEN** exactly one row-created event is emitted

### Requirement: Safe provider diagnostics
Connection checks SHALL report stable errors without credentials or raw provider data. Polling SHALL advance a checkpoint after all successfully ingested events even when events are filtered or duplicates.

#### Scenario: Poll batch ends with a filtered event
- **WHEN** ingestion succeeds and the final event fails a workflow filter
- **THEN** the checkpoint advances to the supplied cursor
