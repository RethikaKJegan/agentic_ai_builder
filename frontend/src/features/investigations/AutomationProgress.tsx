"use client";
import type {CompositionView} from '@/api/compositions';
import {AdaptiveProgress} from '@/features/builder/AdaptiveProgress';

export function AutomationProgress({run,onUpdated,onDetails}:{run:NonNullable<CompositionView['run']>;onUpdated:()=>void;onDetails:()=>void}) {
  const emailSent=Object.values(run.action_instances??{}).some(item=>
    item.state==='completed'&&item.verified_receipt===true&&typeof item.output?.['message_id']==='string'&&!!item.output['message_id']);
  const stopped=['blocked','failed','cancelled'].includes(run.status);
  const waiting=run.status==='paused_for_approval'||run.adaptive?.status==='waiting_for_input';
  const status=run.status==='completed'?'This run is complete.':stopped?'This run needs attention.':waiting?'This run is waiting for your review.':'This run is in progress.';
  return <section aria-label="Automation progress" className="flex flex-wrap items-center gap-3 rounded-lg border p-3 text-sm">
    <p role="status">{emailSent?'Email sent. ':''}{status}</p>
    {stopped&&<p className="text-muted-foreground">Review the saved execution details before starting another run.</p>}
    <button className="rounded border px-3 py-1" onClick={onDetails}>View execution details</button>
    {run.adaptive?.pending_wait&&<AdaptiveProgress run={run} onUpdated={onUpdated} compact/>}
  </section>;
}
