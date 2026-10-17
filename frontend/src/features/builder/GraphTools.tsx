import { useState } from "react";
import type { WorkflowNode, WorkflowEdge } from "@/domain/types";
import { dependencyOrder, graphIssues } from "@/domain/graph-review";
export function GraphTools({
  nodes,
  edges,
  onSelect,
  onConnect,
  onRemove,
}: {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  onSelect: (id: string) => void;
  onConnect: (source: string, target: string, label?: string) => void;
  onRemove: (id: string) => void;
}) {
  const issues = graphIssues(nodes, edges);
  const [source, setSource] = useState("");
  const [target, setTarget] = useState("");
  const [label, setLabel] = useState("");
  const start = nodes.find((n) => n.id === source);
  const outcomes =
    start?.data.kind === "condition"
      ? ((start.data["condition"] as { outcomes?: string[] } | undefined)?.outcomes ?? [])
      : start?.data.kind === "approval"
        ? ["approved", "rejected"]
        : [];
  return (
    <details className="shrink-0 border-b border-border px-4 py-2 text-xs">
      <summary className="cursor-pointer font-medium">
        Workflow outline and connections ·{" "}
        {issues.length ? `${issues.length} issues to review` : "No local topology issues"}
      </summary>
      <p className="my-2 text-muted-foreground">
        Start → dependencies → end. Local diagnostics are advisory; use Validate for authoritative
        contract and Registry checks. Undo/redo affects draft edits only.
      </p>
      {issues.length > 0 && (
        <ul aria-label="Graph diagnostics" className="my-2 space-y-1 text-destructive">
          {issues.map((x, i) => (
            <li key={i}>
              {x.nodeId ? (
                <button
                  type="button"
                  className="text-left underline"
                  onClick={() => onSelect(x.nodeId!)}
                >
                  {x.message}
                </button>
              ) : (
                x.message
              )}
            </li>
          ))}
        </ul>
      )}
      <ol
        aria-label="Accessible workflow outline"
        className="grid max-h-40 gap-1 overflow-y-auto sm:grid-cols-2"
      >
        {dependencyOrder(nodes, edges).map((n, i) => (
          <li key={n.id}>
            <button
              type="button"
              className="rounded-lg border border-border px-2 py-1 text-left"
              onClick={() => onSelect(n.id)}
            >
              {i + 1}. {n.data.label} · {n.data.kind}
              {n.data.kind === "trigger" ? " · Start" : n.data.kind === "output" ? " · End" : ""}
            </button>
          </li>
        ))}
      </ol>
      <form
        className="my-3 flex flex-wrap items-end gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (source && target && (!outcomes.length || label))
            onConnect(source, target, label || undefined);
        }}
      >
        <label>
          From step
          <select
            aria-label="Connection source"
            value={source}
            onChange={(e) => {
              setSource(e.target.value);
              setLabel("");
            }}
            className="block max-w-48 rounded border bg-background p-2"
          >
            <option value="">Choose step</option>
            {nodes
              .filter((n) => n.data.kind !== "output")
              .map((n) => (
                <option key={n.id} value={n.id}>
                  {n.data.label}
                </option>
              ))}
          </select>
        </label>
        <label>
          To step
          <select
            aria-label="Connection target"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            className="block max-w-48 rounded border bg-background p-2"
          >
            <option value="">Choose step</option>
            {nodes
              .filter((n) => n.id !== source && n.data.kind !== "trigger")
              .map((n) => (
                <option key={n.id} value={n.id}>
                  {n.data.label}
                </option>
              ))}
          </select>
        </label>
        {outcomes.length > 0 && (
          <label>
            Branch outcome
            <select
              aria-label="Connection outcome"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              className="block rounded border bg-background p-2"
            >
              <option value="">Choose outcome</option>
              {outcomes.map((o) => (
                <option key={o}>{o}</option>
              ))}
            </select>
          </label>
        )}
        <button
          type="submit"
          disabled={!source || !target || (outcomes.length > 0 && !label)}
          className="rounded border border-border px-3 py-2 disabled:opacity-40"
        >
          Connect steps
        </button>
      </form>
      <ul className="mb-3 max-h-32 space-y-1 overflow-y-auto">
        {edges.map((e) => (
          <li key={e.id}>
            {nodes.find((n) => n.id === e.source)?.data.label ?? e.source} →{" "}
            {nodes.find((n) => n.id === e.target)?.data.label ?? e.target}
            {e.label ? ` · ${e.label}` : ""}{" "}
            <button
              type="button"
              onClick={() => onRemove(e.id)}
              aria-label={`Remove connection ${e.id}`}
              className="ml-2 underline"
            >
              Remove connection
            </button>
          </li>
        ))}
      </ul>
    </details>
  );
}
