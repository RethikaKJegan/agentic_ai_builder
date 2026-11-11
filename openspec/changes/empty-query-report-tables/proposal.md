# Valid report tables for complete empty query results

The saved last-week workflow returned a complete empty grouped result. Its report
agent emitted rows=[] while the downstream spreadsheet tool requires nonempty rows.
Render complete empty results as an explicitly labelled report-status table, never
an invented status group or numeric average. Derive the no-match fact from completed
verified direct query dependencies and pass server-owned report context. Normalize
only empty generated report tabs under that context, before persistence and approval.
Align generated report tabs with downstream literal-tab input limits. Preserve all
nonempty tables, source queries, permissions, effect identities and approval gates.
