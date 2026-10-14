import { useEffect, useMemo, useState } from "react";
import { Network } from "lucide-react";
import { api } from "@/api/client";
import { fromCanonical } from "@/api/mapping";
import { hasCommunication } from "@/domain/communication";
import { workflowDiagram } from "@/domain/communication-diagram";
import type { Workflow } from "@/domain/types";
import type { WorkflowTrace } from "./useWorkflowTrace";
import { ProcurementProjectCommunication } from "./ProcurementProjectCommunication";
import { CommunicationDiagram, DiagramLegend } from "./CommunicationDiagram";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";

export function AgentCommunication({
  workflow,
  trace,
}: {
  workflow: Workflow;
  trace: WorkflowTrace;
}) {
  const [open, setOpen] = useState(false);
  if (!hasCommunication(workflow)) return null;
  const plan = workflow.canonical?.metadata["procurement_plan"];
  const projectId =
    plan && typeof plan === "object" && "project_id" in plan && typeof plan.project_id === "string"
      ? plan.project_id
      : null;
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-background px-2.5 py-1.5 text-xs hover:border-primary">
        <Network className="h-3.5 w-3.5" />
        Agent communication
      </DialogTrigger>
      <DialogContent className="flex h-[94dvh] w-[96vw] max-w-[1600px] flex-col gap-0 overflow-hidden p-0">
        <div className="border-b border-border p-4 pr-12">
          <DialogTitle className="font-display text-lg font-semibold">
            Agent communication
          </DialogTitle>
          <DialogDescription className="mt-1 text-xs">
            See who starts each helper, what they share, and where results go. Click an agent or
            connection for details.
          </DialogDescription>
        </div>
        {open &&
          (projectId ? (
            <ProcurementProjectCommunication
              workflowId={workflow.id}
              version={workflow.serverVersion ?? 1}
            />
          ) : (
            <WorkflowCommunication workflow={workflow} trace={trace} />
          ))}
      </DialogContent>
    </Dialog>
  );
}
function WorkflowCommunication({ workflow, trace }: { workflow: Workflow; trace: WorkflowTrace }) {
  const [mode, setMode] = useState<"configured" | "run">(trace.runId ? "run" : "configured");
  const [revision, setRevision] = useState<Workflow>();
  const [error, setError] = useState<Error>();
  const runWorkflowId = trace.run?.workflow_id;
  const runVersion = trace.run?.workflow_version;
  useEffect(() => {
    if (mode !== "run" || !runWorkflowId || !runVersion) return;
    let disposed = false;
    api
      .request("get_workflow", { workflow_id: runWorkflowId, workflow_version: runVersion })
      .then((result) => {
        if (!disposed) {
          setRevision(fromCanonical(result.workflow).workflow);
          setError(undefined);
        }
      })
      .catch((e) => {
        if (!disposed)
          setError(
            e instanceof Error ? e : new Error("The recorded workflow could not be loaded."),
          );
      });
    return () => {
      disposed = true;
    };
  }, [mode, runWorkflowId, runVersion]);
  const exact =
    revision?.id === runWorkflowId && revision?.serverVersion === runVersion ? revision : undefined;
  const graph = mode === "configured" ? workflow : exact;
  const model = useMemo(
    () =>
      graph
        ? workflowDiagram(
            graph,
            mode === "run" ? trace.events : [],
            mode === "run" ? trace.runId : undefined,
            trace.run?.status,
          )
        : { cards: [], connections: [] },
    [graph, mode, trace.events, trace.runId, trace.run?.status],
  );
  const live = mode === "run" && ["running", "queued", "paused"].includes(trace.run?.status ?? "");
  return (
    <>
      <div className="flex flex-wrap items-center gap-2 border-b p-3 text-xs">
        <label htmlFor="communication-mode">View</label>
        <select
          id="communication-mode"
          className="rounded-md border bg-background p-1.5"
          value={mode}
          onChange={(e) => setMode(e.target.value as "configured" | "run")}
        >
          <option value="configured">Workflow plan</option>
          <option value="run" disabled={!trace.runId}>
            Recorded run
          </option>
        </select>
        {mode === "run" && (
          <select
            aria-label="Communication run"
            className="min-w-0 max-w-full rounded-md border bg-background p-1.5"
            value={trace.runId}
            onChange={(e) => trace.selectRun(e.target.value)}
          >
            {trace.runs.map((run, i) => (
              <option key={run.run_id} value={run.run_id}>
                Run {trace.runs.length - i} · {run.status} · version {run.workflow_version}
              </option>
            ))}
          </select>
        )}
        <span className="text-muted-foreground">
          {mode === "run"
            ? `Recorded run · v${runVersion ?? "…"}`
            : "Plan preview · helpers have not started"}
        </span>
      </div>
      <DiagramLegend live={live} />
      <ApiFeedback error={error ?? (mode === "run" ? trace.error : null)} />
      {!graph ? (
        <p role="status" className="p-5 text-sm">
          {error
            ? "Recorded workflow unavailable. Select Workflow plan to inspect its setup."
            : "Loading the recorded workflow…"}
        </p>
      ) : (
        <CommunicationDiagram
          key={`${mode}:${graph.id}:${mode === "run" ? trace.runId : "plan"}`}
          model={model}
        />
      )}
    </>
  );
}
