# Dataset-scoped intent routing

Saved planning job plan_15426159c7144df4a36f5ae8b1580c9b failed when independently chosen fields and relationship endpoints expanded the metadata source union beyond four datasets. The raw failed selection is not retained, so its particular extra sources are unknown.

New intent transport selects dataset IDs only (at most four), leaving fields/relationships to the existing query-planning model on server-built scoped metadata. A dataset metadata mode provides objective-ranked fields and only current supported relationships wholly inside selected sources. Existing explicit/legacy selections retain their validation and closure behavior. Keep query joins, authority, limits and exact source identities unchanged. No additional model calls, guessed aliases or prompt matching.
