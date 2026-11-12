## ADDED Requirements

### Requirement: Subway workflow display cleanup
The frontend SHALL omit repeated demonstration labels and boilerplate disclaimers from Subway workflow presentation, including node inspectors, steps, reports, Knowledge Map and background details. Supplier display names SHALL omit their demonstration prefix. Essential currency, missing-evidence and coverage facts SHALL remain visible using concise notes. Source identifiers and backend records SHALL remain unchanged.

#### Scenario: Existing workflow content contains demonstration labels
- **WHEN** a Subway user views reports, graph labels or expanded technical details
- **THEN** presentation SHALL omit demonstration prefixes and repetitive policy disclaimers
- **AND** stored records, financial values and graph identities SHALL remain unchanged

#### Scenario: Another tenant views a workflow
- **WHEN** a non-Subway user opens the same components
- **THEN** existing presentation SHALL remain unchanged

#### Scenario: External content already exists
- **WHEN** a saved email, Calendar or spreadsheet result is previewed
- **THEN** only its frontend presentation SHALL change
- **AND** external records and execution payloads SHALL not be rewritten
