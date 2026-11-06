# Design

Use one backend process and application store per client. This avoids shared mutable
request authority and also isolates background jobs, caches, connector instances,
workspace-wide context and code paths that historically rely on a single operator.
The website maps verified account credentials to a signed account-bearing cookie.
Its proxy selects the configured private Simpsons upstream, strips browser authority
headers, and signs a 60-second assertion with a separate per-client secret. The
backend verifies the assertion on every route, including session bootstrap. The
shared backend rejects these assertions; the proxy verifies the responding client.

The tenant store must have a matching provisioned marker. Provisioning creates a
new store, copies only the selected ontology and its two explicit source bindings,
metadata and policy definitions, and re-encrypts credentials with a new tenant key.
No shared workflows, context, integrations, histories, queue entries or arbitrary
company resources are inherited. New workflows use the normal scope-aware APIs.
All existing immutable ontology version IDs and pinned definitions are retained.

Provider credentials must be provisioned independently for this process; the tenant
launcher must not inherit the shared .env file. Browser draft storage is cleared on
account changes, including tab-local fallback state. Deployment requires private
account credentials, a dedicated upstream and tenant-only source/provider access.
