# Design: generic registered-tool workflow execution

## Execution ownership

The persisted workflow DAG is authoritative for ordering, conditions, approvals, and connector calls. Each agent node runs as one bounded CrewAI task with internal delegation disabled. A manager node cannot execute specialist tasks on the side; specialists run only when the graph reaches their nodes. Tool calls stay in graph tool nodes, where the runtime revalidates exact Registry grants, schemas, approval evidence, destinations, and budgets.

## Planner and Registry boundary

Hierarchy construction must retain conditions from the base plan and must not turn an unknown natural-language condition into executable logic. Planner validation checks that every declared condition has a node and every condition node has a declared outcome path. A condition that cannot be represented safely remains an unresolved requirement for human review.

After Registry assignment, tool nodes use the selected tool's accepted input schema. Known canonical mappings remain explicit. Other properties may map from same-named declared workflow inputs. Any required property with no mapping is recorded as unresolved; the workflow cannot pass the existing assignment/review gate until it is wired. The runtime remains the final schema validation boundary.

## Scope and limits

The generic execution contract covers all tools that are registered, authorized, assigned a connector adapter, and configured with provider credentials and destination policy. Tool count or catalog presence alone does not establish live provider availability. Incoming triggers remain governed by the separately configured trigger adapters.
