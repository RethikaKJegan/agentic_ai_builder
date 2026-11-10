# Separate query limitations from missing business inputs

## Why
A plain complaint-record count is repeatedly blocked by model clarification text describing sampled metadata and future execution coverage. These are limitations, not missing field/unit definitions.

## What Changes
Add trusted, generic-query-only CrewAI guidance at execution time, including for saved agent definitions: an expressible authorized query leaves clarification empty, row counts need no measurement field/unit, metadata sampling does not imply result sampling, engine coverage is established during execution, and downstream report/delivery goals are separate. Preserve actual nonempty clarification stop guards; never heuristically clear model clarification or invent coverage/results.

## Impact
One backend source file. No contracts, data schemas, account handling or provider operations change. Controlled transport/runtime checks and normal verified hosted rollout; live model accuracy remains unqualified without a live model test.
