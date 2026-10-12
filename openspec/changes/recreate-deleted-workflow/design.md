# Design

At the authenticated planning boundary, copy the planner response and follow workspace-local tombstones. Each deletion yields a new deterministic ID derived from the old ID and its deletion timestamp. If the replacement was deleted too, follow its tombstone as well. A saved replacement is reused normally; no tombstone or retained revision is removed. Existing agent scoping rebinds structural IDs from the old workflow namespace to the replacement before trusted Registry resolution.

No shared contracts change. Test repeated planning, two successive deletions, workspace isolation, namespace integrity and historical preservation. No existing published workflow is modified or reactivated.
