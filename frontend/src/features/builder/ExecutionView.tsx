import { displayText } from "@/lib/display-text";
import { useMemo, useState } from "react";
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  MiniMap,
  MarkerType,
} from "@xyflow/react";
import type { Workflow } from "@/domain/types";
import type { WorkflowTrace } from "./useWorkflowTrace";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";
import { MeshNode, type MeshFlowNode } from "./MeshNode";
import { NodeTrace } from "./NodeTrace";
import { autoLayout } from "@/domain/layout";
import { dependencyOrder } from "@/domain/graph-review";
import { ProcurementProjectCommunication } from "./ProcurementProjectCommunication";
import { AgentCommunication } from "./AgentCommunication";
import { ApprovalControl } from "@/features/runs/ServerRunView";
const nodeTypes = { mesh: MeshNode };
export function ExecutionView({ trace, workflow, onDesign }: { trace: WorkflowTrace; workflow?: Workflow; onDesign: () => void }) {
  const [scope,setScope]=useState<"project"|"run">("project");
  const [selected, setSelected] = useState("");
  const graph = trace.revision?.workflow;
  const nodes = useMemo(
    () =>
      autoLayout(graph?.nodes ?? [], graph?.edges ?? []).map((n) => ({
        ...n,
        data: {
          ...n.data,
          runStatus: trace.runState[n.id],
          orientation: undefined,
          readOnly: true,
          agentPreview: trace.revision?.agents.find((a) => a.id === n.data.agentId),
        },
        draggable: false,
        connectable: false,
        deletable: false,
      })) as MeshFlowNode[],
    [graph, trace.runState, trace.revision],
  );
  const edges = useMemo(
    () =>
      (graph?.edges ?? []).map((e) => ({
        ...e,
        type: "smoothstep",
        markerEnd: { type: MarkerType.ArrowClosed },
        className: trace.activeEdges.has(e.id) ? "edge-active" : "",
        labelStyle: { fontSize: 12 },
        labelBgPadding: [6, 4] as [number, number],
      })),
    [graph, trace.activeEdges],
  );
  const node = graph?.nodes.find((n) => n.id === selected);
  const pendingApprovals = trace.available && trace.run?.status === "paused_for_approval" && trace.run.run_id === trace.runId
    ? trace.run.approvals.filter(approval => approval.status === "pending" && approval.workflow_id === trace.run!.workflow_id && approval.workflow_version === trace.run!.workflow_version)
    : [];
  if(workflow?.canonical?.metadata['procurement_plan']&&scope==='project')return <div className="flex min-h-0 flex-1 flex-col h-full"><div className="flex items-center justify-between border-b bg-background px-4 py-2 text-xs"><span className="font-medium">Entire procurement workflow</span><button className="rounded-lg border px-3 py-1.5 hover:bg-muted" onClick={()=>setScope('run')}>Inspect parent run</button></div><ProcurementProjectCommunication workflowId={workflow.id} version={workflow.serverVersion??1}/></div>;
  return (
    <section aria-label="Recorded execution" className="flex h-full min-h-0 flex-col">
      <div className="flex flex-wrap items-center gap-2 border-b border-border p-3 text-xs">
        {!!workflow?.canonical?.metadata['procurement_plan']&&<button className="rounded-lg border px-3 py-2" onClick={()=>setScope('project')}>Entire project</button>}
        <label htmlFor="trace-run">Recorded run</label>
        <select
          id="trace-run"
          aria-label="Select workflow run"
          value={trace.runId}
          onChange={(e) => {
            setSelected("");
            trace.selectRun(e.target.value);
          }}
          disabled={!trace.available || !trace.runs.length}
          className="min-w-0 max-w-full rounded-lg border bg-background p-2"
        >
          {!trace.runs.length && <option value="">No recorded runs</option>}
          {trace.runs.map((r) => (
            <option key={r.run_id} value={r.run_id}>
              {r.run_id} · v{r.workflow_version} · {r.status}
            </option>
          ))}
        </select>
        {trace.hasMoreRuns && <button type="button" onClick={trace.loadMoreRuns} className="rounded-lg border px-3 py-2">Older workflow runs</button>}
        {trace.hasMoreEvents && <span role="status">Loading more recorded events…</span>}
        <button
          type="button"
          onClick={trace.retry}
          disabled={trace.loading}
          className="rounded-lg border px-3 py-2"
        >
          Refresh trace
        </button>
        <button type="button" onClick={onDesign} className="rounded-lg border px-3 py-2">
          Return to editable draft
        </button>
        {trace.run && (
          <p className="w-full break-all">
            Read-only historical revision v{trace.run.workflow_version} · Run {trace.run.run_id} ·{" "}
            {trace.run.status}
          </p>
        )}
        {(workflow || graph) && <AgentCommunication workflow={workflow ?? graph!} trace={trace} />}
      </div>
      <ApiFeedback error={trace.error} />
      {pendingApprovals.length > 0 && <section aria-label="Approvals for this run" className="max-h-96 shrink-0 space-y-3 overflow-y-auto border-b p-3">
        <h2 className="text-sm font-semibold">Waiting for your approval</h2>
        {pendingApprovals.map(approval => {
          const details = trace.events.find(event => event.event_type === "approval.pending" && event.details?.["approval_id"] === approval.approval_id)?.details;
          const gate = graph?.nodes.find(candidate => candidate.id === details?.["node_id"]);
          const operationId = details?.["database_operation_id"];
          return <div key={`${trace.runId}:${approval.approval_id}:${approval.status}`} className="min-w-0 space-y-2 break-words">
            <p className="text-sm font-medium">{displayText(gate?.data.label ?? "Pending action")}</p>
            <ApprovalControl approval={approval} emailPreview={details?.["email_preview"]} databaseOperationId={typeof operationId === "string" ? operationId : undefined} onUpdated={trace.retry} />
          </div>;
        })}
      </section>}
      {!trace.available ? (
        <p className="p-4">Execution requires a connected runtime and runs.view permission.</p>
      ) : !trace.runId ? (
        <p className="p-4">
          No persisted runs for this workflow. Use Run published on Workflows, or wait for an active
          configured trigger.
        </p>
      ) : !graph ? (
        <p role="status" className="p-4">
          {trace.error
            ? "The exact recorded revision could not be loaded. No draft graph is substituted. Refresh to retry."
            : "Loading the selected run and its exact workflow revision…"}
        </p>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
          <div className="hidden min-h-80 min-w-0 flex-1 md:block">
            <ReactFlowProvider>
              <ReactFlow
                key={`${trace.runId}:${graph.serverVersion}`}
                nodes={nodes}
                edges={edges}
                nodeTypes={nodeTypes}
                nodesDraggable={false}
                nodesConnectable={false}
                edgesReconnectable={false}
                deleteKeyCode={null}
                onNodeClick={(_, n) => setSelected(n.id)}
                fitView
                fitViewOptions={{ padding: 0.2 }}
                minZoom={0.1}
                proOptions={{ hideAttribution: true }}
              >
                <Background />
                <Controls showInteractive={false} />
                <MiniMap pannable zoomable />
              </ReactFlow>
            </ReactFlowProvider>
          </div>
          <div className="w-full overflow-y-auto p-3 lg:max-w-sm">
            <p className="mb-2 text-xs text-muted-foreground">
              Recorded sequence is authoritative. A step with no events has unknown execution state.
            </p>
            <ol aria-label="Recorded workflow steps" className="space-y-2">
              {dependencyOrder(graph.nodes, graph.edges).map((n, i) => (
                <li key={n.id}>
                  <button
                    type="button"
                    onClick={() => setSelected(n.id)}
                    className={`w-full rounded-lg border p-2 text-left text-sm ${selected === n.id ? "border-primary" : "border-border"}`}
                  >
                    {i + 1}. {displayText(n.data.label)} · {n.data.kind} ·{" "}
                    {trace.runState[n.id] ?? "No recorded status"}
                  </button>
                </li>
              ))}
            </ol>
            {node && (
              <div className="mt-4">
                <h3 className="mb-2 font-medium">{displayText(node.data.label)}</h3>
                <NodeTrace node={node} trace={trace} />
              </div>
            )}
            <details className="mt-4">
              <summary>Run timeline · {trace.events.length} events</summary>
              <ol aria-label="Recorded run events" className="space-y-2 pt-2">
                {trace.events.map((e) => (
                  <li key={e.event_id} className="break-words rounded-lg border p-2 text-xs">
                    {e.event_type} · {e.timestamp}
                    <pre className="overflow-auto whitespace-pre-wrap">
                      {displayText(JSON.stringify(e.details, null, 2))}
                    </pre>
                  </li>
                ))}
              </ol>
            </details>
          </div>
        </div>
      )}
    </section>
  );
}
