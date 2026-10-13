# Procurement first automation slice

## Why
The extension has connectors and a case repository but no execution bridge. The first slice must turn selected requirements and vendor tables into durable BOQ, tracking projections and reviewed RFQ drafts.

## What Changes
Add opt-in internal procurement tools, an authenticated extension service and a bounded coordinator. Use canonical runtime reads, exact mapped ingestion, literal approval-gated spreadsheet creation, reviewed row destinations and approval-gated Gmail drafts. Persist workflow/run references and synchronize only confirmed runtime outputs. Preserve uncertain outcomes without replay.

## Impact
Extension files and this scoped change only. No original application route, workflow, credential or contract changes. Default connector catalog and behavior remain unchanged without procurement enablement. No quotation polling, awards, PO release, fulfilment or Calendar automation in this slice.
