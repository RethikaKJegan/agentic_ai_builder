# Workspace login

Add the owner-requested fixed engineering account login between Launch Workspace and /app. Preserve local-builder/local-workspace identity, existing connector authorization, database contents and action approvals. This supersedes the earlier owner preference for an ungated shared website.

Use a server-only password hash and signing key, an eight-hour HttpOnly session, server checks on workspace pages and backend proxy traffic, same-origin login/logout and bounded login attempts. Retain signed webhooks and the independently bound Google OAuth callback. No planner/runtime/shared-contract changes or external provider writes.
