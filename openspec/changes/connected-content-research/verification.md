# Connected content and public research — 7 November 2026

**Scoped fixes active in the dedicated Simpsons backend. Existing spreadsheet
preserved; the original failed execution was not resumed or replayed.**

## Confirmed live failure

Run `run_b162568366da43f5821d2504552edc03` completed its complaint, inspection,
warranty, replacement, history and recurrence reads, comparison/report content,
spreadsheet content and approved spreadsheet creation. `prepare_email_calendar`
then failed `ACTION_CONTENT_UNVERIFIED`. The service log records `unprovided_url`.
The failed model text is not persisted, so its exact URL difference cannot be
reconstructed. Native-string versus JSON-string URL extraction gave identical
sets for these particular saved inputs; JSON escaping is not claimed as the
proven cause of this particular model response. Gmail/calendar actions had not
been reached. Its content action has an immutable one-call limit.

## Implemented changes

- `runtime/action_plans.py`: validate source tokens and URLs on pure content;
  extract URLs recursively from native strings and tolerate sentence punctuation,
  while still rejecting different hosts/paths/queries, omitted required artifact
  URLs and invented citations. Validation covers all output strings. Technical
  error feedback contains only trusted rule metadata, never rejected text.
- `runtime/graph.py`, `shared/llm_feedback.py`: run that content validator inside
  the existing at-most-one model-correction boundary. Each content invocation
  reserves/enforces one actual model turn. Correction still checks live ownership,
  revision, deadline and remaining action/workflow resource limits. No external
  action is retried by this mechanism.
- `planner/provider.py`: newly reviewed content actions may request two calls
  (generation plus at most one correction), within existing Registry ceilings.
  Old plans/runs/budgets are not increased. Enforced token/cost ceilings can still
  prevent correction; no ceiling is bypassed. A regression verifies a one-call
  action stops safely and leaves its completed spreadsheet untouched.
- `runtime/recovery.py`, `workflow_api/composition_presentation.py`: classify
  content validation as invalid model output, including read-only presentation
  of historical failures, instead of misleading tool/retry-read labels.
- `workflow_api/public_research.py`, `workflow_api/live_providers.py`: explicitly
  configured tenant reuse of existing bounded keyless search/public-page tools,
  Registry grants and public HTTPS/SSRF controls. Default off; enabled only through
  the requested server flag. Bound complaint/serial identifiers (including serials
  in prepared evidence), normalized/URL-encoded variants and email addresses are
  rejected before public dispatch. Privacy context is per invocation/tenant.
  This is not universal detection of arbitrary confidential prose or names.

## Exact verification

Counts are per command; overlapping suites and passing subtests are not added.
All automated model/provider tests use controlled transports, not paid providers.

| Command/log | Actual result |
| --- | --- |
| `/tmp/content-research-before.log` | 3 failed, 1 passed, 35 deselected; 5.55s; reproduces prose-link rejection, no correction and stopped flow |
| `/tmp/content-research-focused.log` | Intermediate 3 passed, 1 failed; revealed the fixture's one-call limit rather than authorizing an unbounded repair |
| `/tmp/content-research-correction.log` | 4 passed, 35 deselected; 6.62s; before explicit one-call denial variant added |
| `/tmp/content-research-confirmed.log` | 5 passed, 44 deselected; 10.16s; content correction, one-call denial, one created sheet/one approved controlled send |
| `/tmp/content-research-presentation.log` | 33 passed, zero failures/skips; 55.65s; source projection/privacy/classification |
| `/tmp/content-research-privacy-feedback.log` | 16 passed, zero failures/skips; 1.74s; public research and existing feedback policy |
| `/tmp/content-research-qualified.log` | 149 passed, 1 failed, 18 passing subtests; 135.48s; legacy procurement fixture below |
| `/tmp/content-research-final.log` | 182 passed, 1 failed, zero skips, 18 passing subtests; 206.18s; complete stated affected-module command, not a clean broad suite |

The final broad module list is `tests/test_connected_action_plans.py`,
`tests/test_runtime.py`, `tests/test_public_research.py`, `tests/test_google_tools.py`,
`tests/test_tenant_google.py`, `tests/test_distributed_configuration.py`,
`tests/test_foundation_fault_tolerance.py`, `tests/test_llm_feedback.py`, and
`tests/test_composition_presentation.py`. Commands use the existing
`.venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider`, private
basetemp directories and `PYTHONDONTWRITEBYTECODE=1`.

**Remaining failed case:**
`test_selected_account_flows_through_native_procurement_and_tracking` still
expects synchronous admission in its legacy procurement harness. Experimental
worker driving reached an additional PROJECTIONS coordination mismatch; those
fixture experiments were reverted completely. The direct tests continue to verify
selected-account tokens, refusal of foreign/revoked scopes, controlled Gmail send,
calendar times/approvals and preservation of completed Sheets receipts. The
separate procurement coordinator is not enabled in this Simpsons deployment.
No assertion was weakened, test deleted/skipped, or clean-suite claim made. This
legacy path remains unqualified and prevents a universal production-readiness claim.

## Live read-only tool checks

- One bounded public query, `Simpsons engines official maintenance manual`,
  returned two HTTPS results. No complaint/serial/email was sent. Returned domains
  were manualslib.com; this does not certify manufacturer authority or relevance.
  `evidence/public-search.json`.
- Gmail profile GET: HTTP200 and identity matched the exact selected saved Google
  connection. Primary-calendar events GET with maxResults1: HTTP200. Only response
  status/counts were retained; no message bodies/calendar titles exported. An
  already-valid cached token was used: zero refreshes/credential changes/writes.
  `evidence/google-readonly.json`. These GETs do not prove actual send/create delivery.
- Isolated web-enabled configured startup against a private copy needed zero new,
  changed or removed schema objects, zero network calls and no workers.
  `evidence/startup-check.json`.

## Activation and preserved effects

With zero queued/running tenant work, only `agentic-builder-simpsons.service`
restarted. Only `BUILDER_CLIENT_WEB_ENABLED="1"` was added to its private server
configuration; all other lines/credential values were verified unchanged. No
frontend/operator/Subway restart, database migration, paid call, email send,
calendar creation or workflow replay occurred. Rollback restores the prior flag
if startup fails. `evidence/activation.json`.

Authenticated read-only GETs confirmed26 registered tools, including
`supplier_web_search`, `supplier_read_page`, `extension_mail_send`,
`extension_sheets_create_report`, `extension_calendar_create`; the original sheet
creation remains completed and the old run remains failed. Historical diagnostic
classification now says invalid_model_output. `evidence/live-verification.json`.

Refresh the website to obtain the new catalogue. The safe continuation is a new
reviewed email/calendar plan explicitly reusing the already-created spreadsheet
URL; do not rerun its spreadsheet-creation step. The old one-call execution cannot
silently acquire a second call. Source verification and human approvals remain
mandatory. Live model quality, actual email/event delivery, prior incident audit,
staging/monitoring/backup/scaling and the legacy procurement failure remain
separate acceptance requirements. No production-readiness claim is made.

Contracts, source whitespace and strict scoped OpenSpec pass. SQL inventory drift
passes (1,194 calls,123 literal tables); this inventory is not a migration or proof
of every SQL expression. Canonical workflow/agent/tool contracts are unchanged.
