# Design

Keep the v2 API and backend unchanged. Build source labels by walking node
parent_id references, excluding synthetic business entities. Render a keyed entity
source-list component with a 100-item initial page, explicit visible/total count,
and Show more entity sources control. Its state resets on entity navigation and
survives polling the same entity. Render ordered relationship field pairs as
source-qualified buttons; retain declared direction versus suggested/unknown
meaning. Selecting a field opens its existing metadata and mapping panel without
requiring management permission. Preserve existing scoped relationship filtering.

Add unit coverage for >100 mappings, source identity, refresh, entity switching,
and field navigation in read-only/stale views. Extend desktop/mobile browser
fixtures to exercise real click behavior; fixtures do not establish live data
correctness. Record fresh checks separately from prior deployment evidence.
