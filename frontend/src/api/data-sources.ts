import { z } from "zod";

export const databaseConnectionSchema = z.object({
  connection_id:z.string(),name:z.string(),engine:z.enum(["mongodb","postgresql"]),host:z.string(),database:z.string(),schemas:z.array(z.string()),description:z.string(),mode:z.string(),
  connection_status:z.enum(["connected","unreachable","authentication_failed","disconnected"]),profiling_status:z.enum(["queued","running","ready","failed","cancelled"]),generation:z.number(),metadata_revision:z.number(),created_at:z.string(),updated_at:z.string(),last_verified_at:z.string().nullable(),last_profiled_at:z.string().nullable(),last_error_code:z.string().nullable(),last_error_message:z.string().nullable(),
});
export const databaseFieldSchema=z.object({field_id:z.string(),name:z.string(),types:z.array(z.string()),discovery_method:z.string(),present_in_samples:z.number().optional(),native_type:z.string().optional(),nullable:z.boolean().optional(),default_expression:z.string().nullable().optional()});
export const databaseDatasetSchema=z.object({dataset_id:z.string(),name:z.string(),database:z.string(),schema:z.string().nullable(),kind:z.string(),fields:z.array(databaseFieldSchema),indexes:z.array(z.record(z.unknown())),constraints:z.array(z.record(z.unknown())),sample_count:z.number(),discovery_method:z.string(),has_validation_rules:z.boolean().optional(),validation_schema_json:z.string().optional()});
export const databaseMetadataSchema=z.object({connection:databaseConnectionSchema,snapshot:z.object({connection_id:z.string(),engine:z.string(),revision:z.number(),discovered_at:z.string(),datasets:z.array(databaseDatasetSchema),warnings:z.array(z.string()),coverage:z.string(),limits:z.record(z.number()),changes:z.object({added:z.array(z.string()),removed:z.array(z.string()),changed:z.array(z.string())})}).nullable()});
export const databaseConnectionsSchema=z.object({configured:z.boolean(),shared_demo_identity:z.boolean(),items:z.array(databaseConnectionSchema)});
export type DatabaseConnection=z.infer<typeof databaseConnectionSchema>;
export type DatabaseMetadata=z.infer<typeof databaseMetadataSchema>;
export type DatabaseConfig={name:string;engine:"mongodb"|"postgresql";uri:string;database:string;schemas:string[];description:string;mode:string};
