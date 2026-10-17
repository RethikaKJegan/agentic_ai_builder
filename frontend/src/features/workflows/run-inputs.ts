import { InputError } from "@/api/feedback";
import type { CanonicalWorkflow } from "@/api/contracts.generated";
export function parseRunInputs(fields: CanonicalWorkflow["inputs"], values: Record<string, string>): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const field of fields) {
    const raw = values[field.name] ?? "";
    const invalid=(message:string)=>new InputError(message,`inputs.${field.name}`);
    if (!raw.trim()) { if (field.required) throw invalid(`${field.name} is required.`); continue; }
    let value: unknown = raw;
    if (field.type === "number" || field.type === "integer") {
      if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(raw.trim())) throw invalid(`${field.name} must be a number.`);
      value = Number(raw);
      if (!Number.isFinite(value) || (field.type === "integer" && !Number.isSafeInteger(value))) throw invalid(`${field.name} must be a ${field.type === "integer" ? "safe integer" : "finite number"}.`);
    } else if (field.type === "boolean") {
      if (!["true", "false"].includes(raw)) throw invalid(`${field.name} must be true or false.`);
      value = raw === "true";
    } else if (field.type === "array" || field.type === "object") {
      try { value = JSON.parse(raw); } catch { throw invalid(`${field.name} must contain valid JSON.`); }
      if (field.type === "array" ? !Array.isArray(value) : value === null || typeof value !== "object" || Array.isArray(value)) throw invalid(`${field.name} must be a JSON ${field.type}.`);
    }
    result[field.name] = value;
  }
  return result;
}
export function eventOnly(workflow: CanonicalWorkflow) {
  const triggers = workflow.metadata["trigger_templates"];
  return workflow.metadata["execution_input_mode"] === "automatic" && Array.isArray(triggers) && triggers.length > 0;
}
