# Planner timeout recovery

A live restaurant workflow generation request raised OpenAI APITimeoutError after the 60-second provider timeout. This escaped PlannerService and was mislabeled INVALID_API_DATA by the API catch-all. Give planning a separate bounded timeout and translate SDK failures into safe retryable planner errors. Verify actual generation/save in isolated storage without publishing or provider writes.

Captured model responses also mixed static input with dynamic mappings and omitted closed save-field schemas. Normalize fresh, unambiguous disjoint input configurations into the supported expression mapping and tighten explicitly declared save-field objects when additionalProperties is omitted. Reject overlapping keys, unsupported literals and explicitly open schemas; preserve saved workflow semantics and never fabricate business output. Surface validation requirement codes after bounded correction instead of another generic provider failure.
