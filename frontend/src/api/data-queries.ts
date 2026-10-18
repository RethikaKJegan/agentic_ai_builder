import { z } from "zod";

export const queryPlanSchema = z.object({
  base_dataset_id:z.string(), joins:z.array(z.object({relationship_id:z.string(),target_dataset_id:z.string()})),
  fields:z.array(z.string()), filters:z.array(z.object({field_id:z.string(),op:z.enum(["eq","ne","gt","gte","lt","lte","is_null","not_null"]),value:z.union([z.string(),z.number(),z.boolean(),z.null()])})),
  group_by:z.array(z.string()),metrics:z.array(z.object({label:z.string(),op:z.enum(["count","sum","avg","min","max"]),expression:z.string()})),
  order_by:z.array(z.object({column:z.string(),direction:z.enum(["asc","desc"])})),limit:z.number().int().min(1).max(500),explanation:z.string(),clarification:z.string(),
});
export const physicalPlanSchema = z.object({strategy:z.enum(["application","postgresql","mongodb","federated"]),reason:z.string(),operations:z.array(z.string()),max_source_rows:z.number().int(),snapshot:z.string()});
export const selectionPreviewSchema = z.object({
  catalog_dataset_count: z.number().int().nonnegative(),
  sources: z.array(z.object({
    dataset_id: z.string(), connection_id: z.string(), engine: z.enum(["postgresql", "mongodb"]), label: z.string(),
    reasons: z.array(z.string()),
    fields: z.array(z.object({field_id: z.string(), label: z.string(), types: z.array(z.string()), purposes: z.array(z.enum(["output", "filter", "group", "metric", "join", "row_count"])).min(1)})),
  })).max(4),
  relationships: z.array(z.object({relationship_id: z.string(), source_dataset_id: z.string(), target_dataset_id: z.string(), status: z.enum(["declared", "accepted"]), field_pairs: z.array(z.object({source_field_id: z.string(), target_field_id: z.string()})).min(1)})).max(3),
  business_mappings: z.array(z.object({node_id: z.string(), entity_name: z.string(), role: z.enum(["represents", "identifier", "reference", "attribute"])})),
  warnings: z.array(z.string()),
});
export type SelectionPreview = z.infer<typeof selectionPreviewSchema>;
export const plannedQuerySchema = z.object({plan_id:z.string(),question:z.string(),plan:queryPlanSchema,graph_revision:z.number().int(),created_at:z.string(),expires_at:z.number(),field_labels:z.record(z.string()),dataset_labels:z.record(z.string()),physical_plan:physicalPlanSchema.optional(),selection_preview:selectionPreviewSchema.optional()});
export const queryStatusSchema = z.object({configured:z.boolean(),max_rows_per_dataset:z.number(),max_bytes:z.number(),max_datasets:z.number(),max_result_rows:z.number(),plan_ttl_seconds:z.number(),jobs_available:z.boolean().optional(),job_timeout_seconds:z.number().optional(),result_ttl_seconds:z.number().optional()});
export const queryFragmentSchema = z.object({dataset_ids:z.array(z.string()),engine:z.enum(["postgresql","mongodb"]),purpose:z.enum(["complete dimension","complete join key domain","partial aggregates"]),snapshot:z.string(),started_at:z.string(),finished_at:z.string(),duration_ms:z.number().int().nonnegative(),source_rows:z.number().int().nonnegative(),transferred_rows:z.number().int().nonnegative(),transferred_bytes:z.number().int().nonnegative()});
export const queryResultSchema = z.object({plan_id:z.string(),executed_plan:queryPlanSchema.optional(),columns:z.array(z.object({key:z.string(),label:z.string()})),rows:z.array(z.record(z.union([z.string(),z.number(),z.boolean(),z.null()]))),total_result_rows:z.number(),matched_rows:z.number(),limited:z.boolean(),executed_at:z.string(),explanation:z.string(),warnings:z.array(z.string()),
  execution:z.object({strategy:z.enum(["application","postgresql","mongodb","federated"]),snapshot:z.string(),duration_ms:z.number().int(),transferred_rows:z.number().int(),transferred_bytes:z.number().int(),fragments:z.array(queryFragmentSchema).optional()}).optional(),
  sources:z.array(z.object({dataset_id:z.string(),label:z.string(),metadata_revision:z.number(),started_at:z.string(),finished_at:z.string(),rows_read:z.number()})),
  join_checks:z.array(z.object({relationship_id:z.string(),source_rows:z.number(),target_rows:z.number(),matched_rows:z.number(),target_unique:z.boolean(),checked_at:z.string()})),
});
export type PlannedQuery = z.infer<typeof plannedQuerySchema>;
export type QueryResult = z.infer<typeof queryResultSchema>;

export const queryJobSchema = z.object({job_id:z.string(),plan_id:z.string(),state:z.enum(["queued","validating","running","finalizing","succeeded","failed","cancel_requested","cancelled"]),attempt:z.number().int(),created_at:z.number(),updated_at:z.number(),deadline_at:z.number(),progress:z.object({stage:z.string(),completed_fragments:z.number().int(),transferred_rows:z.number().int(),transferred_bytes:z.number().int()}),result_expires_at:z.number().nullable(),result_available:z.boolean(),error:z.object({code:z.string(),message:z.string()}).nullable(),planned_query:plannedQuerySchema});
export const queryJobListSchema = z.object({items:z.array(queryJobSchema)});
export type QueryJob = z.infer<typeof queryJobSchema>;
