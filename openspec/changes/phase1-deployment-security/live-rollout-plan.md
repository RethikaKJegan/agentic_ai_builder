# Authorized live rollout — 2026-10-17

User requested loading the tested changes and checking public routing/network isolation. Google Workspace remains deferred. The prior public endpoint issued development sessions; the updated proxy will reject public API access until trusted production identity is implemented. Local development remains explicitly opted in.

Preserve existing systemd units and secrets. Add the two following nonsecret local-mode overrides; retain existing private backend port 8002 and UI port 3001. Atomically replace the active Next build with the verified build after stopping only the frontend. Check aggregate running jobs before gracefully restarting only the Builder backend. Existing database contention edits remain intact. Do not execute workflows or external tools during smoke checks.

## New backend drop-in

Path: `/etc/systemd/system/agentic-builder-backend.service.d/zz-phase1-local.conf`
Original: file does not exist. Exact new contents:

```ini
[Service]
Environment=BUILDER_ENVIRONMENT=development
Environment=BUILDER_DEV_AUTH=1
Environment=BUILDER_UI_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001,http://localhost:3100,http://127.0.0.1:3100
Environment=BUILDER_PLANNER_TIMEOUT_SECONDS=180
```

## New frontend drop-in

Path: `/etc/systemd/system/agentic-builder-frontend.service.d/zz-phase1-local.conf`
Original: file does not exist. Exact new contents:

```ini
[Service]
Environment=BUILDER_ENVIRONMENT=development
Environment=BUILDER_API_URL=http://127.0.0.1:8002
Environment=BUILDER_UI_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001,http://localhost:3100,http://127.0.0.1:3100
Environment=BUILDER_PLANNER_TIMEOUT_SECONDS=180
```

Back up the current .next directory in private local rollout storage. Roll back the build if service health fails. Public successful authentication, identity-bound CSRF checks and permission isolation remain untestable until Google Workspace authentication is implemented. Verify public session issuance is rejected, invalid origins fail, localhost session/read APIs work, HTTPS routing works, and backend listeners are loopback-only.
