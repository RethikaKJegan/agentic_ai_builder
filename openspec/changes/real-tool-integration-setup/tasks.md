# Tasks

- [x] Preserve .env values, add provider configuration and .env.example placeholders, and protect secret files.
- [x] Validate public APIs and local webhook with safe requests.
- [ ] Obtain provider credentials through authorized browser workflows; pause for manual authentication or unavailable automation.
- [ ] Validate authenticated SMTP, GitHub, and Google APIs without external writes; request approval for a Slack message test.
- [x] Write validation evidence and exact remaining manual steps; validate shared contracts and existing tests.

## Evidence and pending intervention

Public HTTPS checks and the loopback webhook positive/negative checks passed; see docs/integration-validation.md. Shared contract validation passed and all 14 existing unittest cases passed. No authenticated provider credentials have been created. Eight integrations remain pending provider setup; browser automation connection and user authentication are needed. OpenSpec CLI is not installed in this environment, so CLI validation of this change is pending. Planning/specification artifacts exist and no shared contract was changed.
