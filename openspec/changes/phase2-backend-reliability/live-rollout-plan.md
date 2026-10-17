# Phase 2 controlled SQLite rollout

The live PostgreSQL migration is not part of this rollout. Preserve the existing database, connector state, credentials, frontend build, nginx, ports and local-only development authentication. The live combined backend is currently systemd-managed; stop it before starting a separate worker so old code cannot compete outside the new supervisor.

## Exact configuration additions

Add `/etc/systemd/system/agentic-builder-backend.service.d/zz-phase2-role.conf`:

```ini
[Service]
Environment=BUILDER_PROCESS_ROLE=api
TimeoutStartSec=180
TimeoutStopSec=240
```

Create `/etc/systemd/system/agentic-builder-worker.service`:

```ini
[Unit]
Description=Agentic AI Builder Background Worker
After=network.target agentic-builder-backend.service

[Service]
Type=simple
User=raf
WorkingDirectory=/home/raf/agentic-ai-builder
Environment=BUILDER_ENVIRONMENT=development
Environment=BUILDER_DEV_AUTH=1
Environment=BUILDER_UI_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001,http://localhost:3100,http://127.0.0.1:3100
Environment=BUILDER_PLANNER_TIMEOUT_SECONDS=180
Environment=BUILDER_PROCESS_ROLE=worker
ExecStart=/home/raf/agentic-ai-builder/.venv-integrations/bin/python scripts/run_builder_worker.py
Restart=always
RestartSec=5
TimeoutStartSec=180
TimeoutStopSec=240

[Install]
WantedBy=multi-user.target
```

The launcher loads existing private `.env` configuration directly, then explicit service environment settings. No full process environment is read/copied and no credentials are changed. The worker has no listening port. Keep existing backend port 8002 and frontend port 3001.

## Sequence and rollback

1. Complete regression, PostgreSQL, contract and specification checks. Save each changed original source from the earliest Phase 2 staging checkpoint into a private rollback directory; never use `git reset` because Phase 1 and prior user changes are uncommitted. Verify sufficient disk space and source hashes.
2. Inspect sanitized local session/health and database queue/active-run counts without printing workflow bodies or credentials. Stop only the managed Builder backend gracefully; existing combined workers stop with it. Verify the old PID/listener is gone. Preserve queued work; record any interrupted invocation for reconciliation.
3. While no Builder workers/API are writing, take online SQLite backups of the main and actual connector databases into a private mode-0700 directory. Do not copy raw WAL files or restore these backups during a successful rollout. Keep source paths unchanged.
4. Install only the exact additions above; run `systemctl daemon-reload`, start API, verify authenticated local read success, then enable/start the new worker. Observe ownership, durable backlog and bounded process behavior. The worker resumes **already configured** background activity; verification submits no new workflows, model calls, email or connector writes.
5. Verify HTTPS HTML, local authenticated reads, anonymous rejection, forbidden public development authentication, correlation IDs and loopback listeners. Frontend code/build is unchanged in Phase 2; no frontend restart is required.
6. If startup/read checks fail, stop the new worker and backend; restore the private Phase 1 source checkpoint, remove only the new backend role override, disable the new worker unit and reload/start the previous combined backend. Preserve live database contents and additive tables/indexes. Do not restore an older snapshot over post-rollout activity. Record recovery evidence before retrying.

This does not enable Google Workspace login or establish successful authenticated production requests.
