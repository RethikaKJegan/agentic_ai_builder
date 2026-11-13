"use client";
import { useState } from 'react';
import { api, type RunRecord } from '@/api/client';
import { useBackend } from '@/api/state';
import { ApiFeedback } from '@/features/workflows/ApiFeedback';
export function StopRun({run,onStopped}:{run:RunRecord;onStopped:()=>void}) {
  const backend=useBackend();
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState<Error|null>(null);
  if (!['queued','running','paused_for_approval'].includes(run.status)||!backend.can('workflow.execute')) return null;
  return <span className="inline-flex flex-wrap items-center gap-2"><button type="button" disabled={busy} className="rounded-lg border border-destructive/40 px-3 py-2 text-sm text-destructive disabled:opacity-40" onClick={async()=>{
    if(busy)return;setBusy(true);setError(null);
    try{await api.stopRun(run.run_id);onStopped();}catch(caught){setError(caught instanceof Error?caught:new Error('Unable to stop this run.'));}finally{setBusy(false);}
  }}>{busy?'Stopping…':'Stop run'}</button><ApiFeedback error={error}/></span>;
}
export function RunSafety({run}:{run:RunRecord}) {
  if(!run.safety)return null;
  const safety=run.safety;
  return <div className="space-y-2 text-xs">{safety.error_code&&<p role="status">Execution stopped: {safety.error_code.replaceAll('_',' ').toLowerCase()}</p>}{safety.cancellation&&<p>Stopped by user request. Further execution is disabled.</p>}{!!safety.uncertain_effects.length&&<p className="text-destructive">An external action needs reconciliation. Verify its provider outcome before preparing another action.</p>}<details><summary>Execution limits and usage</summary><p className="my-2">Workspace policy revision {safety.policy_revision}. Stricter run, workflow and agent restrictions also apply.</p><pre className="max-h-64 overflow-auto whitespace-pre-wrap">{JSON.stringify({limits:safety.effective_policy.limits,usage:safety.usage},null,2)}</pre></details></div>;
}
