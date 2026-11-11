## ADDED Requirements

### Requirement: Plain email drafting prepares content without delivery authority
A request to draft email text SHALL prepare reviewable content without assuming
Gmail persistence, an unspecified recipient or consent to send. Explicit mailbox
storage SHALL retain existing connector-input and approval requirements.

#### Scenario: Oil-leak investigation and draft
- **WHEN** a user asks to review similar oil-leak reports and draft an email
- **THEN** planning may prepare preliminary source review and email text without a recipient question

### Requirement: Population investigation caveats do not block planning
A caveat that a population investigation cannot identify a particular engine SHALL
not be treated as an essential missing ID. Explicit identified-case requirements,
missing access, unknown sources, unsupported operations and actual required inputs
SHALL retain their existing handling.

#### Scenario: Confirmed diagnosis needs matching evidence
- **WHEN** a request requires a confirmed particular-engine diagnosis
- **THEN** no population caveat may be used to invent matching evidence or bypass requirements

### Requirement: Executable inputs determine blocking prerequisites
In question-free mode supported-route interpretation notes SHALL be passed to action
planning as context rather than independently preventing compilation. Actual typed
input validation, source authority, schedule validation and approval gates SHALL
remain enforced. Unsupported and ambiguous operations SHALL not be bypassed.

#### Scenario: Advisory prose alongside a complete request
- **WHEN** interpretation includes sampling or preliminary-review caveats
- **THEN** action planning receives those caveats and checks actual required inputs

### Requirement: Structured selected-account delivery preserves explicit recipients
New model interpretations SHALL classify recipient mode independently of any address.
Selected-account delivery SHALL resolve its address only from the scoped owned
connection. An explicit supplied address SHALL take precedence. Named unresolved
third-party recipients SHALL not silently become selected-account delivery.

#### Scenario: Send email with a selected account and no other target
- **WHEN** delivery is classified as selected-account mode
- **THEN** preparation binds the owned account email and retains normal approval gates
