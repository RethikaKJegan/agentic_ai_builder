- [x] Ground ordered evidence lines without accepting invented facts.
- [x] Recover evidence-only pending quotes using recorded source and normal qualification guards.
- [x] Run focused offline checks and scoped validation.

Four focused evidence tests pass, including invented numbers, numeric prefixes,
reordered lines and mail whitespace. The actual recorded Pump extraction passes
the corrected check. In a temporary local database copy, its existing quote
progressed to QUALIFYING using normal store guards; repeating recovery created
no duplicate. Contracts, strict OpenSpec and diff checks pass. No private data
was sent externally, no live records changed, no emails sent and no service
restarted during verification. Worker recovery requires loading the new code.
