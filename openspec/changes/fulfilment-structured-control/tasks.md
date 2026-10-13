- [x] Implement request-reference delegation and structured synthesis.
- [x] Preserve failed history and bound transport-revision recovery.
- [x] Run focused protocol and recovery regressions.

Twelve focused protocol, recovery and fulfilment guard tests passed. Shared contracts, strict scoped OpenSpec and diff checks passed. The second recorded attempt failed before any event or tool mutation. The provider did not persist the rejected raw output, so its exact invalid field remains unknown. This change removes encoded input reconstruction and constrains synthesis directly. The active job is recovered only by the normal worker after backend reload; no database edits, email sends or service starts were performed during this change. Live processing remains to be verified.
