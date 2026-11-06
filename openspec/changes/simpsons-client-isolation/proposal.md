# Simpsons client authentication and isolation

The website login currently gates a shared local operator. Add a signed Simpsons
account and route it exclusively to a dedicated instance of the existing backend.
The instance pins a Simpsons workspace/subject and uses a separate marked SQLite
store, Registry, credentials and worker configuration. It rejects local-session
cookies and requires short-lived, audience-bound assertions from the website.
No client-supplied workspace, owner, resource ID or prompt changes that authority.

Reuse all current chat/planning, ontology, retrieval, query, Registry, runtime,
lifecycle and worker implementations. Bootstrap only explicitly selected Simpsons
ontology/source dependencies; never copy the shared application database wholesale.
No live provider call, source write or deployment is required for implementation.
