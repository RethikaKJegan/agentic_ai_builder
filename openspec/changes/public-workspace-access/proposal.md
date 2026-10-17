# Restore private website access

## Why
Public pages currently show origin-denied backend errors, false empty counts and indefinite loading because local-only authentication was intentionally retained while Google Workspace was deferred.

## What Changes
- Show a single truthful workspace access state when the session cannot be established, preserving local draft storage.
- Prepare password-protected private preview access at the existing TLS reverse proxy, with exact original-origin/CSRF checks before trusted loopback forwarding.
- Keep public anonymous access denied and backend listeners private; Google Workspace remains a distinct pending production feature.

## Impact
Shared frontend access boundary and the existing Builder TLS virtual host only. No database migration, workflow mutation or new connector grant. Sign-in preference requested from the user before activating the access configuration.
