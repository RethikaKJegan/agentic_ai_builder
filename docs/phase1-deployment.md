# Phase 1: local UI/backend corrections and deferred production login

Google Workspace production authentication was explicitly deferred by the user on 2026-10-17. It has not been implemented or configured. Production startup fails closed until that work is completed. Do not expose development-admin sessions publicly or declare this application production-ready.

## Local startup and private routing

Run the local backend explicitly:

```bash
BUILDER_ENVIRONMENT=development BUILDER_DEV_AUTH=1 .venv-integrations/bin/python scripts/run_live_backend.py
```

The live backend still binds only to `127.0.0.1`, default port 8000. If another service occupies 8000, use an available explicit `--port` and use that same port in Next's server environment. Do not stop unrelated services. The subsequent user-authorized live rollout restarted the backend on 8002 and UI on 3001 with these tested changes. Both retain loopback-only bindings. See `openspec/changes/phase1-deployment-security/live-rollout-verification.md`.

Run Next from `frontend/` with matching configuration:

```bash
BUILDER_ENVIRONMENT=development BUILDER_API_URL=http://127.0.0.1:8000 npm run dev -- --hostname 127.0.0.1
```

`BUILDER_API_URL` is server-only. Browser clients use `/api/backend/...` exclusively. The proxy defaults to live port 8000. Port 8011 remains explicitly configured only by the browser test harness. A configured nondefault live port such as 8002 remains supported.

Set `BUILDER_UI_ORIGINS` explicitly on both services if changing UI ports. Comma-separated entries are trimmed and matched by exact scheme, host and port. Local defaults cover localhost/127.0.0.1 on 3000, 3001 and 3100. Remote origins are rejected in development. Production origin configuration supports `https://praxi.bellcorpstudio.com`, but production backend startup intentionally refuses until trusted authentication is implemented. No wildcard CORS was added.

The proxy validates its upstream at startup through Next instrumentation, rejects public upstream destinations/credentials/paths/query strings, and never follows upstream redirects. It permits configured private IPv4 addresses, loopback or internal single-label service names. Reserved proxy handling for login redirects does not implement Google authentication; no backend Google routes exist.

## Proxy behavior

- Normal API timeout: 30 seconds.
- `BUILDER_PLANNER_TIMEOUT_SECONDS`: 30–300 seconds per provider attempt, default 180. Set the same value for both services. Synchronous proxy and planning-job lease use four provider deadlines plus 30 seconds to cover bounded generation/correction attempts.
- Maximum proxy request body: 2 MiB, checked against declared and streamed byte counts.
- Authenticated responses and errors use `Cache-Control: no-store`.
- Only permitted session cookies and selected headers are forwarded. Correlation and request IDs are sanitized and preserved. Backend errors use canonical contracts; malformed JSON, invalid contracts, wrong service, unavailable service and timeouts have separate codes.
- Mutations are not replayed after a transport failure or timeout. Existing local session recovery retries only explicit pre-execution 401 rejection, preserves exact bodies/idempotency keys, and does not operate for known production sessions or remote browser hosts.
- SSE response bytes and reconnect cursors are forwarded. The establishment timeout ends after stream headers; cancellation/disconnect cancels the upstream stream.
- Signed provider webhook bytes and signature/timestamp headers are preserved. The backend verifies signatures; Slack's verification challenge remains supported.

## Durable planning API

This additive transport extension uses the existing canonical request/response envelope and existing authoritative workflow schemas. No shared v1 contract or generated validator changed. Job data is documented here as `planning-job-v1`: `{job_id, state, result}`. State is queued, running, succeeded, failed or cancelled. `result` is null or a canonical planning response envelope. Future promotion into `shared/contracts/` requires shared-owner review.

- `POST /planning-jobs`: canonical `plan_workflow` request; returns HTTP 202 and a job reference.
- `GET /planning-jobs/{job_id}`: current scoped state and confirmed result.
- `DELETE /planning-jobs/{job_id}`: idempotently cancels queued/running work; completed results remain completed.

All endpoints require a valid session and `workflow.plan`, scoped to workspace and subject. Requests and results use the existing SQLite database in the additive `builder_planning_jobs` table and queue index. Queued work survives restart. Running work has a bounded lease; expired work is marked `PLANNING_INTERRUPTED`, without automatic paid-model replay. Claim fencing prevents late cancelled/interrupted results from replacing terminal state. Providers run outside database transactions. The job worker never saves, approves, publishes, activates or executes a workflow.

Session data advertises `planning_jobs_available`. The UI uses jobs only when advertised and remains compatible with synchronous backends. Overview shows actual job state/reference, supports cancellation and preserves the prompt on errors. Cancellation discards eventual results and cannot undo model usage already incurred. Confirmed failure/cancellation permits a fresh key on the next explicit user retry. Unknown transport outcomes retain the original key. A status error exposes the job reference for recovery; direct GET remains available after reconnect/refresh. Persistent in-UI job resumption across page reload is not implemented.

The planning worker is scoped to the current local single-service deployment. Full production worker separation, queue operations and PostgreSQL are Phase 2 work; this is not a verified multi-replica production deployment.

## Production reminder

Before public deployment, implement Google Workspace login, server-validated individual identities, workspace/role/permission mappings, secure expiring HttpOnly sessions, CSRF enforcement, approval separation, revocation, trusted automation identities and actual HTTPS smoke tests. Configure a Google OAuth web client and the actual Workspace domain; connector authorization tokens are not login identity. Production authentication and public authenticated success remain deferred/unverified.

Keep backend ports private. The observed Builder backend listener was loopback-only; this is not a full firewall or external-internet exposure audit. No firewall, reverse-proxy or credential configuration changed. The live services now have explicit local-mode systemd overrides; public development authentication is blocked until Google Workspace login is implemented.
