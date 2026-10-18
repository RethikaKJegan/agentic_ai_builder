# Original-plan Phase 5: database workflow integration

This is the workflow integration phase from the six-phase knowledge-graph plan,
not the older query-federation phase also numbered 5. The verified implementation
was activated on the running app on 18 October 2026 at the user's request.
Deployment evidence is recorded in the OpenSpec verification document. Live model
generation and an owner-approved cloud write remain separate acceptance checks.

## Planning and published source scope

The server supplies current owned connection metadata, scalar field IDs/types,
reviewed relationships/business mappings, and exact Phase 4 record policies to the
existing planner. It replaces browser-supplied database catalogs and tool lists.
The planner selects one to four required dataset IDs; the server replaces them with
`metadata.database_scope`, pinning source identity, engine and a metadata/credential
generation fingerprint. Queries also pin the reviewed relationship graph hash.
The additive contract is `shared/contracts/data-sources/database-workflow-v1.schema.json`.
Workflow, agent and tool v1 schemas remain unchanged.

Database agents and the master receive a bounded copy of selected field/source and
relationship metadata, explicitly marked untrusted reference data. Existing stable
master/specialist definitions, UUID task instances and handoff evidence remain the
execution model. The metadata is not a credential or an authorization grant.

## Registered workflow tools

| Tool | Inputs and behavior |
| --- | --- |
| `database_read_record` | Exact connection/dataset/identity; reuse the Phase 4 field-limited point read policy |
| `database_read_query` | Supported logical query plan; validate field IDs, filters, metrics and reviewed joins through DataQueries, then execute with its existing bounds |
| `database_prepare_operation` | Up to four exact create/update/delete steps; read before-images and store encrypted immutable operation evidence, without business-data writes |
| `database_execute_operation` | A prepared operation ID linked to this run/revision, after an immediate human approval gate; reuse guarded Phase 4 execution |

These tools are registered in the existing Registry and use normal exact workflow/
agent assignment and publication approval. Source credentials resolve only through
the existing owned encrypted connections. A server-owned credential reference for
the workflow adapter does not independently authorize any source or record.

The query tool invokes no hidden query-planner/model call: workflow generation
supplies the explicit logical plan. Unsupported joins or unresolved business meaning
must be corrected before publication. Existing native pushdown, eligible federation,
complete join checks and bounded application fallback remain in the read engine.
Source snapshots are independent; there is no distributed snapshot or transaction.

## Concrete approval and execution

The supported write graph is:

`read/query → prepare → approval → execute → subsequent configured action`

The execute node must have exactly one incoming edge: the approved edge from its
immediate approval node. It maps `operation_id` from actual prepare output, including
a master's final output after delegated preparation. Specialists may read/query/
prepare; committing inside a delegated tool decision is rejected. A fixed graph
commit agent performs the approved write.

Prepare keys derive from the run and node/task invocation, and a durable journal
links the immutable request digest and operation to its run and revision. Another
run cannot substitute that operation. The link is committed atomically with the
prepared operation. Standalone Operations execution rejects linked operations;
the UI directs their review back to the originating workflow's Execution tab.
Operation responses add optional workflow/run references for that navigation.
The runtime hashes exact execute inputs,
records the operation reference at the approval gate, and checks the current gate
decision again before invocation. Current owner, tool and workspace permissions,
run activity/lease, source scope, policy and before-image are checked before commit.

The initial integration supports manually executed workflows under the existing
connection owner identity. The database operation must be approved by that same
currently authorized owner. Separate approvers and automation-subject delegation
are not silently mapped to an owner's credentials; unsupported identities fail
closed. Existing shared-demo identity limitations remain.

The UI fetches current permitted before-images from Operations instead of placing
them in generic approval events. Approval stays disabled until the concrete preview
is available and the reviewer checks every proposed change. Rejection remains
available when a preview cannot be loaded. A preview expires after ten minutes;
its expiry or a newer source record prevents commit.

Each query/prepare/execute invocation conservatively reserves four tool calls;
point reads reserve one. Set sufficient agent/workflow budgets and at least the
execute tool's 120-second timeout budget; human waiting also consumes the workflow's
overall duration. No automatic connector retry is enabled.

## Configuration, Execution and Google composition

Workflow details displays planned sources, metadata fingerprints, database tools
and literal/mapped inputs. The existing Agent hierarchy shows master/specialists.
Execution displays the exact historical revision, node results, source evidence and
UUID handoffs. Pending database reviews are actionable in Execution and Approvals.
The `database.operation` event records outcome references/counts even on known
partial or uncertain outcomes. Full operation evidence remains available through
owned Operations history and its existing reviewed recovery flow.

Database steps compose with the existing configured Sheets and SMTP/Gmail adapters.
Registered Gmail/Calendar extension tools are advertised only when an actual runtime
connector is configured and Registry discovery permits the current account to see
them. Their normal scopes, destination policies and approvals still apply. This
phase does not enable new Google providers, OAuth scopes or invitations. Unavailable
Calendar/Gmail actions remain unavailable.

Reads and tool outputs are retained in the existing authorized runtime run records;
bounded/redacted event snapshots are application evidence, not private reasoning.
They are separate from the encrypted CRUD before/after snapshots. No new run-output
retention or encryption guarantee is introduced. Existing OTel exports remain
allowlisted metadata and exclude these payloads.

Known failure, partial completion and uncertain commits are distinct. Uncertain
commits block runtime replay. A worker interrupted during an invocation follows the
existing unknown-invocation boundary rather than repeating a write. Recovery is a
separately reviewed Phase 4 compensation, conditional on unchanged after-images,
current inverse permissions and retained evidence; later email/Google failures do
not automatically undo a committed database change.

## Manual acceptance after a separate deployment

1. Refresh metadata and build current relationships. Keep Phase 4 policy restricted
   to dedicated test datasets; verify the owner can read them in Operations.
2. Ask for a manual workflow that reads a specific Atlas test record, prepares an
   explicit permitted field change, requires human approval, and then saves the
   result to a dedicated authorized Sheet. Supply the actual Sheet URL/tab/identity
   and desired columns. Use only available configured Google capabilities.
3. Open Workflow details. Inspect the exact selected source IDs, fields/mappings,
   prepare/approval/execute chain, Google destination and approval gates. Inspect
   Agent hierarchy if the prompt requested master/specialists.
4. Save, validate, approve and publish through the existing builder. Missing scopes,
   assignments, source policies or unsupported mappings must block publication.
5. Run the published workflow manually. In Execution, inspect actual reads and the
   concrete database preview. Independently verify preparation wrote nothing.
6. Review the checkbox and approve. Verify the exact source change independently.
   Inspect any subsequent Google approval in Approvals and the actual returned
   Google result in Execution. A database approval does not approve a different
   Google action; later external writes need their own gate in this combined flow.
7. Prepare another run, change the record externally before approving, and verify
   the guarded write preserves newer data. Repeat with revoked policy or refreshed
   metadata; stale workflows/operations must be blocked.
8. For a cross-source query, use only existing reviewed relationships and confirm
   both actual source evidence entries and complete join checks in Execution.
9. Inspect failed/partial operations in Operations. Do not treat unknown outcomes as
   safe retries; use separate reviewed recovery only for known eligible effects.

Automated verification: `.venv-integrations/bin/python scripts/verify_database_workflows.py`.
It uses disposable local PostgreSQL/MongoDB plus offline provider/Google fixtures;
it never loads saved cloud credentials to perform test writes. Exact results and
known baseline failures are recorded in the Phase 5 OpenSpec verification document.
