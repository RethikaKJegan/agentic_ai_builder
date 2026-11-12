import {z} from 'zod';
import {InvestigationAssessmentSchema} from './contracts.generated';
export const adaptiveRunSchema=z.object({objective:z.string(),status:z.string(),revision:z.number().int(),turns:z.number().int(),
  assessment:InvestigationAssessmentSchema.shape.assessment.nullable(),
  pending_wait:z.object({wait_id:z.string(),requests:z.array(z.object({key:z.string(),reason:z.string(),schema:z.record(z.unknown())}))}).nullable(),
  decisions:z.array(z.object({decision:z.string(),rationale:z.string(),revision:z.number().int()}).passthrough()),
  deterministic_limitations:z.array(z.object({action_id:z.string(),code:z.string(),details:z.unknown().optional()})).optional(),
  revisions:z.array(z.record(z.unknown())),blocker:z.string().optional()});
