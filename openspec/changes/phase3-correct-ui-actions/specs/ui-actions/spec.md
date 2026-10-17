## ADDED Requirements

### Requirement: Explicit lifecycle transitions
The UI SHALL independently save, validate, submit, approve, publish and activate the current revision subject to server permissions.

#### Scenario: Publish approved revision
- **WHEN** a user explicitly publishes a clean approved revision
- **THEN** only publication is requested and approval/activation are not implied

### Requirement: Confirmed persistence
The UI SHALL preserve unsaved edits until a confirmed server save and offer safe reload on conflicts.

#### Scenario: Failed settings save
- **WHEN** the server rejects a settings mutation
- **THEN** the editor retains the input and displays an error without claiming success

### Requirement: Safe manual execution
The UI SHALL validate published workflow inputs and execution permissions before submitting a single run.

#### Scenario: Cancel run input
- **WHEN** a user cancels the run form
- **THEN** no execution request is made

### Requirement: Honest integration and action feedback
The system SHALL distinguish configuration from verified connectivity and inventory all interactive controls.

#### Scenario: Unsupported connectivity check
- **WHEN** a configured provider has no safe live probe
- **THEN** Check configuration reports configured but never verified
