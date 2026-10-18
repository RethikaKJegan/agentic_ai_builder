"use client";
import { displayText } from "@/lib/display-text";
import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import dagre from "@dagrejs/dagre";
import { api } from "@/api/client";
import type { SemanticView as OntologyView } from "@/api/semantic-kg";
import type { RelationshipView } from "@/api/data-relationships";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";
import AutomaticRefresh from "./AutomaticRefresh";
import KGRelationshipReview from "./KGRelationshipReview";

const control = "rounded-lg border bg-background px-3 py-2 text-sm disabled:opacity-40";
export default function BusinessOntology({
  canManage,
  refreshToken = 0,
  onStatus,
}: {
  canManage: boolean;
  refreshToken?: number;
  onStatus?: (status: Pick<RelationshipView, "stale" | "build_status" | "last_error">) => void;
}) {
  const [view, setView] = useState<OntologyView>();
  const [error, setError] = useState<Error>();
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const lock = useRef(false);
  const [selected, setSelected] = useState("");
  const [search, setSearch] = useState("");
  const [connection, setConnection] = useState("");
  const [semanticFilter,setSemanticFilter]=useState("all");
  const [camera, setCamera] = useState({ zoom: 1, x: 0, y: 0 });
  const sequence = useRef(0);
  const svg = useRef<SVGSVGElement>(null);
  const drag = useRef<{ x: number; y: number; left: number; top: number } | null>(null);
  const marker = useId().replaceAll(":", "");
  const load = useCallback(async () => {
    const id = ++sequence.current;
    try {
      const result = await api.knowledgeGraph();
      if (id === sequence.current) {
        setView(result);
        setError(undefined);
        onStatus?.(result);
      }
    } catch (e) {
      if (id === sequence.current)
        setError(e instanceof Error ? e : new Error("Semantic Intelligence unavailable."));
    }
  }, [onStatus]);
  const invalidate = useCallback(() => {
    sequence.current++;
  }, []);
  useEffect(() => {
    void load();
    const timer = setInterval(() => {
      if (!lock.current) void load();
    }, 2000);
    return () => {
      clearInterval(timer);
      invalidate();
    };
  }, [load, invalidate, refreshToken]);
  const connections = useMemo(
    () => [...new Map((view?.entities ?? []).flatMap(e => e.sources.map(source =>
      [source.connection_id, displayText(source.label).split(" / ")[0]] as const))).entries()], [view]);
  const connectionDatasets = new Set((view?.datasets ?? []).filter(d => !connection || d.connection_id === connection).map(d => d.dataset_id));
  const scopedEdges = (view?.relationships ?? []).filter(e => !connection ||
    (connectionDatasets.has(e.source_dataset_id) && connectionDatasets.has(e.target_dataset_id)));
  const scopedEntities = (view?.entities ?? []).map(e => ({...e, sources: e.sources.filter(s => !connection || s.connection_id === connection)})).filter(e => e.sources.length > 0);
  const semanticMatches=new Set(scopedEdges.filter(e=>e.predicate?.toLowerCase().includes(search.toLowerCase())).flatMap(e=>[e.source_entity_id,e.target_entity_id]));
  const filtered = scopedEntities.filter(
    (e) =>
      (!connection || e.sources.some((s) => s.connection_id === connection)) &&
      (`${e.label} ${e.sources.map((s) => s.label).join(" ")}`
        .toLowerCase()
        .includes(search.toLowerCase()) || (!!search&&semanticMatches.has(e.entity_id))),
  );
  const visible = filtered.slice(0, 80);
  const ids = new Set(visible.map((e) => e.entity_id));
  const edges = scopedEdges.filter(
    (e) => ids.has(e.source_entity_id) && ids.has(e.target_entity_id) && (semanticFilter==="all"||e.status===semanticFilter),
  );
  const layout = useMemo(() => {
    const graph = new dagre.graphlib.Graph({ multigraph: true });
    graph.setGraph({ rankdir: "LR", nodesep: 65, ranksep: 170, marginx: 70, marginy: 70 });
    graph.setDefaultEdgeLabel(() => ({}));
    for (const entity of visible) graph.setNode(entity.entity_id, { width: 210, height: 95 });
    for (const edge of edges)
      graph.setEdge(
        edge.source_entity_id,
        edge.target_entity_id,
        { width: 155, height: 40 },
        edge.relationship_id,
      );
    dagre.layout(graph);
    return graph;
    // The Semantic Intelligence revision versions entities, relationships and reviews together.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view?.revision, search, connection,semanticFilter]);
  const width = Math.max(500, layout.graph().width ?? 500),
    height = Math.max(320, layout.graph().height ?? 320);
  const label = (id: string) => view?.entities.find((e) => e.entity_id === id)?.label ?? id;
  const entity = visible.find(e => e.entity_id === selected);
  const edge = edges.find(e => e.relationship_id === selected);
  async function saveReview(body: object) {
    if (!view || !edge || !canManage || view.stale || lock.current) return;
    lock.current = true;
    sequence.current++;
    setBusy(true); setNotice(""); setError(undefined);
    try {
      const result = await api.knowledgeGraph(edge.relationship_id, {revision: view.revision, ...body});
      setView(result); onStatus?.(result);
      setNotice("Business relationship review saved. Technical join permissions are unchanged.");
    } catch (failure) {
      setError(failure instanceof Error ? failure : new Error("Relationship review could not be saved."));
    } finally { lock.current = false; setBusy(false); }
  }
  const activate = (id: string) => ({
    role: "button", tabIndex: 0,
    onPointerDown: (event: React.PointerEvent) => event.stopPropagation(),
    onClick: () => setSelected(id),
    onKeyDown: (event: React.KeyboardEvent) => {
      if (event.key === "Enter" || event.key === " ") { event.preventDefault(); setSelected(id); }
    },
  });
  return (
    <section aria-label="Semantic Intelligence" className="space-y-4">
      <ApiFeedback error={error} onRetry={load} />
      {notice && <p role="status" className="text-sm">{notice}</p>}
      {view?.last_error && (
        <p role="alert" className="text-sm text-destructive">
          {view.last_error}
        </p>
      )}
      {view?.stale && (
        <p role="status" className="rounded-lg border border-amber-300 p-3 text-sm">
          This Semantic Intelligence is updating. The latest metadata will appear when rebuilding finishes.
        </p>
      )}
      {!view && !error && <p role="status">Loading Semantic Intelligence…</p>}
      {view && (
        <>
          <p role="status" className="text-xs text-muted-foreground">
            {visible.length} entities · {edges.length} relationships · {view.build_status === "ready" ? "Current" : view.build_status}
            {view.semantic_status.state === "running" || view.semantic_status.state === "queued" ? " · Updating relationship meanings…" : ""}
          </p>
          {view.semantic_status.last_error && <p role="alert" className="text-sm text-destructive">{view.semantic_status.last_error}</p>}
          <div className="flex flex-wrap gap-2">
            <select aria-label="Semantic relationship status" className={control} value={semanticFilter} onChange={e=>setSemanticFilter(e.target.value)}>{["all","inferred","confirmed","ambiguous","needs_review","rejected"].map(status=><option key={status} value={status}>{status==="all"?"All semantic statuses":status.replaceAll("_"," ")}</option>)}</select>
            <input
              className={control}
              aria-label="Search Semantic Intelligence"
              placeholder="Search entities, relationships or sources"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <select
              className={`${control} max-w-full`}
              aria-label="Semantic Intelligence connection"
              value={connection}
              onChange={(e) => setConnection(e.target.value)}
            >
              <option value="">All connections</option>
              {connections.map(([id, name]) => (
                <option key={id} value={id}>
                  {displayText(name)}
                </option>
              ))}
            </select>
            <button
              className={control}
              onClick={() => setCamera((c) => ({ ...c, zoom: Math.max(0.25, c.zoom / 1.3) }))}
              aria-label="Zoom Semantic Intelligence out"
            >
              −
            </button>
            <output className="self-center text-sm" aria-label="Semantic Intelligence zoom">
              {Math.round(camera.zoom * 100)}%
            </output>
            <button
              className={control}
              onClick={() => setCamera((c) => ({ ...c, zoom: Math.min(8, c.zoom * 1.3) }))}
              aria-label="Zoom Semantic Intelligence in"
            >
              +
            </button>
            <button className={control} onClick={() => setCamera({ zoom: 1, x: 0, y: 0 })}>
              Fit Semantic Intelligence
            </button>
          </div>
          <p className="text-xs text-muted-foreground">
            Drag to pan. Solid edges are confirmed business meanings; dashed edges need review.
            Faded edges are rejected. Arrows show business direction.
          </p>
          {filtered.length > 80 && (
            <p className="text-sm">
              Showing 80 of {filtered.length} entities. Search or filter to inspect the rest.
            </p>
          )}
          <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
            <div className="h-[min(65vh,650px)] min-h-[360px] min-w-0 overflow-hidden rounded-xl border bg-muted/10">
              <svg
                ref={svg}
                role="img"
                aria-label="Semantic Intelligence"
                className="h-full w-full touch-none select-none cursor-grab"
                viewBox={`${(width - width / camera.zoom) / 2 + camera.x} ${(height - height / camera.zoom) / 2 + camera.y} ${width / camera.zoom} ${height / camera.zoom}`}
                onPointerDown={(e) => {
                  if (e.button === 0) {
                    drag.current = { x: e.clientX, y: e.clientY, left: camera.x, top: camera.y };
                    e.currentTarget.setPointerCapture(e.pointerId);
                  }
                }}
                onPointerMove={(e) => {
                  const d = drag.current,
                    m = svg.current?.getScreenCTM();
                  if (d && m)
                    setCamera((c) => ({
                      ...c,
                      x: d.left - (e.clientX - d.x) / m.a,
                      y: d.top - (e.clientY - d.y) / m.d,
                    }));
                }}
                onPointerUp={(e) => {
                  drag.current = null;
                  if (e.currentTarget.hasPointerCapture(e.pointerId))
                    e.currentTarget.releasePointerCapture(e.pointerId);
                }}
                onPointerCancel={() => {
                  drag.current = null;
                }}
              >
                <defs>
                  <marker
                    id={marker}
                    viewBox="0 0 10 10"
                    refX="9"
                    refY="5"
                    markerWidth="7"
                    markerHeight="7"
                    orient="auto"
                  >
                    <path d="M 0 0 L 10 5 L 0 10 z" className="fill-primary" />
                  </marker>
                </defs>
                {edges.map((e) => {
                  const route = layout.edge({
                    v: e.source_entity_id,
                    w: e.target_entity_id,
                    name: e.relationship_id,
                  });
                  return (
                    <g
                      key={e.relationship_id}
                      {...activate(e.relationship_id)}
                      aria-label={displayText(`Relationship ${label(e.source_entity_id)} ${e.predicate??"meaning needs review"} ${label(e.target_entity_id)}`)}
                      className={`cursor-pointer ${e.status === "rejected" ? "opacity-30" : ""}`}
                    >
                      <path
                        d={route.points
                          .map(
                            (p: { x: number; y: number }, i: number) =>
                              `${i ? "L" : "M"} ${p.x} ${p.y}`,
                          )
                          .join(" ")}
                        className="stroke-primary"
                        strokeWidth={selected === e.relationship_id ? 3 : 1.7}
                        strokeDasharray={e.status === "confirmed" ? undefined : "7 5"}
                        fill="none"
                        markerEnd={e.predicate?`url(#${marker})`:undefined}
                      />
                      <rect
                        x={route.x - 80}
                        y={route.y - 20}
                        width="160"
                        height="40"
                        rx="6"
                        className="fill-background stroke-primary/20"
                      />
                      <text
                        x={route.x}
                        y={route.y - 2}
                        textAnchor="middle"
                        fontSize="12"
                        className="fill-foreground"
                      >
                        {(e.predicate??"Meaning needs review").length > 24 ? (e.predicate??"").slice(0,23)+"…" : e.predicate??"Meaning needs review"}
                      </text>
                      <text
                        x={route.x}
                        y={route.y + 14}
                        textAnchor="middle"
                        fontSize="10"
                        className="fill-muted-foreground"
                      >
                        {e.status.replaceAll("_", " ")}
                      </text>
                      <title>
                        {e.predicate} · {e.status} · Technical link {e.technical_status}
                      </title>
                    </g>
                  );
                })}
                {visible.map((e) => {
                  const p = layout.node(e.entity_id);
                  return (
                    <g
                      key={e.entity_id}
                      {...activate(e.entity_id)}
                      className="cursor-pointer"
                      aria-label={displayText(`Entity ${e.label}`)}
                    >
                      <ellipse
                        cx={p.x}
                        cy={p.y}
                        rx="105"
                        ry="47"
                        className="fill-background stroke-primary"
                        strokeWidth={selected === e.entity_id ? 3 : 1.5}
                      />
                      <text
                        x={p.x}
                        y={p.y - 5}
                        textAnchor="middle"
                        fontSize="15"
                        fontWeight="600"
                        className="fill-foreground"
                      >
                        {displayText(e.label.length > 23 ? e.label.slice(0, 22) + "…" : e.label)}
                      </text>
                      <text
                        x={p.x}
                        y={p.y + 17}
                        textAnchor="middle"
                        fontSize="11"
                        className="fill-muted-foreground"
                      >
                        {e.sources.length} source mappings
                      </text>
                      <title>{displayText(e.label)}</title>
                    </g>
                  );
                })}
              </svg>
            </div>
            <aside aria-label="Semantic Intelligence details" className="max-h-[650px] min-w-0 space-y-3 overflow-auto rounded-xl border p-4">
              <h3 className="font-semibold">Inspect</h3>
              {entity ? <>
                <h4 className="font-medium">{displayText(entity.label)}</h4>
                <p className="break-all text-xs text-muted-foreground">Entity ID: {entity.entity_id}</p>
                {entity.sources.map(source => <details key={source.node_id} className="rounded-lg border p-3">
                  <summary className="cursor-pointer break-words text-sm">{displayText(source.label)}</summary>
                  <p className="mt-2 text-xs">{source.role} · {source.status} · {source.types.join(", ")}</p>
                  {source.description && <p className="mt-2 text-sm">{displayText(source.description)}</p>}
                  <pre className="mt-2 max-h-72 overflow-auto whitespace-pre-wrap break-all text-xs">{displayText(JSON.stringify({connection_id: source.connection_id, node_id: source.node_id, metadata: source.metadata}, null, 2))}</pre>
                </details>)}
              </> : edge ? <>
                <h4 className="font-medium">{displayText(label(edge.source_entity_id))} → {edge.predicate ?? "Meaning needs review"} → {displayText(label(edge.target_entity_id))}</h4>
                <p className="text-sm">Business: {edge.status} · Technical: {edge.technical_status}</p>
                <KGRelationshipReview
                  key={`${edge.relationship_id}:${edge.semantic_evidence_hash}:${edge.inferred_at}:${edge.reviewed_at}`}
                  edge={edge} disabled={!canManage || busy || view.stale} save={body => void saveReview(body)}
                />
                <p className="text-sm">{displayText(edge.rationale)}</p>
                <p className="text-xs text-muted-foreground">Method: {edge.inference_method} · numerical confidence: not measured</p>
                {edge.alternatives.length > 0 && <p className="text-xs">Alternatives: {edge.alternatives.join("; ")}</p>}
                <h5 className="text-sm font-medium">Technical linking fields</h5>
                {edge.field_pairs.map(pair => <p key={pair.source_field_id + pair.target_field_id} className="break-all text-xs">{displayText(pair.source_label)} → {displayText(pair.target_label)}</p>)}
                <details open className="rounded-lg border p-3"><summary className="cursor-pointer text-sm">Evidence trace</summary>
                  <pre className="mt-2 max-h-80 overflow-auto whitespace-pre-wrap break-all text-xs">{displayText(JSON.stringify({relationship_id: edge.relationship_id, graph_revision: view.graph_revision, inferred_at: edge.inferred_at, reviewed_at: edge.reviewed_at, evidence_refs: edge.evidence_refs, provenance: edge.provenance, evidence: edge.evidence, qualification: edge.qualification}, null, 2))}</pre>
                </details>
              </> : <p className="text-sm text-muted-foreground">Select a node or relationship to inspect its source metadata and evidence trace.</p>}
            </aside>
          </div>
          {!visible.length && (
            <p className="text-sm">
              {view.graph_revision
                ? "No entities match. Clear the search or change the connection filter."
                : "Build relationships from successfully profiled sources first."}
            </p>
          )}
        </>
      )}
      <AutomaticRefresh canManage={canManage} />
    </section>
  );
}
