# Mobile startup asset recovery — 2026-10-18

The reported screenshot showed the workspace's server-rendered skeleton with no
page content. Fresh Chromium and WebKit sessions loaded the live app, including
tests with blocked local storage and malformed draft JSON. Those storage cases
did not reproduce the failure.

Serving the actual `/app` HTML from the pre-Phase-6 rollback build against the
current public origin reproduced the same skeleton in mobile WebKit. Five
referenced JavaScript chunks returned 404, including the app layout and page.
The affected physical phone's cached HTML was not inspected, so this is a
verified deployment defect matching the symptom rather than direct evidence
from that phone.

Restored 213 missing static assets from the available repository-local rollback
builds. All 64 preexisting static files remained byte-for-byte unchanged. Only
the frontend service restarted; the API and worker stayed active. No server
bundle, page HTML, contract, cloud data, credentials or browser drafts changed.
The previous frontend artifact is backed up at
`.local/ui-rollbacks/mobile-startup-assets-20261018/.next`.

The identical old HTML then hydrated successfully in mobile WebKit with no
static failures or page errors. Evidence is in
`.local/mobile-loading/stale-before.json`, `stale-after.json`, and their PNGs.
Fresh desktop Chromium, mobile Chromium and mobile WebKit also passed Overview
content, reload, navigation through More where applicable, Data Intelligence
Questions, and a second reload. All three finished with no page errors, failed
requests, missing static assets or page-wide horizontal overflow; evidence is
`.local/mobile-loading/fresh-after.json`. Tests wait for prefetches before full
reloads: an earlier immediate-reload probe produced WebKit prefetch cancellation
errors while the requested pages still loaded. This is browser-engine testing,
not a claim of direct verification on the user's iPhone.

Future frontend releases must run `scripts/retain_frontend_assets.py` on the
verified replacement `.next` directory with the active `.next` as a source
before activation. This carries retained dependencies forward and rejects
conflicting bytes before copying. The utility is repository-scoped and copies
only `static/`; it does not activate or restart a service. Four regression tests
cover retention, unchanged active assets, repeatability, conflicts between
sources/target, missing sources and symlinks. Pruning retained assets is a
separate deployment decision; this fix does not promise indefinite compatibility
between arbitrary old client code and future API contracts.
