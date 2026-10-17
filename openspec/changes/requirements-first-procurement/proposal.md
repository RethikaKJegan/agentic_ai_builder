# Requirements-first procurement planning

## Why
The restaurant request asks the AI to generate a BOQ before supplier comparison. The source-driven procurement adapter currently treats every procurement keyword as a request to ingest an existing BOQ spreadsheet, and ignores workspace source context.

## What Changes
Route explicit new-BOQ/requirements-generation requests to the general multi-agent planner with requirements-first guidance. Keep source-backed operational procurement and its approvals unchanged. Reuse trusted workspace spreadsheet candidates for source-backed requests and improve the specific missing-source message. Estimates/unverified quotes must be labelled, and draft planning confers no authority to contact suppliers or issue orders.

## Impact
Planner routing, shared bounded spreadsheet reference selection, source-backed procurement and safe error guidance. No schemas, credentials, live workflow revisions or provider grants change. Verification generates drafts only; it never executes procurement or contacts suppliers.
