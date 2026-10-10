# Design

Keep provider secrets in .env and Google credentials/tokens in credentials.json/token.json, all ignored by Git and restricted to owner access. Preserve existing settings and append missing names. Use HTTPS GET requests and SMTP STARTTLS authentication without message submission. Validate public API response shapes. Use read-only Google scopes and specific resource IDs for Sheets/Docs. A Slack incoming webhook cannot be fully validated without an approved message and remains unverified. Generate a local 256-bit webhook secret and test HMAC verification on a loopback-only endpoint without external registration. Reports contain status and safe error categories only, never response bodies, credential values, or sensitive URLs.

Browser automation is not currently connected. Provider credential creation pauses for user connection/authentication. Connected application credentials are not exportable local API credentials and must not be extracted.

The local Google authorization helper uses a fixed loopback callback at http://127.0.0.1:8765/. An existing Web application OAuth client must register this exact authorized redirect URI.
