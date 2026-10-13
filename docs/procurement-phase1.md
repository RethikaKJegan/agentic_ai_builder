# Procurement Phase 1 in the existing MESH application

## Automatic test mode

At the operator's request, `BUILDER_PROCUREMENT_AUTOMATIC=1` is enabled privately.
New setup prompts may explicitly request `action_mode=automatic` in natural
language. Publication reviews that project policy once; the coordinator selects
up to ten evidence-backed contacts, writes tracking records, creates drafts and
sends RFQs without individual action gates. Missing contacts, unsupported quotes,
changed requirements and uncertain sends still stop or require clarification.
Existing published approval-mode projects keep their saved gates. Generate a
new workflow to use automatic mode; do not rewrite historical approval evidence.

```text
Create a new automatic procurement simulation using [BOQ spreadsheet link].
Find suppliers on the web for each BOQ section and check their published product
and contact pages. Automatically select only candidates with actual published
email addresses and supporting product evidence. Deliver to Chennai workshop by
2026-11-15; quotes due 2026-10-30 at 17:00 Asia/Kolkata; currency INR.
Create tracking records and send RFQs automatically without per-action approval.
Stop after RFQs are sent; do not award orders or release POs. Leave missing
contact information unresolved rather than inventing it.
```

This mode may email real published supplier addresses. For controlled mail
testing, use supplied fictional vendors with inboxes you own instead. Search
results alone do not prove supplier suitability or commercial eligibility.

## Supplier discovery extension

The native Registry includes `supplier_web_search` (DDGS, no search API key) and
`supplier_read_page` (public HTTPS HTML/text only). Install/update integration
dependencies with `pip install -r scripts/requirements-integrations.txt` in the
integration environment. Search failures/rate limits are recorded; there is no
guarantee of unlimited search availability. Private addresses, credentials in
URLs and custom ports are rejected. Up to three redirects are allowed only after
fresh public-address validation and address pinning at each hop. HTML/plain text
downloads are bounded to two MiB, extracted text to 24,000 characters; footer
contacts are retained. Published same-site contact links may be inspected when
the product page has no email. Page text is treated
as untrusted evidence, not executable instructions. DDGS uses bounded backend
fallbacks and a simpler product query after an unavailable section search. An
unavailable source does not silently become a verified supplier. HTTP 403 sites
remain unavailable; research continues with the remaining public sources/sections.

Recovery skips only recorded provider availability failures. Authorization,
cancellation and budget failures still stop the project. Historical STOPPED
projects are preserved: after loading the fix, generate and review a new workflow
for a fresh test rather than replaying the old project's actions.

New prompts support supplied vendors, web discovery without a Vendors tab, or
combined mode. Example:

```text
Create a procurement simulation from the BOQ in [requirements sheet link].
Find potential suppliers on the web for each product section, inspect their
published product/contact pages and show me a shortlist with evidence links.
Use no supplied vendor list. Require my approval of supplier contacts before
RFQ preparation, and individual approval for every external write/send.
Project: workshop supplies. Deliver to Chennai workshop by 2026-11-15.
Quotes due 2026-10-30 at 17:00 Asia/Kolkata. Currency INR.
Stop after confirmed RFQ submission. Do not award orders or release POs.
```

Discovery reads up to eight actual BOQ sections, searches up to three results per
section and creates registered tool/verification action runs. Published email
addresses and verbatim supporting evidence are checked against actual collected
pages; absent emails stay unresolved. Duplicate contacts are grouped. Website
claims do not verify stock, certificates, identity or delivery capability.

At SHORTLIST_REVIEW, refresh Procurement setup & status. Select candidates with
published contacts, inspect their evidence and approve or reject the shortlist.
Only accepted contacts (and supplied contacts in combined mode) enter preparation.
Shortlist approval is recorded with the exact digest, actor and timestamp; stale
or changed selections fail closed. Changed BOQ data after research also stops
preparation. RFQ contacts preserve operator-review evidence rather than pretending
that web candidates came from a source spreadsheet. Calendar milestones, vendor
quotes and awards remain later phases.

Agent communication is one project graph without the per-action dropdown. It
collects exact related run revisions/events, namespaces each node by run and
preserves tool/approval results on click. Summary mode shows the coordinator,
actions and master/specialists; Show all tool and approval steps expands the
details. Green links are recorded handoffs; dashed links show containment or
configured routes, not fabricated agent messages. Large histories are bounded
and complete records remain in Runs. Existing published projects retain their
original plans; regenerate a new reviewed workflow to enable discovery.

The normal live backend exposes procurement when `BUILDER_PROCUREMENT_ENABLED=1`.
It reuses reviewed provider choices in `.local/connector-extension/config.json` and
the separate authorized Google token. The original SMTP/customer workflows remain
available. Stop the isolated extension service when using this integration; it is
not needed for new procurement workflows. Historical extension projects are not
migrated or replayed.

Use the existing frontend and backend ports. In Overview, enter a procurement
objective with requirements/vendor spreadsheet links. Real headers are discovered;
the planner maps them to a reviewed project plan. Supply project description,
delivery address/date, quote deadline with timezone offset, IANA timezone and
comparison currency. Unknown details stay empty. Review and complete them in
**Procurement setup & status**, save, then publish and click **Start procurement**
inside that panel (or **Run published** in the Workflows menu). This is a manual
start: no new source row or spreadsheet trigger value is needed.

Example (replace both links and terms with your actual test data):

```text
Create a procurement simulation for workshop supplies using [requirements sheet
link] and [vendor sheet link]. Prepare the BOQ, group requirements by section and
request quotations from each matching supplied vendor. Deliver to our Chennai
warehouse by 2026-11-15. Quotations are due 2026-10-30 at 17:00 Asia/Kolkata.
Compare in INR. Create a tracking spreadsheet and prepare RFQs. Require approval
for every spreadsheet mutation, draft and email send. Stop after RFQs are sent;
do not award orders or promise purchases.
```

The connected source account must have read access. Tracking writes use the native
Sheets connection; creation/Gmail/Calendar use the reviewed Google connector
token. Both are currently authorized by the operator as Aravind. Tokens, provider
configuration and credentials never enter workflow prompts.

The coordinator reads source tables through canonical specialist tool steps. A bounded
procurement master delegates requirements completeness and vendor coverage review
to two registered sub-agents, collects their results, and records decisions and
handoffs in the existing communication inspector. Both specialists must return
before preparation; BOQ values come from the original authorized Sheet results,
not model-generated replacements. The coordinator then
validates BOQ/vendor records and section grouping, creates the six-tab tracking
spreadsheet, projects records, creates Gmail drafts, and separately submits each
RFQ behind its own exact action approval. For four items/four vendors this may
produce four RFQs depending on actual categories. Arbitrary domains, headers,
accessible spreadsheet links and up to 100 source data rows are supported.

Before starting, Agent communication previews the configured master/specialist
hierarchy. After starting, it opens the actual source-review run automatically.
Existing historical projects retain their already-published source workflow.

Refresh project status also reconnects the local session after a backend restart.
An unstarted project shows Ready to start. A missing procurement route reports
unavailable integration separately from an unrelated upstream service.

Review Approvals as new actions appear. Agent communication stays available for
tool-backed agents; its **Project action** selector opens the actual ingestion,
tracking, draft and send runs. Runs also exposes those child workflows and tool
handoffs. Refresh the procurement status panel to see
counts, issues, action/run IDs and the tracking link. After successful sends,
Gmail message/thread IDs are stored and RFQ tracking rows become OPEN. Final phase
is RFQS_SENT. This denotes confirmed Gmail API submission, not guaranteed inbox
placement. Vendor-reply processing, award/PO and fulfilment belong to later phases.

Disabling or replacing the parent release prevents further coordinator actions
and rechecks parent activity before provider side effects. Repeated starts reuse
the same project; unknown sends are frozen, never automatically retried. Changed
sources/settings after starting require a reviewed new project. Domain state is
under `.local/connector-extension/native-procurement`; workflow/run/approval
records are in the existing MESH workflow database.

Offline checks: `python -m unittest tests.test_integrated_procurement` exercises
real native planning/publication/Registry/runtime/SQLite with simulated model and
Google responses. Live acceptance requires restarting the existing backend and
frontend and running a controlled test with exact action approvals.
