'use client';
import '@xyflow/react/dist/style.css';
import {Background,Controls,Handle,MarkerType,MiniMap,Panel,Position,ReactFlow,ReactFlowProvider,useReactFlow,type Node,type NodeProps} from '@xyflow/react';
import dagre from '@dagrejs/dagre';
import {useMemo} from 'react';
import {Bot,Check,Database,GitBranch,Loader2,Network,Play,FileText,UserRound,AlertCircle} from 'lucide-react';
import {nodeLabel,stateLabels,type InvestigationPlan,type InvestigationRun} from '@/api/investigations';

type Card=Node<{title:string;kind:string;status:string;hasGaps:boolean;condition:boolean;description:string},'investigation'>;
function InvestigationNode({data,selected}:NodeProps<Card>) {
 const Icon=data.kind==='agent'?Bot:data.kind==='retrieval'?Database:data.kind==='condition'?GitBranch:data.kind==='parallel'||data.kind==='join'?Network:data.kind==='human_input'?UserRound:data.kind==='end'?FileText:Play;
 const tone=data.status==='running'?'border-primary bg-highlight':data.hasGaps||data.status==='waiting_for_input'?'border-warning':data.status==='succeeded'?'border-success/60':data.status==='failed'?'border-destructive':selected?'border-primary':'border-border';
 return <div className={`relative w-[250px] rounded-xl border bg-background p-3.5 shadow-soft ${tone} ${data.status==='skipped'?'opacity-45':''}`}>
  {data.kind!=='start'&&<Handle type="target" position={Position.Top}/>}
  <div className="flex items-start gap-2.5"><span className="rounded-lg bg-muted p-2 text-primary"><Icon className="h-4 w-4"/></span><div className="min-w-0"><p className="text-[13px] font-medium leading-snug">{data.title}</p><p className="mt-1 text-[11px] text-muted-foreground">{data.description}</p></div></div>
  <p className="mt-3 flex items-center gap-1.5 text-[11px] text-muted-foreground">{data.status==='running'?<Loader2 className="h-3 w-3 animate-spin"/>:data.hasGaps?<AlertCircle className="h-3 w-3 text-warning"/>:data.status==='succeeded'?<Check className="h-3 w-3 text-success"/>:data.status==='failed'?<AlertCircle className="h-3 w-3 text-destructive"/>:null}{stateLabels[data.status]??data.status}{data.hasGaps?' · Evidence gaps':''}</p>
  {data.kind!=='end'&&(data.condition?(['true','false','unknown'].map((outcome,i)=><Handle key={outcome} id={outcome} type="source" position={Position.Bottom} style={{left:`${25+i*25}%`}}/>)):<Handle type="source" position={Position.Bottom}/>)}
 </div>;
}
const nodeTypes={investigation:InvestigationNode};
function ViewControls({start}:{start:{x:number;y:number}}) {
 const flow=useReactFlow();
 return <Panel position="top-left" className="flex flex-wrap gap-1 rounded-lg border bg-background p-1 shadow-soft"><button className="rounded-md px-2 py-1 text-xs hover:bg-muted" onClick={()=>void flow.fitView({padding:.18,duration:250})}>Fit workflow</button><button className="rounded-md px-2 py-1 text-xs hover:bg-muted" onClick={()=>void flow.setCenter(start.x+125,start.y+220,{zoom:.85,duration:250})}>Readable view</button></Panel>;
}
const descriptions:Record<string,string>={retrieval:'Read connected evidence',agent:'Evidence analysis',condition:'Choose an evidence-based branch',parallel:'Independent tasks',join:'Wait for selected branches',human_input:'Validate required information',start:'Receive investigation request',end:'Findings, sources and remaining gaps',deterministic:'Explain evidence gaps'};
export function investigationLayout(plan:InvestigationPlan) {
 const graph=new dagre.graphlib.Graph();graph.setGraph({rankdir:'TB',nodesep:62,ranksep:78,marginx:30,marginy:30});graph.setDefaultEdgeLabel(()=>({}));
 for(const n of plan.graph.nodes)graph.setNode(n.id,{width:250,height:122});
 for(const e of plan.graph.edges)graph.setEdge(e.source,e.target);
 dagre.layout(graph);return Object.fromEntries(plan.graph.nodes.map(n=>{const p=graph.node(n.id);return [n.id,{x:p.x-125,y:p.y-61}];}));
}
export function InvestigationCanvas({plan,run,selected,onSelect}:{plan:InvestigationPlan;run:InvestigationRun|null;selected:string|null;onSelect:(id:string)=>void}) {
 const positions=useMemo(()=>investigationLayout(plan),[plan]);
 const nodes=useMemo<Card[]>(()=>plan.graph.nodes.map(n=>{const output=run?.outputs[n.id];const gaps=output?.['missing_information'];const hasGaps=run?.node_states[n.id]==='succeeded'&&(output?.['completeness']==='incomplete'||output?.['completion_status']==='completed_with_gaps'||Array.isArray(gaps)&&gaps.length>0||run.branches[n.id]==='unknown');return {id:n.id,type:'investigation',position:positions[n.id]!,selected:selected===n.id,data:{title:nodeLabel(n),kind:n.type,status:run?.node_states[n.id]??'pending',hasGaps,condition:n.type==='condition',description:descriptions[n.type]??'Workflow task'}};}),[plan,run,positions,selected]);
 const edges=useMemo(()=>plan.graph.edges.map(e=>{const state=run?.edge_states[e.id];return {id:e.id,source:e.source,target:e.target,...(e.outcome?{sourceHandle:e.outcome}:{}),type:'smoothstep',label:e.outcome==='true'?'Yes':e.outcome==='false'?'No':e.outcome==='unknown'?'Unknown':undefined,animated:state==='selected'&&run?.status==='running',style:{stroke:state==='selected'?'var(--color-primary)':state==='skipped'?'var(--color-border)':'var(--color-muted-foreground)',strokeWidth:state==='selected'?2.5:1.3,opacity:state==='skipped'?.25:1},markerEnd:{type:MarkerType.ArrowClosed},labelStyle:{fontSize:11},labelBgStyle:{fill:'var(--color-background)'}};}),[plan,run]);
 return <div className="h-full min-h-[460px] w-full bg-canvas" aria-label="Investigation workflow canvas"><ReactFlowProvider><ReactFlow<Card> nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView fitViewOptions={{padding:.18}} minZoom={.18} maxZoom={1.4} nodesDraggable={false} nodesConnectable={false} edgesReconnectable={false} onNodeClick={(_,n)=>onSelect(n.id)} proOptions={{hideAttribution:true}}><Background gap={20} size={1}/><ViewControls start={positions[plan.graph.nodes[0]!.id]!}/><Controls showInteractive={false}/><MiniMap className="!hidden md:!block" pannable zoomable/></ReactFlow></ReactFlowProvider></div>;
}
