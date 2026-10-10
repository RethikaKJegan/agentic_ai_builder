# Proposal

## Why

The project needs one shared blueprint before four people begin implementation. Without a common contract, the Lovable-derived UI, planner backend, Tool Registry, and CrewAI runtime could develop incompatible workflow formats, agent permissions, and API assumptions.

This change establishes the domain-agnostic Agentic AI Builder as a separate platform and defines the behavioral contracts, ownership boundaries, and implementation sequence that Codex and the four contributors will follow.

## What Changes

- Define the Agentic AI Builder as a generic platform for converting natural-language business requirements into validated, editable, executable multi-agent workflows.
- Define a canonical, versioned workflow specification shared by the planner, FastAPI backend, Mesh/Next.js UI, validator, and CrewAI runtime.
- Define the runtime agent contract, including role, goal, instructions, model, inputs, outputs, capabilities, tools, permissions, limits, retries, timeouts, and approval requirements.
- Define a capability-based Tool Registry with least-privilege tool assignment and connector authorization.
- Define the separation between AI agents, deterministic actions, conditions, human approvals, inputs, and outputs.
- Define four balanced implementation segments with named ownership: Suprajha, Aravind, Harihar, and Rethika.
- Define the initial POC connector priorities and explicit exclusions.
- Define API, persistence, validation, security, execution, and observability requirements at blueprint level.
- Preserve the strict boundary that this project is isolated under `/home/raf/agentic-ai-builder` and does not modify Praxi or the fire-detection project.
- Treat the supplied Lovable UI archive as the existing visual baseline rather than a UI to rebuild. Preserve its generic workflow-builder experience and connect it to the real backend pipeline.

## Capabilities

### New Capabilities

- `platform-foundation`: Defines the generic product boundary, shared architecture, four-team ownership model, and project isolation rules.
- `agent-contracts`: Defines configurable runtime agent roles, goals, instructions, models, inputs, outputs, permissions, tools, limits, and approvals.
- `workflow-specification`: Defines the canonical versioned workflow payload used as the single source of truth across planning, editing, validation, and execution.
- `tool-registry`: Defines capability-based connector registration, tool selection, authorization, risk, quotas, and least-privilege assignment.
- `workflow-planning`: Defines natural-language requirement interpretation, task decomposition, capability identification, and structured workflow generation.
- `visual-workflow-editor`: Defines generic visual workflow editing using the supplied Mesh interface migrated to Next.js App Router.
- `workflow-execution`: Defines validated CrewAI execution, application-owned control flow, approvals, retries, timeouts, budgets, and side-effect protection.
- `observability-and-operations`: Defines execution records, run identifiers, Langfuse traces, error reporting, and operational visibility.

### Modified Capabilities

None. This is the first capability blueprint for the new project.

## Impact

- Adds OpenSpec planning artifacts under the isolated `agentic-ai-builder` project.
- Establishes future frontend, backend, shared-contract, connector, database, and observability boundaries.
- Integrates the new Mesh/Next.js/React/TypeScript UI in `frontend/` with FastAPI, OpenAI, CrewAI, PostgreSQL, Langfuse, and approved external integrations.
- Requires four implementation streams to coordinate through the canonical workflow and API contracts.
- Removes simulated backend actions from the UI baseline, then replaces local draft state progressively with backend-backed behavior. Unconnected backend controls remain absent until their adapters are implemented.
- Does not modify any existing Praxi or fire-detection files.
