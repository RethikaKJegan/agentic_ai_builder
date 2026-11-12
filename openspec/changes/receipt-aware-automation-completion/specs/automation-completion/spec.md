## ADDED Requirements
### Requirement: Receipt-aware terminal completion
The runtime SHALL finalize verified business work after all approved required actions complete, with current source authority and connector receipt integrity checks, without requiring a new model assessment of delivery as business evidence.

#### Scenario: Delivery completed
- **WHEN** approved delivery completes after a validated eligible assessment
- **THEN** finalization checks persisted action states and receipt fingerprints without sending again

#### Scenario: Evidence changed
- **WHEN** business evidence or required connector receipt integrity no longer validates
- **THEN** terminal completion is refused and no completed action is replayed

### Requirement: Concise automation outcomes
The automation workflow view SHALL present factual progress and actionable input or approval requests, while preserving technical diagnostics in an inspectable details view.

#### Scenario: Delivered occurrence requires attention
- **WHEN** email delivery succeeded but subsequent processing failed
- **THEN** the view distinguishes the recorded completed action from remaining processing and does not display raw evaluator codes in the main workflow area
