# Subway selection integrity verification

The saved failed job `plan_647c6ca5dc9c4beeabd4791cf432864b` contains `SUBWAY_QUERY_DENIED`: selected fields outside chosen datasets. Failed jobs do not retain the raw model selection, so the exact offending field cannot be reconstructed.

The intent schema previously accepted arbitrary identifier strings and independent source/field lists. The fix constrains generation to current advertised canonical identities and normalizes metadata membership using current authorized field ownership and selected relationship endpoints. Unknown identifiers, cross-tenant access, more than four source datasets, and unsupported joins remain rejected. The query validator itself remains unchanged. No company-specific field aliases, prompt matching or new joins were added.

Provider schemas reserve enum and string capacity for the rest of the routing schema and bound optional field choices. Individual field enums contain at most 200 entries. Limits checked against the [official Structured Outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs). Empty field selection continues the existing metadata expansion path.

Validation: 28 focused selection/intelligence/routing tests and 43 existing Simpsons isolation, Overview integration, full Subway query and demo definition tests passed (71 total). Shared contract validation, generated UI contract check, OpenSpec strict validation and git diff whitespace checks passed. Existing framework deprecation warnings remain.

Copied-store replay used the exact reported objective and three variants, all 52 source descriptors, connected account and recipient, with networking disabled. It reproduced the inconsistent field-owner selection condition and passed normalization plus strict preparation. Routing envelopes stayed between 218,882 and 218,941 bytes, below 220,000. The original raw model decision was not replayed; controlled responses tested metadata consistency. No copied protected records changed.

Backend deployment reloaded only `agentic-builder-subway`. HTTPS checks passed for all three workspaces, including foreign source rejection. Configurations, credentials, ontology packages, automation records, frontend build, histories and other service processes were preserved. Private rollback, backup, checks and live generation evidence reside in `.local/subway-selection-integrity-20261112/`.

Live hosted check: the exact original objective succeeded through the normal authenticated planning queue, HTTP status 200, state `prepared`, job `plan_c0461db8a3674129a23fb2acf672d7dd`, composition `composition_7bd3c8256cda7aa0cf742955`. This created an inert draft only. Runtime run/event, automation and data-query job counts stayed unchanged. No workflow was executed and no email sent. This verifies live draft generation, not resulting business findings or email delivery.
