import { displayText } from "@/lib/display-text";
import { useEffect, useMemo, useState } from "react";
import dagre from "@dagrejs/dagre";
import {
  Background,
  BaseEdge,
  Controls,
  EdgeLabelRenderer,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  ReactFlowProvider,
  getBezierPath,
  getSmoothStepPath,
  useNodesInitialized,
  useReactFlow,
  type Edge,
  type EdgeProps,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import { Bot, CheckCircle2, Circle, Loader2, Network, X } from "lucide-react";
import { communicationUuid } from "@/domain/communication";
import type { DiagramCard, DiagramConnection, DiagramModel } from "@/domain/communication-diagram";
import { ReadableEvidence } from "./CommunicationEvidence";

type CardNode = Node<
  { card: DiagramCard; task?: number | undefined; inspect: () => void },
  "agent"
>;
type ConnectionEdge = Edge<{ connection: DiagramConnection; inspect: () => void }, "communication">;
function AgentCard({ data, selected }: NodeProps<CardNode>) {
  const { card } = data;
  const working = card.status === "Working";
  const complete = card.status === "Completed";
  const failed = ["Failed", "Approval rejected"].includes(card.status);
  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={displayText(`${card.label}${data.task ? ` · Task ${data.task}` : ""} · ${card.spawned ? "Spawned helper · " : ""}${card.status}`)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          data.inspect();
        }
      }}
      className={`h-[160px] w-[280px] rounded-xl border-2 bg-background p-3 text-left shadow-sm ${selected ? "border-primary ring-4 ring-primary/10" : working ? "border-blue-500" : failed ? "border-red-400" : complete ? "border-green-500/60" : "border-border"}`}
    >
      <Handle id="in" type="target" position={Position.Top} style={{ left: "35%" }} />
      <Handle id="out" type="source" position={Position.Bottom} style={{ left: "35%" }} />
      <Handle id="return-in" type="target" position={Position.Bottom} style={{ left: "65%" }} />
      <Handle id="return-out" type="source" position={Position.Top} style={{ left: "65%" }} />
      <div className="flex items-center justify-between gap-2">
        <span className="flex items-center gap-1.5 text-[11px] font-semibold text-primary">
          {card.role === "Coordinator" ? (
            <Network className="h-4 w-4" />
          ) : (
            <Bot className="h-4 w-4" />
          )}
          {card.role==='Coordinator'?'Master agent':card.role==='Helper agent'?'Sub-agent':card.role}
        </span>
        {card.spawned && (
          <span className="rounded-full bg-violet-100 px-2 py-0.5 text-[10px] font-semibold text-violet-700">
            Spawned · Task {data.task}
          </span>
        )}
      </div>
      <p className="mt-2 line-clamp-1 text-sm font-semibold leading-snug">{displayText(card.label)}</p>
      <p className="mt-2 line-clamp-2 text-[11px] leading-relaxed text-muted-foreground">
        {displayText(card.reason ??
          card.description ??
          (card.role === "Coordinator"
            ? "Coordinates the workflow and collects results."
            : "Click to inspect this step’s inputs and results."))}
      </p>
      {card.parent && (
        <p className="mt-1 truncate text-[10px] text-muted-foreground">
          {card.spawned ? "Started by" : "Available to"}: {card.parent}
        </p>
      )}
      <div
        className={`absolute bottom-3 left-3 flex items-center gap-1.5 rounded-full px-2 py-1 text-[11px] font-medium ${working ? "bg-blue-50 text-blue-700" : complete ? "bg-green-50 text-green-700" : failed ? "bg-red-50 text-red-700" : "bg-muted text-muted-foreground"}`}
      >
        {working ? (
          <Loader2 className="h-3 w-3 animate-spin motion-reduce:animate-none" />
        ) : complete ? (
          <CheckCircle2 className="h-3 w-3" />
        ) : (
          <Circle className="h-3 w-3" />
        )}
        {card.status}
      </div>
    </div>
  );
}
export function Connection({ data, ...props }: EdgeProps<ConnectionEdge>) {
  const connection = data?.connection;
  const [path, x, y] = connection?.returned ? getBezierPath(props) : getSmoothStepPath(props);
  return (
    <>
      <BaseEdge
        id={props.id}
        path={path}
        interactionWidth={24}
        {...(props.style ? { style: props.style } : {})}
        {...(props.markerStart ? { markerStart: props.markerStart } : {})}
        {...(props.markerEnd ? { markerEnd: props.markerEnd } : {})}
      />
      <EdgeLabelRenderer>
        <button
          type="button"
          className={`nodrag nopan rounded-full border bg-background px-2.5 py-1 text-[10px] font-medium shadow-sm ${connection?.active ? "border-blue-400 text-blue-700" : connection?.recorded ? "border-green-400 text-green-700" : "border-border text-muted-foreground"}`}
          style={{
            position: "absolute",
            pointerEvents: "all",
            transform: `translate(-50%, -50%) translate(${x}px, ${y + (connection?.returned ? 25 : 0)}px)`,
          }}
          onClick={(e) => {
            e.stopPropagation();
            data?.inspect();
          }}
        >
          {displayText(connection?.label)}
          {connection?.active ? " · Live" : ""}
        </button>
      </EdgeLabelRenderer>
    </>
  );
}
const nodeTypes = { agent: AgentCard };
const edgeTypes = { communication: Connection };
function FitNewAgents({ signature }: { signature: string }) {
  const ready = useNodesInitialized();
  const { fitView } = useReactFlow();
  useEffect(() => {
    if (!ready) return;
    const frame = requestAnimationFrame(() => void fitView({ padding: 0.15, duration: 250 }));
    return () => cancelAnimationFrame(frame);
  }, [ready, signature, fitView]);
  return null;
}
function Evidence({ title, value }: { title: string; value: unknown }) {
  return (
    <section>
      <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {displayText(title)}
      </h4>
      <div className="max-h-72 overflow-auto rounded-lg bg-muted/40 p-3">
        <ReadableEvidence value={value} />
      </div>
    </section>
  );
}
function NodeDetails({ card }: { card: DiagramCard }) {
  const [uuid, setUuid] = useState<string>();
  useEffect(() => {
    let disposed = false;
    communicationUuid(card.workflowId, card.nodeId)
      .then((id) => {
        if (!disposed) setUuid(id);
      })
      .catch(() => {});
    return () => {
      disposed = true;
    };
  }, [card.workflowId, card.nodeId]);
  const decisions = card.events.filter((e) => e.event_type === "agent.decision");
  const received = card.events.filter(
    (e) =>
      e.event_type === "node.handoff" &&
      e.details?.["target_node_id"] === card.nodeId &&
      e.details?.["transfer_kind"] === "delegated_result",
  );
  return (
    <div className="space-y-5">
      <div>
        <p className="text-xs font-medium text-primary">
          {card.role} · {card.status}
        </p>
        <h3 className="mt-1 text-lg font-semibold">{displayText(card.label)}</h3>
        {card.parent && (
          <p className="mt-2 text-sm">
            {card.spawned ? "Started by" : "Configured under"}: <strong>{card.parent}</strong>
          </p>
        )}
        {card.spawned && (
          <p className="mt-2 text-xs text-violet-700">
            This helper was started for a separate task in this run.
          </p>
        )}
      </div>
      <Evidence title="Task and purpose" value={card.reason ?? card.description} />
      {card.configuration!==undefined&&<details className="rounded-lg border p-3"><summary className="cursor-pointer text-xs font-medium">Agent configuration & tool access</summary><ReadableEvidence value={card.configuration}/></details>}
      <Evidence
        title={card.runId ? "Information received" : "Configured inputs"}
        value={card.input}
      />
      <Evidence title="Result" value={card.output} />
      {card.problem !== undefined && <Evidence title="Reported problem" value={card.problem} />}
      {received.length > 0 && (
        <Evidence
          title="Results received from helpers"
          value={received.map((e) => e.details?.["source_output"] ?? e.details?.["receiver_input"])}
        />
      )}
      {decisions.length > 0 && (
        <Evidence
          title="Coordinator decisions"
          value={decisions.map((e) => e.details?.["explanation"])}
        />
      )}
      {!card.runId && (
        <p className="text-xs text-muted-foreground">
          This is the workflow plan. No execution is being claimed.
        </p>
      )}
      <details className="text-xs">
        <summary className="cursor-pointer font-medium">Technical details</summary>
        <dl className="mt-3 space-y-2 break-all">
          <dt>Node UUID</dt>
          <dd className="font-mono">{card.invocationId ?? uuid ?? "Unavailable"}</dd>
          <dt>Node ID</dt>
          <dd>{card.nodeId}</dd>
          {card.agentId && (
            <>
              <dt>Agent ID</dt>
              <dd>{card.agentId}</dd>
            </>
          )}
          {card.runId && (
            <>
              <dt>Run ID</dt>
              <dd>{card.runId}</dd>
            </>
          )}
        </dl>
        <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap break-words">
          {displayText(JSON.stringify(card.events, null, 2))}
        </pre>
      </details>
    </div>
  );
}
function ConnectionDetails({
  connection,
  model,
}: {
  connection: DiagramConnection;
  model: DiagramModel;
}) {
  const from = model.cards.find((c) => c.id === connection.source);
  const to = model.cards.find((c) => c.id === connection.target);
  return (
    <div className="space-y-5">
      <div>
        <p className="text-xs font-medium text-primary">{displayText(connection.label)}</p>
        <h3 className="mt-1 text-base font-semibold">
          {displayText(from?.label)} → {displayText(to?.label)}
        </h3>
        <p className="mt-2 text-sm text-muted-foreground">
          {connection.recorded
            ? connection.returned
              ? "The helper sent its recorded result back."
              : "This connection has recorded execution evidence."
            : "This shows the workflow’s configured structure. No information exchange has been recorded for this connection."}
        </p>
      </div>
      {connection.events.map((event) => (
        <section key={event.event_id} className="space-y-4 rounded-xl border p-3">
          {event.details?.["reason"] !== undefined && (
            <Evidence title="Why this task was assigned" value={event.details["reason"]} />
          )}
          <Evidence
            title={connection.returned ? "Result returned" : "Information shared"}
            value={
              connection.returned
                ? (event.details?.["source_output"] ?? event.details?.["receiver_input"])
                : event.details?.["receiver_input"]
            }
          />
          <details className="text-xs">
            <summary className="cursor-pointer font-medium">Technical details</summary>
            <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap break-words">
              {displayText(JSON.stringify(event, null, 2))}
            </pre>
          </details>
        </section>
      ))}
    </div>
  );
}
export function CommunicationDiagram({ model }: { model: DiagramModel }) {
  const [selection, setSelection] = useState<{ kind: "node" | "connection"; id: string }>();
  const selectedCard =
    selection?.kind === "node" ? model.cards.find((c) => c.id === selection.id) : undefined;
  const selectedConnection =
    selection?.kind === "connection"
      ? model.connections.find((c) => c.id === selection.id)
      : undefined;
  const diagram = useMemo(() => {
    const layout = new dagre.graphlib.Graph();
    layout.setGraph({ rankdir: "TB", nodesep: 40, ranksep: 95 });
    layout.setDefaultEdgeLabel(() => ({}));
    model.cards.forEach((c) => layout.setNode(c.id, { width: 280, height: 160 }));
    model.connections.filter((c) => !c.returned).forEach((c) => layout.setEdge(c.source, c.target));
    dagre.layout(layout);
    const instances = new Map<string, number>();
    const nodes: CardNode[] = model.cards.map((card) => {
      const key = card.runId ?? "plan";
      const task = card.spawned ? (instances.get(key) ?? 0) + 1 : undefined;
      if (task) instances.set(key, task);
      const point = layout.node(card.id);
      return {
        id: card.id,
        type: "agent",
        position: { x: point.x - 140, y: point.y - 80 },
        selected: selectedCard?.id === card.id,
        data: { card, task, inspect: () => setSelection({ kind: "node", id: card.id }) },
      };
    });
    const edges: ConnectionEdge[] = model.connections.map((connection) => {
      const color = connection.active ? "#2563eb" : connection.recorded ? "#16a34a" : "#94a3b8";
      return {
        id: connection.id,
        source: connection.source,
        target: connection.target,
        sourceHandle: connection.returned ? "return-out" : "out",
        targetHandle: connection.returned ? "return-in" : "in",
        type: "communication",
        animated: connection.active,
        markerEnd: { type: MarkerType.ArrowClosed, color },
        style: {
          stroke: color,
          strokeWidth: connection.recorded ? 2.5 : 1.5,
          strokeDasharray: connection.recorded ? undefined : "5 5",
        },
        data: {
          connection,
          inspect: () => setSelection({ kind: "connection", id: connection.id }),
        },
      };
    });
    return { nodes, edges };
  }, [model, selectedCard?.id]);
  const signature = model.cards.map((c) => c.id).join(",");
  return (
    <div className="relative h-full min-h-0 w-full flex-1" aria-label="Agent communication diagram">
      <div className="absolute inset-0"><ReactFlowProvider>
        <ReactFlow
          nodes={diagram.nodes}
          edges={diagram.edges}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          fitView
          minZoom={0.08}
          maxZoom={1.75}
          nodesDraggable={false}
          nodesConnectable={false}
          deleteKeyCode={null}
          proOptions={{ hideAttribution: true }}
          onNodeClick={(_, node) => setSelection({ kind: "node", id: node.id })}
          onEdgeClick={(_, edge) => setSelection({ kind: "connection", id: edge.id })}
          onPaneClick={() => setSelection(undefined)}
        >
          <Background gap={24} />
          <Controls showInteractive={false} />
          <FitNewAgents signature={signature} />
        </ReactFlow>
      </ReactFlowProvider></div>
      {(selectedCard || selectedConnection) && (
        <aside
          aria-label="Agent details"
          className="absolute inset-y-0 right-0 z-20 w-full overflow-y-auto border-l bg-background p-5 shadow-xl md:w-[410px]"
        >
          <button
            type="button"
            aria-label="Close details"
            className="mb-4 flex items-center gap-1 rounded-md border px-2 py-1 text-xs"
            onClick={() => setSelection(undefined)}
          >
            <X className="h-3 w-3" />
            Close details
          </button>
          {selectedCard ? (
            <NodeDetails key={selectedCard.id} card={selectedCard} />
          ) : selectedConnection ? (
            <ConnectionDetails connection={selectedConnection} model={model} />
          ) : null}
        </aside>
      )}
      {!model.cards.length && (
        <p
          role="status"
          className="absolute left-5 top-5 rounded-lg border bg-background p-3 text-sm"
        >
          No diagram activity is available yet.
        </p>
      )}
    </div>
  );
}

export function DiagramLegend({ live }: { live: boolean }) {
  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-1 border-b px-4 py-2 text-[11px] text-muted-foreground">
      <span className="flex items-center gap-1.5">
        <span
          className={`h-2 w-2 rounded-full ${live ? "animate-pulse bg-blue-500 motion-reduce:animate-none" : "bg-muted-foreground"}`}
        />
        {live ? "Live · updates automatically" : "Click any card or connection to inspect"}
      </span>
      <span>Blue moving line: working</span>
      <span>Green arrow: recorded exchange</span>
      <span>Dashed line: planned relationship</span>
      <span className="text-violet-700">Spawned: helper started for this run</span>
    </div>
  );
}
