# Restore owned Google connections in isolated client workspaces

Dedicated client provisioning omitted Google web OAuth configuration. The frontend
proxy additionally discards the OAuth browser cookie for dedicated clients and
routes callbacks using the current login alone. Restore tenant-local OAuth setup,
signed state-bound callback routing, permitted OAuth cookie forwarding and existing
Google workflow connectors using owned-account tokens only. Preserve operator
accounts and all database/ontology isolation. Never copy existing engineering
account tokens or use shared credential fallbacks. User consent completes Google
connection; validation must not send mail, change calendars or call paid models.
