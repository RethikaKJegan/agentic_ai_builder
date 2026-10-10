# Workflow-owned live provider execution

## Why
The normal backend has no live model or Google Sheets adapters. UI-created workflows need reusable provider connections without embedding a lead-specific pipeline in backend code.

## What Changes
- Add an operator-configured live backend launcher with Google Sheets, bounded OpenAI/CrewAI, Gmail and durable workers.
- Add configurable stable row-created detection, incomplete-row handling and correct checkpoint advancement.
- Preserve workflow-authored conditions and agent-output tool mappings; teach the live planner the supported trigger and execution formats.
- Verify provider access, orchestration, approval and replay behavior and document UI setup.

## Capabilities
### New Capabilities
- `live-workflow-providers`: Reusable live providers for published UI-created workflows.

### Modified Capabilities
None; canonical contract shapes remain unchanged.

## Impact
Runtime connectors/model, workflow API bootstrap and lifecycle polling, planner guidance, tests and operator documentation.
