"use client";

import { useEffect, useState } from "react";
import { z } from "zod";
import { api } from "@/api/client";
import type { CanonicalWorkflow } from "@/api/contracts.generated";
import type { DatabaseOperation } from "@/api/data-operations";

const scopeSchema = z.object({
  sources: z.array(
    z.object({
      connection_id: z.string(),
      dataset_id: z.string(),
      label: z.string(),
      engine: z.string(),
      context_hash: z.string(),
    }),
  ),
  graph_hash: z.string().nullable(),
});

export function DatabaseWorkflowReview({ document }: { document: CanonicalWorkflow | undefined }) {
  const scope = scopeSchema.safeParse(document?.metadata["database_scope"]);
  if (!scope.success || !document) return null;
  const steps = document.nodes.filter((node) => node.tool_id?.startsWith("database_"));
  return (
    <section
      aria-label="Planned database operations"
      className="min-w-0 space-y-3 rounded-lg border p-3"
    >
      <h3 className="font-semibold">Planned database operations</h3>
      <p className="text-xs text-muted-foreground">
        These are planned sources and steps. Actual reads, changes and results appear in Execution.
        Each write needs a prepared operation and a separate human approval.
      </p>
      <ul className="space-y-2">
        {scope.data.sources.map((source) => (
          <li key={source.dataset_id} className="break-words text-xs">
            <p className="font-medium">
              {source.label} · {source.engine}
            </p>
            <p className="break-all">Dataset: {source.dataset_id}</p>
            <p>Metadata pinned to {source.context_hash.slice(0, 12)}…</p>
          </li>
        ))}
      </ul>
      <ol className="space-y-2">
        {steps.map((node) => (
          <li key={node.node_id} className="min-w-0 rounded border p-2 text-xs">
            <p className="break-words font-medium">
              {node.label} · {node.tool_id} · {node.agent_id}
            </p>
            <pre className="max-h-48 overflow-auto whitespace-pre-wrap break-all">
              {JSON.stringify(node.configuration, null, 2)}
            </pre>
          </li>
        ))}
      </ol>
      {!steps.length && (
        <p className="text-xs">
          Database work is assigned to specialists; inspect the agent hierarchy and recorded tool
          calls.
        </p>
      )}
    </section>
  );
}

export function DatabaseApprovalPreview({
  operationId,
  onReviewed,
}: {
  operationId: string;
  onReviewed: (ready: boolean) => void;
}) {
  const [operation, setOperation] = useState<DatabaseOperation>();
  const [error, setError] = useState("");
  const [clock, setClock] = useState(() => Date.now() / 1000);
  useEffect(() => {
    const timer = setInterval(() => setClock(Date.now() / 1000), 1000);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    let active = true;
    onReviewed(false);
    void api
      .databaseOperation(operationId)
      .then((value) => {
        if (active) setOperation(value);
      })
      .catch(() => {
        if (active)
          setError("The current database preview could not be loaded. Reload before approving.");
      });
    return () => {
      active = false;
    };
  }, [operationId, onReviewed]);
  const ready =
    operation?.state === "prepared" && operation.preview_available && operation.expires_at > clock;
  useEffect(() => {
    if (!ready) onReviewed(false);
  }, [ready, onReviewed]);
  return (
    <section
      aria-label="Database change awaiting approval"
      className="min-w-0 space-y-2 rounded border p-3 text-xs"
    >
      <p className="break-all font-medium">Database operation {operationId}</p>
      {error && <p role="alert">{error}</p>}
      {!operation && !error && <p role="status">Loading current permitted database preview…</p>}
      {operation && (
        <>
          <p>
            State: {operation.state} · Preview expires{" "}
            {new Date(operation.expires_at * 1000).toLocaleTimeString()}
          </p>
          {ready ? (
            <>
              {operation.steps.map((step, index) => (
                <div key={index} className="min-w-0 space-y-1">
                  <p className="font-medium">
                    {step.action} · {step.label}
                  </p>
                  <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-all">
                    {JSON.stringify(
                      {
                        identity: step.identity,
                        before: step.before,
                        changes: step.values,
                        remove_fields: step.unset_fields,
                      },
                      null,
                      2,
                    )}
                  </pre>
                </div>
              ))}
              <label className="flex items-start gap-2">
                <input type="checkbox" onChange={(event) => onReviewed(event.target.checked)} />I
                reviewed every database target, before-image and proposed change.
              </label>
            </>
          ) : (
            <p role="alert">
              This operation cannot currently be approved. Prepare a fresh operation if evidence
              expired, authority changed or execution already started.
            </p>
          )}
        </>
      )}
    </section>
  );
}
