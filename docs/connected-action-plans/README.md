# Connected action plans — Phase 1 backend

This extension compiles immutable action-instance DAGs through the existing Agentic AI Builder. It does not replace ontology, mapped retrieval, Registry, agent configuration, CrewAI, graph execution, connector journals or persistent cases. It adds no frontend, deployment, adaptive replanning, recurring scheduler or Gmail reply worker.

## Architecture and baseline

Branch audited: `agentic_ai_builder`, commit `13e3e37`; worktree initially clean. The preceding audit passed 230 tests and four subtests. This implementation's additional pre-edit case/research baseline passed 59 tests and failed the four documented research fixture cases; see `openspec/changes/connected-action-plans/verification.md` for exact commands, corrections and final results.

| Concern | Reused implementation | Phase 1 addition |
|---|---|---|
| Structured planning | `planner.provider.OpenAIStructuredOutputProvider` | `plan_actions`, registered capability enum, exact action shape and one bounded provider request |
| Business evidence | `SharedBusinessPreparation`, mapped retrieval/coverage/version pins | Mixed goals prepare the selected registered reads using existing canonical questions; no business workflow template |
| Composition/agents | `BusinessComposition`, `AgentConfigurationFactory`, existing composition table | `prepare_actions`, distinct action configurations, immutable plan and binding context |
| Execution | `GraphRunner`, `CrewExecutor`, Registry assignments | Fixed DAG agent/tool nodes may alternate; typed input resolution and verified action checkpoints |
| Approvals/effects | Existing workflow publication approvals, action digests, connector journals | Every write has its own gate and complete resolved payload; changed inputs invalidate approval |
| Memory/recovery | `ExperienceMemory`, `RecoveryService`, existing run/checkpoint storage | Verified hints reach the provider; explicit safe retries retain completed actions; affected writes require reconciliation |
| Cases | `BusinessCases`, existing CAS/command receipts | Attach plan to an idle prepared stage, pin client/tools/capabilities/inputs and persist action state with the case |

`workflow_api/action_plans.py`, `workflow_api/action_bindings.py` and `runtime/action_plans.py` are compiler/validation hooks, not another executor or scheduler. Old compositions retain their old compilation. Frozen workflow, process and case schemas are unchanged.

## Contract and plan creation

Canonical contract: `shared/contracts/orchestration-plan-v1.json`. An executed controlled example is saved under `shared/contracts/examples/orchestration-plan-v1.json`.

A plan has a unique ID, revision 1, workspace/owner/client scope, original goal, account/resource references, bounded execution constraints and optional deadline/timezone, completion action IDs, missing inputs, provenance references, fingerprint and up to sixteen uniquely named actions. Each action declares its registered capability, dependencies, expected output schema, typed bindings, evidence references, content instructions, exact-payload approvals, optional condition and bounded budgets. The backend supplies scope, IDs, fingerprints and exact registered output schemas. Model proposals cannot install schemas or permissions.

Two Gmail sends are two action IDs, configurations, effect identities, approval gates and receipts. No capability-keyed deduplication is used on this path. Conditions are typed boolean comparisons; no expression strings or code are accepted. Required actions cannot depend on an optional result. Missing required data blocks rather than inventing defaults.

Model planning receives currently configured, policy-eligible registered tool contracts, binding context, minimum tool timeouts and compatible verified experience hints. The backend then rejects unknown capabilities/actions/fields, cycles, incompatible types, duplicate/overlapping bindings, unsupported effects, approval assumptions, unauthorized selected accounts and unbounded budgets. Actual Registry permissions, account consent and destination restrictions are checked again at dispatch.

Use the existing operation with an explicit opt-in context:

```json
{
  "operation": "plan_workflow",
  "request_id": "connected_request_001",
  "idempotency_key": "connected_request_001",
  "payload": {
    "objective": "Investigate the complaint, create a Sheet of findings and email the assigned engineer its link.",
    "context": {
      "planning_mode": "connected_actions",
      "client_id": "configured_client",
      "preparation_id": "<owned saved preparation ID>",
      "google_connection_id": "<owned selected account ID>",
      "user_values": {
        "recipient": "<explicit authorized recipient>",
        "project": "complaint_report",
        "creation": "findings_v1",
        "title": "Complaint findings",
        "task": "complaints"
      }
    }
  }
}
```

This envelope is illustrative; placeholders must be replaced by actual owned resources. The model supplies the action proposal. The response contains the validated plan, composition ID and normal workflow draft. Draft creation does not execute or approve anything. Trusted legacy server-bound connector accounts remain supported when no selected-account override is supplied; an account ID is never invented by the model.

An operator may instead submit an explicit proposal for deterministic testing/review to `BusinessComposition.prepare_actions`. Its `action_plan` object contains only `actions`, `completion_criteria` and `missing_inputs`; scope and expected output schemas remain backend-owned.

## Bindings and authority

Binding objects use `kind`, `target` and `path`, plus either `key` or `action_id`:

```json
{
  "kind": "receipt",
  "target": ["artifact_url"],
  "action_id": "sheet",
  "path": ["spreadsheet_url"]
}
```

| Kind | Source and boundary |
|---|---|
| `literal` | An explicitly supplied `user_values` key; cannot contain a model-invented literal |
| `context` | Backend-validated preparation references/pins |
| `evidence` | Pinned record/mapping observations; identity use needs an operator-owned mapping/path rule |
| `configuration` | Operator-owned case configuration `action_values`; never request/model configuration |
| `output` | Completed declared dependency's schema-valid structured output |
| `generated` | A completed `content.prepare` result; usable as content, never resource or approval authority |
| `receipt` | A completed verified connector result; resource identity paths are restricted to provider identifiers/URLs |

Paths name declared object properties or bounded array indices. Targets name declared input properties. No `eval`, Python expressions, methods, arbitrary attributes or undeclared traversal is used. Source references are action-specific; there is no “latest tool result.” Runtime requires dependency completion and validates the fully resolved input against the registered schema immediately before invocation.

The generic `content.prepare` capability accepts structured `data`, optional verified `artifact_url`, instructions and explicit source references. Its schema supports findings, summaries, subject/body, title/description, tab headers/rows and follow-up questions, with source references and assumptions. A real registered specialist executes through CrewAI. Output validation rejects invented citation references and new artifact/source URLs in email/summary text; a supplied Sheet URL must be retained. This is structural/provenance verification, not a guarantee that an LLM's free-text interpretation is factually correct.

Generated subject/body, report rows and event descriptions may be sent to approved resources. Recipients, calendar IDs, event times, existing destinations, external identifiers and business approvals cannot be generated-content bindings. Fresh connector restrictions still apply to explicit user inputs. An actual creation receipt may establish the new spreadsheet's ID and URL; returned ID/URL mismatches fail verification. Spreadsheet `/edit` URLs are accepted when their ID matches exactly.

Action records retain input field provenance/authority classifications, source references, ACTUAL/DERIVED/INFERRED/SYNTHETIC distinctions, generated assumptions, payload/output fingerprints, agent results, approvals, receipts, effect state, errors and retry decisions. Scenario evidence remains synthetic. Connector confirmation proves a provider operation, not business authorization, physical inspection, shipment, root cause or effectiveness.

## Tools and safeguards

No duplicate Google integration was created.

| Provider | Registered support reused |
|---|---|
| Gmail | Search, read message/thread, attachment read, account profile, structured composition, draft, send and reply |
| Sheets | Read, discover, create empty/structured report, add tabs, authorized record updates/upserts |
| Calendar | Discover/read, create, update, cancel/delete events; these are Calendar events, not Google Tasks |
| Research | Existing Brave/DDGS search and public-page reader, structured URLs/snippets/content hashes |

Availability depends on actual installed Registry tools, configured connectors, current scopes, consent, quotas and destination policy. Calendar guest invitations remain unsupported by the existing adapter; `sendUpdates=none` is preserved. Calendar IDs and times must be explicit; existing local date/time validation is reused. A newly created report uses the existing atomic report-creation adapter. Later updates still need the existing authorized write-target policy; a model cannot grant itself write access from a URL.

Research fetches retain the existing HTTPS/public-IP validation, DNS pinning, redirect revalidation, time/request/response limits and script/style stripping. Page text is untrusted data, not agent instructions. Controlled research tests replace provider transport only; existing SSRF tests exercise the actual guard code.

Each external action retains an exact Registry assignment, current account and payload validation, a run approval over the resolved action, a stable `run_id:action_id` effect key and the existing connector journal. A missing/invalid write receipt or transport uncertainty is recorded as `ACTION_EFFECT_UNVERIFIED`, retaining the original verification code and requiring reconciliation. There is no automatic write retry.

## Backend API and cases

Existing session, origin, permission and owner/workspace checks wrap:

- `POST /business-ontology/v1/action-plans`: prepare a scoped composition/plan.
- `GET /business-ontology/v1/action-plans/{composition_id}`: inspect the owned immutable composition/plan.
- `GET /business-ontology/v1/action-plans/{composition_id}/runs/{run_id}`: inspect its matching persisted execution.
- `POST /business-ontology/v1/cases/{case_id}/action-plan`: attach to an idle prepared stage using `request_key`, `expected_revision`, `stage_instance_id` and `plan_request`.

Case attachment requires the existing pinned capability set, tool allowlist, side-effect ceiling, client, preparation, account and input pins. It does not replace the process definition. Cases execute with normal start/advance/drive commands and workflow/action approvals. The action states and receipts persist inside the existing stage/runtime records; no parallel case database or new queue is introduced.

Restart reuses completed actions and exact command/run keys. Explicit read/content recovery is bounded by reviewed per-action/plan retry/call/time allowances and revalidates current source/Registry authority. Unaffected checkpoints survive. If changed dependencies affect a completed write, or a write result is uncertain, recovery refuses replay and requires reconciliation. Plan revisions remain fixed; recovery is not adaptive replanning.

## Executed evidence

`execution-trace.json` contains the actual controlled plan, persisted run and runtime events for complaint evidence → actual CrewAI findings → registered Sheet creation → verified URL → actual CrewAI email preparation → approved registered Gmail send. It includes every action's inputs, outputs, provenance, approvals and receipt state. `case-trace.json` includes the attached persistent case, composition and run from a separate controlled execution.

The tests reopen storage/runtime between actions, assert one Sheet creation and one send, and verify case reopening, repeated Gmail actions, invalid bindings/receipts, authority, changed approval payloads, revocation, Calendar input validation, research provenance, optional skips and safe recovery. Final verification: **493 tests and 38 subtests passed**, zero final failures, plus shared contract/example validation, strict OpenSpec and diff checks. Exact commands/results and artifact hashes are in the OpenSpec verification record.

All external transports/models are controlled fixtures. These artifacts are execution evidence for the local backend stack, not live Gmail, Sheets, Calendar, public-web or model-quality qualification. No live external write or deployment occurred.

## Remaining phases

Phase 2 adaptive plan revision/replanning is excluded. Phase 3 background scheduling, recurring execution and Gmail reply workers are excluded. Frontend integration is excluded. Actual target-account readiness and live model/provider quality require a separately authorized diagnostic/acceptance session; no connection or business authority is inferred from these fixtures.
