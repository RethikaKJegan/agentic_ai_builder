# Application-owned initial workflow revisions

The successful supplier-audit planning job returned version 2 for an unsaved
workflow. First save (base 0/version 2) conflicted, then the UI's concurrent-save
recovery GET returned WORKFLOW_NOT_FOUND. Initial revisions belong to application
state, not the model. Normalize new planner results to draft/version 1 and make
the UI's first save defensively use version 1 after confirming no saved workflow
exists. Retain existing-workflow and concurrent-save behavior. Recover the
already generated missing draft using normal authorized save only, never publish
or execute. Verify version-2 generation and initial-save regression cases.
