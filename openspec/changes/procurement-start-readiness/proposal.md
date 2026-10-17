# Reject procurement starts before activation

The procurement Start control checks publication but not activation. The reported run was submitted before its release existed; StartConnector rejected the inactive owner with ProcurementError, which the graph reduced to INVOCATION_FAILED. The source spreadsheet and plan are not the cause.

Add a trusted run-admission validator, registered by procurement and applied inside run creation before a new run is queued. It must require the active release to match the requested workflow and revision and leave other workflow types unchanged. Recheck at connector invocation for revocation races and preserve safe domain error codes. Gate the UI using authoritative release state, explain missing activation and recheck before submission. Use no prompt, spreadsheet, vendor or project constants.

Scope the UI's durable start key to the authoritative release ID so repeated clicks reuse one start and a previously failed pre-activation run does not trap a newly activated release.

Verify inactive/disabled/wrong-revision rejection with no run or project effects, active execution with offline providers, preservation of domain failures, unrelated workflow behavior and frontend readiness transitions. Load tested changes into existing services and verify read-only live readiness. Do not automatically replay the failed run or send procurement emails.
