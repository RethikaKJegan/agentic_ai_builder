## ADDED Requirements

### Requirement: Parse equivalent meeting time windows
The inventory report planner SHALL accept explicit time windows introduced with
from, within or between and separated with a dash, to or and. It SHALL retain
explicit date, duration and IST requirements and reject invalid or too-short
windows. The existing final-fitting-slot preference SHALL remain unchanged.

#### Scenario: Supplied test prompt
- **WHEN** a 30-minute review on 20 October 2026 is requested within 3:00–4:00 PM IST
- **THEN** the planner selects 3:30–4:00 PM IST without a missing-time error

#### Scenario: Duration exceeds window
- **WHEN** the requested duration exceeds the explicit window
- **THEN** generation rejects the meeting time
