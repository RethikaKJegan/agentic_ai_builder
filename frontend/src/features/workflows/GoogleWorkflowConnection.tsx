"use client";
import { useEffect, useRef, useState } from 'react';
import { api, type GoogleConnection } from '@/api/client';
import { useBackend } from '@/api/state';
import { useMesh } from '@/domain/store';
import type { Workflow } from '@/domain/types';
import { toCanonical } from '@/api/mapping';
import { editSnapshot, acceptConfirmed } from './workflow-state';
import { ApiFeedback } from './ApiFeedback';

export function GoogleAccountSelect({value,onChange,disabled=false}:{value:string;onChange:(id:string)=>void;disabled?:boolean}){
  const connected=useBackend(s=>s.status==='connected');
  const [items,setItems]=useState<GoogleConnection[]>([]);
  const [error,setError]=useState<Error>();
  useEffect(()=>{if(!connected)return;let live=true;api.googleConnections().then(data=>{if(live)setItems(data.items);}).catch(e=>{if(live)setError(e);});return()=>{live=false;};},[connected]);
  return <div className="space-y-2"><label className="block text-xs font-medium">Google account<select aria-label="Workflow Google account" value={value} disabled={disabled||!connected} onChange={e=>onChange(e.target.value)} className="mt-1 w-full rounded-lg border bg-background px-3 py-2 text-sm"><option value="">Existing server connection (legacy)</option>{value&&!items.some(i=>i.connection_id===value)&&<option value={value}>Selected connection unavailable</option>}{items.map(item=><option key={item.connection_id} value={item.connection_id} disabled={!['connected','verification_failed'].includes(item.status)}>{item.account_email} · {item.status.replaceAll('_',' ')}</option>)}</select></label><p className="text-xs text-muted-foreground">A selected account applies to Gmail, Sheets and Calendar. Missing access stops the operation; another account is never substituted.</p><ApiFeedback error={error}/></div>;
}

export function GoogleWorkflowConnection({workflow}:{workflow:Workflow}){
  const backend=useBackend();
  const current=typeof workflow.canonical?.metadata['google_connection_id']==='string'?workflow.canonical.metadata['google_connection_id']:'';
  const [selected,setSelected]=useState(current);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState<Error>();
  const pending=useRef(false);
  useEffect(()=>{setSelected(current);},[current]);
  const save=async()=>{if(pending.current)return;pending.current=true;setBusy(true);setError(undefined);try{const state=useMesh.getState();const latest=state.workflows.find(w=>w.id===workflow.id)??workflow;const snapshot=editSnapshot(latest,state.agents);const document=toCanonical(latest,state.agents);if(selected)document.metadata['google_connection_id']=selected;else delete document.metadata['google_connection_id'];const result=await api.request('save_workflow_version',{workflow_id:document.workflow_id,workflow_version:document.version,base_version:latest.serverVersion??0,workflow:document});acceptConfirmed(result.workflow,snapshot);await backend.refreshOverview();}catch(e){setError(e instanceof Error?e:new Error('Google binding could not be saved.'));}finally{pending.current=false;setBusy(false);}};
  return <section className="space-y-3 rounded-xl border p-4" aria-label="Workflow Google binding"><h2 className="text-sm font-semibold">Google connection for this revision</h2><GoogleAccountSelect value={selected} onChange={setSelected} disabled={busy||!backend.can('workflow.edit')||!backend.can('tools.assign')}/><p className="text-xs text-muted-foreground">Saving creates a draft revision. Validate, review and publish it through the normal workflow controls. Existing runs keep their original account.</p><button disabled={busy||selected===current||!backend.can('workflow.edit')||!backend.can('tools.assign')} onClick={()=>void save()} className="rounded-lg bg-primary px-3 py-2 text-xs text-primary-foreground disabled:opacity-40">{busy?'Saving…':'Save account binding'}</button><ApiFeedback error={error}/></section>;
}
