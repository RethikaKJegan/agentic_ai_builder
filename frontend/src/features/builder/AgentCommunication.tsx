import { useEffect, useMemo, useState } from "react";
import {
  Background,
  BaseEdge,
  Controls,
  EdgeLabelRenderer,
  getSmoothStepPath,
  getBezierPath,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useUpdateNodeInternals,
  useNodesInitialized,
  useReactFlow,
  type Edge,
  type EdgeProps,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import { Network, ArrowRight } from "lucide-react";
import { api } from "@/api/client";
import type { RunEvent } from "@/api/contracts.generated";
import { fromCanonical } from "@/api/mapping";
import {
  communicationGraph,
  communicationPositions,
  communicationUuid,
  eventsForLink,
  handoffEvents,
  handoffResult,
  withRecordedDataLinks,
  type CommunicationEntity,
  type CommunicationLink,
} from "@/domain/communication";
import type { Workflow } from "@/domain/types";
import type { WorkflowTrace } from "./useWorkflowTrace";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useIsMobile } from "@/hooks/use-mobile";
import { StatusPill } from "@/features/shell/StatusPill";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";
import { NodeTrace } from "./NodeTrace";
import { NODE_META } from "./nodeMeta";

type CardNode = Node<
  { entity: CommunicationEntity; uuid: string; status?: string | undefined },
  "communication"
>;
function AgentCard({ id, data, selected }: NodeProps<CardNode>) {
  const updateNodeInternals = useUpdateNodeInternals();
  useEffect(() => {
    const frame = requestAnimationFrame(() => updateNodeInternals(id));
    return () => cancelAnimationFrame(frame);
  }, [id, data.uuid, updateNodeInternals]);
  const M = NODE_META[data.entity.node.data.kind];
  return (
    <div
      className={`h-[150px] w-[280px] rounded-xl border bg-background p-3 shadow-soft ${selected ? "border-primary" : data.entity.role === "Master agent" ? "border-primary/50" : "border-border"}`}
    >
      <Handle id="route-in" type="target" position={Position.Top} />
      <Handle id="hierarchy-in" type="target" position={Position.Right} style={{ top: "70%" }} />
      <Handle id="data-in" type="target" position={Position.Left} style={{ top: "70%" }} />
      <Handle id="result-in" type="target" position={Position.Bottom} style={{ left: "65%" }} />
      <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-primary">
        {data.entity.role}
      </p>
      <div className="flex items-center gap-2">
        <M.icon className="h-4 w-4 shrink-0 text-primary" />
        <p className="truncate text-sm font-medium">{data.entity.node.data.label}</p>
      </div>
      <p className="mt-2 break-all font-mono text-[10px] text-muted-foreground">UUID {data.uuid}</p>
      {data.status && (
        <div className="mt-2">
          <StatusPill status={data.status} />
        </div>
      )}
      <Handle id="route-out" type="source" position={Position.Bottom} />
      <Handle id="hierarchy-out" type="source" position={Position.Right} style={{ top: "30%" }} />
      <Handle id="data-out" type="source" position={Position.Left} style={{ top: "30%" }} />
      <Handle id="result-out" type="source" position={Position.Top} style={{ left: "65%" }} />
    </div>
  );
}
const nodeTypes = { communication: AgentCard };
type HandoffEdge = Edge<
  { link: CommunicationLink; label: string; returned: boolean; inspect: () => void },
  "communication"
>;
function CommunicationEdge(props: EdgeProps<HandoffEdge>) {
  const [path, x, y] = props.data?.returned ? getBezierPath(props) : getSmoothStepPath(props);
  const labelY = y + (props.data?.returned ? 35 : props.data?.link.kind === "hierarchy" ? -35 : 0);
  return (
    <>
      <BaseEdge
        id={props.id}
        path={path}
        {...(props.markerEnd ? { markerEnd: props.markerEnd } : {})}
        style={props.style}
        interactionWidth={24}
      />
      <EdgeLabelRenderer>
        <button
          type="button"
          className="nodrag nopan rounded-md border border-border bg-background px-2 py-1 text-[10px] shadow-sm hover:border-primary focus:outline-none focus:ring-2 focus:ring-primary"
          style={{
            position: "absolute",
            pointerEvents: "all",
            transform: `translate(-50%, -50%) translate(${x}px, ${labelY}px)`,
          }}
          onClick={(event) => {
            event.stopPropagation();
            props.data?.inspect();
          }}
        >
          {props.data?.label}
        </button>
      </EdgeLabelRenderer>
    </>
  );
}
const edgeTypes = { communication: CommunicationEdge };

function FitSpawnedNodes({ signature }: { signature: string }) {
  const initialized = useNodesInitialized();
  const { fitView } = useReactFlow();
  useEffect(() => {
    if (!initialized) return;
    const frame = requestAnimationFrame(() => void fitView({ padding: 0.18, duration: 150 }));
    return () => cancelAnimationFrame(frame);
  }, [initialized, signature, fitView]);
  return null;
}

export function AgentCommunication({
  workflow,
  trace,
}: {
  workflow: Workflow;
  trace: WorkflowTrace;
}) {
  const [open, setOpen] = useState(false);
  if (!workflow.nodes.some((node) => node.data.kind === "agent")) return null;
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-background px-2.5 py-1.5 text-xs hover:border-primary">
        <Network className="h-3.5 w-3.5" />
        Agent communication
      </DialogTrigger>
      <DialogContent className="flex h-[94dvh] w-[96vw] max-w-[1500px] flex-col gap-0 overflow-hidden p-0">
        <div className="border-b border-border p-4 pr-12">
          <DialogTitle className="font-display text-lg font-semibold">
            Agent communication
          </DialogTitle>
          <DialogDescription className="mt-1 text-xs">
            Inspect master/sub-agent relationships, UUIDs and recorded application handoffs.
          </DialogDescription>
        </div>
        {open && <CommunicationView workflow={workflow} trace={trace} />}
      </DialogContent>
    </Dialog>
  );
}

function CommunicationView({ workflow, trace }: { workflow: Workflow; trace: WorkflowTrace }) {
  const mobile = useIsMobile();
  const [mode, setMode] = useState<"configured" | "run">(trace.runId ? "run" : "configured");
  const [revision, setRevision] = useState<Workflow | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [selection, setSelection] = useState<{ kind: "node" | "link"; id: string } | null>(null);
  const [identity, setIdentity] = useState<{ key: string; ids: Record<string, string> }>({
    key: "",
    ids: {},
  });
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
          setError(null);
        }
      })
      .catch((caught) => {
        if (!disposed)
          setError(
            caught instanceof Error ? caught : new Error("The run revision could not be loaded."),
          );
      });
    return () => {
      disposed = true;
    };
  }, [mode, runWorkflowId, runVersion]);
  const exactRevision =
    revision?.id === runWorkflowId && revision?.serverVersion === runVersion ? revision : null;
  const graph = mode === "configured" ? workflow : exactRevision;
  const identityKey = JSON.stringify([graph?.id, graph?.nodes.map((node) => node.id)]);
  useEffect(() => {
    if (!graph) return;
    let disposed = false;
    Promise.all(
      communicationGraph(graph).entities.map(
        async ({ node }) => [node.id, await communicationUuid(graph.id, node.id)] as const,
      ),
    )
      .then((pairs) => {
        if (!disposed) setIdentity({ key: identityKey, ids: Object.fromEntries(pairs) });
      })
      .catch(() => {
        if (!disposed) setIdentity({ key: identityKey, ids: {} });
      });
    return () => {
      disposed = true;
    };
  }, [graph, identityKey]);
  const uuids = useMemo(
    () => {
      const ids = { ...(identity.key === identityKey ? identity.ids : {}) };
      if (mode === "run" && graph && trace.run) {
        for (const event of trace.events) {
          const d = event.details;
          if (event.event_type === "agent.spawned" && event.run_id === trace.run.run_id && event.workflow_id === graph.id && event.workflow_version === graph.serverVersion && typeof d?.["node_id"] === "string" && typeof d["invocation_id"] === "string") ids[d["node_id"]] = d["invocation_id"];
        }
      }
      return ids;
    },
    [identity, identityKey, mode, graph, trace.run, trace.events],
  );
  const base = useMemo(
    () => (graph ? communicationGraph(graph, mode === "run" ? trace.events : [], mode === "run" ? trace.run?.run_id : undefined) : { entities: [], links: [] }),
    [graph, mode, trace.events, trace.run?.run_id],
  );
  const events = useMemo(
    () =>
      mode === "run" && graph && trace.run
        ? handoffEvents(trace.events, graph, trace.run.run_id)
        : [],
    [mode, graph, trace.run, trace.events],
  );
  const links = useMemo(
    () => withRecordedDataLinks(base.links, events, base.entities.map((entity) => entity.node)),
    [base, events],
  );
  const diagram = useMemo(() => {
    const positions = communicationPositions(base.entities, links, events);
    const nodes: CardNode[] = base.entities.map((entity) => ({
      id: entity.node.id,
      type: "communication",
      width: 280,
      height: 150,
      measured: { width: 280, height: 150 },
      initialWidth: 280,
      initialHeight: 150,
      position: positions[entity.node.id]!,
      selected: selection?.kind === "node" && selection.id === entity.node.id,
      data: {
        entity,
        uuid: uuids[entity.node.id] ?? "available template",
        status: mode === "run" ? trace.runState[entity.node.id] : undefined,
      },
    }));
    const edges = links.map((link) => {
      const matched = eventsForLink(events, link);
      const data = matched.some((event) => event.details?.["transfer_kind"] === "mapped_data");
      const transferLabel = matched.some((event) => event.details?.["transfer_kind"] === "delegated_task") ? "Delegated task" : matched.some((event) => event.details?.["transfer_kind"] === "delegated_result") ? "Returned result" : data ? "Data" : "Execution";
      const returned = matched.some((event) => event.details?.["transfer_kind"] === "delegated_result");
      const delegated = matched.some((event) => event.details?.["transfer_kind"] === "delegated_task");
      const executed =
        mode === "run" &&
        link.kind === "route" &&
        !!link.edgeId &&
        trace.activeEdges.has(link.edgeId);
      const color =
        link.kind === "hierarchy"
          ? "var(--primary)"
          : matched.length
            ? "var(--success)"
            : executed
              ? "var(--primary)"
              : "var(--muted-foreground)";
      return {
        id: link.id,
        source: link.source,
        target: link.target,
        sourceHandle: `${returned ? "result" : delegated ? "route" : link.kind === "hierarchy" ? "hierarchy" : link.kind === "data" ? "data" : "route"}-out`,
        targetHandle: `${returned ? "result" : delegated ? "route" : link.kind === "hierarchy" ? "hierarchy" : link.kind === "data" ? "data" : "route"}-in`,
        type: "communication",
        label: matched.length
          ? `${transferLabel} handoff · ${matched.length}`
          : link.kind === "hierarchy"
            ? "Parent relationship"
            : executed
              ? "Executed route · no handoff snapshot"
              : link.label,
        animated: matched.length > 0,
        selected: selection?.kind === "link" && selection.id === link.id,
        markerEnd: { type: MarkerType.ArrowClosed, color },
        style: {
          stroke: color,
          strokeWidth: matched.length ? 2.5 : 1.5,
          strokeDasharray: link.kind === "hierarchy" ? "5 5" : undefined,
        },
        labelStyle: { fontSize: 10 },
        labelBgStyle: { fill: "var(--background)" },
        labelBgPadding: [5, 3] as [number, number],
        data: {
          link,
          returned,
          label: matched.length
            ? `${transferLabel} handoff · ${matched.length}`
            : link.kind === "hierarchy"
              ? "Parent relationship"
              : executed
                ? "Executed route · no handoff snapshot"
                : link.label,
          inspect: () => setSelection({ kind: "link", id: link.id }),
        },
      };
    });
    return { nodes, edges };
  }, [base.entities, links, uuids, selection, mode, trace.runState, trace.activeEdges, events]);
  const entity =
    selection?.kind === "node"
      ? base.entities.find((item) => item.node.id === selection.id)
      : undefined;
  const link =
    selection?.kind === "link" ? links.find((item) => item.id === selection.id) : undefined;
  const label = (id: string) =>
    base.entities.find((item) => item.node.id === id)?.node.data.label ?? id;
  return (
    <>
      <div className="flex flex-wrap items-center gap-2 border-b border-border p-3 text-xs">
        <label htmlFor="communication-mode">View</label>
        <select
          id="communication-mode"
          className="rounded-md border border-border bg-background p-1.5"
          value={mode}
          onChange={(event) => {
            setMode(event.target.value as "configured" | "run");
            setSelection(null);
          }}
        >
          <option value="configured">Configured workflow</option>
          <option value="run" disabled={!trace.runId}>
            Selected run
          </option>
        </select>
        {mode === "run" && (
          <select
            aria-label="Communication run"
            className="min-w-0 max-w-full rounded-md border border-border bg-background p-1.5"
            value={trace.runId}
            onChange={(event) => {
              trace.selectRun(event.target.value);
              setSelection(null);
            }}
          >
            {trace.runs.map((run) => (
              <option key={run.run_id} value={run.run_id}>
                {run.run_id} · v{run.workflow_version}
              </option>
            ))}
          </select>
        )}
        <span className="text-muted-foreground">
          {mode === "run"
            ? `Recorded run · v${runVersion ?? "…"}`
            : "Current draft · configured relationships"}
        </span>
      </div>
      <div className="border-b border-border px-3 py-2 text-xs text-muted-foreground">
        Dashed: parent relationship · Green: recorded handoff · Grey: configured route. Arrows
        follow application routing; a parent relationship alone does not establish a message
        exchange.
      </div>
      <ApiFeedback error={error ?? (mode === "run" ? trace.error : null)} />
      {!graph ? (
        <p role="status" className="p-5 text-sm">
          {error
            ? "Run revision unavailable. Switch to Configured workflow to inspect the draft."
            : "Loading the selected run revision…"}
        </p>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col md:flex-row">
          <div className={`min-h-0 min-w-0 flex-1 ${mobile && selection ? "hidden" : ""}`}>
            {mobile ? (
              <div className="h-full space-y-4 overflow-y-auto p-3">
                <section aria-label="Communication agents">
                  <h3 className="mb-2 text-sm font-semibold">Agents and steps</h3>
                  {base.entities.map((item) => (
                    <button
                      key={item.node.id}
                      onClick={() => setSelection({ kind: "node", id: item.node.id })}
                      className="mb-2 block w-full rounded-lg border border-border p-3 text-left"
                    >
                      <span className="block text-xs text-primary">{item.role}</span>
                      <span className="block text-sm font-medium">{item.node.data.label}</span>
                      <span className="block break-all font-mono text-[10px] text-muted-foreground">
                        UUID {uuids[item.node.id] ?? "unavailable"}
                      </span>
                    </button>
                  ))}
                </section>
                <section aria-label="Communication connections">
                  <h3 className="mb-2 text-sm font-semibold">Connections</h3>
                  {links.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => setSelection({ kind: "link", id: item.id })}
                      className="mb-2 block w-full rounded-lg border border-border p-3 text-left text-xs"
                    >
                      {label(item.source)} → {label(item.target)}
                      <span className="mt-1 block text-muted-foreground">
                        {item.label} · {eventsForLink(events, item).length} recorded handoffs
                      </span>
                    </button>
                  ))}
                </section>
              </div>
            ) : (
              <ReactFlowProvider key={`${mode}:${graph.id}:${graph.serverVersion ?? "draft"}`}>
                <ReactFlow
                  key={`${mode}:${graph.id}:${graph.serverVersion ?? "draft"}`}
                  nodes={diagram.nodes}
                  edges={diagram.edges}
                  nodeTypes={nodeTypes}
                  edgeTypes={edgeTypes}
                  fitView
                  fitViewOptions={{ padding: 0.18 }}
                  nodesDraggable={false}
                  nodesConnectable={false}
                  deleteKeyCode={null}
                  minZoom={0.15}
                  maxZoom={1.5}
                  proOptions={{ hideAttribution: true }}
                  onNodeClick={(_, node) => setSelection({ kind: "node", id: node.id })}
                  onEdgeClick={(_, edge) => setSelection({ kind: "link", id: edge.id })}
                  onPaneClick={() => setSelection(null)}
                  aria-label="Agent relationship diagram"
                >
                  <Background gap={20} />
                  <Controls showInteractive={false} />
                  <FitSpawnedNodes signature={`${diagram.nodes.map((node) => node.id).join(",")}:${Boolean(selection)}`} />
                </ReactFlow>
              </ReactFlowProvider>
            )}
          </div>
          {(entity || link) && (
            <aside
              aria-label="Communication inspector"
              className="h-full w-full shrink-0 overflow-y-auto border-l border-border p-4 md:w-[390px]"
            >
              <button
                onClick={() => setSelection(null)}
                className="mb-4 rounded-md border border-border px-2 py-1 text-xs"
              >
                {mobile ? "Back to diagram" : "Close details"}
              </button>
              {entity && (
                <div className="space-y-4">
                  <h3 className="font-semibold">{entity.node.data.label}</h3>
                  <p className="text-xs text-primary">{entity.role}</p>
                  <dl className="space-y-2 break-all text-xs">
                    <dt>Node UUID</dt>
                    <dd className="font-mono">{uuids[entity.node.id] ?? "Unavailable"}</dd>
                    <dt>Node ID</dt>
                    <dd>{entity.node.id}</dd>
                    {entity.agentId && (
                      <>
                        <dt>Agent ID</dt>
                        <dd>{entity.agentId}</dd>
                      </>
                    )}
                    {entity.parentNodeId && (
                      <>
                        <dt>Parent agent</dt>
                        <dd>{label(entity.parentNodeId)}</dd>
                      </>
                    )}
                  </dl>
                  {mode === "run" ? (
                    <NodeTrace node={entity.node} trace={trace} />
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      This is the configured relationship. Select a run to inspect execution traces.
                    </p>
                  )}
                </div>
              )}
              {link && (
                <div className="space-y-4">
                  <h3 className="flex items-center gap-2 font-semibold">
                    {label(link.source)} <ArrowRight className="h-4 w-4 shrink-0" />{" "}
                    {label(link.target)}
                  </h3>
                  <p className="text-xs">{link.label}</p>
                  <dl className="space-y-1 break-all text-xs">
                    <dt>Sender node UUID</dt>
                    <dd className="font-mono">{uuids[link.source] ?? "Unavailable"}</dd>
                    <dt>Receiver node UUID</dt>
                    <dd className="font-mono">{uuids[link.target] ?? "Unavailable"}</dd>
                  </dl>
                  {link.kind === "hierarchy" ? (
                    <p className="text-sm text-muted-foreground">
                      Configured parent/sub-agent relationship. Inspect a workflow route or recorded
                      data connection to see actual handoff evidence.
                    </p>
                  ) : mode !== "run" ? (
                    <p className="text-sm text-muted-foreground">
                      Configured route. Select a run to inspect what happened.
                    </p>
                  ) : (
                    <HandoffDetails
                      link={link}
                      events={eventsForLink(events, link)}
                      timeline={trace.events}
                    />
                  )}
                </div>
              )}
            </aside>
          )}
        </div>
      )}
    </>
  );
}

function HandoffDetails({
  link,
  events,
  timeline,
}: {
  link: CommunicationLink;
  events: ReturnType<typeof handoffEvents>;
  timeline: RunEvent[];
}) {
  if (!events.length)
    return (
      <p className="text-sm text-muted-foreground">
        No handoff evidence was captured for this connection in the selected run. It may be skipped
        or predate handoff recording.
      </p>
    );
  return (
    <div className="space-y-4" aria-label="Recorded handoffs">
      {events.map((event) => {
        const details = event.details ?? {};
        const observed = details["transfer_kind"] === "mapped_data";
        const delegatedTask = details["transfer_kind"] === "delegated_task";
        const delegatedResult = details["transfer_kind"] === "delegated_result";
        const result = handoffResult(timeline, event);
        const elapsed = result
          ? Math.max(0, Date.parse(result.timestamp) - Date.parse(event.timestamp))
          : undefined;
        return (
          <section key={event.event_id} className="space-y-3 rounded-lg border border-border p-3">
            <p className="text-sm font-semibold">
              {delegatedTask ? "Delegated task" : delegatedResult ? "Returned specialist result" : observed ? "Mapped data handoff" : "Execution transition"}
            </p>
            <p className="break-all font-mono text-xs">
              Handoff UUID: {String(details["handoff_id"] ?? "not captured")}
            </p>
            <p className="text-xs text-muted-foreground">
              {new Date(event.timestamp).toLocaleString()} · {delegatedResult ? "Result received by the master." : "Inputs prepared for the receiving step."}
            </p>
            <p className="text-xs text-muted-foreground">
              Receiving step:{" "}
              {result?.event_type === "node.completed"
                ? "completed"
                : result?.event_type === "node.failed"
                  ? "failed"
                  : "Result not captured or pending"}
              {elapsed !== undefined ? ` · ${elapsed} ms from handoff` : ""}
            </p>
            {!observed && !delegatedTask && !delegatedResult && (
              <p className="text-xs text-muted-foreground">
                The workflow advanced along this route. No source-output data mapping was recorded
                for it.
              </p>
            )}
            {details["dynamic_output_reference"] === true && (
              <p className="text-xs text-muted-foreground">
                The input includes a dynamic output reference; its exact source is not inferred.
              </p>
            )}
            {[
              ...[
                "source_agent_id",
                "target_agent_id",
                "source_invocation_id",
                "target_invocation_id",
              ].map((key) => [key.replaceAll("_", " "), details[key]] as const),
              ["Input mapping", details["input_mapping"]],
              ["Delegation reason", details["reason"]],
              ["Mapped fields from this source", details["mapped_fields"]],
              ["Receiving step inputs", details["receiver_input"]],
              ["Available source result", details["source_output"]],
              ["Receiving step result", result?.details?.["output"]],
              ["Receiving step error", result?.details?.["error_code"]],
            ].map(([title, value]) => (
              <div key={String(title)}>
                <h4 className="text-xs font-medium capitalize">{String(title)}</h4>
                <pre className="mt-1 max-h-56 overflow-auto whitespace-pre-wrap break-words rounded-md bg-muted/50 p-2 text-[11px]">
                  {value === undefined ? "Not captured" : JSON.stringify(value, null, 2)}
                </pre>
              </div>
            ))}
            <p className="break-all text-[10px] text-muted-foreground">
              Event {event.event_id} · Route {link.edgeId ?? "data dependency"}
            </p>
          </section>
        );
      })}
    </div>
  );
}
