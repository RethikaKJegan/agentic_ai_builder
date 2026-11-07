# Truthful tool-result visibility

Connected database reads currently enter a generic write-receipt projection,
discarding records and using a missing task.selected_tool_id instead of the
persisted selected_tools mapping. Project actual read evidence/counts/collections
and tool identity; preserve existing structured source views, explicit zero-row
outcomes and scoped history. Present readable tool names and result counts before
technical JSON. Include recorded message/artifact identities and bounded read
counts for other tools; never invent a result or success receipt. Fix existing and
future display from saved outputs without rerunning tools or mutating history.
Test projection/zero results/frontend, build in isolation, then activate scoped
frontend and tenant presentation fixes with no database migration/provider action.
