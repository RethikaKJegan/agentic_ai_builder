- [x] Select only executable optional enrichments; retain core evidence validation.
- [x] Label omitted enrichment and disclose limitations in report/delivery output.
- [x] Test partial flows and existing approvals, then deploy and verify generation.

Evidence: 69 tests passed across report planning, native runtime, worker authorization and general planner. A final 33-test compiler run also passed, including ambiguous lookup omission. Native runtime tests cover complete and partial reports, all three approval rejection paths, verified spreadsheet links and limitation disclosure in spreadsheet/email/meeting output with offline transports. Missing quantities still fail. Contracts, strict OpenSpec, Python compilation and diff checks passed. Backend/worker restarted. Live generation uses current products/suppliers while leaving proposed categories unqueried; no live external actions are approved or executed.
