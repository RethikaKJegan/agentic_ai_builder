# Complete Phase 2 source navigation

The detailed knowledge graph already supplies technical containment, metadata,
reviewable entities, qualified relationships and revision-bound persistence.
Close two inspection gaps: entity details silently stop at 100 source mappings,
and relationship linking fields are plain text without source navigation.

Expose all entity source mappings in bounded pages, label them with their complete
connection/database/schema/dataset/field path, and let users inspect either field
of a relationship. Preserve selection across graph refreshes, review permissions,
existing contracts and v1/query behavior. Verify backend regressions and desktop/
mobile production browser fixtures. No source data changes or Phase 3 features.
