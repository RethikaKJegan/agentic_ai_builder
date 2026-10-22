# Existing Semantic Intelligence canvas — 22 October 2026

The Data Intelligence Semantic Intelligence view is updated in place; no new tab, endpoint, backend graph or shared contract was introduced.

Identifier-only concepts resolve to an existing dataset entity only when every source has an unambiguous single-column primary/foreign key to that entity (or MongoDB's own _id). A similar field name is insufficient. Unresolved field concepts retain their own identity and connect by their actual owning dataset. All original source mappings remain inspectable.

Business predicates continue to come from the existing semantic API. The exact existing phrase “is supplied by” renders in the equivalent inverse direction as “supplies”; the original relationship ID and stored direction remain authoritative for review. Unresolved/stale meaning uses a conservative structural label and retains its review status. No new business relationship is inferred by this frontend change.

Disconnected business components connect through their actual connection and current-workspace membership. Slate links and rectangular source nodes distinguish this provenance from blue semantic relationships. Membership/ownership links have metadata evidence and no business-review approval control. They never authorize joins or enter planner source retrieval. Search and connection filters rebuild membership using only visible/scoped mappings. All entities are rendered rather than silently cutting the list at 80.

A deterministic compact layout accounts for both entity bodies and relationship labels, with collision separation, wrapped labels and full-width initial canvas. Pan/zoom, keyboard inspection and existing relationship reviews remain available.

Current metadata verification: 44 original concepts; 15 identifier-only concepts resolved into their existing entities; 29 entities plus 3 source nodes; 42 existing relationships plus 5 source links; zero isolated nodes and one connected component. API response input remains unchanged.

Validation: 22 focused domain/UI tests, TypeScript, ESLint, production build, shared contracts and strict scoped OpenSpec passed. Production desktop/mobile browser checks passed both before activation with isolated captured metadata and after activation against the live HTTPS site. They verify connectivity, source evidence, relationship evidence, filters/search, overflow and no backend mutation requests. The before/after live API comparison confirms unchanged backend graph data, workflow v3 source bindings/nodes/approval gates, refresh settings and connection IDs. Only the frontend restarted; backend and worker remained running. No external tool actions, source database writes or graph/mapping reviews were performed.

Private evidence: .local/semantic-connected-canvas/. Previous frontend build: .local/ui-rollbacks/semantic-connected-canvas-20261022/previous.next.
