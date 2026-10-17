## ADDED Requirements
### Requirement: Detailed zoomable relationship map
The map SHALL use one accent colour, show dataset columns and types, and anchor labelled edges to their matching fields. Declared, proposed, accepted and rejected semantics SHALL remain unchanged. The viewport SHALL have bounded height without internal scrollbars and provide zoom in, zoom out, fit all and pointer panning.
#### Scenario: Inspect column relationships
- **WHEN** a graph with a relationship is displayed
- **THEN** both dataset cards include their columns and the edge identifies the mapped columns and whether it references or matches metadata
#### Scenario: Navigate a large map
- **WHEN** a user zooms or pans the map
- **THEN** the diagram moves within the bounded viewport and Fit all restores the complete diagram
