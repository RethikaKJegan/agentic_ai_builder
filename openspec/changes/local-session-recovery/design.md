# Design

WorkflowClient handles only canonical HTTP 401 AUTHENTICATION_REQUIRED responses. Its session endpoint cannot recursively recover. A shared in-flight promise renews the local session, validates the session response and permits one retry of the rejected request. Repeated rejection, failed renewal, unsafe responses and other modes fail normally. Requests retain their original body, revision and retry key. No successful or uncertain action is replayed.

Successful overview refresh clears only a previous authentication error, preserving other failures. Browser checks invalidate the session of an already open workflows page, then observe recovery on its existing polling cycle.
