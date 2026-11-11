# Hosted public research availability — 11 November 2026

Deployed to https://praxi.bellcorpstudio.com/ as
`public-research-20261111-4e065dc5d242` at 08:30:01 UTC.

The shared opt-in tenant path now registers enabled public-search and page-reading
definitions matching its installed connectors. Intent guidance routes public research
through composed workflows rather than the workspace-knowledge-only path. Simpsons retains its existing
opt-in; Subway now has `BUILDER_CLIENT_WEB_ENABLED=1`. No tenant name is embedded
in the fix. Permission and privacy checks remain active.

Only the tenant backends and shared worker were restarted after the idle check.
Tenant SQLite backups passed quick_check. Source/configuration rollback is retained;
no database restore, frontend change, email or spreadsheet write was performed.
All five services are active; public account scope and health checks passed.

Refresh and generate a new proposal to include actual search tools. Previously
approved workflows were not modified. See [verification](verification.md).
