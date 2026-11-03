# Next.js security patch verification

Status: fixed and verified locally; not deployed. No live service restart or production dependency installation occurred.

## Dependency change

Installed Next.js 16.4.0 was updated to exact version 16.4.3, the latest npm-listed patch in the existing 16.4 line at verification time. `frontend/package.json` and lockfile are aligned. The lock diff changes only the root Next.js declaration, Next.js, @next/env and its platform-specific @next/swc entries. React, database credentials, configuration and application behavior are unchanged.

Official basis: https://nextjs.org/blog/nextjs-security-update-october-14-2026 identifies 16.4.1 as containing the October security fixes. The installed update includes those fixes.

## Passing verification

- Installed Next.js: 16.4.3.
- `npm audit --json --fetch-retries=0 --fetch-timeout=20000`: Next.js no longer listed; zero critical findings. The command exits 1 because unrelated findings remain. See audit-summary.json.
- `npm run typecheck`: passed.
- `npm run lint`: passed.
- `npm run test -- --run src/features/data-sources src/api/proxy.test.ts src/lib/workspace-auth.test.ts`: 106 passed in 17 files.
- `npm run build`: passed on the first build with the patched dependency, without the Next.js security warning.
- Browser tests for both existing Ontology and new Simpson Business Ontology: four passed, desktop and mobile, against the patched production build with isolated/intercepted fixtures.
- Shared contract validation and strict next-security-patch OpenSpec validation passed. Diff whitespace checks passed.

The initial broader test run found two obsolete GraphBuildFeedback fixtures expecting a removed semantic-generation button. The original component already intentionally hides that button. The tests were corrected to exercise current metadata rebuild calls, queued/ready/failed polling, preserved connection selection and the absence of semantic-inference calls. No product behavior was changed to satisfy the tests.

## Remaining audit findings

The full tree still has 14 unrelated findings: 12 moderate and two high, in Vite and Zod at high severity. Vite's reported fix is a compatible patch; npm proposes a major Zod migration. These were not silently upgraded with the Next.js patch. This verification does not claim the dependency tree is entirely clean or that a live deployment has been patched. The generated build is local; a later deployment must install the updated lockfile and restart the appropriate frontend service.

## Rollback

The package/lock diff is separately reviewable. Rolling back the framework patch would restore a known vulnerable dependency and is not recommended; use the verified patched lockfile for deployment. No application/database rollback is needed for this dependency-only runtime change.
