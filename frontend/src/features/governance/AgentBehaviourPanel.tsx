"use client";
import { useEffect,useState } from "react";
import { Switch } from "@/components/ui/switch";
import { api } from "@/api/client";
import { useBackend } from "@/api/state";
import type { BehaviourPreferences,ExecutionPreferences } from "@/api/execution-preferences";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";
type Policies=NonNullable<Awaited<ReturnType<typeof api.monitoring>>['policies']>;
const controls:[keyof BehaviourPreferences,string,string][]=[
 ['formalTone','Formal tone','Use formal, professional wording without changing facts or business rules.'],
 ['conciseResponses','Concise responses','Keep explanations compact while retaining required evidence and disclosures.'],
 ['clarifyUncertainty','Clarify uncertainty','Distinguish verified observations, assumptions and missing information.'],
 ['requireSupportingEvidence','Require supporting evidence','Use supplied evidence references; disclose unsupported findings. Registered evidence schemas and citation checks remain authoritative.'],
];
export function AgentBehaviourPanel(props:{policies:Policies;onViewLimits:()=>void}) {
 const subject=useBackend(s=>s.session?.auth.subject);
 return <Preferences key={JSON.stringify(subject)} {...props}/>;
}
function Preferences({policies,onViewLimits}:{policies:Policies;onViewLimits:()=>void}) {
 const status=useBackend(s=>s.status);const [data,setData]=useState<ExecutionPreferences>();const [value,setValue]=useState<BehaviourPreferences>();const [error,setError]=useState<Error>();const [busy,setBusy]=useState(false);const [message,setMessage]=useState('');
 useEffect(()=>{let live=true;if(status==='connected')api.executionPreferences().then(r=>{if(live){setData(r);setValue(r.settings.behaviours);}}).catch(e=>{if(live)setError(e);});return()=>{live=false;};},[status]);
 const dirty=JSON.stringify(value)!==JSON.stringify(data?.settings.behaviours);const policy=policies.find(p=>p.agents.length);const agent=policy?.agents[0];
 return <section aria-label="Agent Behaviour & Safety" className="mb-7 space-y-4 rounded-2xl border bg-background p-5"><h2 className="text-lg font-semibold">Agent Behaviour &amp; Safety</h2><p className="text-sm text-muted-foreground">Saved for your authenticated workspace account. Applies to new supported model runs; running workflows retain their saved configuration. Style instructions are best effort.</p><ApiFeedback error={error}/>{!data&&<p role="status">{status==='connected'?'Loading effective preferences…':'Connect to load effective preferences.'}</p>}<div className="grid gap-4 sm:grid-cols-2">{controls.map(([key,label,hint])=><div key={key} className="rounded-xl border p-4"><div className="flex items-center justify-between gap-3"><label htmlFor={'behaviour-'+key} className="text-sm font-medium">{label}</label><Switch id={'behaviour-'+key} aria-label={label} disabled={!value||busy} checked={value?.[key]??false} onCheckedChange={checked=>{if(value)setValue({...value,[key]:checked});setMessage('');}}/></div><p className="mt-2 text-xs text-muted-foreground">{hint}</p></div>)}</div><p className="text-xs text-muted-foreground">Permissions, mandatory source/evidence checks, exact approvals and execution limits always apply. Preferences cannot relax them. No abusive-language screening is advertised.</p>{agent&&<p className="text-xs text-muted-foreground">Model calls ≤ {agent.limits.max_llm_calls} · Tool calls ≤ {agent.limits.max_tool_calls} · Retries ≤ {agent.limits.max_retries}</p>}<div className="flex flex-wrap items-center justify-between gap-3"><button onClick={onViewLimits} className="text-xs text-primary">View all limits</button><button type="button" disabled={!value||!data||busy||!dirty} className="rounded-lg bg-primary px-4 py-2 text-xs text-primary-foreground disabled:opacity-40" onClick={async()=>{if(!value||!data)return;setBusy(true);setError(undefined);try{const r=await api.saveExecutionPreferences({expected_revision:data.settings.revision,behaviours:value});setData(r);setValue(r.settings.behaviours);setMessage('Execution preferences saved on the server.');}catch(e){setError(e instanceof Error?e:new Error('Save failed'));}finally{setBusy(false);}}}>{busy?'Saving…':'Apply preferences'}</button></div>{message&&<p role="status" className="text-xs">{message}</p>}</section>;
}
