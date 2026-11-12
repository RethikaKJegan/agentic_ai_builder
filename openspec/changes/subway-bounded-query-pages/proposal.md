# Bounded complete Subway query pages

Saved run run_d7930d9537e644319d9a0e69f1eac992 groups purchase orders by currency, vendorName and _id. The executor rejects more than 10,000 groups even for a paginated result. The 100 KB response cap can also reject a 500-row page after a successful full scan.

Spill aggregate state and sorting to a private, size-bounded temporary SQLite store after the current in-memory threshold. Preserve exact decimal arithmetic, source/row/time bounds, filter/join/currency checks and all-group completeness. Trim display pages to the existing response byte budget while retaining exact total counts and explicit continuation metadata. Never silently sample aggregates or remove source constraints.
