# Design

## Context

The planner, registry, UI/API integration, and runtime are separate OpenSpec changes. This final change is a verification layer and must consume their published handoffs rather than reimplementing their responsibilities.

## Goals / Non-Goals

**Goals:**

- Exercise the complete contract path with one generic workflow and one controlled connector.
- Make failures attributable to a segment and contract boundary.
- Verify safe behavior under approvals, authorization, idempotency, and failure conditions.

**Non-Goals:**

- Add new product capabilities.
- Change the shared contracts during test execution.
- Replace contributor-owned unit, frontend, registry, or runtime tests.

## Decisions

1. **Integration runs only after four handoffs are accepted.** This prevents end-to-end tests from hiding incomplete upstream behavior.
2. **Use a controlled generic workflow.** The example may include email or spreadsheet actions, but the test asserts generic contract behavior rather than procurement-specific logic.
3. **Treat contract versions as test metadata.** Every result records versions so failures caused by drift are distinguishable from implementation defects.
4. **Use test destinations and credentials only.** The demonstration must not send uncontrolled external messages or expose secrets.

## Risks / Trade-offs

- **[Risk] External connector flakiness obscures platform defects.** → Separate connector availability failures from contract and orchestration failures and preserve replayable fixtures.
- **[Risk] Integration tests mutate real external state.** → Require explicit allowlists, test accounts, approval gates, and idempotency keys.
- **[Risk] A passing happy path misses unsafe paths.** → Make denial, rejection, timeout, duplicate, and budget tests required acceptance gates.
