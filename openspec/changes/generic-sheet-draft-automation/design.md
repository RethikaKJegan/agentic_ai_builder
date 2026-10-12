# Design

The required environment target list described below was superseded by `openspec/changes/prompt-owned-sheet-access/`. Normal workflows now carry reviewed prompt-generated targets in metadata; environment targets are only an optional operator ceiling. The original Phase 1 verification remains historical evidence.

Agent generation remains prompt-driven. The model chooses specialist definitions and delegates reads; a deterministic graph tool owned by a registered writer saves schema-validated results after master synthesis. Dynamic writers can use the same tool when their reviewed approvals permit it.

The operator configures BUILDER_SHEETS_WRITE_TARGETS as an array of spreadsheet_id, range (explicit named bounded A1 table including headers), identity_column, writable_columns, and allow_create. This is a resource authorization boundary, not domain logic. The planner receives these public settings and the tool schema. BUILDER_SHEETS_DIRECT_WRITE=1 permits reviewed workflows to write automatically; otherwise existing action gates apply. Neither flag changes email authorization.

The connector resolves rows by stable identity at invocation time, rejects ambiguous headers/IDs and non-scalar values, preserves unassigned cells through sparse batch updates, uses RAW values, and skips identical writes. A file lock per spreadsheet serializes this application's cooperating processes, with bounded acquisition. Blank rows are selected within the authorized capacity only. External editors do not honor this lock; Google Sheets has no transaction here. Partial completion across separate targets is visible as failed/blocked runs, not claimed rolled back. Interrupted external calls retain the runtime unknown-result boundary and never automatically replay.

Existing v1 workflow/agent/tool schemas remain unchanged. A new tool fixture uses the existing update_spreadsheet capability. Tests use real orchestration/connectors with offline model/Google transports. Live credentials, publication and deployment are operator configuration, not fabricated test evidence.
