# Idempotent approval decision replay
A stale browser or concurrent scheduler can repeat an already committed approval using a different request key. Return current run state for an authorized same-decision replay, without changing the first decision or replaying actions. Keep opposite decisions and unauthorized access rejected. Both tenant backends; no frontend or stored history edits.
