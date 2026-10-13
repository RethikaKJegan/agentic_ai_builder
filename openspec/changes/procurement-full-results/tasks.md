- [x] Use full authenticated completed outputs in native procurement.
- [x] Verify a growing thread retains its newest message and noncompleted actions stay pending.

Seven focused result/fulfilment guard tests passed; contracts, strict scoped OpenSpec and diff checks passed. Read-only live diagnosis confirmed the dispatch message is in the persisted completed thread output but omitted from its bounded trace snapshot. No server starts, database changes or email sends were performed. Backend reload is required for the worker to consume the existing reply.
