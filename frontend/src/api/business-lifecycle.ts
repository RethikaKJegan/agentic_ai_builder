import { z } from "zod";
import { InputError } from "./feedback";

const record = z.record(z.unknown());
export const evidenceValueSchema = z
  .object({
    value: z.unknown(),
    data_type: z.string(),
    provenance_type: z.enum(["ACTUAL", "DERIVED", "INFERRED", "SYNTHETIC"]),
    source_references: z.array(record),
    generation_method: z.string(),
    confidence: z.number().nullable(),
    assumptions: z.array(z.string()),
    limitations: z.array(z.string()),
    generated_at: z.string(),
    validity_scope: z.string(),
  })
  .passthrough();
export const inputSpecSchema = z
  .object({
    schema: record,
    binding: z.object({ source: z.string(), path: z.string() }).optional(),
    synthetic_fallback: z.boolean().optional(),
    protected_activity: z.boolean().optional(),
  })
  .passthrough();
export const stageDefinitionSchema = z
  .object({
    stage_instance_id: z.string(),
    name: z.string(),
    required_capabilities: z.array(z.string()),
    required_inputs: z.record(inputSpecSchema),
    optional_inputs: z.record(inputSpecSchema),
    dependency_definitions: z.array(z.string()),
    allowed_tools: z.array(z.string()),
    side_effect_classification: z.string(),
    external_event_requirements: z.array(record),
    transition_rules: z
      .array(
        z.object({
          source: z.string(),
          path: z.string(),
          operator: z.string(),
          value: z.unknown().optional(),
        }),
      )
      .default([]),
  })
  .passthrough();
export const processDefinitionSchema = z
  .object({
    process_definition_id: z.string(),
    version: z.number().int().positive(),
    client_id: z.string(),
    domain_id: z.string(),
    description: z.string().optional(),
    stages: z.array(stageDefinitionSchema).min(1).max(64),
  })
  .passthrough();
const stageSchema = z
  .object({
    stage_instance_id: z.string(),
    definition: stageDefinitionSchema,
    execution_status: z.string(),
    business_outcome_status: z.string(),
    real_world_status: z.string(),
    resolved_inputs: z.record(evidenceValueSchema),
    outputs: z.record(evidenceValueSchema),
    errors: z.array(record),
    retry_history: z.array(record),
    agent_configurations: z.array(record),
    tool_execution_records: z.array(record),
    run_id: z.string().nullable().optional(),
    composition_id: z.string().nullable().optional(),
    created_at: z.string().optional(),
    updated_at: z.string().optional(),
    completed_at: z.string().optional(),
  })
  .passthrough();
export const caseSchema = z
  .object({
    case_id: z.string(),
    workspace_id: z.string(),
    owner_id: z.string(),
    client_id: z.string(),
    revision: z.number().int().positive(),
    process_definition_id: z.string(),
    process_definition_version: z.number().int().positive(),
    process_definition: processDefinitionSchema,
    original_user_goal: z.string(),
    case_status: z.string(),
    execution_status: z.string(),
    business_outcome_status: z.string(),
    updated_at: z.string(),
    stages: z.record(stageSchema),
    waits: z.record(record),
    conflicts: z.array(record),
    assumptions: z.record(evidenceValueSchema),
    execution_history: z.array(record),
    reassessments: z.array(record).optional(),
    prepared_at: z.string().nullable().optional(),
  })
  .passthrough();
export const caseIndexSchema = z.object({
  items: z.array(
    z.object({
      case_id: z.string(),
      client_id: z.string(),
      process_definition_id: z.string(),
      process_definition_version: z.number(),
      original_user_goal: z.string(),
      case_status: z.string(),
      execution_status: z.string(),
      business_outcome_status: z.string(),
      revision: z.number(),
      updated_at: z.string(),
    }),
  ),
  next_cursor: z.number().nullable(),
});
export const processIndexSchema = z.object({
  items: z.array(
    processDefinitionSchema.pick({
      process_definition_id: true,
      version: true,
      client_id: true,
      domain_id: true,
    }),
  ),
});
export const packageDetailsSchema = z
  .object({
    package_id: z.string(),
    revision: z.number(),
    client_id: z.string(),
    process_definitions: z.array(processDefinitionSchema).default([]),
  })
  .passthrough();
export const driveResultSchema = z
  .object({
    case_id: z.string(),
    stop_reason: z.string(),
    commands_used: z.number(),
    revision: z.number().optional(),
    report: record.optional(),
  })
  .passthrough();
export type BusinessCase = z.infer<typeof caseSchema>;
export type ProcessDefinition = z.infer<typeof processDefinitionSchema>;
export type StageDefinition = z.infer<typeof stageDefinitionSchema>;
export type EvidenceValue = z.infer<typeof evidenceValueSchema>;
export type CaseOperation =
  "prepare" | "start" | "advance" | "resume" | "cancel" | "input" | "drive" | "events" | "reassess";
export function words(value: string) {
  return value.replaceAll("_", " ").replaceAll(":", " · ");
}
export function userFields(process: ProcessDefinition) {
  const fields = new Map<string, { spec: z.infer<typeof inputSpecSchema>; required: boolean }>();
  for (const stage of process.stages)
    for (const [name, spec] of Object.entries({
      ...stage.required_inputs,
      ...stage.optional_inputs,
    })) {
      if (spec.binding?.source !== "user" || spec.protected_activity) continue;
      const path = spec.binding.path;
      if (path.split(".").some((p) => ["__proto__", "prototype", "constructor"].includes(p)))
        continue;
      if (!fields.has(path))
        fields.set(path, {
          spec,
          required: name in stage.required_inputs && !spec.synthetic_fallback,
        });
    }
  // Present explicitly referenced user condition values; evaluate every branch on the backend.
  for (const stage of process.stages)
    for (const condition of stage.transition_rules) {
      if (
        condition.source !== "user" ||
        fields.has(condition.path) ||
        condition.path.split(".").some((p) => ["__proto__", "prototype", "constructor"].includes(p))
      )
        continue;
      const literal =
        condition.operator === "in" && Array.isArray(condition.value)
          ? condition.value[0]
          : condition.value;
      const type = ["boolean", "number", "string"].includes(typeof literal)
        ? typeof literal
        : "string";
      fields.set(condition.path, {
        spec: { schema: { type }, binding: { source: "user", path: condition.path } },
        required: false,
      });
    }
  return [...fields].map(([path, value]) => ({ path, ...value }));
}
export function fieldInputs(
  process: ProcessDefinition,
  values: Record<string, string>,
): Record<string, unknown> {
  const inputs: Record<string, unknown> = {};
  for (const { path, spec } of userFields(process)) {
    const raw = values[path];
    if (raw === undefined || raw === "") continue;
    const type = Array.isArray(spec.schema["type"])
      ? (spec.schema["type"] as string[]).find((t) => t !== "null")
      : spec.schema["type"];
    let value: unknown = raw;
    if (type === "boolean") value = raw === "true";
    else if (type === "number" || type === "integer") {
      value = Number(raw);
      if (!Number.isFinite(value) || (type === "integer" && !Number.isInteger(value)))
        throw new InputError(`Provide a valid ${words(path)}.`);
    } else if (type === "object" || type === "array") {
      try {
        value = JSON.parse(raw);
      } catch {
        throw new InputError(`Provide valid JSON for ${words(path)}.`);
      }
    }
    const parts = path.split(".");
    let cursor = inputs;
    for (const part of parts.slice(0, -1)) {
      cursor[part] ??= {};
      if (typeof cursor[part] !== "object" || Array.isArray(cursor[part]) || cursor[part] === null)
        throw new InputError("Overlapping input paths require a reviewed process configuration.");
      cursor = cursor[part] as Record<string, unknown>;
    }
    cursor[parts.at(-1)!] = value;
  }
  return inputs;
}
