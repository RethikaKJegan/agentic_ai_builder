## ADDED Requirements
### Requirement: Direct communication workflow generation
The application SHALL generate an email report and Calendar review workflow without delivery/timing questionnaires or a separate inferred-settings panel when owned destinations and timezone are available. Sending SHALL be the default unless a draft is explicit. Unspecified report-review timing SHALL default to five minutes after report completion. Existing approval SHALL remain required.
#### Scenario: Daily investigation and reading session
- **WHEN** a user requests a daily investigation, email report and thirty-minute Calendar review
- **THEN** compilation immediately pins owned email, primary Calendar, thirty-minute duration and after-ready timing in the generated workflow
#### Scenario: Explicit choices and blocked destinations
- **WHEN** a user requests a draft or fixed review timing, or no unique owned destination exists
- **THEN** explicit choices are retained and only genuinely blocking missing information requires a question
