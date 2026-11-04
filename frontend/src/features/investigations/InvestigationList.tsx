'use client';
import BusinessLifecycle from './BusinessLifecycle';
import {useEffect,useRef,useState} from 'react';
import {api} from '@/api/client';
import {stateLabels,type InvestigationJob} from '@/api/investigations';
import {Link} from '@/lib/navigation';
import {useBackend} from '@/api/state';
import {GitBranch,ArrowRight,MoreHorizontal,Pencil,Trash2} from 'lucide-react';
import {DropdownMenu,DropdownMenuContent,DropdownMenuItem,DropdownMenuTrigger} from '@/components/ui/dropdown-menu';
import {Dialog,DialogContent,DialogDescription,DialogHeader,DialogTitle} from '@/components/ui/dialog';
type Item={composition_id?:string;workflow_id:string;display_name?:string|undefined;objective:string;created_at:string;node_count:number;run_id:string|null;status:string};
export function InvestigationList({lifecycle=false}:{lifecycle?:boolean}={}) {
 const [items,setItems]=useState<Item[]>([]);const [jobs,setJobs]=useState<InvestigationJob[]>([]);const [error,setError]=useState<Error|null>(null);const [attempt,setAttempt]=useState(0);const status=useBackend(s=>s.status);
 const dynamicAvailable=useBackend(s=>s.session?.dynamic_composition_available===true);
 const canEdit=useBackend(s=>s.can('workflow.edit'));const canDelete=useBackend(s=>s.can('workflow.delete'));
 const [action,setAction]=useState<{item:Item;kind:'rename'|'delete'}|null>(null);const [name,setName]=useState('');const [actionError,setActionError]=useState<string|null>(null);const [busy,setBusy]=useState(false);const pending=useRef(false);
 useEffect(()=>{if(status!=='connected')return;let active=true;Promise.allSettled([api.investigations(),dynamicAvailable?api.compositions():Promise.resolve({items:[]})]).then(([legacy,dynamic])=>{if(!active)return;const old=legacy.status==='fulfilled'?legacy.value:{items:[],jobs:[]};const composed=dynamic.status==='fulfilled'?dynamic.value.items:[];setItems([...composed,...old.items].sort((a,b)=>b.created_at.localeCompare(a.created_at)));setJobs(old.jobs.filter(j=>['plan','compose'].includes(j.kind)&&['queued','running'].includes(j.state)));setError(legacy.status==='rejected'||dynamic.status==='rejected'?new Error('Some saved investigations could not be loaded.'):null);});return()=>{active=false;};},[status,attempt,dynamicAvailable]);
 function open(item:Item,kind:'rename'|'delete') {setAction({item,kind});setName((item.display_name??item.objective).slice(0,160));setActionError(null);}
 async function save() {
  if(!action||pending.current||(action.kind==='rename'&&(!canEdit||!name.trim()))||(action.kind==='delete'&&!canDelete))return;
  pending.current=true;setBusy(true);setActionError(null);
  try {
   if(action.kind==='rename'){const result=action.item.composition_id?await api.renameComposition(action.item.composition_id,name.trim()):await api.renameInvestigation(action.item.workflow_id,name.trim());setItems(items=>items.map(i=>i.workflow_id===result.workflow_id?{...i,display_name:result.display_name}:i));}
   else {if(action.item.composition_id)await api.deleteComposition(action.item.composition_id);else await api.deleteInvestigation(action.item.workflow_id);setItems(items=>items.filter(i=>i.workflow_id!==action.item.workflow_id));}
   setAction(null);
  } catch(error){setActionError(error instanceof Error?error.message:'The workflow could not be updated.');}
  finally{pending.current=false;setBusy(false);}
 }
 return <section className="mt-8"><div className="mb-3 flex items-center gap-2"><GitBranch className="h-4 w-4 text-primary"/><h2 className="text-lg font-medium">Business investigations</h2></div>
 {lifecycle&&<BusinessLifecycle/>}
 {error&&<p role="status" className="mb-3 text-sm text-muted-foreground">Saved investigations could not be loaded. <button className="text-primary underline" onClick={()=>setAttempt(n=>n+1)}>Retry investigation list</button></p>}
 {jobs.map(j=><Link key={j.job_id} to="/app/workflows/investigate" search={{job:j.job_id,...(j.kind==='compose'?{dynamic:'1'}:{})}} className="mb-2 block rounded-lg border p-3 text-sm">Workflow generation {j.state} · Open progress</Link>)}
 {items.length===0&&!error?<p className="rounded-xl border border-dashed p-5 text-sm text-muted-foreground">Generate an investigation from the overview to inspect its workflow, evidence and report here.</p>:<div className="divide-y rounded-xl border">{items.map(i=><div key={i.workflow_id} className="flex items-center gap-1 pr-2 hover:bg-canvas sm:pr-3">
 <Link to="/app/workflows/investigate" search={{...(i.composition_id?{composition:i.composition_id}:{workflow:i.workflow_id}),...(i.run_id?{run:i.run_id}:{})}} className="flex min-w-0 flex-1 items-center gap-3 p-4"><span className="min-w-0 flex-1"><span className="line-clamp-2 block break-words text-sm font-medium">{i.display_name??i.objective}</span><span className="mt-1 block text-xs text-muted-foreground">{i.node_count} steps · {stateLabels[i.status]??i.status}</span></span><ArrowRight className="h-4 w-4 shrink-0 text-primary"/></Link>
 <DropdownMenu><DropdownMenuTrigger aria-label={`Actions for ${i.display_name??i.objective}`} className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-muted focus-visible:outline-2 focus-visible:outline-primary"><MoreHorizontal className="h-4 w-4"/></DropdownMenuTrigger><DropdownMenuContent align="end"><DropdownMenuItem disabled={!canEdit} onSelect={()=>open(i,'rename')}><Pencil className="mr-2 h-4 w-4"/>Rename</DropdownMenuItem><DropdownMenuItem disabled={!canDelete||['running','queued','paused_for_approval'].includes(i.status)} onSelect={()=>open(i,'delete')} className="text-destructive"><Trash2 className="mr-2 h-4 w-4"/>Delete workflow</DropdownMenuItem></DropdownMenuContent></DropdownMenu>
 </div>)}</div>}
 <Dialog open={!!action} onOpenChange={open=>{if(!open&&!pending.current)setAction(null);}}><DialogContent className="w-[calc(100vw-2rem)] sm:max-w-md" onEscapeKeyDown={e=>{if(busy)e.preventDefault();}} onPointerDownOutside={e=>{if(busy)e.preventDefault();}}><DialogHeader><DialogTitle>{action?.kind==='delete'?'Delete workflow?':'Rename workflow'}</DialogTitle><DialogDescription>{action?.kind==='delete'?'This removes the workflow from your list. Saved execution history is retained.':'Choose a name to identify this workflow. Its original request stays unchanged.'}</DialogDescription></DialogHeader>
 <form className="space-y-4" onSubmit={e=>{e.preventDefault();void save();}}>{action?.kind==='rename'&&<label className="block text-sm">Workflow name<input autoFocus maxLength={160} aria-label="Workflow name" value={name} disabled={busy} onChange={e=>setName(e.target.value)} className="mt-2 w-full rounded-lg border bg-background px-3 py-2"/></label>}{actionError&&<p role="alert" className="text-sm text-destructive">{actionError}</p>}<div className="flex justify-end gap-2"><button type="button" disabled={busy} onClick={()=>setAction(null)} className="rounded-lg border px-3 py-2 text-sm">Cancel</button><button type="submit" disabled={busy||(action?.kind==='rename'&&!name.trim())} className={`rounded-lg px-3 py-2 text-sm disabled:opacity-40 ${action?.kind==='delete'?'bg-destructive text-white':'bg-primary text-primary-foreground'}`}>{busy?'Saving…':action?.kind==='delete'?'Delete workflow':'Save name'}</button></div></form>
 </DialogContent></Dialog>
 </section>;
}
