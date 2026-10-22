## ADDED Requirements
### Requirement: Attributed illustrative numeric values
Usage & Limits SHALL replace missing numeric placeholders with clearly tagged Sample values and retain all reported numeric values including zero. A visible notice SHALL distinguish illustrative values from configured or measured values. Samples SHALL NOT change backend configuration, runtime behavior or stored browser controls.
#### Scenario: Unsupported reporting
- **WHEN** the service omits a numeric limit or usage
- **THEN** an illustrative numeric value is shown with a Sample label
#### Scenario: Real zero
- **WHEN** the service reports zero
- **THEN** zero remains visible without a Sample label
### Requirement: Supported delegation concept
The existing maxChildren browser hierarchy concept SHALL remain visible as Sub-agents per agent without claiming a reported runtime limit.
#### Scenario: Delegation reference
- **WHEN** delegation limits are inspected
- **THEN** the direct-child concept is retained with source context and illustrative attribution
