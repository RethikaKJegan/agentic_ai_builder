# Integrate procurement Phase 1 into MESH

## Why
Procurement currently requires a separate service and setup helper. Operators need the existing prompt, publication, approvals and traces to prepare and send RFQs.

## What Changes
- Register reviewed Google connectors and procurement tools in the live application.
- Generate a reviewed project plan from actual discovered headers and prompt context.
- Start durable preparation through a published workflow and expose status in its editor.
- Send each RFQ behind its own runtime approval and persist confirmed Gmail identifiers.
- Preserve existing customer workflows and isolated extension defaults.

## Impact
Additive metadata/tools/routes; accepted shared contracts unchanged. No live writes or email sends during implementation verification.
