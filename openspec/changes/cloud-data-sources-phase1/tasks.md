## Implementation
- [x] Add connection/catalog contract, encrypted storage and cloud adapters.
- [x] Add leased background profiling and authenticated routes.
- [x] Add Connections/Metadata UI, navigation and Integrations summary.
## Verification
- [x] Verify ownership, encryption, failures, refresh/disconnect races and adapter metadata.
- [x] Verify frontend types/build and desktop/mobile flows.
- [x] Document configuration, manual acceptance and remaining live-cloud checks.

## Verification evidence
- 48 focused Python tests passed: new data-source ownership/encryption/discovery,
  route safety, credential replacement, refresh/disconnect races, leased recovery,
  catalog contract, plus existing Google connection/tool and native procurement tests.
- 12 frontend tests passed (new Data Intelligence and existing Google UI).
- TypeScript and scoped ESLint passed; isolated production build passed.
- Existing shared-contract validator and strict OpenSpec validation passed.
- Actual preview and deployed public UI checked at 1366×768 and 390×844:
  Atlas/Supabase forms, credential clearing, metadata navigation, Integrations
  summary and existing Google section; no page errors or horizontal overflow.
- Deployed API/worker/frontend services are active. Rollback frontend artifact:
  `.local/ui-rollbacks/data-sources-phase1-20261017-200449`.
- No live Atlas/Supabase credentials were supplied. Real-cloud acceptance remains
  a user UI check; discovery fixtures do not establish successful cloud access.
- No Praxi files were modified. No external email or database write was performed
  by these checks. The temporary preview listener was stopped.

## Atlas discovery compatibility repair
- [x] Remove unsupported top-level batchSize from listCollections in test and profile paths; retain dataset and time limits.
- [x] Add regression coverage rejecting unexpected command options, run focused tests and contract checks.
- [x] Verify read-only discovery against the user-provided Atlas connection and restart backend/worker.

Repair evidence: 22 data-source tests passed; shared-contract and strict OpenSpec
validation passed. The supplied Atlas credentials authenticated successfully.
After removing batchSize, connection testing and bounded profiling succeeded for
categories, customers, employee_territories and employees with no warnings.
No document values or credentials were persisted by the diagnostic. Backend and
worker restarted successfully and the API responded with its expected
authentication requirement (HTTP 401 for an unauthenticated request).

## Supabase deployed TLS trust repair
- [x] Configure the existing PostgreSQL CA setting with system roots plus the official Supabase Root 2021 CA; preserve verify-full.
- [x] Verify connection and bounded metadata discovery with the supplied account, validate contracts and focused checks, then restart backend and worker.
- [x] Document certificate provenance and successful live verification without credentials.

Repair evidence: 22 tests, shared contracts and strict OpenSpec passed. Live
deployment environment connection and profiling passed (7 tables, 0 warnings).
Both restarted services are active; unauthenticated API returns expected HTTP 401.
