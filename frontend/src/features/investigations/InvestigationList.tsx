'use client';
import {useEffect,useState} from 'react';
import {api} from '@/api/client';
import {stateLabels,type InvestigationJob} from '@/api/investigations';
import {Link} from '@/lib/navigation';
import {useBackend} from '@/api/state';
import {GitBranch,ArrowRight} from 'lucide-react';
type Item={workflow_id:string;objective:string;created_at:string;node_count:number;run_id:string|null;status:string};
export function InvestigationList() {
 const [items,setItems]=useState<Item[]>([]);const [jobs,setJobs]=useState<InvestigationJob[]>([]);const [error,setError]=useState<Error|null>(null);const [attempt,setAttempt]=useState(0);const status=useBackend(s=>s.status);
 useEffect(()=>{if(status!=='connected')return;let active=true;api.investigations().then(result=>{if(active){setItems(result.items);setJobs(result.jobs.filter(j=>j.kind==='plan'&&['queued','running'].includes(j.state)));setError(null);}}).catch(e=>{if(active)setError(e instanceof Error?e:new Error('Could not load investigations.'));});return()=>{active=false;};},[status,attempt]);
 return <section className="mt-8"><div className="mb-3 flex items-center gap-2"><GitBranch className="h-4 w-4 text-primary"/><h2 className="text-lg font-medium">Business investigations</h2></div>{error&&<p role="status" className="mb-3 text-sm text-muted-foreground">Saved investigations could not be loaded. <button className="text-primary underline" onClick={()=>setAttempt(n=>n+1)}>Retry investigation list</button></p>}{jobs.map(j=><Link key={j.job_id} to="/app/workflows/investigate" search={{job:j.job_id}} className="mb-2 block rounded-lg border p-3 text-sm">Workflow generation {j.state} · Open progress</Link>)}{items.length===0&&!error?<p className="rounded-xl border border-dashed p-5 text-sm text-muted-foreground">Generate an investigation from the overview to inspect its workflow, evidence and report here.</p>:<div className="divide-y rounded-xl border">{items.map(i=><Link key={i.workflow_id} to="/app/workflows/investigate" search={{workflow:i.workflow_id,...(i.run_id?{run:i.run_id}:{})}} className="flex items-center gap-3 p-4 hover:bg-canvas"><span className="min-w-0 flex-1"><span className="line-clamp-2 block text-sm font-medium">{i.objective}</span><span className="mt-1 block text-xs text-muted-foreground">{i.node_count} steps · {stateLabels[i.status]??i.status}</span></span><ArrowRight className="h-4 w-4 shrink-0 text-primary"/></Link>)}</div>}</section>;
}
