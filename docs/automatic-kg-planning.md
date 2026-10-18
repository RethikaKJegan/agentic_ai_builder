# Automatic KG planning

Overview now accepts a prompt and one Generate workflow action. It does not render
KG source checkboxes, the source preview panel, a Google account picker, or a
second review/open button. Successful save opens the workflow editor directly.
Failures keep the original prompt and provide retry; cancellation and duplicate
in-flight request protection remain. Existing unsaved browser edits are retained.

Before the existing model request, the backend searches the owned metadata index
using dataset/field names, descriptions, concepts and semantic relationships. It
passes a bounded candidate catalog (12 ranked candidates plus bounded structural
bridges, at most 16 sources/70 KB) to the planner. The planner selects the required
one-to-four execution dataset IDs and per-specialist source assignments. The
server checks those IDs against trusted metadata, pins actual selected sources
and semantics in the saved workflow, and preserves existing query/join validation.
There is no extra model call for source selection.

Public explicit source-preview/selection APIs remain compatible for existing
consumers. Their optional manual-choice behavior does not block Overview planning.
No-match or conflicting/missing evidence must remain unresolved in the proposal;
automation does not authorize invented data or missing joins. Catalog candidates
are not execution grants. More than four required execution datasets still needs
staging; the execution scope limit was not raised.

Existing server Google account behavior is used when no workflow-specific binding
is supplied. Account binding remains available in workflow details; no other
account is selected arbitrarily. Credential setup, validation, publish/release and
explicit external-action approvals remain unchanged. Generating a workflow does
not send mail, create sheets/events or commit database changes.
