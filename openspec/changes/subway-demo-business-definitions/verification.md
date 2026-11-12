# Subway example-definition verification

## Implemented scope

- `ontology/subway/demo-business-definitions-v1.json`: eight restaurant procurement,
  finance and performance definitions with generated-example provenance. Definitions
  do not claim a new restaurant sales/POS source or an authoritative company policy.
- `workflow_api/subway_demo_definitions.py`: explicit leading-phrase selection,
  exact owner/workspace and immutable v4 ontology-hash checks, content fingerprint.
- `workflow_api/subway_queries.py`, `workflow_api/overview_automation.py`: provide
  the selected profile to existing intent discovery, with explicit request meanings
  overriding example defaults. Existing authorization and metadata bounds apply.
- `workflow_api/business_planning.py`: carry assumptions separately from cited
  ontology references. Existing saved definitions and source evidence stay intact.
- `workflow_api/action_plans.py`: retain the profile in existing query-planning
  knowledge context and add example disclosure instructions to new report actions.
- `tests/test_subway_demo_definitions.py`: selection/negation/version/tenant
  isolation, context/hash persistence, disclosure instructions and actual isolated
  Registry/CrewAI/runtime query execution.
- `docs/subway-manual-acceptance.md`: fifteen business/integration prompts,
  expected evidence, result recording and external prerequisites.

The selector is an explicit request convention, not a general natural-language
negation interpreter. Start a request with `Use Subway demo definitions v1.` to
select it. Existing requests without that leading directive receive no profile.

## Verification

- Initial new-profile + existing intelligence/evidence-resolution packet: **25 passed**.
- Follow-up profile packet after selector tightening and context assertion: **3 passed**.
  These overlap the initial packet and are not additional distinct coverage.
- Shared contract validation: passed.
- Generated UI contract consistency: passed.
- Strict OpenSpec validation: passed (`valid: true`, no issues).
- Whitespace check: passed.

Broader regression packet: **128 passed**, 218 retained deprecation warnings,
in 334.37 seconds. Covers shared business planning, Simpsons client isolation,
Subway complete queries, autonomous investigations, automations and existing
Overview automation. Together with the initial focused packet this is 153 passing
test cases across disjoint module selections; the three follow-up checks overlap.

Reproduce from the repository root with the existing integration environment:

```bash
env -u BUILDER_DATABASE_URL -u BUILDER_AUXILIARY_DATABASE_URL \
    -u BUILDER_CLIENT_ID -u BUILDER_TEST_POSTGRES_DSN \
    CREWAI_TESTING=true CREWAI_TRACING_ENABLED=false OTEL_SDK_DISABLED=false \
    PYTHONDONTWRITEBYTECODE=1 \
    .venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider \
    tests/test_subway_demo_definitions.py tests/test_subway_intelligence.py \
    tests/test_subway_evidence_resolution.py tests/test_business_planning.py \
    tests/test_simpsons_client_isolation.py tests/test_subway_full_queries.py \
    tests/test_subway_autonomy.py tests/test_subway_automations.py \
    tests/test_overview_automation.py
```

Tests use controlled model responses and synthetic operational rows. The runtime
query verifies all 100 fixture POs, not actual restaurant data. Disclosure is
verified in saved instructions/context; live model compliance with report wording
and live answer quality still require manual acceptance.

## Release and external prerequisites

Local implementation only. No deployment, service restart, credential change,
paid provider request, source write, real delivery or source import occurred.
No shared execution contracts, frontend files or Simpsons business definitions
were changed by this task. Existing unrelated working-tree changes were preserved.

Inspection found native Subway query/data and shared Google/research switches
enabled in local tenant configuration; this does not certify current token scopes
or delivery. The inspected backend/frontend service start times preceded latest
Phase 3 source edits. A hosted release and verification are separate from these
local tests; no claim is made that the new profile is already served publicly.

An example definition can choose a metric for a demo. It cannot establish absent
source values, equivalent store/site identities, actual attachment contents,
company tolerance rules, current-period coverage, real source-event authentication
or an operational refresh adapter. Missing external inputs remain qualified.

## Subsequent authorized deployment

The user subsequently explicitly requested deployment. See `deployment.md` for
the release and hosted verification; the no-deployment statements above describe
the initial implementation turn only.

Copied-store rehearsal exposed a real-metadata discovery bound that the smaller
fixtures had not reproduced. Discovery now retains every source descriptor and
supported relationship while bounding objective-ranked field suggestions, with
explicit returned/total field counts. These are metadata limits, not sampled
business totals. Dataset-only selection expands objective-ranked planning fields.
The full-data query executor, receipts and source processing limits are unchanged.

After that correction: **37 focused tests passed**, covering demo definitions,
intelligence routing and full-query semantics, including an oversized discovery
fixture retaining a requested field beyond the initial metadata positions.
The real copied-store discovery is 178,924 canonical JSON bytes, within the
existing 180,000-byte bound. Bootstrap and native discovery made no network or
model requests, started no workers and preserved protected copied-store records.

Production build and 14 + 20 isolated browser checks passed. Strict OpenSpec,
shared contracts and whitespace checks passed. The two browser selections overlap
in their existing generic-query journeys; these are not 34 unique test scenarios.
