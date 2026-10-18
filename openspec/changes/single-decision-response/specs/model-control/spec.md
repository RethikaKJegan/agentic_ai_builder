## ADDED Requirements

### Requirement: Consume one control decision from validated provider output
The runtime SHALL validate the entire bounded control response against its exact supplied transport schema and consume only the first decision when a provider returns multiple complete control envelopes. It SHALL reject malformed suffixes, partial objects, unknown actions and excess envelopes. It SHALL not execute additional speculative decisions or relax ordinary business JSON validation.

#### Scenario: Concatenated control envelopes
- **WHEN** a response contains several complete valid control envelopes
- **THEN** only the first decision is returned for normal authorized application dispatch

#### Scenario: Invalid trailing content
- **WHEN** any remaining content is incomplete, non-JSON or violates the control schema
- **THEN** the entire response is rejected without tool execution
