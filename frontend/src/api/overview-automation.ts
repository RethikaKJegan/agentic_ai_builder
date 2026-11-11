import {z} from 'zod';

export const overviewResultSchema=z.object({
  version:z.literal('overview-intent-v1'),
  state:z.enum(['legacy','prepared','clarification','unsupported','planning','cancelled']),
  request_key:z.string().optional(),
  workspace:z.object({workspace_id:z.string(),subject_id:z.string()}).optional(),
  intent:z.object({intent_type:z.string(),business_goal:z.string(),side_effects:z.array(z.string())}).passthrough().optional(),
  questions:z.array(z.string()).optional(),
  planning_job:z.object({job_id:z.string(),state:z.string()}).optional(),
  composition_id:z.string().optional(),
  schedule:z.object({cron:z.string(),timezone:z.string(),next_due:z.number(),expires_at:z.number(),max_occurrences:z.number(),missed_run_policy:z.string(),overlap_policy:z.string()}).nullable().optional(),
  operations:z.record(z.unknown()).optional(),
  activation:z.object({state:z.string(),schedule_id:z.string(),authorization_id:z.string(),due:z.number()}).optional(),
  schedule_record:z.object({id:z.string(),state:z.string(),due:z.number().nullable().optional()}).passthrough().optional(),
}).passthrough();
export type OverviewResult=z.infer<typeof overviewResultSchema>;

export const overviewActivationSchema=z.object({state:z.literal('active'),schedule_id:z.string(),authorization_id:z.string(),due:z.number()});

export function overviewStorageKey(workspace:string,owner:string) {
  return 'praxi-overview-review-v1:'+workspace+':'+owner;
}
