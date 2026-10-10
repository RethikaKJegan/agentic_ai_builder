# Frontend contributor instructions

Follow the repository root `../AGENTS.md` and Harihar's OpenSpec change.

- `incoming/pixel-perfect-match-latest.zip` is the source archive; `frontend/` is the active Next.js App Router baseline. The user explicitly authorized replacing TanStack Start and removing demo/nonworking controls.
- Preserve the supplied Mesh visual design and working local editing tools.
- Filesystem pages/layouts in `src/app/` own routing. Screen components live in `src/screens/`. `src/lib/navigation.tsx` adapts view-model destinations to Next Link/router hooks; do not add TanStack Router or Start.
- Local draft state goes through `src/domain/store.ts` and uses `mesh-local-drafts-v1`. Do not load old demo records or erase old browser storage.
- Canvas and WebGL features load on the client; preserve their loading and capability fallbacks.
- Keep graph editing, hierarchy, patterns and template logic in the domain layer.
- Do not restore simulated generation, connector setup, publishing, runs, approvals, role/reset controls, or pretend knowledge ingestion. Their APIs remain pending in Harihar's tasks.
- UI models, local role flags, catalogs and policy controls are draft/presentation data. `../shared/contracts/` is authoritative for backend validation and execution.
- Legacy pure simulator tests are retained as archive regression coverage; no simulator is wired to product actions.
- Validate build, types, lint, domain tests and meaningful desktop/mobile browser flows before claiming baseline completion. Backend integration requires its own contract and consumer acceptance evidence.
