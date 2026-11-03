## ADDED Requirements
### Requirement: Bounded automatic candidate packing
Automatic workflow planning SHALL pack ranked complete source descriptors within its existing metadata budget instead of rejecting an otherwise usable candidate pool merely because all candidates together exceed it.

#### Scenario: Wide optional source
- **WHEN** twelve relevant sources exceed the budget but a ranked subset fits
- **THEN** generation receives the fitting subset with exact source/field identities, filtered relationships and an explicit omission warning

#### Scenario: Explicit selection remains authoritative
- **WHEN** an operator explicitly selects source metadata larger than the supported bound
- **THEN** the existing bounded-selection error remains and no selection is silently substituted
