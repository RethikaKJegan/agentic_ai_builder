# MESH — Implementation Plan (Phase 1 first)

The brief asks for a plan first, then phased delivery. This plan covers the whole system briefly and details Phase 1, which is what gets built on approval.

## Visual design system
- White-first: background #FFFFFF, canvas #F8FAFC, navy text #0F172A, slate #64748B, borders #E2E8F0 / #DBEAFE.
- Blue identity: #2563EB primary, #1D4ED8 hover, #60A5FA accent, #EFF6FF selected surfaces. Green/amber/red reserved for status.
- Space Grotesk (display, editorial scale) + Inter (app UI). 8px spacing, 180–280ms transitions, spring motion, full reduced-motion support.
- All values as oklch semantic tokens in styles.css; shadcn primitives restyled (buttons, tabs, inputs, badges, panels).

## Information architecture
- Public: `/` landing (Product, How it works, Marketplace preview, Governance as anchored narrative sections), CTA to workspace.
- Workspace (`/app/*`): Overview, Workflows, Workflow builder (`/app/workflows/$id`), Agents. Later phases add Marketplace, Runs, Monitoring, Integrations, Knowledge, Governance, Settings — sidebar only lists implemented items.
- Shell: collapsible grouped sidebar, top bar (workspace switcher, breadcrumbs, search, Cmd/Ctrl+K command palette, notifications, user menu, demo role badge), persistent "Create Workflow".

## Domain & state
- Typed models: Organization, Workspace, Member, Agent, Workflow, WorkflowVersion, Node, Edge, Run, RunStep, Policy, Approval, AuditEvent, Connector, KnowledgeSource, MarketplaceAsset — stable IDs, nodes reference agents by ID.
- Single Zustand store persisted to localStorage, accessed only through a repository/service layer so it can be swapped for Lovable Cloud later. Seeded demo data.
- Simulation engine: deterministic template generator (4 scenarios + generic fallback), command parser for composer edits, run simulator stepping through the graph (completion, approval pause, rejected, policy block, tool failure). Everything labeled "Simulated".

## Phase 1 — Foundation & signature journey (build now)
1. Design tokens, fonts, motion primitives.
2. Cinematic landing: full-viewport hero with bespoke canvas/SVG node network resolving into a workflow graph; 6 scroll narrative sections with real product mock renders; final CTA. No fake testimonials/stats.
3. Workspace shell + command palette.
4. Overview: editorial greeting, large composer, 4 starter examples, recent workflows, compact health, recent activity.
5. Workflow builder (@xyflow/react): toolbar (name, status, save indicator, undo/redo, Test, Publish), 7 custom node types, animated blue edges, auto-layout (dagre), fit view, add/delete/connect/drag/rename, bottom AI composer ("Add human approval before sending emails" etc.), right inspector.
6. Agent inspector tabs General | Intelligence | Tools | Knowledge | Safety; model switcher (OpenAI/Anthropic/Google, capability tags, cost tier, demo-only labels).
7. Test panel: input, live node-by-node animation, latency/tokens/cost, guardrail decisions, approval pause with Approve/Reject inline, trace.
8. Publish creates a version; minimal Workflows list and Agents list so nothing dead-ends.
9. End-to-end investor demo steps 1–13 working on shared state (step 14 monitoring lands in Phase 3; a run summary shows meanwhile).

## Later phases
- Phase 2: Agent library page, Marketplace (12 seeded assets, install creates real workflows/agents), Integrations (demo connector states), Knowledge library.
- Phase 3: Governance (Policies with inheritance + effective view, Approvals inbox tied to paused runs, Audit), Admin settings, demo role switcher enforcing permissions, Runs history, Monitoring (Recharts from run records).
- Phase 4: Polish, responsive/mobile list-inspector mode, keyboard shortcuts, QA of full demo.

## Technical details
- Packages: @xyflow/react, motion, zustand, dagre, recharts (Phase 3), cmdk (existing shadcn command).
- Feature folders: `src/features/{landing,shell,overview,builder,agents,simulation}`, `src/domain` (types, seeds, repository).
- Builder is client-only (ClientOnly + lazy import) to avoid SSR issues.
- Each route gets its own head() metadata. Vitest tests for generator, command parser, and run simulator rules (approval pause/resume, policy block).
