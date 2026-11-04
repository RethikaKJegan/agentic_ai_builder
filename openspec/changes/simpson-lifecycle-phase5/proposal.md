# Simpson twelve-stage lifecycle on Phase 4

Configure the exact twelve requested stages in a versioned process manifest, reuse
BusinessCases, EvidenceCompletion, BusinessComposition and the existing Registry /
master-child / CrewAI runtime. Add a bounded command-loop driver and deterministic
persisted analytical reports. No frontend, new agent engine, source write or live
external action is part of implementation verification.

Inspected integration baseline: Phase 4 case/command tables and CAS revisions;
business-lifecycle-v1 and business-case-v1 contracts; mapped shared preparation;
catalogue and composition signatures; signed lifecycle context; runtime run-creation
hook and guarded recovery; existing HTTP auth and business_cases CLI; Phase 4
verification and deterministic Registry/runtime fixtures.

Concrete contract gap: Phase 4 event requirements always block their analytical
stage. Add optional `blocking: false` to an event requirement, allowed only for
provisional analytical/read stages. The actual wait stays pending and authorization
events still require existing approval authority. Protected approval values are
never generated. Existing definitions default to blocking behavior.

Also resolve conjunctions with a known false predicate as skipped even if another
predicate is unavailable; a rejected warranty must not wait on an unexecuted branch.

The driver calls existing prepare/start/advance/resume commands, stores bounded
request progress in the existing command receipt table, stops at real waits and
never approves workflows/actions or automatically retries uncertain effects.
