# Rethika runtime

This package implements application-owned execution on the existing canonical
workflow, agent, tool, authentication, run/event and API contracts. The accepted
additive `workflow-operations-v2` contract owns release and trigger lifecycle;
all v1 contracts remain unchanged.

## Local development

From `/home/raf/agentic-ai-builder`:

```sh
.venv-integrations/bin/python -m pip install --cache-dir .pip-cache -r requirements-runtime.txt
BUILDER_DEV_AUTH=1 BUILDER_DEV_ROLES=admin BUILDER_RUNTIME_ENABLED=1 .venv-integrations/bin/python -m uvicorn workflow_api.main:app --host 127.0.0.1 --port 8000
```

The runtime is disabled by default. Explicitly enabling it connects existing
execute_workflow/get_run/list_run_events/decide_approval operations. Development
admins then receive workflow.execute; builders/viewers are not elevated.
This is still the upstream local session/SQLite POC, not production authentication.

Default configuration supports deterministic manual execution. Model and connector
calls require trusted server adapters; missing adapters produce stable blocked
runs, never synthetic output. Existing external-write revision publication remains
blocked by Harihar's APPROVAL_SERVICE_REQUIRED gate until the trusted publication
approval boundary is integrated. Runtime gate approval does not fabricate upstream
registry approval evidence or authorize an unpublished draft.

## Server integration

- `RuntimeService(workflow_service, observer=...)` stores run identities, request
  hashes, application trace/correlation references, node/edge state and counters
  in the existing repository-local SQLite database.
- `GraphRunner(runtime, agents=..., connectors=...)` owns DAG execution. Pass fresh
  trusted execution auth to advance, and authorized approver auth to decide.
- `RuntimeWorker(runner, authenticate)` polls queued/resumed/expired-approval runs.
  authenticate(workspace, subject) must resolve current trusted authority, or
  return None. Start/stop this worker in the server lifecycle once configured;
  no identity/scopes are reconstructed from saved runs. It is not auto-started
  by the default development server.
- `CrewExecutor(registry_adapter, OpenAIModelFactory(rates))` uses the accepted
  registered agent definitions and model IDs. rates is an explicit server-owned
  mapping of model ID to input_per_token/output_per_token; do not derive it from
  a workflow or client request. The SDK uses configured OPENAI_API_KEY, disables
  automatic retries and response storage, and receives bounded output/duration
  parameters. Missing supported tokenizer/rates/provider fails closed.
- `SMTPConnector(resolve, allowed_recipients, allowed_hosts)` resolves an opaque
  credential reference only inside the adapter. Configure STARTTLS port 587,
  approved sender/host and exact recipients. Real sends require current registry
  approval evidence and an approved run gate. No credentials are persisted here.
- `OpenTelemetryObserver(tracer)` or `otlp_observer(endpoint, headers)` exports
  committed allowlisted application events. An operator can configure an OTel or
  Langfuse-compatible OTLP endpoint. Call export_traces, or use RuntimeWorker;
  export failure does not grant execution or roll back run evidence.

## Execution configuration and behavior

Optional node.configuration supports input (literal object), input_mapping
(object field to deterministic expression), on_timeout (stop/branch/retry),
timeout_outcome (an explicitly configured edge outcome), error_outcome (explicit
failure branch) and existing presentation ui. Other execution configuration fails
closed; unsupported hierarchy remains blocked by the upstream validator.

Expressions use input/inputs and outputs/nodes objects, dictionary attributes or
subscripts, literal comparisons, membership and boolean operators. No calls,
imports or arbitrary code are permitted. Boolean yes/no branches are supported;
other declared outcomes must be returned explicitly. Ambiguous planner expression
strings and missing outcome mappings remain blocked instead of guessed.

A join waits until all incoming paths are resolved, runs once if at least one is
selected, and propagates skip when all are skipped. Approval rejection and expiry
stop by default, or follow explicitly configured branch/retry policies. Agent
approval requirements apply before model and tool invocation.

Counters are cumulative for workflow and agent: calls, tokens, retries and
estimated cost, plus workflow/agent duration. Every external action consumes the
canonical tool-call budget (also its side-effect ceiling). The model bridge
reserves worst-case usage before every provider request; unused tokens/cost are
not refunded. This conservative strategy may stop sooner than an actual-usage
strategy but never expands declared budgets. Basic email/SSN redaction and
instruction-override detection complement policy/schema checks; they are not a
complete PII or adversarial-prompt detection system.

Each provider invocation commits an intent before calling out. A crash with an
in-flight intent blocks on lease expiry as UNKNOWN_INVOCATION_RESULT. Safe retry
requires an adapter-confirmed pre-effect RetryableInvocation and retry_safe=True;
external-write adapters never automatically retry. SMTP Message-ID is stable
reconciliation metadata, not provider deduplication or proof of delivery. Uncertain
SMTP submission blocks; completed external effects are never claimed reversed.

Registry policy/credentials/quota remain trusted snapshots. The runtime revalidates
exact assignments and tool metadata before calls but does not provide a live
provider quota reservation service. Workers must refresh policy/configuration and
resolve trusted approval evidence. Release automation stores a server-issued
automation identity, but never stores a Registry authorization reference as
authority. After restart, operator-owned Registry configuration is reconstructed
and exact assignments are issued and revalidated again before dispatch.

CrewAI 1.0 is pinned to preserve the upstream OpenAI SDK constraint. Its first-run
trace collection/interactive prompt and raw task replay store are disabled. Our
validated records and allowlisted OTel spans are the observability boundary.

## Published lifecycle and incoming event support

`workflow_api.lifecycle.LifecycleService` persists immutable releases, atomic active
pointers, trigger bindings, receipts, checkpoints, leased jobs, dead letters,
overview sequences and deletion tombstones. Publication registers triggers and
cuts over only after all preparations succeed. It never runs a workflow. Existing
jobs retain their release when a newer revision is published.

Supported incoming sources are deliberately narrow:

- `generic_hmac_webhook` is the real HTTP source. It requires an opaque server-side
  secret reference, HMAC-SHA256 over `timestamp.canonical_json`, and a timestamp no
  more than five minutes old. Workspace routing comes from the binding.
- `fake_push`, `fake_poll`, and `fake_schedule` are deterministic acceptance adapters.
  Polling stores a stable cursor and defaults to a current-state baseline. Schedules
  require an IANA timezone, five-field cron text, and timezone-aware tick instants.

SMTP remains outbound only. GitHub, Google, Gmail/IMAP, Slack, and arbitrary Registry
tools are not incoming sources. The generic webhook does not manage a remote provider
subscription. Provider challenge flows, cron calculation, poll HTTP clients, and a
distributed queue transport remain operator adapter work.

Lifecycle workers lease bounded batches. Expired leases recover after a crash; jobs
move to dead letter after bounded retries and can be explicitly replayed. Delete
blocks dispatch locally, cancels queued jobs and active runs at safe runtime
boundaries, retains audit evidence, and retries cleanup through `reconcile_cleanup`.
Authenticated overview snapshots and sequence-resumable SSE use polling fallback.

## Verification

```sh
.venv-integrations/bin/python -m unittest discover -s tests -v
python3 scripts/validate_contracts.py
python3 scripts/generate_ui_contracts.py --check
openspec validate rethika-runtime-observability --type change --strict --json
```

Tests use explicit offline providers/SMTP transports and trusted test-only registry
fixtures. No real model request, email, event registration or provider trace export
is made by the suite. Actual CrewAI execution and actual OTel SDK spans are tested.

The lifecycle suite covers first publish, activation compensation/conflicts, push,
poll baseline/checkpoints, timezone schedules, signed webhook freshness, duplicate
and self-event rejection, lease recovery, dead-letter replay, restart recovery,
release-pinned republish, overview resume, disablement, deletion and cleanup retry.
The real-source demonstration is authenticated local HTTP using the generic signed
webhook; it makes no external SaaS subscription or external call.
