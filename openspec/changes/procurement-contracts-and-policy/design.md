## Scope
Step 1 defines data and behavior only. Keep domain record revisions separate from canonical workflow revisions. JSON Schema validates representation; a later orchestrator must enforce cross-record references, evidence authority, arithmetic, state guards and exact runtime approvals transactionally.

## Decisions
Use decimal strings and a project-selected comparison currency; do not invent FX or missing commercial details. Maintain independent project, RFQ, quote and order states. Preserve source hashes, message/thread IDs, resource ownership, policy revisions and evidence. Partial quantities never imply complete fulfilment. Agents recommend but never authorize their own writes.

## Approval boundary
Default external writes require trusted human approval, preserving current extension gates. Reads and validated internal processing can run automatically. The policy artifact is not loaded by the current runtime; later automatic-action profiles need explicit implementation and authorization.

## Closure
Require verified buyer receipt, acceptance, resolved exceptions and complete quantities. Supplier delivery reports are insufficient. Project completion also requires every required item to be resolved. Calendar cleanup targets only persisted project-owned event IDs; failure does not erase procurement records.

## Verification
Validate JSON Schemas, positive fixtures, rejected unsafe/invalid representations and state/policy references. Verify canonical contracts and original file hashes. No provider operation is required.
