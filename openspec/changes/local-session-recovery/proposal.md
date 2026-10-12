# Local session recovery

Restarting the local backend rotates its development session cookie. Open UI tabs retain the old cookie, report AUTHENTICATION_REQUIRED on overview polling, and never reconnect or clear the error.

Renew a validated local-development session on explicit authentication rejection and retry the rejected request once with its original body and idempotency key. Share concurrent renewals. Clear the stale authentication banner after overview recovery. Keep non-local sessions and authorization failures explicit.
