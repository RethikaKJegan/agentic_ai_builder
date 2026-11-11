# Verification — 10 November 2026

Automatic Overview planning is question-free when the server-owned
`BUILDER_QUESTION_FREE_WORKFLOWS=1` setting is enabled. Planning uses available
workspace context and supported defaults. A symptom investigation without a case ID
may review similar historical records and must distinguish preliminary evidence
from a diagnosis of the user's engine. Explicit identifiers and constraints remain
part of the request.

Unresolved requirements create saved blocked drafts with empty question lists.
These drafts have no selected tools or schedule. Canonical unresolved-requirement
metadata prevents approval/execution, and composition verification rejects removal
of that metadata. Authorization errors remain errors. Runtime queries with unresolved
meaning or unsupported operations remain blocked; the UI shows limitations rather
than clarification answer forms.

Evidence:

- Backend routing, action preparation, query integration and defaults: **112 passed**.
- Final policy regression after adding explicit no-ID preliminary-investigation guidance:
  **32 passed** (overlapping cases, not 32 additional unique tests).
- Frontend: **564 passed** across 86 files.
- Exact isolated production artifact: **18 desktop/mobile browser checks passed**,
  including automatic navigation, blocked drafts, disabled approval, no answer fields,
  queue retries, refresh recovery and query coverage display.
- Production build, TypeScript, source ESLint, canonical contract validation,
  generated UI contract check and strict OpenSpec validation passed. Source lint
  excludes historical retained Next artifacts; the repository-wide lint command
  also scans those generated artifacts.
- Copied Simpson store: startup/session/source/query/investigation APIs passed;
  protected historical rows unchanged; controlled missing-requirement interpretation
  created a blocked draft with no questions; removing its blocker was rejected.
  Networking and workers were disabled during rehearsal. No paid model calls,
  source execution or provider delivery were performed.

The tests use controlled interpretation/planning responses. They establish the
fallback, context, integrity and UI behavior; they do not establish that every live
model response will produce a fully executable investigation. No new full-text or
semantic query operator, cross-source relationship, complete symptom search or
verified engine diagnosis is claimed. Bounded qualitative review must disclose
truncation, preserve source identity and avoid duplicate counts for overlapping
reads of one source. Missing capabilities remain limitations.

Hosted verification and preservation results are recorded in [deployment.md](deployment.md).
