# Registry approval submission fix

Submission currently requires all tool grants to be approved before a revision can enter approval review. Permit submission when every referenced tool has an authorized or pending-approval assignment and the only Registry reasons are approval-required and its uncovered-tool summary. Submission must not install approval evidence or enable execution. Continue blocking unresolved requirements and all denied/missing assignments, returning bounded actionable requirements through the existing error details rendered by the UI. Preserve revision, ownership and idempotency checks. No workflow, destination, credential or shared-contract changes.

The user subsequently chose “Only fix submission and show the missing setup.” Automatic spreadsheet creation/export is excluded from this change. Preserve the saved workflow and its unresolved destination requirement.
