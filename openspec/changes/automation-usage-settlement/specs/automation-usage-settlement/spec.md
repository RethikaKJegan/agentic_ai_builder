## ADDED Requirements

### Requirement: Model usage settlement respects server accounting policy
Confirmed model usage SHALL be finite, nonnegative and contain one confirmed call. Provider-managed token and cost accounting SHALL record actual usage without imposing a provisional token/cost allocation as a ceiling. Bounded accounting and call limits SHALL remain enforced.

#### Scenario: Provider-managed usage exceeds allocation
- **WHEN** confirmed tokens exceed a provisional allocation under provider-managed policy
- **THEN** the runtime records actual usage and continues subject to remaining execution controls

#### Scenario: Invalid or bounded excessive usage
- **WHEN** counters are invalid or exceed an enforced bound
- **THEN** the runtime refuses settlement

### Requirement: Occurrence evaluation distinguishes business evidence and execution controls
The evaluator SHALL assess business evidence independently of scheduler-owned recurrence and delivery receipts. Final completion SHALL still require completed requested actions and reviewed delivery authority.

#### Scenario: Daily summary has no send receipt yet
- **WHEN** source evidence supports the business summary but delivery remains pending
- **THEN** the evaluator may permit the reviewed delivery action without claiming delivery is complete
