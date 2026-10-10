# Design

## Context

The supplied `incoming/pixel-perfect-match-latest.zip` is a TanStack Start/React/TypeScript/Tailwind application with a workflow canvas, agent/tool views, run history, and local simulation. Its active source in `frontend/` has been migrated to Next.js App Router with demo actions removed. The integration must connect it to versioned APIs without replacing its visual structure.

## Goals / Non-Goals

**Goals:**

- Introduce a typed API/client boundary around the existing screens and state model.
- Map server payloads into existing visual components while preserving the canonical workflow shape at the boundary.
- Make errors, approvals, versioning, and run states observable and honest.

**Non-Goals:**

- Rebuild or redesign the Lovable UI.
- Implement backend planning, registry authorization, connector execution, or observability.
- Treat local simulation as production execution.

## Decisions

1. **Adapter at the boundary:** API adapters translate transport payloads into the UI's existing view models; the canonical workflow remains authoritative for requests and persistence.
2. **Server state replaces local persistence incrementally:** retain local state only for explicitly labeled draft/preview behavior while workflow lifecycle operations use the backend.
3. **Capability-driven controls:** visibility and enabled states derive from authorization and workflow status, not hard-coded assumptions.
4. **Idempotent mutations:** save, publish, approval, and execution requests carry accepted idempotency/correlation metadata and reconcile repeated responses safely.

## Risks / Trade-offs

- **[Risk] Existing local view models diverge from contracts.** → Add mapping tests and reject unsupported fields rather than silently dropping behavior.
- **[Risk] Backend latency changes the interaction feel.** → Preserve optimistic visual affordances only where rollback/error states are explicit.
- **[Risk] A demo connector is mistaken for real execution.** → Display configuration/simulation labels and server-backed run status separately.

## Migration Plan

1. Integrate the supplied UI source as the frontend baseline.
2. Add API client types and read-only workflow loading first.
3. Add save, validation, approval, publish, execution, and history mutations in contract order.
4. Remove or isolate localStorage behavior as each server-backed flow becomes available.
5. Roll back by disabling API mutations while retaining the UI and clearly labeled preview mode.

## Updated UI baseline — 2026-10-10

The user supplied `incoming/pixel-perfect-match-latest.zip` and authorized migration to Next.js before backend integration. Use `frontend/` as the active baseline; retain `agentt.zip` only as historical input. Preserve the Mesh design, cinematic landing, canvas, and local editing tools. Remove simulated generation, connector setup, knowledge uploads, run/approval/publish actions and demo role/reset controls. Backend-dependent pages show truthful empty/unconnected states. Browser draft storage has its own key and is not canonical workflow persistence. Keep all backend integration and downstream acceptance tasks open until separately verified.

## Local API implementation decisions

The user authorized proceeding with a server-configured development identity when no existing login system was identified. Use the planned FastAPI layer and a same-origin Next.js proxy. Development authentication is opt-in, restricted to loopback hosts, and uses an HttpOnly session cookie. Roles and permissions come from server configuration, never request payloads. Default to a builder without approval, publishing or execution grants. Production authentication remains a replaceable server boundary.

Persist canonical workflow revisions and mutation idempotency records transactionally in a repository-local SQLite database for the local POC. PostgreSQL remains the production target; this delivery does not claim production database integration. Keep remote workflows out of browser draft storage. Preserve canonical sections and represent canvas presentation in optional node layout/configuration metadata; unsupported execution semantics must fail validation rather than disappear.

Wrap the existing planner and registry services without changing their implementation. Normalize legacy planner errors into `data.error` and expose only safe errors. Registry discovery is not an executable assignment. Reject client-created assignments and elevated revision statuses; publication requires exact server validation and approval plus current authorized assignments. The trusted registry adapter loads explicit operator configuration through Aravind's public registration methods, verifies embedded agent definitions, and evaluates exact revision/schema/destination bindings through assignment/revalidation methods. Missing configuration, denied tools and pending approvals remain blocked. UI responses expose only safe assignment-state projections; executable references stay at a trusted server-only boundary for Rethika.

Do not create runtime, connector or runtime-approval behavior. Expose explicit unavailable errors for those operations and hide their mutations when the service is absent. Client adapters and consumer tests may use injected contract fixtures, but product data must never use those fixtures. Tasks requiring real runtime/approval integration and Rethika's review remain open.
