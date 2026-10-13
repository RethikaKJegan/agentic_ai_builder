import { useEffect, useMemo, useState } from "react";
import { Background, Controls, ReactFlow, ReactFlowProvider, Handle, Position, type NodeProps } from "@xyflow/react";
import dagre from "@dagrejs/dagre";
import { api } from "@/api/client";
import { procurementGraph, compactProcurementGraph, type ProjectCommunication } from "@/domain/procurement-communication";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";

function Card({ data }: NodeProps) {
  return <div className="w-60 rounded-xl border bg-background p-3 shadow-sm">
    <Handle type="target" position={Position.Top} /><p className="text-xs text-primary">{String(data["role"])}</p>
    <p className="break-words text-sm font-medium">{String(data["label"])}</p>
    <p className="mt-1 text-xs text-muted-foreground">{String(data["status"])}</p><Handle type="source" position={Position.Bottom} />
  </div>;
}
const nodeTypes = { project: Card };

export function ProcurementProjectCommunication({ workflowId, version }: { workflowId: string; version: number }) {
  const [project, setProject] = useState<ProjectCommunication>();
  const [error, setError] = useState<Error>();
  const [selected, setSelected] = useState("");
  const [expanded, setExpanded] = useState(false);
  useEffect(() => {
    let disposed = false; let timer: ReturnType<typeof setTimeout>;
    const refresh = async () => {
      try { const value = await api.procurementProjectCommunication(workflowId, version); if (!disposed) { setProject(value); setError(undefined); } }
      catch (e) { if (!disposed) setError(e instanceof Error ? e : new Error("Project communication could not be loaded.")); }
      finally { if (!disposed) timer = setTimeout(() => void refresh(), 5000); }
    };
    void refresh(); return () => { disposed = true; clearTimeout(timer); };
  }, [workflowId, version]);
  const graph = useMemo(() => {
    if (!project) return { nodes: [], edges: [] };
    const combined = expanded ? procurementGraph(project) : compactProcurementGraph(project);
    const visible = combined.nodes.filter(n => expanded || !n.parent || n.role === "Recorded project action" || n.role === "Master agent" || n.role === "Sub-agent");
    const ids = new Set(visible.map(n => n.id));
    const edges = combined.edges.filter(e => ids.has(e.source) && ids.has(e.target));
    for (const n of visible) if (n.parent && ids.has(n.parent) && !edges.some(e => e.target === n.id))
      edges.push({ id: `contains:${n.id}`, source: n.parent, target: n.id, label: "Contains", recorded: false });
    const layout = new dagre.graphlib.Graph(); layout.setGraph({ rankdir: "TB", nodesep: 35, ranksep: 70 }); layout.setDefaultEdgeLabel(() => ({}));
    visible.forEach(n => layout.setNode(n.id, { width: 240, height: 100 }));
    // Recorded return arrows remain visible but do not form layout cycles.
    edges.filter(e => !e.recorded).forEach(e => layout.setEdge(e.source, e.target)); dagre.layout(layout);
    return { nodes: visible.map(n => ({ id: n.id, type: "project", position: { x: layout.node(n.id).x - 120, y: layout.node(n.id).y - 50 }, data: n })),
      edges: edges.map(e => ({ ...e, style: { stroke: e.recorded ? "#16a34a" : "#94a3b8", strokeDasharray: e.recorded ? undefined : "5 5" } })) };
  }, [project, expanded]);
  const details = project ? (expanded ? procurementGraph(project) : compactProcurementGraph(project)).nodes.find(n => n.id === selected) : undefined;
  return <>
    <div className="space-y-2 border-b p-3 text-xs"><p>Entire procurement workflow · {project?.phase ?? "Loading"}. Click any card for its original run, tool results, approvals and recorded explanations.</p>
      <label><input type="checkbox" checked={expanded} onChange={e => setExpanded(e.target.checked)} /> Show all tool and approval steps</label>
      <p>Green arrows are recorded handoffs. Dashed arrows show project/action containment or configured routes.</p>
      {project?.truncated && <p>Large traces are bounded here; the complete action history remains in Runs.</p>}
      <ApiFeedback error={error} /></div>
    <div className="flex min-h-0 flex-1 flex-col md:flex-row">
      <div className="min-h-[350px] min-w-0 flex-1"><ReactFlowProvider>
        <ReactFlow key={`${expanded}:${project?.actions.length ?? 0}`} nodes={graph.nodes} edges={graph.edges} nodeTypes={nodeTypes} fitView minZoom={0.05}
          onNodeClick={(_, node) => setSelected(node.id)}><Background /><Controls /></ReactFlow>
      </ReactFlowProvider></div>
      {details && <aside className="max-h-[45vh] w-full overflow-auto border-l p-3 md:max-h-none md:w-96">
        <p className="font-medium">{details.label}</p><p className="break-all text-xs">{details.runId}</p>
        <pre className="mt-2 whitespace-pre-wrap break-words text-xs">{JSON.stringify(details.details, null, 2)}</pre>
      </aside>}
    </div>
  </>;
}
