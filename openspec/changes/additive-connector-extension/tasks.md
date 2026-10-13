## 1. Extension implementation
- [x] 1.1 Add canonical tool definitions and bounded transport/credential helpers.
- [x] 1.2 Add restricted multi-sheet adapters, Calendar operations, Gmail operations and optional search.
- [x] 1.3 Add isolated application composition, launcher and separate OAuth setup.
- [x] 1.4 Document configuration, activation, limitations and examples.

## 2. Verification
- [x] 2.1 Verify actual adapters offline, including denial and failure boundaries.
- [x] 2.2 Verify Registry/runtime integration and action approval with isolated fixtures.
- [x] 2.3 Run existing regression suites, contracts and strict OpenSpec checks.
- [x] 2.4 Confirm all pre-existing tracked file hashes are unchanged.

Verification: 31 extension tests, 275 existing backend tests, 90 existing frontend tests, typecheck/lint, isolated UI build, both desktop/mobile browser scenarios, contracts/client drift, pip consistency and strict OpenSpec passed. All 484 pre-existing tracked file hashes are unchanged. Evidence: connector_extension/VERIFICATION.md and .local/connector-extension/verification/. No live provider operation or existing workflow modification occurred.

## 3. Generalized Sheets follow-up
- [x] 3.1 Enable account-accessible Sheets without configured resource IDs; retain optional operator ceilings.
- [x] 3.2 Add bounded tab/header discovery and prompt-link planner discovery.
- [x] 3.3 Bind writes to reviewed workflow targets and normalize spreadsheet links internally.
- [x] 3.4 Verify different spreadsheets across workflows, consent/access denial, ceilings and write isolation.

Generalized Sheets verification: 41 extension tests, 275 original backend tests, both desktop/mobile browser flows, contract/client checks and strict OpenSpec passed. All 484 original tracked file hashes are unchanged. Only extension files and its planning artifacts were updated.

## 4. Generalized connector defaults
- [x] 4.1 Add account-accessible Calendar discovery and event operations without fixed calendar IDs.
- [x] 4.2 Discover connected Gmail identity and support workflow-selected recipients without fixed sender/recipient setup.
- [x] 4.3 Keep search, message/thread selection and attachment references driven by workflow inputs; add runtime search filters.
- [x] 4.4 Verify optional restrictions, workflow approval, different resources and unchanged original files.

Generalized connectors verification: 53 extension tests, 275 original backend tests, 90 original frontend tests, typecheck/lint, both desktop/mobile browser flows, contracts/client drift and strict OpenSpec passed. Verified independent workflow approval retention and explicit snapshot revocation. All 484 original tracked files remain unchanged. Evidence: connector_extension/VERIFICATION.md and generalized-features-* records under .local/connector-extension/verification/.

## 5. Live attachment identifier compatibility
- [x] 5.1 Accept bounded opaque Gmail attachment IDs longer than 255 characters.
- [x] 5.2 Verify actual adapter handling, reject oversized/invalid IDs before requests, and repeat the live dummy attachment download.
- [x] 5.3 Resolve stable MIME-part references across changing Gmail attachment IDs and verify downloaded bytes.

Live attachment verification: Google returned 404-character rotating opaque IDs. Extended the extension-only input bound to 4096 and added stable MIME part references resolved against the exact selected message. All 55 extension tests and strict OpenSpec pass. Actual Gmail message read/download workflows retrieved the 71-byte dummy file and verified exact contents. All 484 original tracked files remain unchanged. Evidence: .local/connector-extension/verification/attachment-id-tests.log and live-gmail-attachment-result.json.
