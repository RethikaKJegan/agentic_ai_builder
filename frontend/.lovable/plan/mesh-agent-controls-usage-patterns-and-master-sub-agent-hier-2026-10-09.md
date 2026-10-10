# MESH — Agent Controls, Usage, Patterns and Master/Sub-Agent Hierarchy

Adds five features inside existing pages (Governance, workflow editor, Agents, Agent inspector). No new sidebar items, no redesign. All runs stay simulated and labelled.

## 1. Governance → "Agent Control" tab
- Overview strip: total / active / paused agents, total runs, estimated spend (from simulated runs), current limits.
- Controls (switches, number inputs, dropdowns): agent execution on/off, max agents per workflow, max runs per day, max estimated spend, max sub-agent depth, max children per agent, allowed tools, blocked models, require approval for sensitive actions (email send, ERP ledger, refunds).
- Organization and workspace columns; workspace can only tighten. Admin-only edits; others see read-only note. Every change goes to the audit log.

## 2. Governance → "Usage" tab
- Four KPI cards: Active Agents, Total Runs, Estimated Cost, Blocked Executions.
- Table: Agent | Workflow | Runs | Estimated Cost | Status | Actions (Pause/Resume, Open). Search, status filter, sortable columns, default sorted by cost so top consumers show first. "Simulated usage" label; empty state when no runs.

## 3. Patterns panel in the workflow editor
- Narrow, collapsible left panel with five draggable patterns: Sequential, Parallel, Conditional, Human Approval, Supervisor.
- Drop on canvas creates connected nodes at the drop point (new agents created, or pick an existing agent in the inspector afterwards). Works with existing move/edit/connect/delete, auto-layout, undo/redo and saving. Keyboard alternative: Enter on a pattern inserts it at canvas centre. Hidden on phone step-list mode (replaced by an "Add pattern" menu).

## 4. Master Agent → Sub-Agent hierarchy (standout)
- "Generate Workflow" now produces a hierarchy: Master Agent at top → child agents → their tools/tasks → final output. Example prompt yields Customer Support Orchestrator with Research, Analysis, Response and Escalation agents.
- New node style: master node larger with blue accent; child nodes show model, purpose, tool count, status and parent; subtle connectors.
- Expand/collapse a child group from the node. Click opens the existing inspector. "Add sub-agent" / remove on agent nodes; nesting blocked beyond depth and child limits with an inline reason.
- Simulated run shows delegation: master hands task to each child, child outputs roll up into the combined result; trace lists parent → child steps.
- Two new sample master-agent workflows seeded (support orchestrator, invoice processing supervisor) without wiping existing demo data.

## 5. Agent-level controls
- "Controls" section in Agent inspector and a status column + quick pause on Agents page: Active/Paused, parent agent / sub-agent (read-only from hierarchy), max execution budget, allowed tools, require approval, usage and recent runs (expandable).
- Pausing a parent stops its children from running through it; the run trace explains which control blocked it.

## Enforcement (one place)
Every run checks, in order: org execution switch → agent paused (or a paused ancestor) → depth/children/agents-per-workflow limits → allowed tools and models → daily run and spend limits → agent budget → approval for sensitive actions. Blocks appear in the trace with a plain explanation and are written to the audit log. Organization → workspace → workflow → agent: lower levels can only be stricter.

## Validation
Unit tests for: policy inheritance cannot loosen limits; paused parent blocks children; depth and child limits; spend and run caps; pattern insertion produces connected nodes; hierarchy generation for the example prompt. Playwright walk of the five acceptance criteria, plus existing tests and the earlier demo flow still passing.

## Technical details
- `src/domain/types.ts`: optional `parentAgentId`, `paused`, `budgetUsd`, `requireApproval`, `allowedTools` on Agent; optional `parentId`, `collapsed`, `role: "master"|"sub"` on node data; `RunStep.delegatedBy`. All optional so persisted data still loads; store version bump with a migrate that adds defaults and seeds samples once.
- `src/domain/governance.ts`: `AgentControls` (org + workspace) and `resolveControls()` (min of numeric limits, intersection of allow-lists, union of blocks); `checkExecution(agent, ancestors, controls, usage)` returns a reason or null.
- `src/domain/hierarchy.ts` (new, pure): `planHierarchy(prompt)` deterministic keyword→role mapping; `addSubAgent`, `removeSubAgent`, `descendants`, `depthOf`, `visibleNodes` (collapse).
- `src/domain/patterns.ts` (new, pure): `insertPattern(kind, at)` returns nodes/edges.
- `src/domain/simulator.ts`: call `checkExecution` per agent step; record delegation; pass usage totals.
- `src/domain/store.ts`: `controls` state, `setControls`, `toggleAgentPause`, hierarchy actions; all logged to audit.
- UI: `app.governance.tsx` two new tabs; `features/builder/PatternsPanel.tsx` + drop handler in `Builder.tsx`; master/sub variants in `MeshNode.tsx`; controls section in `AgentInspector.tsx`; status/pause in `app.agents.tsx`.
- `AGENTS.md`: note hierarchy/pattern modules and single enforcement point.
