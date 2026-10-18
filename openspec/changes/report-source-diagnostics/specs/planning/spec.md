## ADDED Requirements
### Requirement: Explain missing inventory relationships
The inventory compiler SHALL distinguish missing executable lookup relationships from invalid proposed source IDs. Such setup failures SHALL provide safe review guidance and SHALL NOT be presented as retryable LLM corrections.

#### Scenario: Category relationship is proposed
- **WHEN** one inventory source exists but its required category relationship is not accepted or declared
- **THEN** generation returns INVENTORY_LINK_REQUIRED with category relationship review guidance
- **AND** no suggested relationship is automatically accepted

#### Scenario: Required links are accepted
- **WHEN** inventory has unambiguous declared or accepted category and supplier links
- **THEN** normal source selection and report compilation proceed
