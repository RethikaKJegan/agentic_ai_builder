## ADDED Requirements
### Requirement: Focused workflow presentation
The application SHALL show one prompt-based workflow list with Rename, Duplicate and Delete actions, preserving original prompts and execution history across all workspaces.
#### Scenario: Duplicate a saved workflow
- **WHEN** an authorized user duplicates a workflow
- **THEN** a distinct editable workflow is saved without copying runs, releases or automation authorization
### Requirement: Scoped background and knowledge
The application SHALL show workflow-specific continuation records in the workflow Background tab and omit unrelated module cards in This workflow knowledge mode.
#### Scenario: Open workflow background
- **WHEN** a workflow Background tab is opened
- **THEN** automation records and jobs belong to that workflow
### Requirement: Short display titles
The application SHALL generate a three-to-four-word display title during intent understanding before planning, preserving the full original objective and manual renames.
#### Scenario: Interpret a new request
- **WHEN** the model interprets a new request
- **THEN** it returns a short display title used in the saved workflow list
