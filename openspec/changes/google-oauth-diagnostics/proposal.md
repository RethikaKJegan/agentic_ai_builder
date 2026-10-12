# Recover Google OAuth setup failures

The remote consent helper hides all failures behind a generic message. Add safe actionable diagnostics and account selection, retaining private redirect input and strict callback/state checks. Accept a scope-change token only when its actual grants cover every requested permission, including Sheets write access. Preserve the existing token on failure.
