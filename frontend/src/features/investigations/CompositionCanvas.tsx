'use client';
import {subwayDisplay} from '@/domain/subway-presentation';
import {useBackend} from '@/api/state';
import '@xyflow/react/dist/style.css';
import {useMemo} from 'react';
import {subwayCardSize,workflowCardTitle} from '@/domain/workflow-card-layout';
import dagre from '@dagrejs/dagre';
import {ReactFlow,ReactFlowProvider,Background,Controls,MiniMap,Handle,Position,MarkerType,type Node,type NodeProps} from '@xyflow/react';
import {Bot,Database,Check,AlertCircle,Loader2,Network} from 'lucide-react';
import {taskEdges,taskStateLabels,type CompositionView} from '@/api/compositions';
type Card=Node<{label:string;kind:string;state:string;condition:boolean;compact?:boolean},'task'>;
function TaskCard({data,selected}:NodeProps<Card>) {
 const Icon=data.kind==='retrieval'?Database:data.kind==='master'?Network:Bot;
 const tone=data.state==='running'?'border-primary bg-highlight':data.state==='completed'?'border-success/60':data.state==='needs_input'?'border-warning':['failed','interrupted','blocked'].includes(data.state)?'border-destructive':selected?'border-primary':'border-border';
 return <div className={`${data.compact?'w-[280px] h-[168px] flex flex-col':'w-[260px]'} rounded-xl border bg-background p-4 shadow-soft ${tone}`}><Handle type="target" position={Position.Top}/><div className="flex gap-3"><Icon className="mt-1 h-5 w-5 shrink-0 text-primary"/><p className={data.compact?"line-clamp-2 text-sm font-medium leading-5":"text-sm font-medium"}>{data.label}</p></div><p className={data.compact?"mt-2 line-clamp-2 text-xs text-muted-foreground":"mt-2 text-xs text-muted-foreground"}>{data.kind==='master'?'Coordinates the specialist agents':data.condition?'Checks required evidence before analysis':data.kind==='retrieval'?'Reads authorized business evidence':data.kind==='approval'?'An authorized user reviews the exact action':data.kind==='action'?'Runs only after the required action approval':'Uses completed dependency results'}</p><p className={`${data.compact?'mt-auto pt-3':'mt-3'} flex items-center gap-1 text-xs text-muted-foreground`}>{data.state==='running'?<Loader2 className="h-3 w-3 animate-spin"/>:data.state==='completed'?<Check className="h-3 w-3 text-success"/>:['needs_input','failed','blocked','interrupted'].includes(data.state)?<AlertCircle className="h-3 w-3"/>:null}{taskStateLabels[data.state]??data.state}</p><Handle type="source" position={Position.Bottom}/></div>;
}
const nodeTypes={task:TaskCard};
export function CompositionCanvas({view:sourceView,onSelect}:{view:CompositionView;onSelect:(id:string)=>void}) {
 const workspace=useBackend(s=>s.session?.auth.subject.workspace_id);const view=useMemo(()=>subwayDisplay(sourceView,workspace),[sourceView,workspace]);
 const compact=true;
 const graph=useMemo(()=>{
  const gates=view.tasks.flatMap(t=>t.approval_gate?[{...t.approval_gate,kind:'approval',condition:false}]:[]);const gateByTask=Object.fromEntries(view.tasks.filter(t=>t.approval_gate).map(t=>[t.id,t.approval_gate!.id]));
  const edges=[...taskEdges(view.tasks).map(e=>({...e,target:gateByTask[e.target]??e.target})),...view.tasks.filter(t=>t.approval_gate).map(t=>({id:`${t.approval_gate!.id}-${t.id}`,source:t.approval_gate!.id,target:t.id}))];const root='coordinator';
  const definitions=[{id:root,label:'Goal coordinator',kind:'master',state:view.run?.status==='completed'?'completed':view.run?.status==='running'?'running':view.run?.status??'pending',condition:false},...gates,...view.tasks.map(t=>({...t,condition:t.condition==='required_facts_available'}))];
  const allEdges=[...view.tasks.filter(t=>!t.depends_on.length).map(t=>({id:`master-${t.id}`,source:root,target:gateByTask[t.id]??t.id})),...edges];
  const layout=new dagre.graphlib.Graph();layout.setGraph({rankdir:'TB',nodesep:compact?80:65,ranksep:compact?70:85});layout.setDefaultEdgeLabel(()=>({}));
  const size=compact?subwayCardSize:{width:260,height:150};
  definitions.forEach(n=>layout.setNode(n.id,{...size}));allEdges.forEach(e=>layout.setEdge(e.source,e.target));dagre.layout(layout);
  const nodes:Card[]=definitions.map(n=>({id:n.id,type:'task',position:{x:layout.node(n.id).x-size.width/2,y:layout.node(n.id).y-size.height/2},data:{label:compact?workflowCardTitle(n.id,n.label):n.label,kind:n.kind,state:n.state,condition:n.condition,compact}}));
  const byId=Object.fromEntries(definitions.map(t=>[t.id,t]));
  return {nodes,edges:allEdges.map(e=>({...e,type:'smoothstep',markerEnd:{type:MarkerType.ArrowClosed},animated:byId[e.target]?.state==='running',style:{stroke:byId[e.source]?.state==='completed'?'var(--color-primary)':'var(--color-border)',strokeWidth:2}}))};
 },[view,compact]);
 return <div className="h-full min-h-[480px] w-full bg-canvas" aria-label="Dynamic investigation workflow canvas"><ReactFlowProvider><ReactFlow<Card> {...graph} nodeTypes={nodeTypes} fitView fitViewOptions={compact?{nodes:graph.nodes.filter(n=>n.id==='coordinator'||n.position.y===Math.min(...graph.nodes.filter(n=>n.id!=='coordinator').map(n=>n.position.y))).map(n=>({id:n.id})),padding:.18,minZoom:.55,maxZoom:.9}:{}} minZoom={.2} maxZoom={1.4} nodesDraggable={false} nodesConnectable={false} edgesReconnectable={false} onNodeClick={(_,node)=>onSelect(node.id)} proOptions={{hideAttribution:true}}><Background gap={20}/>{compact&&<div className="absolute right-3 top-3 z-10 rounded-md border bg-background/95 px-3 py-2 text-xs text-muted-foreground pointer-events-none">Drag to explore · Select a step for details</div>}<Controls showInteractive={false}/><MiniMap className="!hidden md:!block"/></ReactFlow></ReactFlowProvider></div>;
}
