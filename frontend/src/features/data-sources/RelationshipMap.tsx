"use client";

import { useId, useMemo, useRef, useState } from "react";
import dagre from "@dagrejs/dagre";
import type { RelationshipView } from "@/api/data-relationships";

type Graph = NonNullable<RelationshipView["graph"]>;
const WIDTH = 340;
const HEADER = 68;
const ROW = 26;
const clip = (text: string, length: number) => text.length > length ? `${text.slice(0, length - 1)}…` : text;

export default function RelationshipMap({graph, selected, onSelect}: {graph: Graph; selected: string; onSelect: (id: string) => void}) {
  const marker = useId().replace(/:/g, "");
  const svg = useRef<SVGSVGElement>(null);
  const drag = useRef<{x: number; y: number; left: number; top: number} | null>(null);
  const [camera, setCamera] = useState({zoom: 1, x: 0, y: 0});
  const layout = useMemo(() => {
    const nodes = new Map(graph.nodes.map(node => [node.node_id, node]));
    const datasets = graph.nodes.filter(node => node.kind === "dataset").slice(0, 24);
    const fields = new Map(datasets.map(node => [node.node_id, graph.nodes.filter(field => field.kind === "field" && field.parent_id === node.node_id)]));
    const visible = new Set(datasets.map(node => node.node_id));
    const relationships = graph.relationships.filter(edge => edge.status !== "rejected" && visible.has(edge.source_dataset_id) && visible.has(edge.target_dataset_id));
    const diagram = new dagre.graphlib.Graph({multigraph: true});
    diagram.setGraph({rankdir: "LR", nodesep: 90, ranksep: 310, edgesep: 45, marginx: 60, marginy: 60});
    diagram.setDefaultEdgeLabel(() => ({}));
    datasets.forEach(node => diagram.setNode(node.node_id, {width: WIDTH, height: HEADER + Math.max(1, fields.get(node.node_id)!.length) * ROW + 12}));
    relationships.forEach(edge => diagram.setEdge(edge.source_dataset_id, edge.target_dataset_id, {width: 280, height: 28 + edge.field_pairs.length * 19, labelpos: "c"}, edge.relationship_id));
    dagre.layout(diagram);
    return {nodes, datasets, fields, relationships, diagram, width: Math.max(500, diagram.graph().width ?? 0), height: Math.max(260, diagram.graph().height ?? 0)};
  }, [graph.nodes, graph.relationships]);
  const width = layout.width / camera.zoom;
  const height = layout.height / camera.zoom;
  const left = (layout.width - width) / 2 + camera.x;
  const top = (layout.height - height) / 2 + camera.y;
  const zoom = (factor: number) => setCamera(value => ({...value, zoom: Math.min(8, Math.max(0.25, value.zoom * factor))}));
  const control = "rounded-lg border bg-background px-3 py-2 text-xs font-medium disabled:opacity-40";
  return <details className="rounded-xl border p-4" open>
    <summary className="cursor-pointer text-sm font-medium">Dataset relationship map</summary>
    <p className="mt-2 text-xs text-muted-foreground">Columns connect to their related columns. Solid lines: declared or accepted. Dashed lines: proposals. Rejected suggestions are hidden.</p>
    <div className="my-3 flex flex-wrap items-center gap-2" role="group" aria-label="Map controls">
      <button className={control} aria-label="Zoom out" disabled={camera.zoom <= 0.25} onClick={() => zoom(1 / 1.3)}>−</button>
      <output className="min-w-12 text-center text-xs" aria-label="Map zoom">{Math.round(camera.zoom * 100)}%</output>
      <button className={control} aria-label="Zoom in" disabled={camera.zoom >= 8} onClick={() => zoom(1.3)}>+</button>
      <button className={control} onClick={() => setCamera({zoom: 1, x: 0, y: 0})}>Fit all</button>
      <span className="text-xs text-muted-foreground">Drag to pan · 100% fits the map · select a table or column to inspect</span>
    </div>
    <div className="h-[min(60vh,600px)] min-h-[320px] overflow-hidden rounded-lg border bg-muted/20" data-testid="relationship-map-viewport">
      <svg ref={svg} role="img" aria-label="Dataset relationship map" viewBox={`${left} ${top} ${width} ${height}`} className="h-full w-full touch-none select-none cursor-grab active:cursor-grabbing"
        onPointerDown={event => {
          if(event.button !== 0) return;
          drag.current = {x: event.clientX, y: event.clientY, left: camera.x, top: camera.y};
          event.currentTarget.setPointerCapture(event.pointerId);
        }}
        onPointerMove={event => {
          const start = drag.current;
          const matrix = svg.current?.getScreenCTM();
          if(!start || !matrix) return;
          setCamera(value => ({...value, x: start.left - (event.clientX - start.x) / matrix.a, y: start.top - (event.clientY - start.y) / matrix.d}));
        }}
        onPointerUp={event => {drag.current = null; if(event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);}}
        onPointerCancel={() => {drag.current = null;}}>
        <defs><marker id={marker} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" className="fill-primary"/></marker></defs>
        {layout.relationships.flatMap(edge => {
          const route = layout.diagram.edge({v: edge.source_dataset_id, w: edge.target_dataset_id, name: edge.relationship_id});
          return edge.field_pairs.map((pair, index) => {
            const source = layout.diagram.node(edge.source_dataset_id);
            const target = layout.diagram.node(edge.target_dataset_id);
            const forward = target.x >= source.x;
            const fieldY = (dataset: string, field: string, y: number, h: number) => y - h / 2 + HEADER + Math.max(0, layout.fields.get(dataset)!.findIndex(node => node.node_id === field)) * ROW + ROW / 2;
            const a = {x: source.x + (forward ? WIDTH / 2 : -WIDTH / 2), y: fieldY(edge.source_dataset_id, pair.source_field_id, source.y, source.height)};
            const b = {x: target.x + (forward ? -WIDTH / 2 : WIDTH / 2), y: fieldY(edge.target_dataset_id, pair.target_field_id, target.y, target.height)};
            const points = [a, ...route.points.slice(1, -1), b];
            return <path key={`${edge.relationship_id}-${index}`} d={points.map((point, i) => `${i ? "L" : "M"} ${point.x} ${point.y}`).join(" ")} fill="none" className="stroke-primary" strokeWidth="1.5" strokeDasharray={edge.status === "proposed" ? "7 5" : undefined} markerEnd={`url(#${marker})`} markerStart={edge.kind === "suggested" ? `url(#${marker})` : undefined}><title>{layout.nodes.get(pair.source_field_id)?.label} {edge.kind === "declared" ? "references" : "matches name/type of"} {layout.nodes.get(pair.target_field_id)?.label} · {edge.status}</title></path>;
          });
        })}
        {layout.datasets.map(node => {
          const position = layout.diagram.node(node.node_id);
          const fields = layout.fields.get(node.node_id)!;
          const activate = (id: string) => ({role: "button", tabIndex: 0, onPointerDown: (event: React.PointerEvent) => event.stopPropagation(), onClick: () => onSelect(id), onKeyDown: (event: React.KeyboardEvent) => {if(event.key === "Enter" || event.key === " ") {event.preventDefault(); onSelect(id);}}});
          return <g key={node.node_id} transform={`translate(${position.x - WIDTH / 2},${position.y - position.height / 2})`}>
            <rect width={WIDTH} height={position.height} rx="10" className="fill-background stroke-primary" strokeWidth={selected === node.node_id || fields.some(field => field.node_id === selected) ? 2.5 : 1}/>
            <g {...activate(node.node_id)} aria-label={`Explore ${layout.nodes.get(node.connection_id)?.label} / ${node.label}`} className="cursor-pointer">
              <title>{node.label}</title><rect width={WIDTH} height={HEADER} rx="10" className="fill-primary/5"/>
              <text x="14" y="25" fontSize="15" fontWeight="600" className="fill-foreground">{clip(node.label, 37)}</text>
              <text x="14" y="46" fontSize="12" className="fill-muted-foreground">{clip(layout.nodes.get(node.connection_id)?.label ?? "", 43)}</text>
            </g>
            <line x1="0" x2={WIDTH} y1={HEADER - 4} y2={HEADER - 4} className="stroke-primary/30"/>
            {fields.map((field, index) => <g key={field.node_id} {...activate(field.node_id)} aria-label={`Inspect ${node.label}.${field.label}`} className="cursor-pointer">
              <title>{field.label} · {field.types.join(", ")}</title>
              <rect x="1" y={HEADER + index * ROW} width={WIDTH - 2} height={ROW} className={selected === field.node_id ? "fill-primary/15" : "fill-transparent hover:fill-primary/5"}/>
              <text x="14" y={HEADER + index * ROW + 18} fontSize="12" className="fill-foreground">{clip(field.label, 29)}</text>
              <text x={WIDTH - 14} y={HEADER + index * ROW + 18} textAnchor="end" fontSize="10" className="fill-muted-foreground">{clip(field.types.join(", "), 17)}</text>
              <circle cx="0" cy={HEADER + index * ROW + ROW / 2} r="2.5" className="fill-primary"/><circle cx={WIDTH} cy={HEADER + index * ROW + ROW / 2} r="2.5" className="fill-primary"/>
            </g>)}
            {!fields.length && <text x="14" y={HEADER + 18} fontSize="12" className="fill-muted-foreground">No columns discovered</text>}
          </g>;
        })}
        {layout.relationships.map(edge => {
          const route = layout.diagram.edge({v: edge.source_dataset_id, w: edge.target_dataset_id, name: edge.relationship_id});
          return <g key={edge.relationship_id} transform={`translate(${route.x},${route.y})`} className="pointer-events-none">
            <rect x="-140" y={-route.height / 2} width="280" height={route.height} rx="6" className="fill-background stroke-primary/30"/>
            <text textAnchor="middle" fontSize="11" className="fill-foreground">
              <tspan x="0" y={-route.height / 2 + 16}>{edge.kind === "declared" ? "references" : "matches name/type (unverified)"} · {edge.status}</tspan>
              {edge.field_pairs.map((pair, index) => <tspan key={index} x="0" dy="19">{clip(layout.nodes.get(pair.source_field_id)?.label ?? "", 19)} {edge.kind === "declared" ? "→" : "↔"} {clip(layout.nodes.get(pair.target_field_id)?.label ?? "", 19)}</tspan>)}
            </text>
          </g>;
        })}
      </svg>
    </div>
    {graph.nodes.filter(node => node.kind === "dataset").length > 24 && <p className="mt-2 text-xs text-muted-foreground">Map shows the first 24 datasets; use the explorer below for all datasets.</p>}
  </details>;
}
