import { CanonicalWorkflowSchema, type CanonicalWorkflow } from "@/api/contracts.generated";
import { fromCanonical, toCanonical, stableSnapshot } from "@/api/mapping";
import type { Workflow, Agent } from "@/domain/types";
const identityKeys = [
  "node_id",
  "edge_id",
  "agent_id",
  "condition_id",
  "approval_gate_id",
  "tool_id",
  "stakeholder_id",
  "name",
];
/** Three-way merge is explicit and refuses overlapping edits rather than guessing. */
export function rebaseDraft(current: Workflow, agents: Agent[], remote: CanonicalWorkflow) {
  if (!current.canonical) throw new Error("A saved baseline is required.");
  const editable = (document: CanonicalWorkflow) => {
    const mapped = fromCanonical(document);
    const candidate = toCanonical(mapped.workflow, mapped.agents, remote.version + 1);
    delete candidate.metadata["updated_at"];
    return candidate;
  };
  const local = toCanonical(current, agents, remote.version + 1);
  delete local.metadata["updated_at"];
  const conflicts: string[] = [];
  const equal = (a: unknown, b: unknown) => stableSnapshot(a) === stableSnapshot(b);
  function merge(base: unknown, working: unknown, incoming: unknown, path: string): unknown {
    if (equal(working, base)) return incoming;
    if (equal(incoming, base) || equal(working, incoming)) return working;
    if (Array.isArray(base) && Array.isArray(working) && Array.isArray(incoming)) {
      const key = identityKeys.find((k) =>
        [...base, ...working, ...incoming].every(
          (item) => item && typeof item === "object" && typeof item[k] === "string",
        ),
      );
      if (key) {
        const map = (items: Record<string, unknown>[]) =>
          new Map(items.map((item) => [String(item[key]), item]));
        const b = map(base),
          w = map(working),
          r = map(incoming);
        const ids = [...new Set([...r.keys(), ...w.keys(), ...b.keys()])];
        return ids.flatMap((id) => {
          const result = merge(b.get(id), w.get(id), r.get(id), `${path}[${id}]`);
          return result === undefined ? [] : [result];
        });
      }
    }
    if (
      base &&
      working &&
      incoming &&
      typeof base === "object" &&
      typeof working === "object" &&
      typeof incoming === "object" &&
      !Array.isArray(base) &&
      !Array.isArray(working) &&
      !Array.isArray(incoming)
    ) {
      const b = base as Record<string, unknown>,
        w = working as Record<string, unknown>,
        r = incoming as Record<string, unknown>;
      const result: Record<string, unknown> = {};
      for (const key of new Set([...Object.keys(b), ...Object.keys(w), ...Object.keys(r)])) {
        const value = merge(b[key], w[key], r[key], path ? `${path}.${key}` : key);
        if (value !== undefined) result[key] = value;
      }
      return result;
    }
    conflicts.push(path || "workflow");
    return working;
  }
  const merged = merge(editable(current.canonical), local, editable(remote), "");
  return { conflicts, workflow: conflicts.length ? null : CanonicalWorkflowSchema.parse(merged) };
}
