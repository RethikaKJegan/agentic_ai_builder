## ADDED Requirements
### Requirement: Animated generation button
While generation is pending the overview button SHALL display three animated dots instead of visible Generating text. It SHALL remain disabled, expose an accessible busy label and respect reduced-motion preferences. Idle and retry behavior SHALL remain unchanged.

#### Scenario: Pending generation
- **WHEN** the workflow is generating
- **THEN** the button shows the thinking animation and cannot submit another request
- **AND** reduced-motion users see static dots
