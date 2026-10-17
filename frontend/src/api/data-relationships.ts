import { z } from "zod";

export const relationshipNodeSchema = z.object({
  node_id: z.string(), kind: z.enum(["connection", "dataset", "field"]),
  label: z.string(), connection_id: z.string(), parent_id: z.string().nullable(),
  types: z.array(z.string()), discovery_method: z.string(), description: z.string(),
});
export const relationshipSchema = z.object({
  relationship_id: z.string(), kind: z.enum(["declared", "suggested"]),
  source_dataset_id: z.string(), target_dataset_id: z.string(),
  field_pairs: z.array(z.object({ source_field_id: z.string(), target_field_id: z.string() })),
  evidence: z.array(z.string()), evidence_hash: z.string(),
  status: z.enum(["declared", "proposed", "accepted", "rejected"]), reviewed_at: z.string().nullable(),
});
export const relationshipViewSchema = z.object({
  graph: z.object({
    revision: z.number().int(), built_at: z.string(),
    sources: z.array(z.object({ connection_id: z.string(), revision: z.number().int(), generation: z.number().int() })),
    nodes: z.array(relationshipNodeSchema), relationships: z.array(relationshipSchema), warnings: z.array(z.string()),
  }).nullable(), stale: z.boolean(), build_status: z.enum(["idle", "queued", "running", "ready", "failed"]), last_error: z.string().nullable(),
});
export type RelationshipView = z.infer<typeof relationshipViewSchema>;
export type RelationshipNode = z.infer<typeof relationshipNodeSchema>;
