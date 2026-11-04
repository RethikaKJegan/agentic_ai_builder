# Investigation recovery/details verification — 4 November 2026, 18:33 IST

## Report cross-check and failure attribution

The supplied simple report was compared with persisted source checkpoints in
`run_968e5b5647054b2eb893e4e19ddb2acc`. All four analysis result reference sets
(8/7/13/12 findings) passed independent source-pair validation. Serial, hours,
symptom, inspection date, defect text and invalid raw failure date matched mapped
source observations. This does not establish causal diagnosis or company authority.
Compatible repeated reads now merge field subsets for UI record counts; this run
has 23 distinct record identifiers rather than the previous displayed 24.

The two historical complex failures kept only INVOCATION_FAILED. The precise
original underlying exception was discarded and cannot honestly be reconstructed.
The replacement specialist failed before tool dispatch after ~3.2 seconds; worker
logs also contained unclassified transaction failures. A controlled reproduction
confirmed a concrete flaw in this path: read-only tool discovery acquired a writer
lock and failed under another writer. It now succeeds while that writer remains
held. Other read-only delegation checks also use read transactions. State changes
still serialize and recheck authority. Busy limits remain finite.

Storage contention now retains DATABASE_BUSY and its distinct recovery category;
uncertain writes require reconciliation. Unknown failures direct service inspection,
not an unfounded instruction to fix ontology/evidence. Safe failure type/stage,
trace reference and categorized database logs improve future diagnosis without
recording raw exceptions, SQL, rejected model output or credentials.

## Feedback and UI

Pure-model output correction retains the existing bounded validation loop.
New runs can receive task-scoped, sanitized model-error hints from the latest failed
run of the exact same workspace, owner and approved revision. Hints are not business
evidence, validated organizational experience or authority. Code, knowledge,
permissions and external actions are not automatically changed. Sources are reread
and independently validated. No automatic paid new run or uncertain-write replay.

Workflow details contains the question, original preparation context, selected
Google account and optional action fields. Regeneration preserves prior history and
requires normal lifecycle approval. Run/report/recovery/cancel/refresh actions share
the toolbar; the full question is removed from the canvas header. Actual read
receipts expose counts and bounded identifiers without mailbox bodies/page cursors.

## Verification

- Final backend: **88 passed, 18 subtests passed**, covering recovery/details,
  canonical runtime and composition, including writer-lock reproduction, typed busy
  failure, source-qualified record merging, receipt privacy, scoped prior-run
  feedback and a complete eight-task comparison/warranty/replacement workflow.
- Additional memory/presentation/reliability suite: 72 passed with one initial
  failure caused by the new test not attaching its runtime runner to the UI fixture.
  That fixture was corrected; the complete final backend suite above passes.
- Frontend **466 passed**; types, ESLint and staged production build passed.
- Desktop/mobile browsers **12 passed**, including details/question/account controls,
  aligned toolbar, missing-input editing, recovery, approval and legacy histories.
- Canonical contracts, generated UI contract drift, strict scoped OpenSpec and
  diff checks passed. No shared workflow/agent/tool schema changes.

## Authorized actual-model acceptance

After explicit user approval to include bounded replacement evidence, actual
configured OpenAI/CrewAI ran the full hard goal in a private application/registry
copy. Endpoint api.openai.com; provider storage disabled; no credentials,
attachments, Google actions or company writes.

- Composition `composition_0277f1f71bf5c2b604deaf4d`; receipt available privately under
  `.local/dynamic-investigation-checks/check-ffyh5erm/`.
- Run `run_1d0b2ebc0fa34945ad814ccf8e1e66ed`: **completed**, eight task checkpoints.
- Four business retrieval tasks, comparison and report completed.
- Warranty assessment and replacement review returned qualified needs-input
  results, preserving missing policy/identity/authorization evidence.
- Four bounded read tools and 14 runtime model turns. No final error.

The initial automated approval rejection for this expanded evidence scope was
resolved by the user's explicit authorization before the test was run. This is a
bounded actual-model acceptance, not proof of all future prompts or all Google tools.

## Deployment

Live at https://praxi.bellcorpstudio.com/app, build `4MoUMoCDpzd9kBBsOIA3I`,
activated 4 November 2026, 18:33 IST. Backend, worker and frontend active. Normal login and
unauthenticated rejection, active worker, existing failed workflow, diagnostic
reference, question/account drawer, four selectable account entries, toolbar
alignment, mobile layout and assets passed public checks. Zero browser errors.
No production workflow/model run or Google operation was initiated by deployment
verification. Account visibility does not prove all four accounts' tools succeed.

Table fingerprints preserved all existing workflow revisions (85,165), runtime runs
(85,169), legacy plans/runs (11/12), ontology versions/documents (8/24) and two saved
compositions. Original failed runs remain unchanged; Start new run uses current
code. Account/request changes generate a new immutable composition. No company
source writes, ontology import, policy invention or scenario-data import.

Private rollback build/database/source backups, public screenshots and preservation
receipts: `.local/investigation-recovery-release/`. Do not restore an old database
over later user work. No credentials, Nginx or service configurations were changed.

Real Gmail search execution remains an explicit user test using an owned selected
account and query. Real Google writes still need approved test targets and action
authorization. Provider failures, contention and genuinely missing facts remain
possible; the implementation does not claim failure-free arbitrary execution.

Files and exact UI test instructions:
`docs/simpson-business-ontology/investigation-recovery-details.md`.
