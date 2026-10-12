# Dynamic agent delegation

The communication diagram previously observed predefined execution only. Add workflow-independent runtime delegation: a master chooses registered specialists and task inputs during execution, receives their results, and can delegate again or finish. No ticket-specific routes or hardcoded specialist selection.

Authority remains the reviewed workflow revision and its registered agents. New task instances use fresh UUIDs, not new credentials or provider-created permissions. External tools remain on the existing authorized graph path.
