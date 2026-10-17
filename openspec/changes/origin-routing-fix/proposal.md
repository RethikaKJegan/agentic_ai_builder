# Correct shared website backend routing

## Why
The website's external HTTPS origin was forwarded directly into a loopback-only application. The resulting origin rejection appeared across all server-backed tabs. Temporary password authentication was subsequently rejected by the user; Google authorization is for connector access only.

## What Changes
Remove the temporary HTTP password gate, its credentials, and unfinished shared access-screen code. Retain explicit original-origin and cross-site/CSRF rejection at the Builder HTTPS reverse proxy before forwarding the API through its configured loopback origin. Preserve secure HttpOnly SameSite session cookies, private API listeners, existing workflows, connector credentials and prior UI corrections.

## Impact
Only the Builder virtual host and exact rollback of the preceding unfinished UI changes. Shared anonymous website access is explicitly selected by the owner, with the existing single workspace identity/permissions. This is not individual user authentication or a production identity deployment. No workflow/provider mutation or database migration is required.

## Workflow timeout exposed by restored access
The live database contains 56,050 workflow identities. Initial collection/overview reads attempted to load all documents and perform per-workflow queries, exceeding the API deadline. Add bounded keyset workflow pages, page-scoped overview reads and explicit first/next page controls with the real total; preserve all existing data and direct workflow reads.
