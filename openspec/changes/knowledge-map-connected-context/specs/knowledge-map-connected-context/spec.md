## ADDED Requirements

### Requirement: Distinct direct context highlighting
The map SHALL highlight direct neighbours of verified executed concepts in light
green, using saved ontology relationships in either direction. It SHALL retain a
separate solid green executed appearance and label context as unverified usage.
It SHALL NOT propagate highlighting beyond one hop or increase execution counts.

#### Scenario: Connected chain
- **WHEN** executed concept A connects to B and B connects to C
- **THEN** A is executed, B is connected context and C is not context through A

#### Scenario: Step selection
- **WHEN** a step without recorded executed concepts is selected
- **THEN** context highlights from other steps disappear
