# Design

Add optional continuation data to delegate decisions, plus continue and wait decisions. Without continuation, a delegate batch joins before the next master turn. With continuation, the next turn sees progress, completed results and pending task identities while children run. Continue updates progress; wait joins pending work. Finish with outstanding children discards the premature output and requests synthesis again after joining. Before the last allowed turn, join pending tasks so the final turn can incorporate all results.

Use a session-owned executor capped at four child workers. Every submitted task retains its spawning master invocation UUID for both handoffs. Transactions independently reserve budgets and persist events. Cancel queued futures on failure, drain active bounded calls, and recheck run ownership before invocation and result acceptance. Interrupted sessions retain the existing unknown-result recovery behavior.
