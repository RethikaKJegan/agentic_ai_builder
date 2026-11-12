'use client';
import {useBackend} from '@/api/state';
import {subwayDisplay} from '@/domain/subway-presentation';
import {useEffect,useState} from 'react';
import {z} from 'zod';
import {api} from '@/api/client';
import {runKnowledgeSchema,recoveryInspectionSchema,operationalAlertsSchema} from '@/api/reliability';
const words=(s:string)=>s.replaceAll('_',' ').toLowerCase();
export function RunKnowledge({runId}:{runId:string}) {
 const workspace=useBackend(s=>s.session?.auth.subject.workspace_id);
 const [sourceValue,setValue]=useState<z.infer<typeof runKnowledgeSchema>|null>(null);const [error,setError]=useState(false);
 const value=subwayDisplay(sourceValue,workspace);
 useEffect(()=>{let active=true;setValue(null);setError(false);api.runKnowledge(runId).then(v=>{if(active)setValue(v);}).catch(()=>{if(active)setError(true);});return()=>{active=false;};},[runId]);
 return <section aria-label="Pinned account knowledge" className="space-y-3"><h3 className="font-medium">Pinned account knowledge</h3>{error?<p role="status" className="text-sm">Account knowledge is unavailable for this run or your current permissions.</p>:!value?<p role="status" className="text-sm">Loading saved knowledge references…</p>:<><p className="text-xs text-muted-foreground">{value.qualification}</p>{!value.projections.length&&<p className="text-sm">This historical run has no unified graph pin.</p>}{value.projections.map(p=><article key={p.pin.source_key+':'+p.pin.revision} className="space-y-2 rounded-lg border p-3 text-sm"><p>Knowledge version {p.pin.revision} · {p.current?'Current authorized evidence':'Historical evidence — review freshness'}</p>{p.reason&&<p role="status">{p.reason}</p>}<ul className="flex flex-wrap gap-2">{p.nodes.map(n=><li key={n.node_id} className="rounded border px-2 py-1 text-xs">{n.label??n.reference??n.kind} · {words(n.status)}</li>)}</ul><ul className="space-y-2">{p.edges.map(e=><li key={e.edge_id}>{p.nodes.find(n=>n.node_id===e.source)?.label??p.nodes.find(n=>n.node_id===e.source)?.reference??'Source'} → <strong>{e.predicate}</strong> → {p.nodes.find(n=>n.node_id===e.target)?.label??p.nodes.find(n=>n.node_id===e.target)?.reference??'Target'} <span className="text-muted-foreground">({words(e.status)})</span></li>)}</ul>{!p.edges.length&&<p className="text-xs text-muted-foreground">No supported relationship path in this bounded projection.</p>}</article>)}</>}</section>;
}
export function RecoveryEvidence({runId}:{runId:string}) {
 const workspace=useBackend(s=>s.session?.auth.subject.workspace_id);
 const [sourceValue,setValue]=useState<z.infer<typeof recoveryInspectionSchema>|null>(null);const [failed,setFailed]=useState(false);
 const value=subwayDisplay(sourceValue,workspace);
 useEffect(()=>{let active=true;setValue(null);setFailed(false);api.recoveryInspection(runId).then(v=>{if(active)setValue(v);}).catch(()=>{if(active)setFailed(true);});return()=>{active=false;};},[runId]);
 return <section aria-label="Recovery and reconciliation" className="space-y-2"><h3 className="font-medium">Recovery and reconciliation</h3>{failed?<p className="text-sm">Recovery evidence is unavailable. Refresh saved run status before acting.</p>:!value?<p className="text-sm">Loading persisted recovery evidence…</p>:<><p className="text-sm">Required action: {words(value.required_action)}</p><p className="text-xs text-muted-foreground">{value.guidance}</p>{value.uncertain_invocations.map((i,index)=><div key={index} role="alert" className="rounded-lg border border-destructive/40 p-3 text-sm"><p>Provider outcome requires reconciliation</p><p className="break-all text-xs">Effect reference: {i.effect_reference??'Inspect original invocation history'}</p></div>)}<p className="text-xs">{value.completed_checkpoints.length} completed checkpoints preserved. Automatic replay is disabled.</p></>}</section>;
}
export function OperationalAlerts() {
 const workspace=useBackend(s=>s.session?.auth.subject.workspace_id);
 const [sourceValue,setValue]=useState<z.infer<typeof operationalAlertsSchema>|null>(null);const [failed,setFailed]=useState(false);
 const value=subwayDisplay(sourceValue,workspace);
 useEffect(()=>{let active=true;api.operationalAlerts().then(v=>{if(active)setValue(v);}).catch(()=>{if(active)setFailed(true);});return()=>{active=false;};},[]);
 return <section aria-label="Operational alerts" className="space-y-2"><h3 className="font-medium">Operational alerts</h3>{failed?<p role="status">Operational diagnostics are unavailable.</p>:!value?<p>Loading persisted operational status…</p>:<>{!value.alerts.length&&<p>No configured alert conditions are active.</p>}{value.alerts.map(a=><article key={a.code} role="alert" className="rounded-lg border p-3 text-sm"><p>{words(a.code)} · {a.count}</p><p>{a.action}</p></article>)}<p className="text-xs text-muted-foreground">{value.qualification}</p></>}</section>;
}
