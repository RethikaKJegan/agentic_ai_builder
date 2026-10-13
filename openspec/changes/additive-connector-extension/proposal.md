## Why
The Builder needs optional Sheets, Calendar, Mail and web-search operations for future procurement workflows while preserving every existing source file, credential and published workflow.

## What Changes
- Add a standalone connector_extension package, tool catalog, private OAuth helper, operator configuration and opt-in launcher.
- Reuse canonical Registry/runtime interfaces and existing Sheets adapters.
- Add bounded Calendar event operations, Gmail thread/message/attachment/draft/send/reply operations and optional Brave search.
- Add isolated tests and setup documentation. No existing files, schemas, launchers or databases are changed.

## Impact
Only new files under connector_extension/ and this OpenSpec change. New connector state and credentials are separate. No live provider actions occur during implementation. Procurement business logic, document parsing and UI redesign are out of scope.
