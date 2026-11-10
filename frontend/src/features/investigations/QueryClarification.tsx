"use client";
import {useState} from 'react';
import {api} from '@/api/client';
import {useBackend} from '@/api/state';
import type {ActionDocument} from '@/api/orchestration';
import type {CompositionView} from '@/api/compositions';
import {useNavigate} from '@/lib/navigation';
import {ApiFeedback} from '@/features/workflows/ApiFeedback';
import {useOrchestrationCommand} from './useOrchestrationCommand';

const record=(value:unknown):Record<string,unknown>=>value&&typeof value==='object'&&!Array.isArray(value)?value as Record<string,unknown>:{};
export function QueryClarification({doc,view}:{doc:ActionDocument;view:CompositionView}) {
 const [definition,setDefinition]=useState('');
 const command=useOrchestrationCommand();
 const backend=useBackend();
 const navigate=useNavigate();
 const questions=[...new Set(view.tasks.filter(t=>t.result?.classification==='query_clarification').flatMap(t=>t.result?.missing_information??[]))];
 const objective=doc.action_plan.goal+'\nBusiness definition supplied by the user: '+definition.trim();
 const tooLong=objective.length>4000;
 async function clarify(){
  if(!definition.trim()||tooLong)return;
  await command.act('clarify-query:'+doc.composition_id,{objective,google_connection_id:doc.google_connection_id??null},async intent=>{
   const next=await api.createActionPlan({objective,request_key:String(intent['request_key']),automatic_inputs:true,
    client_id:doc.action_plan.scope.client_id,business_request:record(view.request_context?.['business_request']),
    user_values:record(record(doc['binding_context'])['user_values']),resources:view.resources,
    ...(doc.google_connection_id?{google_connection_id:doc.google_connection_id}:{})});
   navigate({to:'/app/workflows/investigate',search:{connected:'1',composition:next.composition_id}});
  });
 }
 return <section aria-label="Query clarification" className="space-y-3 rounded-lg border border-warning/50 p-4">
  <h3 className="font-semibold">Clarification needed</h3>
  {questions.map((question,i)=><p key={i} className="break-words text-sm">{question}</p>)}
  <p className="text-sm text-muted-foreground">This query has not executed. Supply the intended field and unit to generate a new workflow for review using the selected account.</p>
  <label className="block space-y-1 text-sm"><span>Business definition</span><textarea aria-label="Business definition" value={definition} onChange={e=>setDefinition(e.target.value)} maxLength={1000} rows={3} disabled={command.busy||command.unknown} className="w-full rounded-lg border bg-background p-2"/></label>
  {tooLong&&<p role="alert" className="text-sm">The updated request exceeds 4,000 characters. Shorten the definition or edit the original prompt.</p>}
  <button className="rounded-lg border px-3 py-2 text-sm disabled:opacity-40" disabled={!definition.trim()||tooLong||command.busy||command.unknown||!backend.can('workflow.plan')} onClick={()=>void clarify()}>Generate clarified workflow</button>
  <ApiFeedback error={command.error}/>
  {command.unknown&&<button className="rounded-lg border px-3 py-2 text-sm" disabled={command.busy} onClick={command.retry}>Check generation outcome</button>}
 </section>;
}
