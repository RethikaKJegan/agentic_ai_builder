# EDA overview

Open Data Intelligence → EDA for a desktop presentation of discovered database
structure. This intentionally simple version uses existing metadata/KG read APIs;
it does not scan business tables, submit model requests or run new analysis jobs.

- Select one connection or All connections.
- Cards show successful metadata snapshots, datasets, fields and in-scope KG links.
- Charts show field types, the six datasets with most fields, semantic relationship
  statuses and declared/sampled discovery coverage.
- Discovery samples are profiling document samples, not total row counts.
- Refresh insights reloads saved metadata. Changes to connection identities,
  metadata revisions, generations or profiling status automatically reload an open
  tab; ordinary identical status polls do not repeat its metadata reads.
- Failed connections produce partial-data notices. Missing snapshots have an empty
  state, and unavailable KG counts display a dash. Stale KG summaries are labelled.

No sales trends, revenue, stock analysis, missing-value rates or record counts are
fabricated. Existing workflow source selection, KG editing, CRUD and Google
integrations are unchanged. No new backend service or persisted analysis is added.
