# Verification — 10 November 2026

Saved failed run: `run_a938964ef45a47b3858068bb69778899`.
The query-planning model failed typed validation twice; no source step ran. The
previous runtime persisted a generic correction hint but neither rejected query
nor exact validation reason, so the original specific violation cannot be proven.
No claim is made that the source, recipient or a particular field caused this run.

The correction constrains the model response schema for catalogues without authorized
joins: each permitted base dataset has its own projected-field enum. An empty-source
clarification branch is retained. Aggregate/count and valid source projections still
fit. Catalogues with relationships, more than 12 datasets, over 700 field definitions
or specialized schema size over 100 KB retain the existing schema and strict validation.
These are transport bounds, not new data access permissions. No source is selected
by this helper, no field is silently dropped and explicit tool payloads are unchanged.

Correction feedback now includes the trusted typed validator's precise rule. Failed
model validation also records agent.output_rejected with a bounded rule in run events,
including the final unsuccessful attempt. Raw rejected model output and source rows
are not logged. Existing two-call, token/cost, permission and source guards remain.

Rehearsal on a fresh copied Simpson store reused the actual failed run's reviewed
catalogue. Controlled valid source projection passed the specialized schema; a foreign
projection failed it and received precise unavailable-field feedback. Protected rows
were unchanged, networking and workers were disabled. This is not reconstruction of
the missing rejected model output and not a live model/source execution claim.

Regression coverage includes schema source coupling, independent dataset selection,
clarification/count output, relationship/large-catalogue fallbacks, exact safe feedback,
durable queries, worker lease fencing, bounded correction failure and success, recorded
rejection diagnostics, existing clarification behavior and email drafting/delivery
preparation. Test counts and deployment checks are recorded in deployment.md.

Verification does not call paid models or submit email, Sheets or Calendar writes.
The change prevents foreign projected fields at model transport for the bounded
no-relationship case; it cannot guarantee every future model output or unsupported
operation succeeds. Invalid plans must still stop before source execution.
