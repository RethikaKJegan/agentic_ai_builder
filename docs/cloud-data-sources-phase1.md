# Cloud Data Sources — Phase 1

## Delivered scope

Data Intelligence (`/app/data-intelligence`) connects MongoDB Atlas and Supabase
PostgreSQL, automatically queues real metadata discovery and displays versioned
snapshots. Integrations shows summaries from the same connection records.
Google accounts, procurement and existing workflow contracts are preserved.
Praxi was read as a reference only; no runtime dependency points into its folders.
Knowledge graph inference, question routing, business queries and CRUD belong to
later phases. This phase reads MongoDB samples and PostgreSQL metadata only.

## Configuration

Install `requirements-data-sources.txt` in the backend/worker Python environment.
Set `BUILDER_DATA_SOURCE_KEY_FILE` to an existing persistent Fernet key file readable
only by the service identity. If unset, the existing `BUILDER_GOOGLE_KEY_FILE` is
used. Never rotate/delete a key without migrating encrypted credentials.
Backend and worker must use the same key and application database.

`BUILDER_DATA_SOURCE_CA_FILE` optionally supplies a trusted PostgreSQL CA bundle;
the default is `/etc/ssl/certs/ca-certificates.crt`. TLS certificate/hostname
verification is required. Do not disable it to work around connection errors.

The existing supervised worker includes `DataSourceWorker`. A stopped worker leaves
new jobs queued; the page does not pretend discovery succeeded. Worker health is
available through the existing Monitoring worker-health endpoint.

The current deployment still has a shared local demo identity. Ownership checks
are enforced against the authenticated subject/workspace, but users sharing that
identity share its connections. Use dedicated demo databases until application
user sign-in is configured.

## Manual UI acceptance

1. Open https://praxi.bellcorpstudio.com/app/data-intelligence.
2. Select Connect MongoDB Atlas. Use the Atlas Drivers URI with database username
   and password, select one database, and enter a connection name. Percent-encode
   URI password characters. Enable server network access in Atlas and use a user
   authorized to list collections/indexes and read the selected collections.
3. Test connection, then Connect and profile. Confirm queued → running → ready.
4. View metadata. Compare collection names, nested paths, mixed field types and
   indexes against Atlas. No document values are saved in the catalog. Field
   presence is measured against at most 25 sampled documents, not a full schema.
5. Connect Supabase PostgreSQL using the database connection string from its
   Connect dialog, not the Supabase API URL/anon/service-role key. Choose direct,
   session pooler (5432) or transaction pooler (6543) to match the endpoint. Choose
   schemas explicitly (default public). Ensure the application server can reach
   the endpoint and trust its certificate. Direct endpoints may require IPv6;
   use the project-provided compatible pooler endpoint where appropriate.
6. Test, connect, and inspect tables/views, types, nullability, defaults, indexes,
   primary/unique/check constraints and ordered composite foreign keys. Visibility
   is restricted by the supplied database role. No PostgreSQL business rows are read.
7. Add a test column/table externally, click Refresh metadata and inspect revision
   increments and added/removed/changed entries. A sampled MongoDB field absent
   from a later sample is not proof of deletion; the UI states this.
8. Confirm credential errors are safe and understandable. Update credentials
   without changing connection identity, or create a new connection for a different
   endpoint/database. A failed refresh preserves the last successful snapshot.
9. Disconnect a connection and confirm new profiling is disabled. Credentials are
   removed locally; historical metadata is retained, and cloud data is unchanged.
10. Open Integrations and verify the same connection summaries and existing Google
    management remain available.

## API and persistence

All routes use the existing session, origin protection, response envelope and
`Cache-Control: no-store`. Read requires `tools.read`; management requires
`tools.assign`. Unknown/foreign connection IDs return not found.

- `GET /data-sources`: safe owned summaries and configuration status.
- `POST /data-sources/test`: transient real connection/discovery-access check.
- `POST /data-sources`: repeat check, encrypt configuration, enqueue profiling.
- `GET /data-sources/{id}` and `GET /data-sources/{id}/metadata`: latest snapshot.
- `POST /data-sources/{id}/verify`: health check, without schema discovery.
- `POST /data-sources/{id}/refresh-metadata`: coalesces an already active job.
- `POST /data-sources/{id}/credentials`: verify/replace settings for the same target
  and invalidate older jobs. Historical metadata remains until a successful refresh.
- `POST /data-sources/{id}/disconnect`: erase credentials and cancel pending jobs.

Connection request fields: `name`, `engine` (`mongodb`/`postgresql`), `uri`,
`database`, `schemas`, `description`, `mode`. Engine-specific cloud hosts/options
are validated server-side. URI is never returned. Supabase connections pin libpq
addresses to public addresses checked before connection while retaining hostname
certificate verification. Atlas validates provider SRV targets and public addresses;
TLS verification remains enabled. Deployment egress rules provide an additional
boundary against DNS changes during the driver's own discovery.

Additive tables: `data_source_connections`, `data_source_profile_jobs`,
`data_source_snapshots`, `data_source_audit`, `data_source_migrations`.
The catalog contract is `shared/contracts/data-sources/cloud-metadata-v1.schema.json`;
typed client schemas are in `frontend/src/api/data-sources.ts`.

Jobs have durable leases and attempt counts, token-checked completion and connection
generation checks. Expired jobs can be recovered after restart. Disconnect or
credential replacement prevents an older job from publishing/reactivating data.
Network I/O never holds the application's storage transaction.

Limits in this first version: 20 active connections per owner/workspace, 100 datasets,
1000 fields per dataset, 25 MongoDB documents per collection, nesting depth 6,
10 array elements sampled per document field, 100 indexes/constraints per dataset,
2 MB per metadata snapshot. Discovery uses timeouts and marks limited coverage.
The 60-second discovery budget is checked between datasets; an in-flight operation
can consume its own timeout before cancellation. These are bounded implementation
limits, not a claim that every database is completely profiled.

Metadata revisions are retained. No automatic retention/purge policy is introduced.
Descriptions/schema definitions are untrusted metadata, not agent instructions.

## Verification

Focused tests use cloud boundary fixtures; they do not contact real Atlas/Supabase
or perform cloud writes. Live credential acceptance must be completed by the user.
Verification counts and deployment evidence are recorded in the OpenSpec tasks.

Driver references:
- https://www.mongodb.com/docs/languages/python/pymongo-driver/current/connect/connection-options/
- https://www.psycopg.org/psycopg3/docs/api/connections.html

### Atlas discovery compatibility repair

Atlas rejected a top-level `batchSize` argument forwarded by PyMongo's
`list_collections`. Both connection testing and profiling now omit that option;
the existing dataset, sample and time limits still apply. Live read-only Northwind
connection testing and profiling passed for four collections without warnings.
The diagnostic did not create a saved connection.

## Supabase TLS trust repair (2026-10-17)

Live connection testing failed with `SSL error: certificate verify failed` before
authentication. Supabase shared poolers use Supabase's own root CA, which is not
in the operating system root bundle. The deployment now sets
`BUILDER_DATA_SOURCE_CA_FILE` in its private `.env` to
`.local/certs/postgres-ca-bundle.pem` (absolute path in the setting). The bundle
contains the system roots and `.local/certs/supabase-prod-ca-2021.crt`. Both API
and worker load this setting; certificate and hostname verification remain
`verify-full`. No application code or shared contract changed.

The CA was downloaded over verified HTTPS from the exact production URL in
Supabase's official dashboard source:
https://supabase-downloads.s3-ap-southeast-1.amazonaws.com/prod/ssl/prod-ca-2021.crt
(source: `apps/studio/hooks/custom-content/custom-content.json` in supabase/supabase).
SHA-256 certificate fingerprint:
`807025AD50D4ED219D2C9C7D299C004F824EB00CF7F65AFEF607D07B72E6CAFA`.
For redeployment, download that certificate, concatenate it after the system
CA bundle, set the existing CA environment variable to the resulting absolute
path, and restart API/worker. Do not trust a root copied from an unverified
database handshake. Supabase guidance:
https://supabase.com/docs/guides/platform/ssl-enforcement

Read-only connection testing and bounded profiling passed with the supplied
account and the official CA: order_details, orders, products, regions, shippers,
suppliers and territories; no warnings. The diagnostic saved no connection,
credentials or business rows. Password special characters must be percent-encoded
in the user-entered URI (`@` becomes `%40`). Focused data-source tests: 22 passed;
shared contracts and strict OpenSpec validation passed.
