- [x] Add persistent title endpoint and read projections without editing executable revisions.
- [x] Add Rename menu/dialog for server workflows and local drafts.
- [x] Test permissions, persistence, conflict and revision preservation; verify UI and deploy.

User approved minimal edits to existing files after clarifying the initial new-files-only constraint. Title storage uses a namespaced workspace setting and leaves executable revision JSON unchanged. Six backend tests and 28 frontend/API tests passed, plus build, types, lint, contracts, strict OpenSpec and diff checks. Desktop/mobile browser checks cover the actual menu, dialog, mocked rename and persistence after refresh; no real title was changed in browser tests. Live deployed endpoint rejects an empty title and frontend responds HTTP 200. Frontend/backend/worker deployed with frontend rollback build retained.
