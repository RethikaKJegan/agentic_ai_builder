# Proposal

## Why

The planner can identify capabilities and required external actions, but it must not decide which credentials, scopes, or providers an agent may use. Aravind's segment provides the controlled Agent and Tool Registry boundary that converts planner requirements into authorized, least-privilege assignments.

## What Changes

- Validate agent definitions against `agent-contract-v1`.
- Register approved tools and connector metadata against `tool-contract-v1`.
- Match planner capability requirements to eligible tools.
- Enforce identity, workspace, role, scope, risk, quota, availability, and approval rules.
- Store credential references only; never store raw credentials in workflow payloads.
- Return stable authorization and registry errors using the accepted API and error contracts.
- Publish registry metadata for Harihar and authorized assignments for Rethika.
- Do not implement the planner, rebuild the UI, or execute external tools.

## Capabilities

### New Capabilities

- `agent-tool-registry`: Validates agents, registers tools, and produces authorized least-privilege assignments.

### Modified Capabilities

- None.

## Impact

- New registry and authorization service modules, fixtures, and tests.
- Consumes Suprajha's planner handoff and the accepted v1 shared contracts.
- Downstream consumers are Harihar's UI/API integration and Rethika's runtime.
