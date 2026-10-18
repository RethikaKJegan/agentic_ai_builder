# Connection lifecycle verification

Scoped changes: DataSources owned delete action, matching route/client union, explicit Edit connection/Reconnect/Delete connection controls. Existing add, credential verification and disconnect APIs reused. Deleted app credentials, snapshots, profile jobs and refresh settings cannot be republished by an in-flight profile. Audit retained; relationship rebuild requested. No cloud adapter calls during delete.

48 backend tests passed (data sources, relationships, refresh), six focused UI tests passed, TypeScript/lint/build/contracts/scoped strict OpenSpec/diff checks passed. Desktop/mobile staged and deployed browser lifecycle checks passed using mocked mutations. No real connection or cloud data was disconnected, deleted or changed during verification.

Backend reloaded for delete support; worker left running. Frontend activated as 20aYcxeETKmU9_QLsFanv with prior build/81 assets retained. Configuration unchanged. Read-only session, worker-health and connection-list checks returned 200. Evidence: .local/connection-lifecycle/.
