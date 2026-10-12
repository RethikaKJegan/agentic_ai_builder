# Design

Use additive `dynamic-delegation-v1.json` for optional `metadata.dynamic_delegation`, keyed by master node ID. Keep existing v1 schemas unchanged. Each entry bounds rounds and spawned tasks. Specialists are registered child agent definitions, not fixed graph execution nodes. The application invokes a bounded master decision turn with an internal output protocol: delegate a batch with agent IDs, inputs and concise evidence-based reasons, or finish with the master's declared output. Results return as data for the next master turn.

Every provider call reserves cumulative workflow and agent budgets, persists intent before invocation, and revalidates revision/auth before and after invocation. Crash recovery blocks an interrupted parent rather than replaying uncertain work. Cancellation prevents further calls. No automatic retries of a partially completed delegation batch. Validate the entire batch before any child starts. Reject unregistered/nonchild agents, invalid schemas, unmet approvals and overflow. Tools remain separately gated graph nodes.

Emit standard observed/started/completed/failed node events plus spawn and actual bidirectional handoff evidence. Diagram derives ephemeral child nodes only from exact-run events. Static hierarchy generation now produces one dynamic master with available child definitions; specialist provider calls are chosen at runtime.
