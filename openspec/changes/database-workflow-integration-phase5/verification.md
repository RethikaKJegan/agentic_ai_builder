# Phase 5 verification — 18 October 2026

Original-plan database workflow integration is implemented and activated. See
`docs/database-workflow-integration-phase5.md` for supported scope and manual
acceptance. The implementation verification below predates activation; the rollout
evidence is recorded separately at the end. No live provider demonstration is claimed.

## Backend evidence

- `scripts/verify_database_workflows.py`: 440 passed, no skips, 40 subtests passed
  in 329.27 seconds. Disposable PostgreSQL 16/MongoDB replica sets; planner,
  Registry, runtime/delegation, existing Google/Sheets, graph/query/job regressions.
  Log: `.local/phase5-workflow/backend.log`. Existing deprecation warnings remain.
- After final atomic workflow-origin/console-execution hardening, reran the complete
  21-test Phase 5 file, 30 native CRUD tests and three lightweight HTTP consumers:
  54 passed without skips in 92.17 seconds. These overlap the broad run; counts
  must not be added. A final Google-composition fixture refresh also passed.
- Native workflows exercised PostgreSQL/MongoDB read/create/update/delete, actual
  before-image conflicts, policy/authority/metadata revocation, expiry, rejection,
  cross-run operation substitution and lost commit acknowledgement without replay.
- A validated cross-source query used a dedicated explicitly reviewed test link,
  read both engines and checked complete join evidence. It does not claim the
  relationship was automatically inferred or review proved runtime cardinality.
- A master delegated real reads/preparation to a stable specialist, returned the
  actual operation ID, paused for review and committed through the fixed graph
  node. Native writes remained absent before approval. Delegated model decisions
  were explicit offline fixtures, not a live model acceptance run.
- A database update composed with a separately approved Google Sheets action using
  the real Registry/runtime boundary and an offline Google transport. Existing
  Calendar/Gmail adapter tests and registered/configured tool visibility were
  included. No real Google action was performed.
- Workflow origins are committed with preparation in the same transaction.
  Standalone Operations execute is denied for linked operations; the UI returns
  the reviewer to the originating Execution view. Normal standalone CRUD remains
  compatible. Recovery remains separately reviewed, not automatic rollback.

## Frontend evidence and known baseline failures

- Final full suite: 279 passed and seven failed (286 total). The seven failures
  reproduce against the saved pre-Phase-5 source snapshot with identical failing
  test identities. They are not represented as a clean full-suite pass.
- Baseline failures: automatic-source input expectation; integration navigation
  mock missing useNavigate; duplicate planner-error alert expectation; lifecycle
  visibility expectation; two missing ResizeObserver hierarchy test cases; old
  whole-project Agent communication button expectation.
- Evidence: `.local/phase5-workflow/frontend-final.json`, `frontend-baseline.json`,
  `frontend.log`. Baseline rerun used `.local/phase4-crud/frontend` source.
- Focused database/approval/runtime UI files: 41 passed, including current-preview
  review, unavailable preview denial, and workflow-origin console navigation.
- Final isolated production build, TypeScript and scoped ESLint passed. Build log:
  `.local/phase5-workflow/build.log`; artifact is under that directory's frontend.
- Final production Chromium browser fixtures: 34 desktop/mobile scenarios passed,
  including four Phase 5 cases for planned source display, console-to-workflow
  routing, exact review and successful result inspection, plus stale preview denial.
  Log: `.local/phase5-workflow/browser.log`. Responses are fixture-backed, using
  synthetic native-run evidence; no cloud effects are inferred from browser tests.
- Shared contracts, operations/workflow schemas, registered inline tool schemas,
  generated UI drift, strict scoped OpenSpec and whitespace checks passed.

## Deployment and scope boundaries

No service restart, Phase 5 build activation, cloud row mutation, email send,
calendar action, live model request, policy change or credential change was
performed. Existing Phase 4 service PIDs remained unchanged and active. Individual
production login/IAM remains deferred; shared demo identity is unchanged.

This delivery supports manual runs under the existing source owner with that
owner's current human approval. Automation-subject delegation and independent
approver credential delegation remain denied. Specialists may prepare writes;
commit uses a fixed graph node. Source operations remain exact-key scalar steps,
at most four per group. Separate sources have no shared transaction; uncertain
effects block retries and known partial effects require explicit recovery review.

No physical-device, WebKit, live cross-source-to-Google acceptance or downstream
contributor acceptance is inferred. Configuration and execution are reviewable
locally; activation and live acceptance are subsequent work.

## User-authorized activation — 18 October 2026

The user subsequently requested Phase 5 activation on the running app. Activated
the verified build `s8AXfHzKo306b6DcfGzYL`, replacing Phase 4 build
`zQFwuMLj3YJulWO9QmS8i`. Frontend source matched the tested artifact. Retained
305 previous static assets and backed up the prior frontend and SQLite database
under `.local/phase5-workflow/activation/`. The database backup is private.

Restarted the backend, worker and frontend services; all report active. Authenticated
live Registry discovery exposes database_read_record, database_read_query,
database_prepare_operation and database_execute_operation. The existing Atlas test
target remains configured. Environment and database-write policy bytes are unchanged.
No model generation, cloud record mutation or Google action was triggered by the
activation checks. The original implementation-only restrictions above describe
the earlier delivery, not this subsequently authorized rollout.

Activation script and evidence: `.local/phase5-workflow/activate.py` and
`.local/phase5-workflow/activation/result.json`. Previous frontend rollback artifact:
`.local/phase5-workflow/activation/previous-next`. A new model-generated draft and
owner-reviewed execution are still required to confirm the reported planning error
is resolved for the user's prompt.

Read-only Chromium smoke checks passed on local and public origins at desktop and
mobile sizes (four scenarios): authenticated Registry tools and test-target status,
Operations rendering, reload, no page errors, missing static assets or horizontal
overflow. No API mutations were made. Evidence and screenshots:
`.local/phase5-workflow/activation/browser.json` and adjacent PNG files. These checks
do not claim Safari/WebKit coverage or a live generated workflow execution.
