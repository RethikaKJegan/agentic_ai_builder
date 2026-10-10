# Remaining Contract Consumers

| Contract | Suprajha | Aravind | Harihar | Rethika |
| --- | --- | --- | --- | --- |
| API payloads | Planner request/response | Tool and capability endpoints | UI client and workflow lifecycle | Execution and run endpoints |
| Error format | Planner failures | Registry and authorization failures | UI-safe error display | Runtime and connector failures |
| Authentication/permissions | Planner subject context | Tool scopes and connector authorization | UI action visibility | Runtime enforcement |
| Branching/approvals | Planner conditions and approval requirements | Tool approval metadata | Approval controls and status display | Branch selection and pause/resume |
| Run/versioning | Planner revision reference | Authorized workflow version | Save/publish/run display | Runtime state and idempotency |

All consumers must use the versioned files under `shared/contracts/` and must not create service-specific shapes.
