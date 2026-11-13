import { z } from 'zod';
const count = z.number().int().nonnegative();
export const executionPolicySchema = z.object({
  read_only: z.boolean(), require_action_approval: z.boolean(), restricted_tools: z.array(z.string()), restricted_sources: z.array(z.string()),
  limits: z.object({timeout_seconds:count.positive().optional(),max_llm_calls:count.optional(),max_tool_calls:count.optional(),max_tokens:count.optional(),max_retries:count.optional(),max_delegation_calls:count.optional()}).strict(),
  model_timeout_seconds:count.positive().nullable(),tool_timeout_seconds:count.positive().nullable(),delegation_timeout_seconds:count.positive().nullable(),step_timeout_seconds:count.positive().nullable(),
}).strict();
export const governancePolicySchema = z.object({revision:count,policy:executionPolicySchema,scope:z.string(),enforcement:z.string(),cost_accounting:z.string(),audit:z.array(z.object({actor_id:z.string(),timestamp:z.number(),revision:count,policy_sha256:z.string()})).optional()});
export const runSafetySchema = z.object({error_code:z.string().nullable(),cancellation:z.object({requested_at:z.number(),requested_by:z.string(),reason:z.string()}).nullable(),usage:z.record(z.number()),uncertain_effects:z.array(z.object({effect_reference:z.string().nullable(),outcome:z.string()})),effective_policy:executionPolicySchema,policy_revision:count});
export type ExecutionPolicy = z.infer<typeof executionPolicySchema>;
