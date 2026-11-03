"use client";
import '@xyflow/react/dist/style.css';
import {ReactFlow,Background,Controls,MarkerType,type Node,type Edge} from '@xyflow/react';
import {useEffect,useMemo,useState} from 'react';
import type {BusinessSourceGraph} from '@/api/business-ontology';
export default function BusinessGraphCanvas({graph,onSelect}:{graph:BusinessSourceGraph;onSelect:(id:string)=>void}){
 const [compact,setCompact]=useState(false);
 useEffect(()=>{const media=window.matchMedia('(max-width:640px)');const update=()=>setCompact(media.matches);update();media.addEventListener('change',update);return()=>media.removeEventListener('change',update);},[]);
 const nodes=useMemo(()=>{const rows={service:0,quality:0};return graph.records.map(record=>({id:record.node_id,position:{x:compact?0:record.role==='service'?0:520,y:rows[record.role]++*95+(compact&&record.role==='quality'?graph.records.filter(r=>r.role==='service').length*95+50:0)},data:{label:`${record.collection} · ${String(record.key['_id']??record.node_id.slice(0,8))}`},style:{width:270,fontSize:compact?16:12},ariaLabel:`${record.collection} source record`,draggable:false} satisfies Node));},[graph,compact]);
 const edges=useMemo(()=>graph.edges.map((edge,index)=>({id:`edge-${index}`,source:edge.source,target:edge.target,label:edge.classification==='candidate'?'Candidate match':'Source reference',style:{stroke:edge.classification==='candidate'?'#b7791f':'#2563eb',strokeDasharray:edge.classification==='candidate'?'6 4':undefined},markerEnd:{type:MarkerType.ArrowClosed}} satisfies Edge)),[graph]);
 return <div aria-label="Source graph canvas" className="h-96 w-full overflow-hidden rounded-xl border"><ReactFlow key={compact?'compact':'wide'} nodes={nodes} edges={edges} fitView minZoom={0.05} maxZoom={2} nodesDraggable={false} nodesConnectable={false} onNodeClick={(_,node)=>onSelect(node.id)}><Background/><Controls showInteractive={false}/></ReactFlow></div>;
}
