# Investigation report schema reliability

The real I-2026-3-068 UI run failed at summary with MODEL_OUTPUT_SCHEMA_INVALID. Its original invalid payload/schema path was not retained, so the exact violating field is unknown. Investigation generation currently requests JSON object mode, not strict schema output. The same objective incorrectly adds warranty despite an explicit exclusion.

Use strict request-specific response schemas for investigation analysis while preserving local citation validation, budgets and no hidden retries. Honor explicit negative task clauses. Retain safe schema-path diagnostics on future failures. Test and roll out backend/worker for UI retesting; preserve original runs and company data. Existing local evidence refinement changes must remain intact.
