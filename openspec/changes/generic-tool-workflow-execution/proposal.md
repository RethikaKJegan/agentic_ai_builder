# Generic workflow execution across registered tools

## Problem

Hierarchical workflows can fail before their graph starts: the CrewAI manager is also included in its worker list, and the workflow graph separately schedules specialist nodes. Hierarchical planning can also discard conditional control flow. Tool-node input mapping is partly capability-specific, so newly registered tools can be selected without enough information to execute safely.

## Change

Make the graph runner the sole owner of workflow ordering and tool invocation. Configure CrewAI managers separately from workers when a hierarchy is used for an agent task. Preserve and validate declared condition branches in planner output. Derive tool input mappings from accepted Registry schemas and workflow inputs, and retain unresolved requirements whenever a required value cannot be mapped.

This applies to any approved workflow and any currently authorized Registry tool. It does not claim provider credentials, quotas, live accounts, incoming-event adapters, or endpoints are automatically configured by a Registry record.

## Acceptance

- A hierarchical plan does not fail because its manager appears among workers.
- A specialist node and connector each execute only at their declared graph position.
- Declared conditions remain connected to declared outcomes; unsupported expressions or unmapped required connector inputs block approval with a reviewable requirement.
- Tool inputs are checked against the exact Registry input schema before provider invocation.
