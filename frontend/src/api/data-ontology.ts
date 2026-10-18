import { z } from "zod";

const review = z.enum(["suggested", "confirmed", "rejected", "needs_review"]);
export const ontologySchema = z.object({
  version: z.literal(1),
  revision: z.string(),
  stale: z.boolean(),
  build_status: z.enum(["idle", "queued", "running", "ready", "failed"]),
  last_error: z.string().nullable(),
  graph_revision: z.number().int(),
  built_at: z.string().nullable(),
  entities: z.array(
    z.object({
      entity_id: z.string(),
      label: z.string(),
      sources: z.array(
        z.object({
          node_id: z.string(),
          connection_id: z.string(),
          label: z.string(),
          kind: z.string(),
          role: z.string(),
          status: review,
          types: z.array(z.string()),
          metadata: z.record(z.unknown()),
        }),
      ),
    }),
  ),
  relationships: z.array(
    z.object({
      relationship_id: z.string(),
      source_entity_id: z.string(),
      target_entity_id: z.string(),
      predicate: z.string(),
      reversed: z.boolean(),
      status: review,
      reviewed_at: z.string().nullable(),
      evidence_hash: z.string(),
      technical_relationship_id: z.string(),
      technical_status: z.string(),
      source_dataset_id: z.string(),
      target_dataset_id: z.string(),
      field_pairs: z.array(
        z.object({
          source_field_id: z.string(),
          target_field_id: z.string(),
          source_label: z.string(),
          target_label: z.string(),
        }),
      ),
      evidence: z.array(z.string()),
      qualification: z.record(z.string()),
    }),
  ),
  warnings: z.array(z.string()),
});
export const refreshSchema = z.object({
  version: z.literal(1),
  items: z.array(
    z.object({
      connection_id: z.string(),
      name: z.string(),
      enabled: z.boolean(),
      interval_seconds: z.number().int(),
      next_check_at: z.number().nullable(),
      last_attempt_at: z.string().nullable(),
      last_success_at: z.string().nullable(),
      last_change_at: z.string().nullable(),
      consecutive_failures: z.number().int(),
      profiling_status: z.string(),
      connection_status: z.string(),
      metadata_revision: z.number().int(),
      last_error_message: z.string().nullable(),
    }),
  ),
});
export type OntologyView = z.infer<typeof ontologySchema>;
export type OntologyEdge = OntologyView["relationships"][number];
export type RefreshView = z.infer<typeof refreshSchema>;
