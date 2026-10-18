import { z } from "zod";
export const knowledgePreviewSchema = z.object({
  version:z.union([z.literal(1),z.literal(2)]),revision:z.string(),indexed_at:z.string(),
  coverage:z.object({connections:z.number().int(),datasets:z.number().int(),matched_datasets:z.number().int(),candidate_limit:z.literal(12),source_limit:z.literal(4),metadata_only:z.literal(true)}),
  query_terms:z.array(z.string()),requires_selection:z.boolean(),graph_stale:z.boolean(),
  candidates:z.array(z.object({dataset_id:z.string(),connection_id:z.string(),label:z.string(),engine:z.string(),score:z.number(),selected:z.boolean(),reasons:z.array(z.string()),fields:z.array(z.string()),operations:z.array(z.string())})),
  semantic_relationships:z.array(z.object({relationship_id:z.string(),technical_relationship_id:z.string(),source_dataset_id:z.string(),target_dataset_id:z.string(),predicate:z.string(),reversed:z.boolean(),status:z.enum(["inferred","confirmed"]),semantic_evidence_hash:z.string(),evidence_refs:z.array(z.string()),confidence:z.null()})).optional(),
  source_ids:z.array(z.string()).max(4),
  relationships:z.array(z.object({relationship_id:z.string(),source_dataset_id:z.string(),target_dataset_id:z.string(),status:z.string(),field_pairs:z.array(z.object({source_field_id:z.string(),target_field_id:z.string()}))})),
  warnings:z.array(z.string()),tools:z.array(z.object({tool_id:z.string(),capability:z.string(),approval_required:z.boolean(),description:z.string()})),
});
export type KnowledgePreview = z.infer<typeof knowledgePreviewSchema>;
export type KnowledgeSelection = {revision:string;source_ids:string[]};
