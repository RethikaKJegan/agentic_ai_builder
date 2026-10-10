# Design

## Context

This is a greenfield project in `/home/raf/agentic-ai-builder`. The new `incoming/pixel-perfect-match-latest.zip` supersedes `agentt.zip` as the UI source baseline. Its Mesh interface is migrated from TanStack Start to Next.js App Router in `frontend/`, retaining React, TypeScript, Tailwind, `@xyflow/react`, Zustand, and local draft editing. It includes workflow, agent, approval, integration, run, monitoring, governance, marketplace, knowledge, and settings surfaces. Demo/nonworking backend actions are removed; unconnected pages show their actual state. The backend and runtime must connect to this UI while preserving its design.

The central architectural constraint is one canonical, versioned workflow specification shared by planning, visual editing, validation, and execution. The platform must separate flexible LLM planning from controlled application-owned execution. See `proposal.md` and the capability specifications for the behavioral contracts.

## Goals / Non-Goals

**Goals:**

- Provide a stable contract that four contributors can implement against in parallel.
- Keep planning, editing, validation, execution, and observability separate.
- Represent AI work, deterministic actions, conditions, approvals, inputs, and outputs explicitly.
- Enforce least privilege, bounded execution, approval gates, connector restrictions, and trace privacy.
- Allow the Lovable-derived UI to evolve without coupling the workflow model to a frontend library.
- Start with OpenAI as the model provider while preserving a provider-neutral model configuration.
- Prefer real free-tier or already-authorized connectors for the POC.

**Non-Goals:**

- Building a procurement-only application.
- Replacing the existing Praxi or fire-detection projects.
- Allowing the LLM or CrewAI to invent connectors, permissions, or arbitrary control flow.
- Requiring every planned task to become an AI agent.
- Implementing every external connector before the first end-to-end demonstration.
- Treating Langfuse as an authorization, budgeting, or policy-enforcement layer.

## Decisions

### 1. Separate platform layers

Use the following logical layers:

```text
Mesh/Next.js App Router UI
        ↓ HTTPS/JSON API
FastAPI application layer
        ├── Workflow planner
        ├── Workflow/version service
        ├── Tool Registry and selector
        ├── Validator and policy engine
        ├── Credential references
        ├── Execution manager
        └── Run/approval state
        ↓
CrewAI adapter + application-owned graph runtime
        ↓
Approved connector implementations
        ↓
PostgreSQL + Langfuse/OpenTelemetry
```

The frontend never receives raw credentials, directly runs CrewAI, or generates executable Python. The application layer owns authorization, validation, budgets, and side effects. The existing UI's localStorage/Zustand simulation is replaced progressively by API-backed services through a repository/client boundary.

**Alternative considered:** Put planning and execution directly in the browser UI. Rejected because it would expose server-side credentials and make policy enforcement dependent on browser behavior.

### 2. Canonical workflow specification

Use a JSON-compatible schema owned by the shared-contract workstream. At blueprint level it contains:

```json
{
  "workflow_id": "string",
  "version": 1,
  "name": "string",
  "description": "string",
  "status": "draft|validated|approved|archived",
  "inputs": [],
  "outputs": [],
  "stakeholders": [],
  "agents": [],
  "tools": [],
  "nodes": [],
  "edges": [],
  "conditions": [],
  "approval_gates": [],
  "execution_policy": {},
  "error_policy": {},
  "metadata": {}
}
```

Each node has a stable ID, type, configuration, and optional layout metadata. Layout metadata is never used for execution order. Edges and explicit conditions determine reachability.

**Alternative considered:** Store separate React Flow and CrewAI representations. Rejected because they would drift and make validation incomplete.

### 3. Agent contract

Agent configuration is data, not hard-coded Python. Each agent record contains identity, role, goal, instructions, provider/model configuration, input/output schemas, required capabilities, selected tools, permissions, limits, retry/timeout policies, and approval requirements.

The runtime constructs a restricted tool set from the validated selected-tool references. The planner may request capabilities, but it cannot directly choose arbitrary API endpoints or bypass registry policy.

### 4. Capability-based Tool Registry

Registry entries map a business capability to one or more approved connector implementations. The registry stores schemas and policy metadata, while credentials remain in a server-side secret mechanism and are referenced by ID.

Initial priority is:

1. Gmail-compatible SMTP or Brevo SMTP
2. Google Sheets
3. Google Drive and Docs
4. Google Calendar
5. GitHub REST API
6. Slack webhook
7. Open-Meteo
8. Approved HTTP/webhook connector

Twilio, paid SMS, phone calls, paid Maps, mandatory paid CRM/ERP systems, and unrestricted arbitrary HTTP execution are out of scope for the POC.

### 5. Planner and validator boundary

The planner receives natural-language requirements and returns structured workflow data through schema-constrained model output. The validator then checks references, types, graph reachability, permissions, conditions, approval gates, budgets, and connector availability.

The planner is advisory. A workflow cannot execute merely because the model produced it. User review, backend validation, approval, and runtime authorization are separate gates.

### 6. Application-owned control flow around CrewAI

CrewAI will be used to instantiate and run approved agents and tasks, but the application will own graph traversal, branch selection, approval pauses, retries, timeouts, budgets, run state, and external side-effect policy.

**Alternative considered:** Use a single sequential CrewAI crew for all workflows. Rejected because arbitrary branching, approval nodes, retries, and side-effect controls require explicit application state.

### 7. API contract boundary

The shared contract workstream will define exact schemas for at least:

- `POST /workflows/plan`
- `GET /workflows`
- `GET /workflows/{workflow_id}`
- `PUT /workflows/{workflow_id}/versions/{version}`
- `POST /workflows/{workflow_id}/validate`
- `POST /workflows/{workflow_id}/approve`
- `POST /workflows/{workflow_id}/execute`
- `GET /runs/{run_id}`
- `GET /runs/{run_id}/events`
- `GET /tools`
- `GET /agents/capabilities`

The UI consumes these contracts and does not make assumptions about database tables or runtime classes.

### 8. Shared contract gate and four-person workstreams

The canonical workflow schema, agent contract, tool contract, API payloads, error format, authentication and permission rules, branching/approval semantics, run statuses, and versioning rules are a shared prerequisite reviewed by all four owners. They are not a separate person's entire segment.

#### Segment 1: Suprajha — Natural-language planning pipeline

Suprajha owns requirement intake, OpenAI structured planning, task/stakeholder identification, agent-versus-deterministic classification, conditions and approval identification, capability identification, planner errors, and generic planner tests. The output is a schema-valid canonical workflow proposal consumed by the existing UI.

#### Segment 2: Aravind — Agent and Tool Registry

Aravind owns agent capability definitions, agent configuration rules, Tool Registry entries, capability-to-tool matching, connector metadata, permission scopes, credential references, risk/quota/availability checks, approval metadata, least-privilege assignment, and registry tests. The output is an authorized tool set for each validated agent.

#### Segment 3: Harihar — Lovable UI integration and workflow API

Harihar owns migrating the new Mesh baseline to Next.js and connecting it to backend APIs, replacing local browser draft state progressively, workflow loading/saving/versioning, agent and tool panel integration, validation errors, approval/publish actions, run status/history, API client/adapters, and frontend integration tests. Harihar preserves the supplied visual design and removes demo/nonworking actions before backend integration.

#### Segment 4: Rethika — Runtime and observability

Rethika owns CrewAI agent/task creation, application-level graph execution, conditions, approval pauses, retries, timeouts, budgets, connector invocation, run records, Langfuse/OpenTelemetry traces, error reporting, and runtime security tests.

The four segments are pipeline stages: Suprajha plans, Aravind authorizes capabilities, Harihar connects the product experience, and Rethika executes and observes. No owner may change a shared contract silently; contract changes require an OpenSpec change reviewed by all affected owners.

### 9. Project layout

```text
agentic-ai-builder/
├── openspec/
│   ├── config.yaml
│   ├── specs/
│   └── changes/
├── docs/blueprint/
├── frontend/                 # active Mesh/Next.js UI integration target
├── backend/
├── shared/
│   ├── schemas/
│   ├── api-contracts/
│   └── agent-contracts/
├── tests/
└── AGENTS.md
```

The shared contracts are frozen and authoritative. The user authorized importing the new Mesh archive into `frontend/`, migrating it to Next.js and removing demo/nonworking actions before API integration. `agentt.zip` remains historical input; `incoming/mesh-nextjs-final.zip` packages the active source baseline.

### 10. OpenSpec and Codex workflow

OpenSpec artifacts are versioned with this project. Each implementation segment becomes a separate change with proposal, specs, design, and tasks. Codex applies only an approved change and verifies the resulting implementation against its tasks and scenarios.

The master blueprint is planning-only. The next implementation changes should be created only after this blueprint is reviewed and approved.

## Risks / Trade-offs

- [Workflow schema becomes too broad] → Start with a small typed node model and add node types only through reviewed contract changes.
- [Lovable UI diverges from backend behavior] → Make the canonical workflow payload and API contract authoritative; treat UI positions as presentation data.
- [LLM produces unsafe or invalid plans] → Require structured output, backend validation, least-privilege tool selection, review, approval, and runtime revalidation.
- [CrewAI cannot represent an arbitrary graph directly] → Keep graph traversal and execution state in an application-owned orchestration layer.
- [External free-tier APIs change quotas or policies] → Store availability and quota metadata in the Tool Registry and provide mock/test adapters only when clearly labeled.
- [Four contributors create overlapping changes] → Assign directory ownership, require shared-contract review, and integrate through small OpenSpec changes.
- [Sensitive data enters traces] → Redact credentials and protected fields before Langfuse/OpenTelemetry export.
- [Local setup becomes expensive or fragile] → Use Docker Compose for PostgreSQL and self-hosted Langfuse where practical, with documented optional service startup.

## Migration Plan

This is a greenfield project, so there is no production migration. The implementation sequence is:

1. Review and approve this master blueprint.
2. Create the shared contract and foundation change.
3. Implement the canonical workflow schema and API contracts.
4. Implement planner/registry, UI, and runtime changes against those contracts.
5. Add one real connector and one generic demonstration workflow.
6. Run validation, integration, end-to-end, security, and failure-path tests.
7. Archive completed OpenSpec changes and sync the durable specs.

Rollback during POC development is by reverting the relevant project branch/change; no existing project is modified.
