# Authorized Phase 4 activation — 18 October 2026

User requested activation on the running Builder app. Activate the already verified
frontend snapshot after checking source/configuration parity and retaining active
static assets. Preserve the prior build and environment file in a private local
rollback directory. Set only BUILDER_DATA_WRITE_POLICY_FILE to the verified
Atlas-only test policy. Restart the existing Builder API, worker and frontend;
preserve connection storage, encryption keys, authentication and origin restrictions.

Verify service health, a fresh authenticated Operations status, discovered target
identity/fields and actual desktop/mobile rendering without mocked API responses.
Perform no cloud CRUD, model requests, workflow execution or policy broadening.
If activation fails, restore the previous build/environment and restart services.
Record actual deployment evidence and any public-origin limitations afterward.
