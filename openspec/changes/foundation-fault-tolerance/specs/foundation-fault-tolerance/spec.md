## ADDED Requirements

### Requirement: Live execution ownership
The runtime SHALL require running state, the current owner token and an unexpired
lease before dispatching invocations or committing invocation outcomes. It SHALL
revalidate current Registry authority and the pinned workflow after intent persistence.
Delegated success and failure paths SHALL enforce the same ownership boundary.
Confirmed model usage settlement SHALL also require current ownership before
releasing unused reservations. Live leases SHALL NOT extend workflow or agent deadlines.

#### Scenario: Cancelled intent before dispatch
- **WHEN** cancellation commits after invocation intent and before dispatch validation
- **THEN** the adapter is not called and the cancelled state is preserved

#### Scenario: Delayed result after lease expiry
- **WHEN** a connector returns after its worker lease expires
- **THEN** the expired owner cannot checkpoint the result and restart blocks the uncertain intent

#### Scenario: Model usage arrives after cancellation
- **WHEN** a delegated model response returns after cancellation or ownership loss
- **THEN** it cannot settle usage or reduce the persisted conservative reservation

### Requirement: Supported failure policies
Workflow validation SHALL reject unsupported timeout policies and missing timeout
or error branch paths before execution while accepting existing supported policies.

#### Scenario: Missing timeout branch
- **WHEN** an approval specifies a timeout outcome without a matching outgoing edge
- **THEN** validation rejects the document with UNSUPPORTED_EXECUTION_CONFIGURATION

### Requirement: Operator recovery evidence
The backend SHALL expose a read-only, authenticated, tenant-scoped recovery view
with original invocation/effect identities, completed checkpoint hashes, consumed
usage and conservative reconciliation guidance. It SHALL distinguish missing intent
from uncertain invocation and SHALL NOT accept caller assertions as provider receipts.

#### Scenario: Unknown send
- **WHEN** an email intent has an uncertain result
- **THEN** the operator sees its original identity and reconciliation requirement without authorizing replay

### Requirement: Report read-back reconciliation
The existing operator reconciliation command SHALL support report exports using
the exact original workspace, workflow revision and runtime effect reference.
It SHALL verify existing provider markers and content before updating the local
journal, without issuing provider mutations or unblocking a runtime automatically.

#### Scenario: Original report identity
- **WHEN** an operator supplies the original report intent and existing spreadsheet
- **THEN** verified provider read-back repairs its journal receipt without creating another report
