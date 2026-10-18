import {z} from "zod";
import {ontologySchema} from "./data-ontology";
const status=z.enum(["inferred","ambiguous","confirmed","rejected","needs_review"]);
export const semanticViewSchema=ontologySchema.extend({
 version:z.literal(2),
 datasets:z.array(z.object({dataset_id:z.string(),label:z.string(),connection_id:z.string(),fields:z.array(z.object({field_id:z.string(),name:z.string(),types:z.array(z.string())}))})),
 entities:z.array(ontologySchema.shape.entities.element.extend({sources:z.array(ontologySchema.shape.entities.element.shape.sources.element.extend({description:z.string()}))})),
 relationships:z.array(ontologySchema.shape.relationships.element.extend({predicate:z.string().nullable(),status,confidence:z.null(),semantic_evidence_hash:z.string(),inference_method:z.string(),rationale:z.string(),evidence_refs:z.array(z.string()),alternatives:z.array(z.string()),inferred_at:z.string().nullable(),provenance:z.object({structural_relationship_id:z.string(),source_dataset_id:z.string(),target_dataset_id:z.string(),field_pairs:z.array(z.object({source_field_id:z.string(),target_field_id:z.string(),source_label:z.string(),target_label:z.string()})),source_revisions:z.array(z.object({connection_id:z.string(),revision:z.number(),generation:z.number()})),record_evidence:z.literal("not_sampled")})})),
 semantic_status:z.object({configured:z.boolean(),enabled:z.boolean(),state:z.enum(["idle","queued","running","ready","failed"]),last_error:z.string().nullable(),input_hash:z.string()}),
});
const scalar=z.union([z.string(),z.number(),z.boolean(),z.null()]);
export const recordGraphSchema=z.object({version:z.literal(1),kg_revision:z.string(),retrieved_at:z.string(),limited:z.boolean(),
 nodes:z.array(z.object({node_id:z.string(),dataset_id:z.string(),dataset_label:z.string(),identity_field_id:z.string(),identity_value:scalar,label_field_id:z.string(),label:z.string(),fields:z.array(z.object({field_id:z.string(),name:z.string(),value:scalar}))})).max(11),
 edges:z.array(z.object({edge_id:z.string(),relationship_id:z.string(),source_node_id:z.string(),target_node_id:z.string(),predicate:z.string(),semantic_status:status,structural_relationship_id:z.string(),observed_fields:z.array(z.object({source_field_id:z.string(),target_field_id:z.string(),value:scalar}))})).max(10),
 sources:z.array(z.object({dataset_id:z.string(),label:z.string(),metadata_revision:z.number(),started_at:z.string(),finished_at:z.string(),rows_read:z.number()})),
 query_traces:z.array(z.object({plan_id:z.string(),plan:z.record(z.unknown()),total_result_rows:z.number(),executed_at:z.string()})),warnings:z.array(z.string())});
export type SemanticView=z.infer<typeof semanticViewSchema>;
export type SemanticEdge=SemanticView["relationships"][number];
export type RecordGraph=z.infer<typeof recordGraphSchema>;
