# Design

The parent pauses its polling in detailed mode but never receives the child's
fresh build status. The child also waits six seconds even during a short build.
Measured live metadata-only rebuild: 0.741 seconds; v2 read: 0.020 seconds.

Publish accepted detailed-view status to the parent without copying v2 nodes into
v1 graph state. Trigger an immediate detailed read after a build request, retain
visible graph and explorer state, and poll at one second while queued/running.
Keep the six-second idle interval and single active polling owner. Ignore disposed
or superseded reads. Test ready and failed builds, fresh revisions, navigation
preservation and late responses, then verify isolated production desktop/mobile.
