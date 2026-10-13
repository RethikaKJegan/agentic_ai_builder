# Procurement extension

Status: **the first slice is connected to the isolated extension runtime**. Version 1 definitions remain the foundation; the SQLite repository and opt-in coordinator now implement source ingestion, BOQ/RFQ preparation, tracking projections and Gmail drafts. Quotation/order automation and the full proposed policy remain later work. Original application files, shared contracts and the earlier live pilot ledger remain unchanged.

- [Record shapes and invariants](CONTRACTS.md)
- [Lifecycle, approval policy and stop conditions](POLICY.md)
- Versioned artifacts: `contracts/v1/records.schema.json`, `policy.schema.json`, `policy.default.json`, `states.json`, `examples.json`.
- Offline verification: `.venv-integrations/bin/python connector_extension/procurement/verify_contracts.py` from the repository root.

The accepted workflow, agent, tool, API, approval and runtime contracts under `shared/contracts/` remain execution authority. Procurement records supplement them; a domain approval row cannot mint a Registry grant or authorize a connector call.

Step 1 adds no spreadsheet creation, SQLite tables, API route, worker, agent prompt, provider call or automatic-action mode. The default policy file is a reviewable definition, not configuration read by `connector_extension.app`. Later steps must implement the documented guards and reconcile this policy with the existing mandatory write gates before claiming automation.

## Next implementation boundary

Step 2 implements opt-in spreadsheet/tab creation tools and the six-table tracking layout; see [setup and recovery](SPREADSHEETS.md). These create empty header-initialized tables, not procurement business records. Step 3 implements the separate SQLite repository and transactional state guards; see [persistence and integration boundary](PERSISTENCE.md). Step 4 connects it to opt-in scoped service routes, registered deterministic specialists and a coordinator for source ingestion, approved tracking projections and RFQ drafts; see [first-slice automation](AUTOMATION.md). Subsequent quotation/order orchestration will keep canonical runtime permissions and budgets intact. Any change to the reviewed default policy requires a new policy revision and explicit operator review; unattended external writes remain a future implementation choice.
