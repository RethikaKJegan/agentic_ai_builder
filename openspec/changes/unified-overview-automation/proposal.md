# Unified Overview automation

## Why
Short business requests must select existing capabilities without requiring users to choose a route or type cron. Customer-specific vocabulary must come from authorized knowledge, not new routing branches.

## What Changes
- Opt-in backend AI interpretation through the existing action-plan transport, with legacy dispatch unchanged when disabled.
- Existing Overview displays a scoped composition and schedule review. No new page or prompt.
- Internal versioned temporal-query annotation pins all query semantics except two explicitly reviewed time bounds; existing exact-query consent remains the default.
- Existing scheduler, lifecycle queue, CrewAI content agents and Registry execute the workflow. No replacement executor, scheduler, store or retrieval algorithm.
- MongoDB native date filters preserve source-wide validation and existing limits.

## Impact
Additive internal metadata only; shared contracts unchanged. Feature is disabled by default and scoped by workspace allowlist. No production activation or provider mutations during qualification. Existing saved definitions remain immutable.
