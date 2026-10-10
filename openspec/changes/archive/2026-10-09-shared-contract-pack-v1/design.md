# Design

## Context

The master blueprint defines four owners and a shared contract gate. The first contract stage must establish the workflow, agent, and tool formats before API and runtime work begins. The project also needs a versioned handoff record so contributors can join at different times without losing upstream decisions or defects.

The contributor protocol is a project-development workflow for Codex and the team. It is not a product feature exposed to end users and does not itself authorize code changes.

## Goals / Non-Goals

**Goals:**

- Define machine-readable v1 contract artifacts for workflows, agents, and tools.
- Keep the contracts independent of React/TanStack UI models and CrewAI internals.
- Give each named contributor a concise, role-specific onboarding briefing.
- Preserve upstream outputs, defects, dependencies, and verification evidence across handoffs.
- Make the next contract stages explicit without implementing them prematurely.

**Non-Goals:**

- Implementing FastAPI routes, authentication, branching, approvals, run states, or runtime execution.
- Adding the UI archive to the project or changing its code.
- Automatically assigning code changes based only on a contributor’s name.
- Treating contributor notes as a substitute for tests or contract validation.

## Decisions

### 1. Contract artifacts are versioned and backend-neutral

Store the durable contract artifacts under:

```text
shared/
└── contracts/
    ├── workflow-schema-v1.json
    ├── agent-contract-v1.json
    ├── tool-contract-v1.json
    └── examples/
```

The JSON contracts describe data shape and validation constraints. They do not contain UI layout rules, database-specific fields, or CrewAI object definitions.

**Alternative considered:** Reuse the existing UI TypeScript models as the canonical contract. Rejected because the UI currently includes demo-only fields and local simulation behavior.

### 2. Contributor handoff is a versioned Markdown record

Store contributor ownership and handoffs under:

```text
docs/
└── contributors/
    ├── ownership.md
    ├── onboarding.md
    └── handoffs/
        ├── suprajha.md
        ├── aravind.md
        ├── harihar.md
        └── rethika.md
```

Each handoff uses this structure:

```text
Contributor
Segment
Status
Completed work
Verification evidence
Changed contracts
Known defects
Unresolved decisions
Dependencies and upstream inputs
Downstream notifications
Next actions
Blockers
```

### 3. Name-based onboarding behavior

When a contributor explicitly identifies themselves, Codex reads the ownership and handoff records and responds with:

1. Their segment and responsibilities.
2. Required inputs and contract versions.
3. Completed upstream work.
4. Known defects and unresolved items.
5. Dependencies and downstream impact.
6. Verification steps and next actions.

The response must distinguish facts recorded in the handoff from assumptions and must not claim a task is complete without evidence.

### 4. Handoff blocking rules

An upstream defect blocks downstream work when it violates a shared contract or makes the downstream input unusable. A cosmetic issue or an independent optional task is recorded as a warning rather than a hard block.

Aravind’s onboarding must show Suprajha’s planner output and schema issues. Harihar’s onboarding must show the accepted workflow and tool contracts. Rethika’s onboarding must show the complete accumulated context from all earlier segments.

### 5. Contract-first implementation boundary

This change ends after the first three contract artifacts and handoff protocol are defined and validated. Later changes will define API payloads, errors, authentication, branching, approvals, run states, and versioning.

## Risks / Trade-offs

- [Handoff notes become stale] → Require verification evidence, contract versions, and an owner/date on every completion record.
- [A name is ambiguous] → Ask the contributor to confirm their identity rather than guessing.
- [Contributor notes hide implementation defects] → Require tests, validation output, or explicit unresolved status for every claimed deliverable.
- [Contracts diverge from the UI] → Treat the contracts as backend-neutral and add explicit mapping tests in the later UI-integration change.
- [People skip the shared gate] → Mark downstream segments blocked until required contract versions are reviewed and recorded.

## Migration Plan

1. Add the v1 contract artifacts and examples.
2. Add ownership and handoff templates for all four contributors.
3. Have Suprajha, Aravind, Harihar, and Rethika review the contract pack.
4. Record accepted contract versions and any blockers.
5. Create the API/error/authentication contract change next.

Rollback is removing or reverting this planning change before implementation; no existing UI or project is modified by this change.
