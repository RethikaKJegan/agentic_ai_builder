# Mixed report inputs and explicit India-time schedule — 6 November 2026

The reported overlapping target was recovered in backend diagnostics: `prepare_review_package` bound a known workspace-context snapshot and several complaint/inspection/warranty/replacement/history/recurrence/comparison/search outputs to the same `data` target. Existing normalization coalesced upstream outputs alone but rejected their mixture with context. The original model correction retained the mixture. An earlier rejected proposal also redundantly repeated `research_request` in its own source path.

Automatic goal-mode content preparation now retains known whole-object context as primary data and lets the existing runtime attach every explicit upstream result. Multiple whole contexts are bundled with their original keys rather than discarded. Data-reference dependencies are materialized before coalescing, so all evidence-producing actions remain dependencies. This is restricted to whole `data` objects with empty paths and known context/upstream sources. Partial bindings, unknown keys, other tool inputs and receipt requirements still undergo strict validation; receipt bindings are not silently dropped or downgraded. No stored or approved revision is modified.

A redundant known research context path is removed only when it repeats the selected key and no actual child with that name exists. Legitimate same-name nested values remain intact.

The exact user phrase “10 AM India time” is now accepted as an explicit hour-only 12-hour clock and the unambiguous Asia/Kolkata timezone. Existing IANA timezone and minute-precision inputs remain supported. Dates, duration and timezone must still be supplied; missing/invalid/ambiguous schedules are not guessed. The expected review is 10 November 2026, 10:00–10:30 AM Asia/Kolkata.

Targeted verification: 13 passed, 44 deselected. These exercise actual Registry/CrewAI/GraphRunner with controlled providers, preserve all mixed context/source results through execution, test one and multiple contexts, protect explicit receipt requirements and cover India-time/IANA clock formats plus existing invalid-schedule cases. Full affected-suite and public exact-prompt results are recorded after completion. Private evidence, the exact unchanged user prompt and prior source copy are under `.local/mixed-content-fix-20261106/`.

## Deployed exact-prompt verification

The user's unchanged prompt generated `composition_b178fb18c114445f09c44581` through the public frontend with the actual configured model in one planning call. Generation and canonical compilation both returned HTTP 200. Its 16 actions include web search, populated Sheet creation, Gmail send and Calendar creation, without missing inputs. The self-recipient matches the selected account. All output references have explicit dependencies, and all three write actions retain exact-payload approval. The parsed Calendar schedule is 10 November 2026, 10:00–10:30 AM Asia/Kolkata in the selected account's primary calendar.

Public desktop/mobile normal-login reads passed with zero browser errors or failed API reads. The exact-prompt desktop screenshot was visually inspected. There are zero runtime executions for this draft: no search, Sheet, email or Calendar action was executed. This verifies generation and compilation, not the final business report or live external provider outcomes.

The backend/worker source fix is deployed. All three services are active with zero automatic restarts. No frontend rebuild, database migration, Git commit or push was performed. Prior rejected attempts and approved workflow revisions remain unchanged.

[Open the verified exact-prompt draft](https://praxi.bellcorpstudio.com/app/workflows/investigate?connected=1&composition=composition_b178fb18c114445f09c44581).

Final affected suites: **90 passed** (goal planning and connected runtime); the earlier 13 targeted tests overlap and are not added. Shared contracts and whitespace checks passed. Existing deprecation warnings remain.
