## ADDED Requirements
### Requirement: Browser agent preferences
Organization Policies SHALL expose Communication, Behaviour & Safety and Response Boundaries preset-button groups with accessible On/Off switches. Language selection SHALL appear only when enabled. Selecting a preset SHALL update that group's settings; manually changing a setting SHALL mark that group Custom. Apply preferences SHALL persist only these browser preferences using the existing store, without modifying agents, workflow requests or runtime configuration.
#### Scenario: Apply and reload
- **WHEN** a user selects presets, customizes toggles and applies
- **THEN** those preferences survive a reload and unrelated browser/runtime state is preserved
#### Scenario: Unapplied changes
- **WHEN** switches change without Apply
- **THEN** the committed browser preference record remains unchanged
### Requirement: Existing limits and navigation
The section SHALL show a compact available revision/agent limit reference and View all limits SHALL select the existing Usage & Limits tab. Governance SHALL retain exactly three primary tabs and existing policy/audit behavior.
#### Scenario: Limits link
- **WHEN** View all limits is selected
- **THEN** the existing Usage & Limits tab opens without a backend mutation
