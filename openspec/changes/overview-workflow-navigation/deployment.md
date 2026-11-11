# Hosted Overview-to-Workflows navigation — 10 November 2026

Deployed to **https://praxi.bellcorpstudio.com/app**.

- Release: `workflow-navigation-20261110-68bceec971d2`.
- Source manifest SHA-256: `68bceec971d230a1a5455127e6044d4c34988ef414aa3ef7711541e45618f448`.
- Frontend build: `oyDtV0TfweDoMGSpb6VrX`; previous: `EiDLCCE7beRH3coeDHj3o`.
- Activated: 10 November 2026, 21:42:08 India time (16:12:08 UTC).
- Backend baseline remains [composed-intent routing](../composed-intent-routing/deployment.md).

After a new workflow is generated successfully in Overview, the application opens
that workflow under Workflows with its graph, steps, report and approval/schedule
review. Clarification, failure and pending feedback remain by the Overview prompt.
The full workflow is no longer embedded below it. Refreshing workflow details
restores the saved review without generating or executing work again.

The isolated production artifact passed 563 unit tests, 16 fixture browser journeys,
types, source lint, build and contract/spec checks. Six hosted read-only browser
checks and authenticated HTTPS checks passed across all accounts. Real Simpsons
saved-review loading and refresh passed on desktop/mobile. See
[verification](verification.md) for scope and limitations.

Only the existing frontend service was stopped/swapped/started. Its previous
artifact is retained at `frontend/.next-before-overview-navigation-20261110`;
previous static chunks were copied into the new artifact for existing sessions.
Exact prior source and artifact manifests, fresh configuration copies and history
counts were retained privately. Existing verified database snapshots remain
available; no database replacement, migration or restoration was part of this
frontend-only release. Backend services and the shared worker were not restarted;
their PIDs stayed unchanged. Existing history, encrypted credentials and
configuration are preserved (generated Registry metadata excluded).

Application-only frontend rollback:

```
.venv-integrations/bin/python .local/overview-workflow-navigation-20261110/release_control.py rollback
```

This restores the prior frontend artifact/source and removes the added review
loader. It does not restart backend services or change databases or schedules.
