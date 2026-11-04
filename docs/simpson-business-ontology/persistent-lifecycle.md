# Phase 4 persistent business lifecycle

Implemented locally, backend only. Business cases now outlive agent runs and pin
immutable process definitions, ontology/mapping context, capability contracts and
secret-free operator configuration. Execution completion and business outcome are
separate: an analytical result can be complete while its physical activity remains
unverified. No official Simpson policy or operational process has been invented.

## Existing components reused

`WorkflowStore.transaction` and its SQLite/Postgres adapter supply storage and
serialization. `BusinessPreparation`, `BusinessRetrieval`, ontology versions and
existing mappings supply actual evidence. `ClientPackages` supplies other domains.
`BusinessComposition`, the existing planner, compiler, `AgentConfigurationFactory`,
Registry assignments, master-child delegation, `CrewExecutor`, `GraphRunner`,
runtime checkpoints, working/experience memory and guarded recovery remain the
execution path. Cases do not implement another agent loop or install permissions.

The integration audit is recorded in
`openspec/changes/persistent-business-lifecycle/proposal.md`.

## Files and migrations

New implementation: `workflow_api/business_cases.py`,
`workflow_api/evidence_completion.py`, `scripts/business_cases.py`.

Integration edits: `workflow_api/business_ontology_routes.py`,
`workflow_api/business_composition.py`, `runtime/capability_composition.py`,
`workflow_api/capability_contracts.py`, `runtime/service.py`, `scripts/validate_contracts.py`.

Contracts: `shared/contracts/business-lifecycle-v1.json`,
`shared/contracts/business-case-v1.json`,
`shared/contracts/examples/business-lifecycle-v1.json`.

Tests: `tests/test_business_cases.py`, `tests/test_business_case_runtime.py`.
Specification, tasks and verification: `openspec/changes/persistent-business-lifecycle/`.
Documentation includes this report and the repository-only Rethika handoff.

Migration version 1 is additive and follows the existing service-owned migration
convention: `business_case_migrations`, `business_process_definitions`,
`business_cases`, `business_case_commands`. Initialization creates these in the
configured application store. No existing table is replaced or backfilled. No live
database migration, deployment or service restart was performed in this change.

## Contracts and state

Process versions contain full executable stage contracts. `stage_definition_id`
can repeat; `stage_instance_id` must be unique. Dependencies are acyclic and stage
bindings must name an upstream dependency. An existing case retains its process
snapshot after a new version is published. Case state is schema-checked on writes.

Cases retain the requested identity, goal, timestamps, pins, stage indexes,
evidence/assumption/action references and timeline. Tenant identity follows the
existing application convention: workspace plus owner is the isolation boundary;
`tenant_id` equals the authenticated workspace, not a caller-selected tenant.

Stages independently support CREATED, READY, RUNNING, WAITING_FOR_INPUT,
WAITING_FOR_EVENT, WAITING_FOR_AUTHORIZATION, COMPLETED,
COMPLETED_PROVISIONALLY, BLOCKED, FAILED and CANCELLED. Case execution status is
COMPLETED for a terminal analytical result; business outcome remains PROVISIONAL
when assumptions or model interpretation were used. Physical status has its own
UNVERIFIED, REPORTED_BY_AUTHENTICATED_SOURCE or CONNECTOR_CONFIRMED value.
Connector confirmation never asserts that a physical inspection or shipment occurred.

Every mutation has a durable scoped request-key receipt. Revision compare-and-swap
protects concurrent commands; transactions preserve command/state atomicity.
Repeated execution commands return current saved state without dispatching again.
Independent eligible stages execute concurrently, up to four per command. False
branch predicates record SKIPPED business outcomes; unavailable predicates wait.
Inputs, outputs and each stage's independent failure/retry history survive restarts.
Execution deadlines, event deadlines and escalation reasons are retained.

## Evidence completion and bindings

Required/optional input schemas bind to `user`, pinned server `config`,
`stage:<instance_id>`, `input` or authenticated `event` values. An `evidence_mapping`
reads actual mapped records from shared preparation. Output bindings also support
`runtime` narrative and verified deterministic `receipt` paths. Dotted object/array
paths are supported; resolved values are checked against the consuming JSON schema.
Earlier outputs therefore do not need to be supplied manually again.

Resolution prefers actual mapped evidence and actual bindings, then deterministic
derivation, configured evidence-grounded inference, then explicit synthetic fallback.
Derivations support copy, sum, difference, concatenation and date differences.
Inference requires actual/derived basis references and an explicit configured
explanation; it is not an unrestricted model-generated claim of fact.

Every value carries ACTUAL, DERIVED, INFERRED or SYNTHETIC provenance, type,
source references, method, nullable confidence, assumptions, timestamp, case scope,
permitted uses and limitations. Actual user/event assertions identify their origin;
ACTUAL does not imply independently confirmed physical truth. Invalid/conflicting
actual values block resolution. Later actual values retain conflicts with previous
assumptions rather than overwriting business source records.

Synthetic values are seeded by case/stage/input and stored per case. Schemas drive
generation; explicit fallback values handle constraints beyond the conservative
generator. Declared stage bindings preserve identifiers and relationships, and
generated dates use the same case timestamp. Policy assumptions have a case-local
version, no commercial authority and no authoritative publication rights. Protected
activity/approval inputs cannot be generated. All non-ACTUAL external-action inputs
are refused; existing Registry and workflow/action approvals still apply to actual
external inputs. The lifecycle has no separate simulation execution mode.

## Agents, tools and recovery

Preparation resolves all declared future capability dependencies before pinning.
When a capability stage becomes eligible, the existing planner/factory creates its
bounded composition and saves a normal workflow draft. It may correctly wait for
normal workflow validation/approval. Use the existing workflow validate/approve
endpoints with their normal envelopes and permissions. A case does not approve
its own workflow or tool action, and no SME-validation step is added.

Resolved case inputs and provenance enter signed, bounded composition metadata;
the master cannot replace specialist inputs. Registry matching, stage tool
allowlists, exact assignments, source pins and existing result/receipt verification
all remain enforced. Model narrative is INFERRED, never silently verified evidence.
The existing `send_email` capability is now catalogued as `mail.send`, and a nonempty
connector `message_id` is required. A fake-transport acceptance runs through normal
workflow and action approvals, binds that actual receipt into a reply wait and
resumes only a correctly correlated reply. No real message was sent. As with other
dynamic external actions, connector registrations must fit the existing no-blind-
retry policy; the test explicitly registers the SMTP fixture with zero retries.
Runtime tool calls/results, checkpoints and outputs are retained on the stage and
actual source packets feed downstream evidence resolution.

An optional trusted Python `on_created` hook attaches case/run state in the same
runtime transaction. Case cancellation and active-run cancellation also share a
transaction. Tests cover cancellation racing run creation with zero orphan runs.
In-flight external operations retain the existing runtime's cancellation limits.

Explicit resume reconciles existing run IDs and completed checkpoints. It uses
`RecoveryService` within the approved retry/budget/source constraints, preserving
unrelated completed work. It never creates replacement invocations for uncertain
writes. Those require existing provider/journal reconciliation before recovery;
the case engine does not implement an automatic remote write reconciler.

## Events and backend interfaces

All routes use the existing authenticated session, origin checks and no-store API
envelopes under `/business-ontology/v1`:

| Method | Path | Purpose |
|---|---|---|
| POST | `/process-definitions` | Publish an immutable process version |
| GET | `/process-definitions/{id}/{version}` | Inspect a scoped version |
| POST | `/cases` | Create a case from a process and goal |
| GET | `/cases/{id}` | Inspect complete durable state |
| POST | `/cases/{id}/{operation}` | prepare, start, advance, resume, input, cancel |
| POST | `/cases/{id}/events` | Submit a correlated external event |
| GET | `/cases/{id}/sections/{section}` | stages, evidence, assumptions, agents, tools, waits, timeline, conflicts, outcomes |

Create accepts `request_key`, `process_definition_id`,
`process_definition_version`, `original_user_goal`, optional `inputs`,
`business_request`, `resources`, package ID/revision and Google connection ID.
Normal commands require `request_key` and `expected_revision`; `input` also accepts
`inputs`. Preparation pins evidence; start/advance lazily prepare executable stage
workflows once their dependencies and inputs are available. Further advances are
explicit bounded commands, including after an event makes a stage ready.

Event bodies contain `request_key`, `event_id`, `event_type`, `source`,
`correlation_keys` and typed `payload`. Waits retain ID, case/stage, source/type,
keys, creation/deadline, status, continuation and retry/escalation policy. Events
must match exactly one wait, and event identity/content is deduplicated. Current
owner write authority and `events.ingest` are required; authorization events also
require `workflow.approve`. The submitting identity is recorded. This endpoint is
an authenticated event command, not a public unsigned provider webhook.

An allowed event timeout may complete analysis provisionally while the real-world
wait remains TIMED_OUT and activity UNVERIFIED. Authorization waits never generate
approval. Late events on completed provisional stages are retained with an explicit
downstream-reassessment conflict; completed conclusions are not silently promoted.

## CLI

`scripts/business_cases.py` supports publish, create, prepare, start, advance,
resume, cancel, input, event and inspect, including all inspection sections.
JSON arguments name local files. Two access paths use the same lifecycle semantics:

```bash
# Isolated diagnostics: the supplied example uses no model or external write tool.
.venv-integrations/bin/python scripts/business_cases.py --database /tmp/cases.sqlite \
  publish --json shared/contracts/examples/business-lifecycle-v1.json

# Configured execution: uses the existing authenticated backend and all normal gates.
.venv-integrations/bin/python scripts/business_cases.py \
  --api-url https://builder.example/api/backend --cookie-file /path/to/session-cookie \
  advance --case-id case_example --json /path/to/command.json
```

The cookie file contains an existing session Cookie header, not newly minted
authority. Remote redirects are refused and non-local HTTP is rejected. Isolated
diagnostics cannot install paid models or live write connectors; configured agent
execution uses the backend access path. The example is illustrative and does not
claim to be an official Simpson policy or a predefined twelve-stage process.

## Verification and limits

Exact commands/results are recorded in
`openspec/changes/persistent-business-lifecycle/verification.md`. Acceptance covers
real application stores, actual mapped evidence fixtures, actual CrewAI with fake
model transports, existing Registry controls and eight separate CLI processes.
No paid model or live external write was used for verification. No frontend file
was changed. Configured live provider quality and live PostgreSQL deployment have
not been tested for this phase.

Processes are bounded to 64 stages, four concurrent stage dispatches and an 8 MB
case document. JSON value schemas must be self-contained; unsupported generation
constraints require an explicit schema-compatible fallback or remain missing.
Source/knowledge corrections or changes to already composed inputs require fresh
reviewed case/composition pins. Server configuration is snapshotted per case;
callers cannot supply that authority through case payloads.

Provider-specific event delivery/polling and ongoing advances must be invoked by
authorized existing infrastructure or explicit backend/CLI commands. No new
background paid-execution daemon, official client policy, arbitrary capability,
SME approval, client onboarding or Phase 5 feature is installed automatically.
