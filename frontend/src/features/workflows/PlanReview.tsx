import { knowledgePreviewSchema } from "@/api/knowledge-graph";
import { KnowledgeSourcePreview } from "./KnowledgeSourcePreview";
import type { CanonicalWorkflow } from "@/api/contracts.generated";
import type { Workflow } from "@/domain/types";
import { dependencyOrder, graphIssues } from "@/domain/graph-review";
import { fromCanonical } from "@/api/mapping";
import { DatabaseWorkflowReview } from "./DatabaseWorkflowReview";
export function PlanReview({
  document,
  workflow,
  generated = false,
}: {
  document?: CanonicalWorkflow;
  workflow?: Workflow;
  generated?: boolean;
}) {
  const graph = workflow ?? (document ? fromCanonical(document).workflow : undefined);
  if (!graph) return null;
  const canonical = document ?? graph.canonical;
  const retrieved = knowledgePreviewSchema.safeParse(canonical?.metadata['knowledge_graph_retrieval']);
  const issues = graphIssues(graph.nodes, graph.edges);
  const trigger =
    canonical?.metadata["trigger_templates"] ??
    canonical?.metadata["triggers"] ??
    canonical?.metadata["trigger"];
  return (
    <section
      aria-label="Workflow plan review"
      className="space-y-3 rounded-xl border border-border bg-background p-4 text-sm"
    >
      <h2 className="font-semibold">
        {generated ? "Generated plan — human review required" : "Review workflow plan"}
      </h2>
      <p>
        {generated
          ? "The planner produced this draft. Confirm the proposed steps, data access, destinations and approval policies before validation."
          : "Review the working draft below. Server validation and reviewed tool authorization are required before publication."}{" "}
        Saving a draft does not make it operational.
      </p>
      <dl className="grid gap-3 sm:grid-cols-2">
        <div>
          <dt className="font-medium">Goal</dt>
          <dd className="break-words text-muted-foreground">{graph.description || graph.name}</dd>
        </div>
        <div>
          <dt className="font-medium">Data sources and inputs</dt>
          <dd className="text-muted-foreground">
            {canonical?.inputs
              .map((i) => `${i.name} (${i.type}${i.required ? ", required" : ""})`)
              .join("; ") || "No inputs declared. Confirm source access and mappings."}
          </dd>
        </div>
        <div>
          <dt className="font-medium">Start and trigger</dt>
          <dd className="break-words text-muted-foreground">
            {graph.nodes
              .filter((n) => n.data.kind === "trigger")
              .map((n) => n.data.label)
              .join(", ") || "Missing start trigger"}
          </dd>
          <dd className="break-words whitespace-pre-wrap text-xs">
            {trigger
              ? JSON.stringify(trigger, null, 2)
              : "No event binding declared. Review whether manual input or event configuration is required."}
          </dd>
        </div>
        <div>
          <dt className="font-medium">Expected outputs</dt>
          <dd className="text-muted-foreground">
            {canonical?.outputs.map((o) => `${o.name} (${o.type})`).join("; ") ||
              graph.nodes
                .filter((n) => n.data.kind === "output")
                .map((n) => n.data.label)
                .join(", ") ||
              "Define expected outputs."}
          </dd>
        </div>
      </dl>
      {retrieved.success&&<KnowledgeSourcePreview view={retrieved.data}/>}
      <DatabaseWorkflowReview document={canonical} />
      <details open={generated}>
        <summary className="cursor-pointer font-medium">Major steps and branches</summary>
        <ol className="mt-2 space-y-1">
          {dependencyOrder(graph.nodes, graph.edges).map((n, i) => (
            <li key={n.id}>
              {i + 1}. {n.data.label} · {n.data.kind}
              {graph.edges.some((e) => e.source === n.id && e.label) && (
                <span className="text-muted-foreground">
                  {" "}
                  ·{" "}
                  {graph.edges
                    .filter((e) => e.source === n.id)
                    .map((e) => e.label || "next")
                    .join(" / ")}
                </span>
              )}
            </li>
          ))}
        </ol>
      </details>
      <details open={generated}>
        <summary className="cursor-pointer font-medium">
          Agent responsibilities and required tools
        </summary>
        <ul className="mt-2 space-y-1">
          {canonical?.agents.map((a) => (
            <li key={a.agent_id}>
              {a.role}: {a.goal} · tools:{" "}
              {a.allowed_tool_ids.join(", ") || "No reviewed tool grants"}
            </li>
          ))}
          {!canonical?.agents.length && <li>No agent definitions declared.</li>}
          {canonical?.tools.map((t) => (
            <li key={t.tool_id}>
              {t.tool_id} · {t.capability} · configuration and Registry authorization require review
            </li>
          ))}
        </ul>
      </details>
      <div>
        <h3 className="font-medium">Approval points</h3>
        <ul>
          {canonical?.approval_gates.map((g) => (
            <li key={g.approval_gate_id}>
              {g.approval_gate_id} · roles: {g.approver_roles.join(", ")} · on rejection:{" "}
              {g.on_reject}
            </li>
          ))}
          {!canonical?.approval_gates.length && (
            <li className="text-muted-foreground">
              No runtime approval gates declared. Revision approval is still a separate step.
            </li>
          )}
        </ul>
      </div>
      <div>
        <h3 className="font-medium">Configuration and human confirmation</h3>
        <p className="text-muted-foreground">
          Confirm data source URLs, input mappings, provider credentials, tool grants, trigger
          source/schedule and output destinations. Configured providers are not necessarily
          verified. Automatic operation requires active trigger bindings.
        </p>
        {issues.length > 0 && (
          <ul aria-label="Plan issues" className="mt-2 list-disc pl-4 text-destructive">
            {issues.map((x, i) => (
              <li key={i}>{x.message}</li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
