import "@xyflow/react/dist/style.css";
import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  addEdge,
  applyEdgeChanges,
  applyNodeChanges,
  useReactFlow,
  type Connection,
  type Edge,
  type EdgeChange,
  type NodeChange,
} from "@xyflow/react";
import { Link, useNavigate } from "@/lib/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowLeft,
  Copy,
  LayoutTemplate,
  MoreHorizontal,
  Plus,
  Redo2,
  Sparkles,
  Trash2,
  Undo2,
  ChevronDown,
  ChevronUp,
  Check,
} from "lucide-react";
import { toast } from "sonner";
import { useMesh } from "@/domain/store";
import { applyCommand, SUPPORTED_COMMANDS } from "@/domain/commands";
import { autoLayout } from "@/domain/layout";
import { uid } from "@/domain/ids";
import { makeAgent } from "@/domain/templates";
import type {
  NodeKind,
  StepStatus,
  Workflow,
  WorkflowEdge,
  WorkflowNode,
} from "@/domain/types";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useIsMobile } from "@/hooks/use-mobile";
import { AgentInspector } from "@/features/agents/AgentInspector";
import { StatusPill } from "@/features/shell/StatusPill";
import { MeshNode, NodeActions, type MeshFlowNode } from "./MeshNode";
import { PatternsPanel, PATTERN_MIME } from "./PatternsPanel";
import { insertPattern, PATTERNS, type PatternKind } from "@/domain/patterns";
import {
  addSubAgent,
  depthOf,
  hiddenIds,
  isHierarchy,
  layoutTB,
  removeSubtree,
} from "@/domain/hierarchy";
import { NODE_META } from "./nodeMeta";
import { WorkflowControls } from "@/features/workflows/WorkflowControls";

const nodeTypes = { mesh: MeshNode };
type Graph = { nodes: WorkflowNode[]; edges: WorkflowEdge[] };

const clean = (nodes: MeshFlowNode[]): WorkflowNode[] =>
  nodes.map((n) => ({
    id: n.id,
    type: "mesh",
    position: n.position,
    data: { ...n.data, runStatus: undefined },
  }));

export default function BuilderRoot({ workflow }: { workflow: Workflow }) {
  return (
    <ReactFlowProvider>
      <Builder key={workflow.id} workflow={workflow} />
    </ReactFlowProvider>
  );
}

function Builder({ workflow }: { workflow: Workflow }) {
  const navigate = useNavigate();
  const { fitView, screenToFlowPosition } = useReactFlow();
  const store = useMesh();
  const agents = store.agents;
  const [nodes, setNodes] = useState<MeshFlowNode[]>(() => workflow.nodes as MeshFlowNode[]);
  const [edges, setEdges] = useState<WorkflowEdge[]>(workflow.edges);
  const nodesRef = useRef(nodes);
  const edgesRef = useRef(edges);
  nodesRef.current = nodes;
  edgesRef.current = edges;
  const [past, setPast] = useState<Graph[]>([]);
  const [future, setFuture] = useState<Graph[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [panel, setPanel] = useState<"inspector" | null>(null);
  const [savedAt, setSavedAt] = useState<Date>(new Date(workflow.updatedAt));
  const [composerOpen, setComposerOpen] = useState(
    () => typeof window === "undefined" || window.innerWidth >= 768,
  );
  const [cmd, setCmd] = useState("");
  const [runState] = useState<Record<string, StepStatus | "running">>({});
  const [activeEdges] = useState<Set<string>>(new Set());
  const isMobile = useIsMobile();

  const commit = useCallback(
    (g: Graph, opts: { history?: boolean } = {}) => {
      if (opts.history !== false) {
        const previous = { nodes: clean(nodesRef.current), edges: [...edgesRef.current] };
        setPast((p) => [
          ...p.slice(-49),
          previous,
        ]);
        setFuture([]);
      }
      setNodes(g.nodes as MeshFlowNode[]);
      setEdges(g.edges);
      store.updateGraph(workflow.id, clean(g.nodes as MeshFlowNode[]), g.edges);
      setSavedAt(new Date());
    },
    [store, workflow.id],
  );

  const undo = useCallback(() => {
    const prev = past[past.length - 1];
    if (!prev) return;
    setFuture((f) => [{ nodes: clean(nodesRef.current), edges: edgesRef.current }, ...f]);
    setPast((p) => p.slice(0, -1));
    commit(prev, { history: false });
  }, [past, commit]);
  const redo = useCallback(() => {
    const next = future[0];
    if (!next) return;
    setPast((p) => [...p, { nodes: clean(nodesRef.current), edges: edgesRef.current }]);
    setFuture((f) => f.slice(1));
    commit(next, { history: false });
  }, [future, commit]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      if (t.closest("input, textarea, select, [contenteditable]")) return;
      if (e.key === "Escape") {
        setPanel(null);
        return;
      }
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "z") {
        e.preventDefault();
        if (e.shiftKey) redo();
        else undo();
      } else if (!e.metaKey && !e.ctrlKey && e.key.toLowerCase() === "f") {
        fitView({ duration: 250, padding: 0.15, maxZoom: 1 });
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [undo, redo, fitView]);

  useEffect(() => {
    const t = setTimeout(() => fitView({ duration: 250, padding: 0.15, maxZoom: 1 }), 60);
    return () => clearTimeout(t);
  }, [panel, fitView]);

  const onNodesChange = useCallback(
    (changes: NodeChange<MeshFlowNode>[]) => {
      const removed = changes
        .filter((c) => c.type === "remove")
        .map((c) => (c as { id: string }).id);
      const next = applyNodeChanges(changes, nodesRef.current);
      if (removed.length) {
        if (nodesRef.current.some((n) => removed.includes(n.id) && n.data.kind === "trigger")) {
          toast.error("Every workflow needs a trigger.");
          return;
        }
        commit({
          nodes: next,
          edges: edgesRef.current.filter(
            (e) => !removed.includes(e.source) && !removed.includes(e.target),
          ),
        });
        setSelectedId(null);
        setPanel((p) => (p === "inspector" ? null : p));
      } else {
        setNodes(next);
      }
    },
    [commit],
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange<Edge>[]) => {
      const next = applyEdgeChanges(
        changes,
        edgesRef.current as Edge[],
      ) as unknown as WorkflowEdge[];
      if (changes.some((c) => c.type === "remove"))
        commit({ nodes: nodesRef.current, edges: next });
      else
        setEdges(
          next.map((e) => ({ id: e.id, source: e.source, target: e.target, label: e.label })),
        );
    },
    [commit],
  );

  const onConnect = useCallback(
    (c: Connection) => {
      if (c.source === c.target) return;
      const src = nodesRef.current.find((n) => n.id === c.source);
      const declared = src?.data.kind === "condition" ? (src.data["condition"] as { outcomes?: string[] } | undefined)?.outcomes ?? ["critical", "standard"]
        : src?.data.kind === "approval" ? ["approved", "rejected"] : undefined;
      const label = declared?.find((outcome) => !edgesRef.current.some((edge) => edge.source === c.source && edge.label === outcome));
      if (declared && !label) { toast("Every declared outcome already has a connection."); return; }
      if (edgesRef.current.some((edge) => edge.source === c.source && edge.target === c.target && edge.label === label)) return;
      const next = addEdge(
        { ...c, id: uid("edge"), label } as Edge,
        edgesRef.current as Edge[],
      ) as unknown as WorkflowEdge[];
      commit({
        nodes: nodesRef.current,
        edges: next.map((e) => ({
          id: e.id,
          source: e.source,
          target: e.target,
          label: e.label as string | undefined,
        })),
      });
    },
    [commit],
  );

  const addNode = (kind: NodeKind, agentId?: string) => {
    const maxX = Math.max(0, ...nodesRef.current.map((n) => n.position.x));
    let aid = agentId;
    if (kind === "agent" && !aid) {
      const a = makeAgent(
        {
          name: "New Agent",
          role: "Assistant",
          purpose: "Describe what this agent does.",
          instructions: "",
          modelId: "gpt-5-mini",
          tools: [],
          knowledge: [],
        },
        workflow.workspaceId,
      );
      useMesh.setState((s) => ({ agents: [a, ...s.agents] }));
      aid = a.id;
    }
    const agentName = aid ? useMesh.getState().agents.find((a) => a.id === aid)?.name : undefined;
    const n: MeshFlowNode = {
      id: uid("node"),
      type: "mesh",
      position: { x: maxX + 300, y: 60 },
      data: { kind, label: agentName ?? NODE_META[kind].label, description: "", agentId: aid },
    };
    commit({ nodes: [...nodesRef.current, n], edges: edgesRef.current });
    setSelectedId(n.id);
    setPanel("inspector");
  };

  const insertPatternAt = (kind: PatternKind, at?: { x: number; y: number }) => {
    const pos =
      at ??
      screenToFlowPosition({ x: window.innerWidth / 2 - 250, y: window.innerHeight / 2 - 80 });
    const p = insertPattern(kind, pos, workflow.workspaceId);
    const limit = useMesh.getState().controlContext(workflow.id).controls.maxAgentsPerWorkflow;
    const count = nodesRef.current.filter((n) => n.data.kind === "agent").length + p.agents.length;
    if (count > limit) {
      toast.error(`Pattern would bring this workflow to ${count} agents`, {
        description: `Agent controls allow at most ${limit} per workflow.`,
      });
      return;
    }
    useMesh.setState((s) => ({ agents: [...p.agents, ...s.agents] }));
    commit({
      nodes: [...nodesRef.current, ...(p.nodes as MeshFlowNode[])],
      edges: [...edgesRef.current, ...p.edges],
    });
    toast.success(`${PATTERNS.find((x) => x.id === kind)?.name} pattern added`, {
      description: "Connect it to your flow, then edit each step.",
    });
  };

  const onDrop = (e: React.DragEvent) => {
    const kind = e.dataTransfer.getData(PATTERN_MIME) as PatternKind;
    if (!kind) return;
    e.preventDefault();
    insertPatternAt(kind, screenToFlowPosition({ x: e.clientX, y: e.clientY }));
  };

  const toggleCollapse = useCallback(
    (id: string) => {
      commit(
        {
          nodes: nodesRef.current.map((n) =>
            n.id === id ? { ...n, data: { ...n.data, collapsed: !n.data.collapsed } } : n,
          ),
          edges: edgesRef.current,
        },
        { history: false },
      );
    },
    [commit],
  );
  const nodeActions = useMemo(() => ({ toggleCollapse }), [toggleCollapse]);

  const addChild = (parentId: string) => {
    const parent = nodesRef.current.find((n) => n.id === parentId);
    const c = useMesh.getState().controlContext(workflow.id).controls;
    const r = addSubAgent(
      { nodes: clean(nodesRef.current), edges: edgesRef.current },
      parentId,
      { maxDepth: c.maxDepth, maxChildren: c.maxChildren, maxAgents: c.maxAgentsPerWorkflow },
      parent?.data.agentId,
      workflow.workspaceId,
    );
    if (!r.ok) {
      toast.error("Can't add sub-agent", { description: r.reason });
      return;
    }
    useMesh.setState((s) => ({ agents: [r.agent, ...s.agents] }));
    commit({
      nodes: r.nodes.map((n) =>
        n.id === parentId ? { ...n, data: { ...n.data, collapsed: false } } : n,
      ),
      edges: r.edges,
    });
    store.audited("Added sub-agent", `${r.agent.name} under ${parent?.data.label}`);
    const added = r.nodes[r.nodes.length - 1]!;
    setSelectedId(added.id);
  };

  const removeChild = (id: string) => {
    const n = nodesRef.current.find((x) => x.id === id);
    const r = removeSubtree({ nodes: clean(nodesRef.current), edges: edgesRef.current }, id);
    commit({ nodes: r.nodes, edges: r.edges });
    store.audited(
      "Removed sub-agent",
      `${n?.data.label}${r.removed > 1 ? ` and ${r.removed - 1} nested steps` : ""}`,
    );
    setSelectedId(null);
    setPanel(null);
  };

  const tidy = () => {
    const layout = isHierarchy(nodesRef.current) ? layoutTB : autoLayout;
    commit({ nodes: layout(clean(nodesRef.current), edgesRef.current), edges: edgesRef.current });
    setTimeout(() => fitView({ duration: 300, padding: 0.2 }), 50);
  };

  const runCommand = (text = cmd) => {
    if (!text.trim()) return;
    const r = applyCommand({ nodes: clean(nodesRef.current), edges: edgesRef.current }, text);
    if (!r.ok) {
      toast.error(r.message);
      return;
    }
    commit(r.graph);
    store.audited("Edited by instruction", text);
    setCmd("");
    toast.success(r.message, { description: "Local draft edit · undo with ⌘Z" });
    setTimeout(() => fitView({ duration: 300, padding: 0.2 }), 50);
  };

  const current = store.workflows.find((w) => w.id === workflow.id) ?? workflow;

  const hidden = useMemo(() => hiddenIds(nodes), [nodes]);
  const flowNodes = useMemo(
    () =>
      nodes.map((n) => ({
        ...n,
        hidden: hidden.has(n.id),
        data: {
          ...n.data,
          runStatus: runState[n.id],
          childCount:
            n.data.kind === "agent"
              ? nodes.filter((c) => c.data.parentNodeId === n.id && c.data.kind === "agent").length
              : 0,
          parentLabel: n.data.parentNodeId
            ? nodes.find((p) => p.id === n.data.parentNodeId)?.data.label
            : undefined,
        },
      })),
    [nodes, runState, hidden],
  );
  const flowEdges: Edge[] = useMemo(
    () =>
      edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.label,
        type: "smoothstep",
        hidden: hidden.has(e.source) || hidden.has(e.target),
        className: activeEdges.has(e.id) ? "edge-active" : "",
        labelBgPadding: [6, 3] as [number, number],
        labelBgBorderRadius: 6,
        labelStyle: { fontSize: 10, fontWeight: 500, fill: "var(--primary-deep)" },
        labelBgStyle: { fill: "var(--highlight)" },
      })),
    [edges, activeEdges, hidden],
  );

  const selected = nodes.find((n) => n.id === selectedId);
  const selectedAgent = selected?.data.agentId
    ? agents.find((a) => a.id === selected.data.agentId)
    : undefined;
  const updateNodeData = (patch: Partial<WorkflowNode["data"]>) => {
    if (!selected) return;
    commit({
      nodes: nodesRef.current.map((n) =>
        n.id === selected.id ? { ...n, data: { ...n.data, ...patch } } : n,
      ),
      edges: edgesRef.current,
    });
  };

  return (
    <div className="flex h-full flex-col">
      {/* Toolbar */}
      <div className="flex h-12 shrink-0 items-center gap-2 border-b border-border px-3">
        <Link
          to="/app/workflows"
          className="rounded-md p-1.5 text-muted-foreground hover:bg-muted"
          aria-label="Back to workflows"
        >
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <input
          aria-label="Workflow name"
          value={current.name}
          onChange={(e) => store.renameWorkflow(workflow.id, e.target.value)}
          className="w-28 min-w-0 max-w-[280px] flex-1 rounded-md sm:w-auto sm:flex-none bg-transparent px-1.5 py-1 font-medium outline-none hover:bg-muted focus:bg-muted"
        />
        <span className="hidden sm:contents">
          <StatusPill
            status={
              current.status === "published" ? `v${current.serverVersion ?? current.versions.length} published` : current.status
            }
            tone={current.status === "published" ? "success" : "neutral"}
          />
        </span>
        <span className="hidden items-center gap-1 text-xs text-muted-foreground lg:flex">
          <Check className="h-3 w-3" />
          {current.serverVersion ? "Unsaved edits stay in memory" : `Saved in browser ${savedAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`}
        </span>
        <div className="flex-1" />
        <button
          onClick={undo}
          disabled={!past.length}
          className="hidden rounded-md p-1.5 text-muted-foreground hover:bg-muted disabled:opacity-40 sm:block"
          aria-label="Undo"
        >
          <Undo2 className="h-4 w-4" />
        </button>
        <button
          onClick={redo}
          disabled={!future.length}
          className="hidden rounded-md p-1.5 text-muted-foreground hover:bg-muted disabled:opacity-40 sm:block"
          aria-label="Redo"
        >
          <Redo2 className="h-4 w-4" />
        </button>
        <DropdownMenu>
          <DropdownMenuTrigger aria-label="Add step" className="flex h-8 items-center gap-1 rounded-lg border border-border px-2.5 text-sm hover:border-border-accent">
            <Plus className="h-4 w-4" />
            <span className="hidden sm:inline">Add step</span>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            {(Object.keys(NODE_META) as NodeKind[]).map((k) => {
              const M = NODE_META[k];
              return (
                <DropdownMenuItem key={k} onSelect={() => addNode(k)}>
                  <M.icon className="mr-2 h-4 w-4" />
                  {k === "agent" ? "New AI agent" : M.label}
                </DropdownMenuItem>
              );
            })}
            <DropdownMenuSeparator />
            <DropdownMenuLabel className="text-xs text-muted-foreground">
              Patterns
            </DropdownMenuLabel>
            {PATTERNS.map((p) => (
              <DropdownMenuItem key={p.id} onSelect={() => insertPatternAt(p.id)}>
                {p.name}{" "}
                <span className="ml-auto pl-2 text-[10px] text-muted-foreground">
                  {p.description}
                </span>
              </DropdownMenuItem>
            ))}
            {agents.length > 0 && <DropdownMenuSeparator />}
            {agents.length > 0 && (
              <DropdownMenuLabel className="text-xs text-muted-foreground">
                Reuse an agent
              </DropdownMenuLabel>
            )}
            {agents.slice(0, 8).map((a) => (
              <DropdownMenuItem key={a.id} onSelect={() => addNode("agent", a.id)}>
                {a.name}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
        <DropdownMenu>
          <DropdownMenuTrigger
            className="rounded-md p-1.5 text-muted-foreground hover:bg-muted"
            aria-label="More actions"
          >
            <MoreHorizontal className="h-4 w-4" />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onSelect={tidy}>
              <LayoutTemplate className="mr-2 h-4 w-4" />
              Auto-layout
            </DropdownMenuItem>
            <DropdownMenuItem
              onSelect={() => {
                const id = store.duplicateWorkflow(workflow.id);
                if (id) navigate({ to: "/app/workflows/$id", params: { id } });
              }}
            >
              <Copy className="mr-2 h-4 w-4" />
              Duplicate
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuLabel className="text-xs text-muted-foreground">
              Versions
            </DropdownMenuLabel>
            {current.versions.length === 0 && (
              <p className="px-2 py-1.5 text-sm text-muted-foreground">Not published yet</p>
            )}
            {current.versions
              .slice()
              .reverse()
              .slice(0, 5)
              .map((v) => (
                <p key={v.id} className="px-2 py-1.5 text-sm">
                  <span className="font-medium">v{v.version}</span>{" "}
                  <span className="text-muted-foreground">
                    · {new Date(v.publishedAt).toLocaleString()}
                  </span>
                </p>
              ))}
            <DropdownMenuSeparator />
            <DropdownMenuLabel className="text-xs text-muted-foreground">
              Recent runs
            </DropdownMenuLabel>
            <p className="px-2 py-1.5 text-sm text-muted-foreground">Run history awaits backend integration</p>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <WorkflowControls workflow={current} />
      <div className="flex min-h-0 flex-1">
        {/* Canvas */}
        <div className="relative min-w-0 flex-1 bg-canvas">
          {isMobile ? (
            <ol className="h-full space-y-2 overflow-y-auto p-4 pb-48" aria-label="Workflow steps">
              {nodes.map((n, i) => {
                const M = NODE_META[n.data.kind];
                const st = runState[n.id];
                return (
                  <li key={n.id}>
                    <button
                      onClick={() => {
                        setSelectedId(n.id);
                        setPanel("inspector");
                      }}
                      className={`flex w-full items-center gap-3 rounded-xl border bg-background p-3 text-left ${selectedId === n.id ? "border-primary" : "border-border"}`}
                    >
                      <span className="w-5 text-xs text-muted-foreground">{i + 1}</span>
                      <span
                        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${M.tone}`}
                      >
                        <M.icon className="h-4 w-4" />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium">{n.data.label}</span>
                        <span className="block truncate text-xs text-muted-foreground">
                          {M.label}
                        </span>
                      </span>
                      {st && <StatusPill status={st} />}
                    </button>
                  </li>
                );
              })}
            </ol>
          ) : (
            <NodeActions.Provider value={nodeActions}>
              <PatternsPanel onInsert={(k) => insertPatternAt(k)} />
              <ReactFlow
                onDragOver={(e) => {
                  if (e.dataTransfer.types.includes(PATTERN_MIME)) {
                    e.preventDefault();
                    e.dataTransfer.dropEffect = "copy";
                  }
                }}
                onDrop={onDrop}
                nodes={flowNodes}
                edges={flowEdges}
                nodeTypes={nodeTypes}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onConnect={onConnect}
                onNodeDragStop={() => commit({ nodes: nodesRef.current, edges: edgesRef.current })}
                onNodeClick={(_, n) => {
                  setSelectedId(n.id);
                  setPanel("inspector");
                }}
                onPaneClick={() => {
                  setSelectedId(null);
                  setPanel((p) => (p === "inspector" ? null : p));
                }}
                fitView
                fitViewOptions={{ padding: 0.15, maxZoom: 1 }}
                minZoom={0.2}
                deleteKeyCode={["Backspace", "Delete"]}
                proOptions={{ hideAttribution: true }}
              >
                <Background
                  variant={BackgroundVariant.Dots}
                  gap={20}
                  size={1.2}
                  color="var(--border)"
                />
                <Controls
                  showInteractive={false}
                  className="!rounded-lg !border !border-border !shadow-soft"
                />
                <MiniMap
                  pannable
                  zoomable
                  className="!hidden !rounded-lg !border !border-border lg:!block"
                  maskColor="color-mix(in oklab, var(--canvas) 70%, transparent)"
                  nodeColor="var(--border-accent)"
                />
              </ReactFlow>
            </NodeActions.Provider>
          )}

          {/* Local command editor */}
          <div className="pointer-events-none absolute inset-x-0 bottom-4 flex justify-center px-4">
            <div className="pointer-events-auto w-full max-w-2xl rounded-2xl border border-border-accent bg-background/95 shadow-lift backdrop-blur">
              <button
                onClick={() => setComposerOpen((o) => !o)}
                className="flex w-full items-center gap-2 px-4 py-2 text-xs text-muted-foreground"
              >
                <Sparkles className="h-3.5 w-3.5 text-primary" /> Local editing commands{" "}
                <span className="text-muted-foreground/70">· draft edits</span>
                <span className="flex-1" />
                {composerOpen ? (
                  <ChevronDown className="h-3.5 w-3.5" />
                ) : (
                  <ChevronUp className="h-3.5 w-3.5" />
                )}
              </button>
              {composerOpen && (
                <div className="px-3 pb-3">
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      runCommand();
                    }}
                    className="flex gap-2"
                  >
                    <input
                      value={cmd}
                      onChange={(e) => setCmd(e.target.value)}
                      placeholder="e.g. Add human approval before sending emails"
                      aria-label="Instruction"
                      className="min-w-0 flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
                    />
                    <button
                      type="submit"
                      className="rounded-lg bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary-deep"
                    >
                      Apply
                    </button>
                  </form>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {SUPPORTED_COMMANDS.map((c) => (
                      <button
                        key={c}
                        onClick={() => runCommand(c)}
                        className="rounded-full border border-border px-2.5 py-0.5 text-[11px] text-muted-foreground transition-colors hover:border-primary hover:text-primary"
                      >
                        {c}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right panel */}
        {panel && (
          <aside className="fixed inset-0 z-40 w-full shrink-0 border-l border-border bg-background md:relative md:inset-auto md:z-20 md:max-w-[380px]">
            {selected ? (
              <div className="flex h-full flex-col">
                <div className="flex items-center gap-2 border-b border-border px-4 py-3">
                  {(() => {
                    const M = NODE_META[selected.data.kind];
                    return (
                      <span
                        className={`flex h-7 w-7 items-center justify-center rounded-md ${M.tone}`}
                      >
                        <M.icon className="h-3.5 w-3.5" />
                      </span>
                    );
                  })()}
                  <input
                    aria-label="Step name"
                    value={selected.data.label}
                    onChange={(e) => updateNodeData({ label: e.target.value })}
                    className="min-w-0 flex-1 rounded-md bg-transparent px-1 py-0.5 text-sm font-medium outline-none hover:bg-muted focus:bg-muted"
                  />
                  <button
                    onClick={() => onNodesChange([{ type: "remove", id: selected.id }])}
                    className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-destructive"
                    aria-label="Delete step"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => setPanel(null)}
                    className="rounded-md p-1.5 text-muted-foreground hover:bg-muted"
                    aria-label="Close inspector"
                  >
                    ×
                  </button>
                </div>
                <div className="flex-1 overflow-y-auto p-4">
                  {selectedAgent ? (
                    <>
                      <HierarchyBox
                        node={selected}
                        nodes={nodes}
                        depth={depthOf(nodes, selected.id)}
                        onSelect={(id) => setSelectedId(id)}
                        onAdd={() => addChild(selected.id)}
                        onRemove={() => removeChild(selected.id)}
                      />
                      <p className="mb-3 text-xs text-muted-foreground">
                        Reusable agent · edits apply wherever{" "}
                        <Link
                          to="/app/agents"
                          search={{ agent: selectedAgent.id }}
                          className="text-primary"
                        >
                          {selectedAgent.name}
                        </Link>{" "}
                        is used.
                      </p>
                      <AgentInspector agent={selectedAgent} />
                    </>
                  ) : (
                    <div className="space-y-4">
                      <div>
                        <label
                          htmlFor="node-desc"
                          className="mb-1.5 block text-xs font-medium text-muted-foreground"
                        >
                          Description
                        </label>
                        <textarea
                          id="node-desc"
                          rows={3}
                          value={selected.data.description ?? ""}
                          onChange={(e) => updateNodeData({ description: e.target.value })}
                          className="w-full rounded-lg border border-border px-3 py-2 text-sm outline-none focus:border-primary"
                        />
                      </div>
                      {selected.data.kind === "condition" && (
                        <div className="space-y-2 text-xs">
                          <label className="block">Condition expression<input aria-label="Condition expression" className="mt-1 w-full rounded-lg border border-border p-2" value={String((selected.data["condition"] as { expression?: string } | undefined)?.expression ?? "")} onChange={(e) => updateNodeData({ condition: { condition_id: String(selected.data["conditionId"] ?? `condition_${selected.id}`), outcomes: (selected.data["condition"] as { outcomes?: string[] } | undefined)?.outcomes ?? ["critical", "standard"], expression: e.target.value } })} /></label>
                          <label className="block">Outcomes (comma separated)<input aria-label="Condition outcomes" className="mt-1 w-full rounded-lg border border-border p-2" value={((selected.data["condition"] as { outcomes?: string[] } | undefined)?.outcomes ?? ["critical", "standard"]).join(", ")} onChange={(e) => updateNodeData({ condition: { condition_id: String(selected.data["conditionId"] ?? `condition_${selected.id}`), expression: String((selected.data["condition"] as { expression?: string } | undefined)?.expression ?? ""), outcomes: e.target.value.split(",").map((value) => value.trim()).filter(Boolean) } })} /></label>
                          <p>Declared outcomes: {((selected.data["condition"] as { outcomes?: string[] } | undefined)?.outcomes ?? []).join(", ") || "Configure outgoing branch labels"}</p>
                          <p>Outgoing branches: {edges.filter((e) => e.source === selected.id).map((e) => e.label || "unmatched").join(", ") || "None"}</p>
                        </div>
                      )}
                      {selected.data.kind === "approval" && (
                        <p className="text-xs text-muted-foreground">
                          Approval gate · roles: {((selected.data["approval"] as { approver_roles?: string[] } | undefined)?.approver_roles ?? ["approver"]).join(", ")} · rejection: {String((selected.data["approval"] as { on_reject?: string } | undefined)?.on_reject ?? "stop")} · timeout: {String((selected.data["approval"] as { timeout_seconds?: number } | undefined)?.timeout_seconds ?? "not configured")}. Runtime decisions resume the approved path.
                        </p>
                      )}
                      <p className="text-xs text-muted-foreground">
                        {NODE_META[selected.data.kind].label}
                        {selected.data.tool ? ` · ${selected.data.tool} (not configured)` : ""}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            ) : null}
          </aside>
        )}
      </div>
    </div>
  );
}

function HierarchyBox({
  node,
  nodes,
  depth,
  onSelect,
  onAdd,
  onRemove,
}: {
  node: WorkflowNode;
  nodes: WorkflowNode[];
  depth: number;
  onSelect: (id: string) => void;
  onAdd: () => void;
  onRemove: () => void;
}) {
  const parent = node.data.parentNodeId
    ? nodes.find((n) => n.id === node.data.parentNodeId)
    : undefined;
  const kids = nodes.filter((n) => n.data.parentNodeId === node.id && n.data.kind === "agent");
  return (
    <div className="mb-4 rounded-xl border border-border-accent bg-highlight/40 p-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-primary-deep">
          {node.data.role === "master"
            ? "Master agent"
            : node.data.role === "sub"
              ? "Sub-agent"
              : "Agent"}{" "}
          · level {depth}
        </p>
        {node.data.role === "sub" && (
          <button
            onClick={onRemove}
            className="text-[11px] text-muted-foreground hover:text-destructive"
          >
            Remove sub-agent
          </button>
        )}
      </div>
      {parent && (
        <p className="mt-1 text-xs text-muted-foreground">
          Reports to{" "}
          <button onClick={() => onSelect(parent.id)} className="text-primary hover:underline">
            {parent.data.label}
          </button>
        </p>
      )}
      {kids.length > 0 && (
        <ul className="mt-2 space-y-1">
          {kids.map((k) => (
            <li key={k.id}>
              <button
                onClick={() => onSelect(k.id)}
                className="w-full truncate rounded-md bg-background px-2 py-1 text-left text-xs hover:text-primary"
              >
                ↳ {k.data.label}
              </button>
            </li>
          ))}
        </ul>
      )}
      <button
        onClick={onAdd}
        className="mt-2 flex h-8 w-full items-center justify-center gap-1.5 rounded-lg border border-dashed border-primary/40 text-xs font-medium text-primary hover:bg-background"
      >
        <Plus className="h-3.5 w-3.5" />
        Add sub-agent
      </button>
    </div>
  );
}
