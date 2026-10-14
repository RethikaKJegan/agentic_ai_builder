import { useEffect, useMemo, useState } from "react";
import { api } from "@/api/client";
import { projectDiagram, type ProjectCommunication } from "@/domain/procurement-communication";
import { friendlyLabel } from "@/domain/communication-diagram";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";
import { CommunicationDiagram, DiagramLegend } from "./CommunicationDiagram";

export function ProcurementProjectCommunication({
  workflowId,
  version,
}: {
  workflowId: string;
  version: number;
}) {
  const [state, setState] = useState<{ key: string; project: ProjectCommunication }>();
  const [error, setError] = useState<Error>();
  const key = `${workflowId}:${version}`;
  useEffect(() => {
    let disposed = false;
    let timer: ReturnType<typeof setTimeout>;
    const refresh = async () => {
      try {
        const project = await api.procurementProjectCommunication(workflowId, version);
        if (!disposed) {
          setState({ key: `${workflowId}:${version}`, project });
          setError(undefined);
        }
      } catch (e) {
        if (!disposed)
          setError(
            e instanceof Error ? e : new Error("Project communication could not be loaded."),
          );
      } finally {
        if (!disposed) timer = setTimeout(() => void refresh(), 3000);
      }
    };
    void refresh();
    return () => {
      disposed = true;
      clearTimeout(timer);
    };
  }, [workflowId, version]);
  const project = state?.key === key ? state.project : undefined;
  const model = useMemo(
    () => (project ? projectDiagram(project) : { cards: [], connections: [] }),
    [project],
  );
  const live = !!project?.actions.some((action) =>
    ["running", "queued", "paused"].includes(action.run.status),
  );
  return (
    <>
      <div className="flex flex-wrap items-center gap-3 border-b p-3 text-xs">
        <span className="font-medium">{project?.root_workflow.name ?? "Loading workflow"}</span>
        <span className="capitalize text-muted-foreground">
          {friendlyLabel(project?.phase ?? "Loading")}
        </span>
        <span className="text-muted-foreground">
          Entire workflow · {project?.actions.length ?? 0} recorded actions
        </span>
        {project?.truncated && (
          <p>Showing available recent activity. Complete action history is in Runs.</p>
        )}
      </div>
      <DiagramLegend live={live} />
      <ApiFeedback error={error} />
      {project ? (
        <CommunicationDiagram key={key} model={model} />
      ) : (
        <p role="status" className="p-5 text-sm">
          Loading workflow diagram…
        </p>
      )}
    </>
  );
}
