# Design

## Context

The planner, registry, UI/API integration, and runtime are separate OpenSpec changes. This final change consumes their published handoffs and supplies the explicit adapters needed to turn planner requirements into a reviewable executable revision.

## Goals / Non-Goals

**Goals:**

- Exercise the complete contract path with arbitrary capability combinations and
  one controlled connector per enabled provider class.
- Resolve planner capabilities automatically through the Registry while retaining server-owned authorization.
- Generate executable agent/tool graphs with typed data mappings, explicit
  condition outcomes, trigger bindings, and exact approval boundaries.
- Keep provider selection generic: provider-specific behavior belongs to
  Registry tool definitions and server adapters, never to a workflow-name branch
  in the planner.
- Make failures attributable to a segment and contract boundary.
- Verify safe behavior under approvals, authorization, idempotency, and failure conditions.

**Non-Goals:**

- Let planner output create permissions, credentials, destinations, or authorization references.
- Change the shared contracts during test execution.
- Replace contributor-owned unit, frontend, registry, or runtime tests.
- Claim a real provider delivery when credentials and an approved destination are not configured.
- Treat an environment variable alone as configuration input, not proof that a
  provider adapter, tool definition, or trigger is executable.

## Decisions

1. **Integration runs only after four handoffs are accepted.** This prevents end-to-end tests from hiding incomplete upstream behavior.
2. **Use a controlled generic workflow.** The example may include email or spreadsheet actions, but the test asserts generic contract behavior rather than procurement-specific logic.
3. **Treat contract versions as test metadata.** Every result records versions so failures caused by drift are distinguishable from implementation defects.
4. **Use test destinations and credentials only.** The demonstration must not send uncontrolled external messages or expose secrets.
5. **Resolve before approval.** Validation normalizes workflow-scoped agents, selects an eligible tool by capability, materializes executable tool references, and persists a new resolved revision when executable fields change.
6. **Keep reasoning and side effects separate.** CrewAI executes agent nodes. Application-owned graph orchestration invokes Registry-authorized connector nodes only after the exact run approval gate succeeds.
7. **Bind approval to the action.** External-action evidence covers the workflow revision, agent, tool, destination, and stable action boundary; it is not reusable for unrelated content or recipients.
8. **Use deterministic local adapters first.** The required acceptance path uses offline controlled adapters. A real SMTP smoke test is conditional on operator configuration.
9. **Separate capability planning from provider execution.** Planner output names
   capabilities and data mappings; Registry selects a versioned tool; the runtime
   dispatches through a provider adapter selected by tool ID. No provider is
   selected by string matching in the UI or by credentials found in a client
   payload.
10. **Model incoming events explicitly.** A read/send tool is not an event source.
    Row polling, provider push subscriptions, and schedules require a trigger
    binding, a trusted automation identity, a durable cursor/receipt, and a
    release-bound dispatch job.
11. **Expose the same generic state everywhere.** Discovery, editor, approvals,
    runs, and monitoring consume versioned server projections for every provider;
    they must not synthesize a provider-specific local status.

## Risks / Trade-offs

- **[Risk] External connector flakiness obscures platform defects.** → Separate connector availability failures from contract and orchestration failures and preserve replayable fixtures.
- **[Risk] Integration tests mutate real external state.** → Require explicit allowlists, test accounts, approval gates, and idempotency keys.
- **[Risk] A passing happy path misses unsafe paths.** → Make denial, rejection, timeout, duplicate, and budget tests required acceptance gates.
