# Integration validation report

Checked (UTC): 2026-10-09T12:00:52.352007+00:00

| Integration | Status | Evidence / remaining setup |
| --- | --- | --- |
| Open-Meteo API | verified | GET forecast returned a numeric current temperature. |
| Open Library API | verified | GET search returned matching books. |
| Generic REST API Connector | verified | JSONPlaceholder GET /posts/1 returned the expected record. |
| GitHub REST API | verified | Authenticated GET /user verified; private repository permissions not tested. |
| Slack Incoming Webhooks | requires_approval | No message posted. An authenticated webhook test requires approval to post. |
| Gmail SMTP | verified | STARTTLS, AUTH, and NOOP verified. No email sent; delivery untested. |
| Brevo SMTP | requires_setup | SMTP username and app password/SMTP key are missing. |
| Google Sheets API | verified | Authenticated read of the configured resource succeeded; writes untested. |
| Google Docs API | verified | Authenticated read of the configured resource succeeded; writes untested. |
| Google Drive API | verified | Authenticated files.list succeeded; writes untested. |
| Google Calendar API | verified | Authenticated events.list succeeded; no event created. |
| Webhook Connector | verified | Local loopback POST accepted a valid HMAC and rejected invalid/tampered payloads. No external registration. |

## Limits

- Configuration and smoke checks only; registry/runtime wiring is not implemented.
- No emails, Slack messages, calendar events, billing, or external webhook registration.
- Local webhook is a POC receiver without replay protection; not exposed publicly.
