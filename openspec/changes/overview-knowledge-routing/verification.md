# Knowledge routing verification — 10 November 2026

The exact reported prompt was “Explain what operating hours means using this
workspace’s business knowledge.” Hosted Simpson composition
`composition_99ef82a220a8675c162f77b9` correctly classified it as `knowledge` but
proposed a record query. Run `run_91929fc1ebb147659db78ae4d55631d2` failed with
`DATA_QUERY_INVALID`. Retrieved knowledge was missing from the content input.

The fix pins owner-scoped knowledge in the Overview intent, binds it to content
preparation, exposes only `content.prepare`, and requires provided citations.
Missing knowledge returns clarification. Query and lease validation are unchanged.

- Focused hotfix tests: 7 passed.
- Combined routing/API, retrieval, presentation, binding and population acceptance
  regressions: 107 passed, 10 warnings.
- Canonical contracts, generated contract drift, strict OpenSpec and patch
  formatting passed.
- Exact prompt completed with actual copied Simpson knowledge through existing
  Registry approval, CrewAI and runtime. Interpretation, plan and model response
  were controlled, with network blocked. No live-model acceptance is claimed.
  No record-query job was added and no tool call was recorded.
- Actual knowledge version: `bov_b573b6114fd3e5e361fe599692a20985`; reference:
  `concept:complaints:reported_operating_hours`; definition: “An operating-hour
  observation reported with a complaint.” Source basis remains
  `curated_supplied_blueprint_draft`, without claiming verified measurement or
  equivalent source fields.
- Authenticated HTTPS checks pass for all three accounts; six desktop/mobile
  browser journeys pass with zero page errors or overflow and API mutations blocked.
- The historical failed run's public view now explains the incorrect query plan.
  Its saved execution is identical to the pre-hotfix document hash.

Private evidence is retained in `.local/overview-knowledge-fix-20261110/`.
No paid model call, live workflow submission or provider write was used in checks.
