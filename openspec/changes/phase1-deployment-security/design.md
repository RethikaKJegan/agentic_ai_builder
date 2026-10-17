# Design

Google Workspace production authentication is deferred by the user. Production startup fails closed. Local/test authentication is explicitly opted into, limited to loopback origins/hosts, and preserves existing server-owned permissions and worker identities. No Google credentials, sessions, or provider login adapters are introduced.

Origins use exact normalized scheme/host/port values. The launcher's merged configuration is passed directly to FastAPI. The browser uses only relative API routes. Private live upstream defaults to 8000; test API 8011 is explicit. The proxy forwards only permitted headers/cookies, preserves signed webhook bytes and streaming, and distinguishes transport failures from invalid response contracts. No mutation is replayed after uncertain transport failure.

Synchronous planning remains compatible with a deadline covering bounded planner attempts. Durable planning jobs provide scoped status, cancellation and retrieval independently of browser request lifetime. Canonical existing plan envelopes and workflow contracts are retained.
