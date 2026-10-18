## ADDED Requirements
### Requirement: Rename workflow titles
The workflow actions menu SHALL offer Rename to editors. Server titles SHALL persist in the workspace independently of executable revisions. Renaming SHALL NOT create revisions or change releases, runs, grants or approval bindings. Empty names, names over 200 characters and stale expected names SHALL be rejected.

#### Scenario: Rename a published workflow
- **WHEN** an editor saves a valid new title
- **THEN** the workflow list and editor show the new title after refresh
- **AND** existing executable revisions and active run bindings remain unchanged

#### Scenario: Stale rename
- **WHEN** another editor has changed the title
- **THEN** the stale rename fails with reload guidance
