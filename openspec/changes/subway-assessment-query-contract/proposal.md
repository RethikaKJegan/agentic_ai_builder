# Generic assessment detail-query compatibility

The model produced a valid detail query with extra base fields, but the assessment required an exact ID-only projection. The connector raised an API error that the runtime hid as INVOCATION_FAILED. Validate the caller's complete detail query, then select native IDs deterministically for all registered assessments without changing filters, ordering, offset or bounds. Preserve typed API error codes at the runtime connector boundary and classify expected failures accurately. Deploy Subway only; no live external/model actions or Simpson mutations.
