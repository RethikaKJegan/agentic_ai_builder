# Durable automation — Phase 3

Durable event subscriptions, timers and recurring schedules extend the existing `TriggerScheduler` and `LifecycleService` queue. `LifecycleDriver` remains the bounded case controller, `GraphRunner` remains the executor, and Phase 2 remains the evaluator/planner. No additional scheduler thread, planner, case store or permanent LLM session is introduced.

A reply resumes an existing case/run. A schedule occurrence starts a distinct execution of an explicitly pinned approved workflow. These are separate queue operations.

## Explicit configuration and authorization

Subscriptions and recurring consent are authenticated backend commands. A model's wait request and OAuth scopes alone do not authorize monitoring or unattended writes. The future frontend must submit the explicit subscription or recurring business-consent request after the user reviews it.

Gmail monitoring requires the selected owned Google connection, `gmail.readonly`, an enabled `extension_mail_thread` connector, and its current Registry assignment in an approved polling workflow. That workflow must select the same account. The subscription correlates to actual verified send receipts from the case: Gmail thread ID, provider message ID and RFC Message-ID. Participants must match the actually authorized recipient. No engineer contact or reply receipt is invented. The existing Gmail connector supplies bounded MIME parsing, receipt timestamps and thread reads; no legacy IMAP monitor is used.

Recurring consent requires approval authority and includes owner/workspace, selected account, registered operations with input schemas, explicit recipient/resource restrictions, purpose, content scope, exact cron/timezone, action/occurrence ceilings and expiry. Its operation schemas constrain generated content; the exact approved workflow and its source bindings constrain what is executed. Content scope prose is descriptive, not a semantic model-quality guarantee.

The consent is checked against each actual resolved write payload. A matching pending runtime approval is approved through the existing `GraphRunner.decide` API with a persisted consent/payload reference. Exceeding scope leaves the exact-payload gate pending. Fresh owner permissions, Registry assignments, selected-account binding, consent state and workflow fingerprint are revalidated before consequential execution. Revocation does not fall back to another Google account.

## Backend API

All endpoints use the existing authenticated session, origin protections and response/error envelope. Requests are defined by `shared/contracts/durable-automation-v1.json`.

| Method/path | Body or query | Purpose |
| --- | --- | --- |
| `POST /business-ontology/v1/automation/subscriptions` | `request_key`, `case_id`, `wait_id`, `stage_id`, `provider`, `connection_id`, `correlation`, `participants`, `expected_information`, `payload_mapping`, `deadline`, `poll_workflow` | Register an external event wait |
| `POST /business-ontology/v1/automation/authorizations` | `request_key`, `connection_id`, `operations`, `purpose`, `content_scope`, `schedule`, `limits`, `expires_at` | Approve bounded recurring business consent |
| `POST /business-ontology/v1/automation/schedules` | `request_key`, `workflow`, `authorization_id`, `cron`, `timezone`, `missed_run_policy`, `overlap_policy`, `inputs` | Register recurring execution |
| `POST /business-ontology/v1/automation/timers` | `request_key`, `case_id`, `wait_id`, `stage_id`, `due`, `purpose` | Register a case timer |
| `POST /business-ontology/v1/automation/{id}/control` | `request_key`, `action`: `pause`, `resume`, `cancel`, `revoke` | Control a subscription, timer, schedule or consent; consent changes require approval authority |
| `GET /business-ontology/v1/automation` | optional `kind`, `before`, `limit` (1–100) | Page scoped records, inspect pending replies/occurrences/timers and recent jobs |
| `GET /business-ontology/v1/automation/{id}` | — | Inspect next due time, state, cursor, retries, receipt references and errors |

Epoch timestamps are UTC seconds. `workflow` and `poll_workflow` are `{workflow_id, workflow_version}` references. Gmail `correlation` contains `thread_id`, `sent_message_id`, `rfc_message_id`; `payload_mapping` maps saved wait fields to explicit normalized provider-payload paths, such as `{"finding":"text"}`. Paths use the existing restricted lifecycle data-path parser, never expressions or evaluation.

`operations` maps registered tool IDs to local JSON Schemas. Identity/destination fields need explicit constant/enum restrictions. For example, Gmail send requires a fixed authorized `to`, with bounded `subject` and `body`; report creation requires a fixed `project_id`. An executed consent example is in `shared/contracts/examples/durable-automation-v1.json`.

A recurring workflow is an independent approved workflow, not a case-owned adaptive revision. Create/review the existing connected-action workflow using Phase 1 APIs, then schedule its exact revision. A newer approved revision does not silently replace the consented one: recurring execution uses the existing pinned-automation runtime entry point and verifies the stored fingerprint. Deleting the workflow or revoking authority still blocks execution.

## Event and worker flow

1. Existing connected actions create the report and send the email, persisting verified receipts.
2. Phase 2 enters a typed external wait; explicit subscription registration binds that wait, selected account and actual send identifiers.
3. The existing scheduler polls the registered adapter with fresh owner authentication. Gmail requires matching thread, RFC reply references, participant and timestamp; self-messages, unrelated senders and automated/bulk replies are excluded.
4. Event evidence, processed message identity and a stable continuation job commit together using the existing case event/supply transaction. Cross-subscription message deduplication prevents reusing an old reply for a later wait on the same case.
5. Existing lifecycle job claims, leases and heartbeats fence workers. A case serialization key prevents two queued jobs from executing that case concurrently. Expired claims can be recovered; stale workers cannot complete another worker's job.
6. The worker invokes a bounded LifecycleDriver turn. Phase 2 evaluates the new evidence and preserves completed actions/revision history. New consequential actions retain their ordinary approval requirements.

The standard `TriggerScheduler` registers its owner-authentication callback for automation dispatch when one is not already configured. Live process roles continue to use the existing WorkerSupervisor and fresh authentication broker. Existing trigger/runtime worker configuration controls startup; no worker or production service was started by this implementation.

The driver uses at most 16 commands/120 seconds per background turn. Command-budget continuation is chained with stable IDs and a 64-turn ceiling; Phase 2's cumulative reasoning/tool/token/active-time limits still apply. Queue/occurrence outcomes retain compact case/run references; full receipts and source payloads remain in canonical runtime/case storage.

## Time, schedules and recovery

Cron supports five fields with lists, ranges and steps, plus IANA timezones. The next occurrence is calculated from UTC minutes. Spring DST gaps have no occurrence; repeated fall wall-clock minutes have distinct UTC occurrence IDs. Day-of-month and weekday use standard cron OR semantics when both are restricted. The search horizon is bounded to five years.

Missed-run policies are `skip`, `coalesce`, and `catch_up` (at most ten occurrences prepared per tick). Overlap policies are `forbid` and `allow`; `forbid` also blocks behind unresolved uncertain effects. Each occurrence has a stable identity derived from schedule/scope/due time, its own run and execution history. The existing mapped-read connector refreshes current evidence for each run. Poll retries do not move cron occurrences off their original recurrence grid.

Timers cover follow-up, reply deadline, approval deadline, escalation, delayed continuation and retry-after purposes. They produce actual timer-expiry observations and queue reevaluation; they never fabricate a reply or directly send a reminder. Any resulting reminder must be proposed, validated and authorized by the existing engine. Registering a reply subscription also registers its deadline timer atomically. Pausing/cancelling a subscription controls that linked timer.

Registered external waits suspend only elapsed execution-time accounting. On resume, the backend records the duration and adjusts the active-time anchor, retaining original wall-clock start, consumed tokens/tool calls and existing receipts. This prevents runtime workers from timing out a legitimate multi-day wait without resetting execution budgets. Timer and manual typed-event acceptance use the same durable continuation boundary.

Provider errors retain stable redacted codes, attempts and bounded backoff; processed IDs/cursors survive restart. Unknown external effects remain blocked for the existing connector/runtime reconciliation path. Recovery after a completed send reuses the same occurrence/run/effect identities instead of resending. No policy is broadened by an email body, timer, worker restart or stored OAuth scope.

## Persistence and qualification

The existing WorkflowStore SQLite/PostgreSQL boundary owns additive `automation_records`, `automation_deliveries`, a delivery index and an idempotent automation migration marker. Continuation jobs and fenced claims use existing `lifecycle_jobs`/`lifecycle_job_claims`. Event evidence remains on existing cases; full execution/effect receipts stay on existing runs/journals. No production data was reset. Table initialization is idempotent at service construction, following the existing persistence architecture; no deployment or operator-run production migration was performed.

See [verification.md](verification.md), [manifest.json](manifest.json) and the six execution traces for exact results. SQLite and controlled provider execution were verified. PostgreSQL checks were collected but skipped because a test DSN was not configured; deployed migration/concurrency qualification remains necessary. These tests do not prove live OAuth consent, Gmail deliverability, live model quality or business/physical outcomes.

Frontend integration remains outside this phase: use the existing Workflow → Business Investigation UI to collect reviewed account/recipient/subscription/consent settings and call these APIs; show waits, pending approvals, next-run times, occurrence histories and reconciliation errors. Deployment, live provider validation and operational quota/retention decisions remain separately authorized work.
