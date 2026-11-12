## ADDED Requirements
### Requirement: Preserve requested Calendar actions
Connected Calendar work SHALL require no unrelated business dataset. A prepared plan SHALL retain its requested Calendar action and exact reviewed destination and event timing.

#### Scenario: Calendar-only request
- **WHEN** the request supplies a selected account, primary calendar and explicit event interval
- **THEN** a reviewable Calendar action is prepared without a dataset clarification

#### Scenario: Recurring same-day review
- **WHEN** a reviewed daily workflow creates a review on its occurrence day
- **THEN** the event timestamps resolve from the durable occurrence time and reviewed timezone, with approvals preserved

#### Scenario: Planner omits Calendar action
- **WHEN** the proposed plan omits a required Calendar operation
- **THEN** bounded planning correction or an explicit preparation failure occurs, never a successful report-only substitute
