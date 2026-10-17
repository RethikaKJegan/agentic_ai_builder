# Live rollout verification — 2026-10-17

This supersedes the earlier implementation report's statement that live services had not been restarted. The user explicitly requested deployment and verification. Google Workspace production login remains deferred.

## Deployment performed

- Retained systemd-managed service configuration and credentials; no complete process environments were read or copied. Automatic review rejected the proposed secret-bearing environment copy; it was unnecessary and was replaced with systemd-managed restart.
- Installed the exact nonsecret local-mode overrides shown in `live-rollout-plan.md` as `zz-phase1-local.conf` for both Builder services.
- Loaded tested Next build `2HahRkykuyEw0TDpukF8q` into the active `frontend/.next` directory. Preserved the previous build under `.local/phase1-rollout/previous-next` for rollback.
- Gracefully restarted only `agentic-builder-backend.service` and `agentic-builder-frontend.service`.
- Backend main PID changed from 3792423 to 3828449; frontend systemd main PID changed from 3652594 to 3828452. Both were active/running with zero automatic restarts at verification.
- Kept the existing private backend port 8002 and frontend port 3001. No nginx, firewall, DNS, Google credentials or unrelated projects were modified.

## Confirmed live behavior

Before deployment, the public HTTPS session endpoint returned a development session. After deployment it rejects public development authentication with 403 and does not set a session cookie. This closes a real exposure; it is not successful production authentication.

- HTTPS page: HTTP 200.
- HTTPS app: HTTP 200.
- HTTP redirect: HTTP 301.
- Public session blocked: HTTP 403 (`ORIGIN_NOT_AUTHORIZED`).
- Public workflows blocked: HTTP 403 (`ORIGIN_NOT_AUTHORIZED`).
- Backend anonymous read: HTTP 401 (`AUTHENTICATION_REQUIRED`).
- Backend anonymous mutation: HTTP 401 (`AUTHENTICATION_REQUIRED`).
- Backend unauthorized origin: HTTP 403 (`ORIGIN_NOT_AUTHORIZED`).
- Backend public Host rejected: HTTP 403 (`DEVELOPMENT_AUTH_LOCAL_ONLY`).
- Local session: HTTP 200.
- Local authenticated workflows: HTTP 200.
- Local authenticated overview: HTTP 200.
- Credentialed CSRF origin rejection: HTTP 403 (`ORIGIN_NOT_AUTHORIZED`).
- Credentialed wrong-port origin rejection: HTTP 403 (`ORIGIN_NOT_AUTHORIZED`).
- Cross-site session rejection: HTTP 403 (`ORIGIN_NOT_AUTHORIZED`).
- Expired local session: HTTP 401 (`AUTHENTICATION_REQUIRED`).
- TLS certificate validation passed using TLSv1.3; certificate expires Nov 17 13:51:58 2026 GMT.

Local session cookies were verified HttpOnly/SameSite=Strict. Authenticated local workflow and overview reads succeeded. Correlation IDs survived the proxy/backend boundary. Invalid origins, wrong-port origins and cross-site requests were rejected. No smoke request generated, saved, approved, published or manually executed a workflow. The malformed POST probes could not invoke a valid planner operation even if origin protection failed.

## Browser verification

- local desktop: session HTTP 200, durable planning advertised; zero page errors.
- local mobile: session HTTP 200, durable planning advertised; zero page errors.
- public HTTPS browser: page HTTP 200, API HTTP 403; zero page errors.

Desktop/mobile static assets loaded without errors. No browser called private backend ports directly. Screenshots and sanitized evidence are in `.local/phase1-rollout/`.

## Network isolation and limits

`ss` confirmed the backend listens only on `127.0.0.1:8002` and the frontend only on `127.0.0.1:3001`. The domain's nginx route forwards to the frontend, not directly to the backend. HTTP redirects to HTTPS. TCP connection attempts to the public hostname on 8000, 8002, 3001 and 8011 timed out. UFW is inactive; isolation here is established by loopback binding plus the observed public-port behavior, not by an enabled host firewall. Public-port tests were made from this server and are not an independent external network audit.

Existing configured background procurement workers continued their ordinary activity after restart. The completed runtime count increased from 51,681 to 51,711 during one observation window; dispatch-job counts were unchanged and no planning jobs were submitted. These are observations, not evidence of duplicate effects or proof that no background execution occurred. Smoke verification itself submitted no workflow/model/email actions. Full worker restart/idempotency validation remains Phase 2 work.

## Still deferred

Google Workspace login, individual production identities/permissions, secure production sessions, successful authenticated public requests, and identity-bound production CSRF/permission tests cannot be verified until that authentication is implemented. The public HTML application is reachable, but its API is deliberately unavailable publicly rather than exposing development-admin sessions. Local development remains functional. Do not describe this state as fully operational production deployment.
