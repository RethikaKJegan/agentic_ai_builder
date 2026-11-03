- [x] 1a. Move reusable profiling/drift helpers and profile storage into shared database services; retire old UI screens, public API routes and new legacy-selection creation.
- [ ] 1b. Remove the remaining internal legacy library/initialization and obsolete tooling after resolving automatic-review restrictions on runtime replacement and deletion. Historical compatibility is preserved in the meantime.
- [x] 2. Add source metadata, profile jobs, revision diffs and impact inspection to Business Ontology for both configured sources.
- [x] 3. Add bounded, authorized record browsing with source identity/revision provenance and post-read revalidation.
- [x] 4. Verify permissions, drift, profile lifecycle, retired public routes, frontend behavior and existing workflow regressions without paid model calls; build and deploy.

Explicit user approval persists. Public-workspace retirement is deployed. Full internal library removal remains blocked by automatic action review; do not describe that cleanup as complete or ask for the same user approval again. See verification.md and retirement-review.md.
