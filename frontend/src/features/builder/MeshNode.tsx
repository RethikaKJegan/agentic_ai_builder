import { Handle, Position, type NodeProps, type Node } from "@xyflow/react";
import { createContext, memo, useContext } from "react";
import { Check, ChevronDown, ChevronRight, Loader2, Minus, Network, Pause, PauseCircle, X } from "lucide-react";
import { NODE_META } from "./nodeMeta";
import { useMesh } from "@/domain/store";
import { getModel } from "@/domain/models";
import type { WorkflowNodeData } from "@/domain/types";

export type MeshFlowNode = Node<WorkflowNodeData & { runStatus?: string | undefined; childCount?: number | undefined; parentLabel?: string | undefined }, "mesh">;

/** Canvas-level actions available to nodes (provided by the builder). */
export const NodeActions = createContext<{ toggleCollapse: (id: string) => void }>({ toggleCollapse: () => {} });

function MeshNodeImpl({ id, data, selected }: NodeProps<MeshFlowNode>) {
  const meta = NODE_META[data.kind];
  const actions = useContext(NodeActions);
  const agent = useMesh((s) => (data.agentId ? s.agents.find((a) => a.id === data.agentId) : undefined));
  const st = data.runStatus;
  const tb = data.orientation === "tb";
  const isMaster = data.role === "master";
  const isSub = data.role === "sub";
  const ring =
    st === "running" ? "border-primary node-running" :
    st === "success" || st === "approved" ? "border-success/60" :
    st === "paused" ? "border-warning" :
    st === "failed" || st === "rejected" || st === "blocked" ? "border-destructive" :
    selected ? "border-primary shadow-lift" :
    isMaster ? "border-primary/50" : "border-border hover:border-border-accent";
  const Icon = isMaster ? Network : meta.icon;

  return (
    <div className={`${isMaster ? "w-[280px] bg-gradient-to-b from-highlight to-background p-3.5" : "w-[248px] bg-background p-3"} rounded-xl border shadow-soft transition-[border-color,box-shadow] duration-200 ${ring} ${agent?.paused ? "opacity-70" : ""}`}>
      {data.kind !== "trigger" && <Handle type="target" position={tb ? Position.Top : Position.Left} />}
      {(isMaster || isSub) && (
        <p className={`mb-1.5 text-[10px] font-medium uppercase tracking-wider ${isMaster ? "text-primary" : "text-muted-foreground"}`}>
          {isMaster ? "Master agent" : `Sub-agent${data.parentLabel ? ` · of ${data.parentLabel}` : ""}`}
        </p>
      )}
      <div className="flex items-start gap-2.5">
        <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${meta.tone}`}>
          <Icon className="h-4 w-4" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-[13px] font-medium leading-tight">{data.label}</p>
          <p className="mt-0.5 truncate text-[11px] text-muted-foreground">
            {data.kind === "agent" && agent ? `${getModel(agent.modelId).name}${agent.tools.length ? ` · ${agent.tools.length} tool${agent.tools.length > 1 ? "s" : ""}` : ""}` : data.tool ?? meta.label}
          </p>
        </div>
        {st && (
          <span className="mt-0.5">
            {st === "running" && <Loader2 className="h-4 w-4 animate-spin text-primary" />}
            {(st === "success" || st === "approved") && <Check className="h-4 w-4 text-success" />}
            {st === "paused" && <Pause className="h-4 w-4 text-warning" />}
            {st === "skipped" && <Minus className="h-4 w-4 text-muted-foreground" />}
            {(st === "failed" || st === "rejected" || st === "blocked") && <X className="h-4 w-4 text-destructive" />}
          </span>
        )}
      </div>
      {(agent?.purpose || data.description) && <p className="mt-2 line-clamp-1 text-[11px] text-muted-foreground">{data.description || agent?.purpose}</p>}
      {(agent?.paused || (data.childCount ?? 0) > 0) && (
        <div className="mt-2 flex items-center gap-2">
          {agent?.paused && <span className="inline-flex items-center gap-1 rounded-full bg-warning/15 px-1.5 py-0.5 text-[10px] font-medium text-warning"><PauseCircle className="h-3 w-3" />Paused</span>}
          {(data.childCount ?? 0) > 0 && (
            <button
              onClick={(e) => { e.stopPropagation(); actions.toggleCollapse(id); }}
              className="nodrag ml-auto inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px] text-primary hover:bg-highlight"
              aria-expanded={!data.collapsed}
              aria-label={data.collapsed ? `Expand ${data.label}` : `Collapse ${data.label}`}
            >
              {data.collapsed ? <ChevronRight className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              {data.collapsed ? `${data.childCount} hidden` : `${data.childCount} sub-agent${data.childCount! > 1 ? "s" : ""}`}
            </button>
          )}
        </div>
      )}
      {data.kind !== "output" && <Handle type="source" position={tb ? Position.Bottom : Position.Right} />}
    </div>
  );
}

export const MeshNode = memo(MeshNodeImpl);
