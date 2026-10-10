# Contract Stage Status

The previously deferred control-contract stages are now defined, reviewed, validated, and accepted:

1. API request/response payloads — accepted in `api-and-control-contracts-v1`
2. Error envelope and request correlation — accepted in `api-and-control-contracts-v1`
3. Authentication and permission rules — accepted in `api-and-control-contracts-v1`
4. Branching and approval semantics — accepted in `api-and-control-contracts-v1`
5. Run statuses and versioning — accepted in `api-and-control-contracts-v1`

No downstream implementation may invent alternate formats. All consumers must use the versioned files under `shared/contracts/`.
