# Next.js security patch

## Why
The user requested remediation of the Next.js build advisory before eventual deployment. Installed Next.js 16.4.0 precedes the October 14 security fixes available in 16.4.1. npm lists 16.4.3 as the latest patch on the existing 16.4 line.

## What Changes
- Pin Next.js to 16.4.3 and update its lockfile dependencies.
- Verify the installed framework is no longer reported by npm audit, build without the warning, and run frontend/desktop/mobile regressions.
- Preserve existing ontology work, shared contracts, configuration, databases and live services.

## Impact
Frontend package metadata and lockfile, verification documentation, and correction of two obsolete metadata-rebuild regression fixtures. No application behavior changes. No application behavior rewrite, major framework migration, database access, deployment or service restart. Other audit findings are assessed and reported separately rather than silently claiming a clean dependency tree.
