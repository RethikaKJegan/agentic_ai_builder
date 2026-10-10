# Slack DM to Gmail integration

## Why
Slack Socket Mode is enabled remotely but no product listener receives events. The normal backend has no Gmail connector or trusted SMTP registrations.

## What Changes
Add an opt-in local Socket Mode backend, operator-owned Gmail registry setup, durable DM receipt routing, a setup CLI that prepares an executable draft with reviewed event mappings, diagnostics and verification. Preserve existing drafts, shared contracts, exact-action approval and recipient restrictions. No live delivery is claimed without provider evidence.

## Capabilities
### New Capabilities
- `slack-gmail-integration`: Receive configured Slack DMs and execute approved Gmail notifications.
### Modified Capabilities
- None.

## Impact
Workflow API provider bootstrap, listener, operator scripts, dependencies, tests and documentation.
