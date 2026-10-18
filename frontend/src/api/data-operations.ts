import { z } from "zod";

export const databaseActionSchema = z.enum(["create", "read", "update", "delete"]);
const values = z.record(z.union([z.string(), z.number(), z.boolean(), z.null()]));
export const databaseStepSchema = z.object({
  connection_id: z.string(),
  dataset_id: z.string(),
  action: z.enum(["create", "update", "delete"]),
  identity: values,
  values,
  unset_fields: z.array(z.string()),
});
export type DatabaseStep = z.infer<typeof databaseStepSchema>;
export const databaseOperationSchema = z.object({
  operation_id: z.string(),
  state: z.enum(["prepared", "running", "succeeded", "failed", "partial", "uncertain", "expired"]),
  created_at: z.number(),
  expires_at: z.number(),
  recovery_until: z.number(),
  recovery_of: z.string().nullable(),
  recovery_operation_id: z.string().nullable(),
  preview_available: z.boolean(),
  workflow_run_id: z.string().optional(),
  workflow_id: z.string().optional(),
  steps: z.array(
    z.object({
      action: z.enum(["create", "update", "delete"]),
      connection_id: z.string(),
      dataset_id: z.string(),
      label: z.string(),
      tool_id: z.string(),
      state: z.enum(["pending", "running", "succeeded", "failed", "uncertain"]),
      matched_records: z.number().int().min(0).max(1),
      affected_records: z.number().int().min(0).max(1),
      error_code: z.string().nullable(),
      identity: values.optional(),
      values: values.optional(),
      unset_fields: z.array(z.string()).optional(),
      before: values.nullable().optional(),
      after: values.nullable().optional(),
    }),
  ),
});
export type DatabaseOperation = z.infer<typeof databaseOperationSchema>;
export const databaseOperationsSchema = z.object({
  configured: z.boolean(),
  targets: z.array(
    z.object({
      connection_id: z.string(),
      dataset_id: z.string(),
      label: z.string(),
      engine: z.enum(["postgresql", "mongodb"]),
      identity_fields: z.array(z.string()),
      writable_fields: z.array(z.string()),
      operations: z.array(databaseActionSchema),
    }),
  ),
  items: z.array(databaseOperationSchema),
  tools: z.array(
    z.object({
      tool_id: z.string(),
      provider_id: z.string(),
      capability: z.string(),
      approval_required: z.boolean(),
    }),
  ),
});
export const databaseRecordSchema = z.object({
  record: values.nullable(),
  matched_records: z.number().int().min(0).max(1),
  label: z.string(),
});
