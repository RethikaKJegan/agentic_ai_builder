import { z } from "zod";

const record = z.record(z.unknown());
export const actionSchema = z
  .object({
    action_id: z.string(),
    capability_id: z.string(),
    depends_on: z.array(z.string()),
    bindings: z.array(record),
    instructions: z.string(),
    evidence_references: z.array(z.unknown()),
    required_approvals: z.array(z.string()),
    expected_output_schema: record,
  })
  .passthrough();
export const planSchema = z
  .object({
    schema_version: z.enum(["orchestration-plan-v1", "orchestration-plan-v2"]),
    plan_id: z.string(),
    revision: z.number(),
    scope: z.object({ workspace_id: z.string(), owner_id: z.string(), client_id: z.string() }),
    goal: z.string(),
    completion_criteria: z.array(z.string()),
    missing_inputs: z.array(z.unknown()),
    actions: z.array(actionSchema),
  })
  .passthrough();
export const actionDocumentSchema = z
  .object({
    composition_id: z.string(),
    scope: z.object({ workspace: z.string(), owner: z.string() }),
    action_plan: planSchema,
    selected_tools: z.record(z.object({ tool_id: z.string() }).passthrough()),
    configurations: z.array(record),
    google_connection_id: z.string().nullable().optional(),
  })
  .passthrough();
export const instanceSchema = z
  .object({
    state: z.string(),
    resolved_inputs: record.optional(),
    output: record.optional(),
    verified_receipt: z.boolean().optional(),
    provenance_type: z.string().optional(),
    external_effect_status: z.string().optional(),
    input_provenance: z.array(record).optional(),
  })
  .passthrough();
export const adaptiveSchema = z
  .object({
    phase: z.string(),
    status: z.string(),
    stage_instance_id: z.string(),
    plan_revision: z.number().optional(),
    composition_id: z.string().nullable(),
    run_id: z.string().nullable(),
    revision_history: z.array(record),
    decisions: z.array(record),
    pending_wait: z
      .object({
        wait_id: z.string(),
        kind: z.string(),
        deadline: z.number(),
        schemas: z.record(record).optional(),
      })
      .passthrough()
      .nullable(),
  })
  .passthrough();
export const automationSchema = z
  .object({
    id: z.string(),
    kind: z.string(),
    state: z.string(),
    request: record.optional().default({}),
  })
  .passthrough();
export const automationListSchema = z.object({
  items: z.array(automationSchema),
  has_more: z.boolean(),
  next_cursor: z.string().nullable(),
  jobs: z.array(record),
  health: record,
});
export type ActionDocument = z.infer<typeof actionDocumentSchema>;
export type AdaptiveState = z.infer<typeof adaptiveSchema>;
export type AutomationRecord = z.infer<typeof automationSchema>;
export function objectInput(text: string): Record<string, unknown> {
  const parsed: unknown = JSON.parse(text);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed))
    throw new Error("Enter a JSON object.");
  return parsed as Record<string, unknown>;
}
// Only complete, backend-verified tool results can supply clickable artifacts.
export function receiptLinks(instance: z.infer<typeof instanceSchema>): string[] {
  if (instance.state !== "completed" || instance.verified_receipt !== true) return [];
  return [
    ...new Set(
      Object.entries(instance.output ?? {})
        .filter(
          ([key, value]) =>
            ["spreadsheet_url", "event_url", "htmlLink", "url", "web_url"].includes(key) &&
            typeof value === "string",
        )
        .flatMap(([, value]) => {
          try {
            const url = new URL(String(value));
            return url.protocol === "https:" && !url.username && !url.password ? [url.href] : [];
          } catch {
            return [];
          }
        }),
    ),
  ];
}
