# Recover Google OAuth setup failures

The remote consent helper hides all failures behind a generic message. Add safe actionable diagnostics and account selection, retaining private redirect input and strict callback/state checks. Accept a scope-change token only when its actual grants cover every requested permission, including Sheets write access. Preserve the existing token on failure.

Provide an alternative using Google's OAuth Playground with the user's own web client and Google's HTTPS redirect. Import its refresh token through hidden local input, verify a refresh with Google's official token endpoint, and require explicit returned scope evidence before saving.

Follow-up diagnostics distinguish allowlisted structured Google refresh error codes without printing response descriptions. Refresh requests omit redundant Sheets readonly when write is configured; original requested permissions remain the validation authority. Reject plainly incorrect token input before network exchange.
