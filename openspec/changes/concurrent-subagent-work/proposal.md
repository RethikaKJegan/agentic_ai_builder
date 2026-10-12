# Concurrent subagent work

Extend the existing runtime delegation session so a master can delegate a task with a continuation, work on that continuation while children execute, and join validated results before final synthesis. Existing delegate/finish callers retain their behavior. Conditions and task content remain agent-selected, with no domain-specific routing.

Use bounded threads and existing transaction, authorization, budget, schema, cancellation and trace boundaries. External tools remain explicit authorized graph nodes; this change does not give child agents new connector access.
