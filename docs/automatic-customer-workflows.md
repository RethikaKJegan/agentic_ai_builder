# Automatic customer workflows

Provide a Google Sheets link and a plain-language objective. Setup discovery reads
actual tab titles, headers and row-shape counts. Customer row contents are not sent
to the planner or persisted in the discovery catalog. The planner chooses the case
source, identity and email columns, supporting tables, matching instructions and
agent roles. Ambiguous source tables require a short clarification.

The backend requires its existing Google read consent, model configuration and
SMTP/IMAP credentials. Enable `BUILDER_EMAIL_DIRECT_SEND=1` and
`BUILDER_REPLY_MONITOR=1`. Manager destinations must be in
`BUILDER_EMAIL_RECIPIENTS`; the default manager is `BUILDER_CASE_BOSS_EMAIL` or the
configured SMTP account. Restart the existing backend once to load code/config.

Example setup prompt:

```text
Automatically handle manufacturing customer complaints using [Google Sheet link].
Check all relevant supporting records, email each customer and monitor replies.
Send appropriate follow-ups and escalate unresolved cases to aravind@bellcorpstudio.com.
Close only when the customer explicitly confirms resolution, and notify the manager.
Keep all spreadsheets read-only. Do not promise refunds or replacements without
manager approval.
```

The same setup works for restaurant complaints with that domain in the objective.
No A1 ranges, tool identifiers or fixed agent names are needed. Tables still need
clear, unique headers and stable case identifiers. Column names with spaces work.

Review the generated workflow and its **Automatic email policy**, then Publish.
Disable older workflows watching the same complaints to avoid parallel handling.
Wait for source readiness/baseline, then append a fresh unique case. Existing rows
are ignored on first activation. An initial email should send without a per-email
approval. The customer replies normally in the same email thread.

Matched replies enter durable SQLite jobs. The reply agent receives the original
concern, cumulative earlier findings, conversation and published master policy. It
can request fresh reads from published supporting tables. Routine follow-ups and
manager notifications run automatically. Explicit resolution evidence is required
for closure; merely sending an email or receiving thanks does not close a case.

Runs is an audit/health view. Automatic cases show action/job states instead of
approval buttons. Existing manual workflows keep their saved approval behavior.
Disabling a workflow prevents new automatic case actions. A recorded uncertain
SMTP submission is never automatically resent. Different cases retain separate
thread identifiers; auto-generated/bulk messages are excluded from reply handling.

All spreadsheets stay read-only and case states live in SQLite. Configured model,
tool, token and cost limits remain enforced. Financial commitments are outside
routine automation; generated messages still need practical live evaluation.

Verification includes simulated Google discovery, actual bounded CrewAI with fake
model responses, publication, three delegated supporting-table checks, automatic
SMTP submission, reply correlation, fresh evidence reads, escalation and closure
for restaurant and manufacturing objectives. Tests also cover restart recovery,
disabled workflows, source-recipient isolation and uncertain-delivery deduplication.
Passing simulations does not establish real mailbox delivery or model accuracy.
