# Simpsons complete workspace audit

Audit live client pages and APIs without paid model calls or external actions.
Correct any reproducible integration gaps found using isolated tests. Current
findings: Runs/Monitoring poll the optional legacy inbox-monitor endpoint even
when absent; startup treats the supervisor's process lease owner as a tenant user,
which prevents recovery after an unclean stop. Preserve client data and Google
account ownership. Check metadata-change warnings against actual read readiness.
