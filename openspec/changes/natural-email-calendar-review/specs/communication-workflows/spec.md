## ADDED Requirements
### Requirement: Connected communication intent resolves naturally
Both tenants SHALL resolve owned account defaults and primary Calendar identity internally and ask only unresolved user-facing questions.
#### Scenario: Ordinary report and review request
- **WHEN** a user requests an email report and a thirty-minute review with a daily trigger
- **THEN** the application resolves owned destinations and asks for any ambiguous delivery/timing choice using ordinary language
### Requirement: Review timing remains authorized and in the future
The existing approval and recurring consent SHALL pin account, recipient, calendar, report dependencies, duration and timing policy. After-ready times SHALL resolve once before exact approval and remain stable across recovery.
#### Scenario: Report completes late
- **WHEN** the approved policy schedules review after report completion
- **THEN** the Calendar start uses the reviewed future lead time rather than an elapsed trigger time
### Requirement: Partial delivery remains independent
Confirmed deliveries SHALL remain recorded and never be replayed when another communication action fails. Unknown writes SHALL require reconciliation.
#### Scenario: Calendar fails after email succeeds
- **WHEN** the email has a confirmed receipt and Calendar fails
- **THEN** the UI retains Report emailed and identifies Calendar attention without repeating the email
