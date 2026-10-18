"use client";
import {useId,useMemo,useState} from "react";
import dagre from "@dagrejs/dagre";
import type {KnowledgePreview} from "@/api/knowledge-graph";

export function KnowledgeSelectionMap({view}:{view:KnowledgePreview}) {
 const marker=useId().replaceAll(":","");
 const [active,setActive]=useState("");
 const layout=useMemo(()=>{
  const graph=new dagre.graphlib.Graph({multigraph:true}).setGraph({rankdir:"LR",ranksep:110,nodesep:35,marginx:24,marginy:24}).setDefaultEdgeLabel(()=>({}));
  const nodes=view.candidates.filter(s=>view.source_ids.includes(s.dataset_id));
  nodes.forEach(s=>graph.setNode(s.dataset_id,{width:180,height:80}));
  view.relationships.forEach(e=>{const semantic=view.semantic_relationships?.find(s=>s.technical_relationship_id===e.relationship_id);const reverse=semantic?.reversed;graph.setEdge(reverse?e.target_dataset_id:e.source_dataset_id,reverse?e.source_dataset_id:e.target_dataset_id,{width:140,height:24},e.relationship_id);});
  dagre.layout(graph);
  return {graph,nodes,width:Math.max(240,graph.graph().width??240),height:Math.max(130,graph.graph().height??130)};
 },[view]);
 if(!layout.nodes.length)return null;
 const connected=new Set(view.relationships.filter(e=>e.source_dataset_id===active||e.target_dataset_id===active).flatMap(e=>[e.source_dataset_id,e.target_dataset_id]));
 return <div className="rounded-lg border border-border bg-background p-2"><svg role="img" aria-label="Selected Knowledge graph subgraph" viewBox={`0 0 ${layout.width} ${layout.height}`} className="w-full" style={{maxHeight:340,minHeight:160}}>
  <defs><marker id={marker} markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 Z" fill="currentColor"/></marker></defs>
  {view.relationships.map(e=>{const semantic=view.semantic_relationships?.find(s=>s.technical_relationship_id===e.relationship_id);const edge=layout.graph.edge({v:semantic?.reversed?e.target_dataset_id:e.source_dataset_id,w:semantic?.reversed?e.source_dataset_id:e.target_dataset_id,name:e.relationship_id});return <g key={e.relationship_id} className="text-primary" opacity={!active||connected.has(e.source_dataset_id)?1:.3}><polyline points={edge.points.map((p:{x:number;y:number})=>`${p.x},${p.y}`).join(" ")} fill="none" stroke="currentColor" strokeWidth="2" markerEnd={`url(#${marker})`}/><rect x={edge.x-70} y={edge.y-12} width="140" height="24" rx="6" className="fill-background"/><text x={edge.x} y={edge.y+4} textAnchor="middle" fontSize="12" fill="currentColor">{semantic?.predicate??"Meaning needs review"}</text></g>;})}
  {layout.nodes.map(source=>{const n=layout.graph.node(source.dataset_id);const title=source.label.split(" / ").at(-1)??source.label;const choose=()=>setActive(active===source.dataset_id?"":source.dataset_id);return <g key={source.dataset_id} role="button" tabIndex={0} aria-label={`Inspect planning source ${source.label}`} aria-pressed={active===source.dataset_id} onClick={choose} onKeyDown={e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();choose();}}} className="cursor-pointer outline-none focus:opacity-70" opacity={!active||active===source.dataset_id||connected.has(source.dataset_id)?1:.35}><title>{source.label}</title><ellipse cx={n.x} cy={n.y} rx="90" ry="40" fill={source.engine==="mongodb"?"#f0fdf4":"#eff6ff"} stroke={active===source.dataset_id?"#1d4ed8":source.engine==="mongodb"?"#15803d":"#2563eb"} strokeWidth={active===source.dataset_id?3:1.5}/><text x={n.x} y={n.y-2} textAnchor="middle" fontSize="13" fontWeight="600" fill="#0f172a">{title.length>23?title.slice(0,21)+"…":title}</text><text x={n.x} y={n.y+18} textAnchor="middle" fontSize="11" fill="#475569">{source.engine}</text></g>;})}
 </svg><p className="px-2 text-xs text-muted-foreground">Selected datasets and their declared or accepted links. Select a node to highlight its neighbors; inspect exact linking fields below.</p></div>;
}
