- [x] Format inventory summaries and meeting agendas consistently.
- [x] Add safe HTML email alternative with plain-text fallback.
- [x] Verify facts, links, escaping, attachments and approvals; deploy backend.

Evidence: 56 report planner/formatting/mail connector tests passed, plus 25 general planner/HTML checks and 2 native runtime success flows (complete and partial, each with three approvals and verified URL handoffs). Desktop/mobile HTML previews have no horizontal overflow and were visually inspected. HTML escapes source text, uses no remote images and retains a plain-text MIME alternative. Contracts, strict OpenSpec, compilation and diff checks passed. Backend/worker restarted. Existing sent email and events were not modified; formatting applies to subsequent deliveries. Local previews: .local/briefing-format-preview.html and .local/calendar-format-preview.txt.
