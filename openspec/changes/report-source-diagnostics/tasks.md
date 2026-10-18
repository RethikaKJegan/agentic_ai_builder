- [x] Diagnose unique inventory sources with missing approved lookup links.
- [x] Surface safe setup guidance and preserve nonretryable status.
- [x] Verify accepted links succeed and proposed links remain blocked; deploy backend.

Evidence: 31 compiler tests and 2 API/Registry tests passed, including proposed-link rejection, accepted-link recovery, no LLM call on seed setup failure, actionable error response and real configuration edit rejection. Contracts, strict OpenSpec and diff validation passed. Backend and worker restarted. Live metadata inspection found current Atlas categories dataset meta_7b518434a9d75819fb0d401ba8397a3b and proposed relationship rel_88b890b14999e717e545a65e7de92ca9 to Supabase products. Prior workflow used a different category identity. No relationship review, cloud write, approval or workflow execution was performed. Generation still requires review of the current category link.
