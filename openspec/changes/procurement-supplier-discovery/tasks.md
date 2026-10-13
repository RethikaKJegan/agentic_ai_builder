## Tasks
- [x] Restrict research recovery to recorded provider failures and map page transport errors to PAGE_UNAVAILABLE.

Follow-up verification: 24 focused supplier-discovery/native-procurement tests
passed, including unavailable section/page continuation and authorization denial.
Live read-only checks returned three results for piping and safety; the original
pump query failed, while its simpler `Water pumps suppliers` fallback returned
three results. Contracts and strict scoped OpenSpec validation passed. Backend
8002 was not listening; services and historical stopped projects were left
unchanged. No real RFQs or spreadsheet mutations were performed.
- [x] Recover public-page redirects/large HTML, contact links and transient search failures without replaying external writes.

Failure fix: live traces showed PAGE_UNAVAILABLE, PAGE_TOO_LARGE and SEARCH_UNAVAILABLE. Seven focused reader/fallback checks passed. A read-only live check confirmed one formerly oversized page with a published contact and a working pump search; two sites still reject requests with HTTP 403 and are skipped. Existing stopped runs are retained; no service restart or RFQ submission was performed.
- [ ] Implement search/page tools with bounded public-network access and evidence recording.
- [ ] Add discovery orchestration, candidate extraction, shortlist review and source provenance.
- [ ] Support generic setup modes and one project communication graph in the existing UI.
- [ ] Verify discovery, review authority, no duplicate sends, graph isolation and existing workflow compatibility.
