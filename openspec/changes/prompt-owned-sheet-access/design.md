# Design

`metadata.sheet_write_targets` contains the validated target settings already used by Phase 1. The planner generates this from the setup prompt and includes the record tool for configured Google connections. Missing destinations remain unresolved. Approval/publication and immutable revision hashes bind the target list to the reviewed workflow. The editor shows the list before publication.

The record connector binds a fresh restricted adapter to the reviewed workflow at the existing graph/delegated execution boundary. No model inputs or incoming rows can set this binding. Invocation still requires exact Registry grants, write policy, applicable approvals and budgets. Direct unbound adapters with no targets deny all writes. Optional environment ceilings can only narrow a workflow's range, writable columns and create permission; legacy workflows without metadata can retain configured environment targets.

New spreadsheets require no environment edit or restart after one-time connection/policy setup. Google account access remains required. Existing v1 schemas and grant shapes are unchanged; metadata access settings are validated by application code. No universal connector access is inferred merely from Google credentials.
