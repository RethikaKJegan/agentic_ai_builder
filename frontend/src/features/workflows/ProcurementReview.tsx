"use client";
import { displayText } from "@/lib/display-text";
import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/api/client";
import { useBackend } from "@/api/state";
import { useMesh } from "@/domain/store";
import type { Workflow } from "@/domain/types";
import { toCanonical } from "@/api/mapping";
import { editSnapshot, acceptConfirmed } from "./workflow-state";
import { ApiFeedback } from "./ApiFeedback";
import { Dialog, DialogContent, DialogTitle, DialogDescription, DialogTrigger } from '@/components/ui/dialog';
import { ProcurementOverview, PurchaseOrderProgress, ProcurementVendors } from './ProcurementStatusCards';
import { Settings2, RefreshCw, ArrowUpRight } from 'lucide-react';

type FulfilmentSettings = { enabled: true; buyer_email: string; manager_email: string; acceptance_hours: number; reminder_hours: number; allow_delivery_reschedule: boolean };
type Plan = { project_id: string; name: string; simulation: boolean;
  context: Record<string, string | null>; requirements: { spreadsheet_url: string; range: string; columns: Record<string, string> };
  vendors: { spreadsheet_url: string; range: string; columns: Record<string, string> } | null;
  supplier_mode?: "supplied" | "discover" | "combined"; search_region?: string; action_mode?: "approval" | "automatic";
  phase2?: { enabled: true; calendar_id: string; reminder_minutes: number; purchasing_limit: string | null; allow_single_offer: boolean } | null;
  phase3?: FulfilmentSettings | null };
export function ProcurementReview({ workflow, onStarted }: { workflow: Workflow; onStarted?: (() => void) | undefined }) {
  const backend = useBackend();
  const [open,setOpen]=useState(false);
  const [tab,setTab]=useState<'overview'|'setup'|'vendors'|'orders'|'activity'>('overview');
  const [search,setSearch]=useState('');
  const raw = workflow.canonical?.metadata["procurement_plan"];
  const plan = raw && typeof raw === "object" && "project_id" in raw ? raw as Plan : null;
  const [draft, setDraft] = useState<Plan | null>(plan);
  const [status, setStatus] = useState<Awaited<ReturnType<typeof api.procurementStatus>>>();
  const [error, setError] = useState<Error>();
  const [busy, setBusy] = useState(false);
  const [releaseState, setReleaseState] = useState<Awaited<ReturnType<typeof api.releaseState>>>();
  const [releaseError, setReleaseError] = useState(false);
  const pending = useRef(false);
  const [startRun, setStartRun] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [notStarted, setNotStarted] = useState(false);
  const [fulfilment, setFulfilment] = useState<FulfilmentSettings>({ enabled: true, buyer_email: "", manager_email: "", acceptance_hours: 24, reminder_hours: 24, allow_delivery_reschedule: false });
  const live = backend.overview[workflow.id];
  const publishedVersion = live?.published_version;
  useEffect(() => { setDraft(plan); }, [raw]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!plan) return;
    let disposed = false;
    setReleaseState(undefined); setReleaseError(false);
    api.releaseState(workflow.id).then(result => {
      if (!disposed) setReleaseState(result);
    }).catch(() => { if (!disposed) setReleaseError(true); });
    return () => { disposed = true; };
  }, [workflow.id, !!plan, publishedVersion, live?.release_id, live?.activation_state]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(()=>{
    if(!open||!plan)return;
    let disposed=false;
    const timer=setInterval(()=>{if(pending.current)return;void api.procurementStatus(plan.project_id).then(next=>{if(!disposed){setStatus(next);setNotStarted(false);}}).catch(()=>{/* Keep the last confirmed snapshot; explicit refresh displays errors. */});},8000);
    return()=>{disposed=true;clearInterval(timer);};
  },[open,plan?.project_id]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!plan || !draft) return null;
  const editable = backend.can("workflow.edit") && (workflow.canonical?.status === "draft" || workflow.canonical?.status === "validated");
  const activeRelease = releaseState?.workflow_id === workflow.id && releaseState.release?.state === "active" && releaseState.release.workflow_version === publishedVersion;
  const startReason = !publishedVersion ? "Publish this workflow before starting procurement."
    : releaseError ? "Could not check activation. Refresh project status to try again."
      : !releaseState ? "Checking workflow activation…"
        : !activeRelease ? `Activate published revision v${publishedVersion} before starting procurement.` : "";
  const start = async () => {
    if (pending.current || startReason || !publishedVersion || !backend.can("workflow.execute") || !backend.session?.runtime_available) return;
    pending.current = true; setBusy(true); setError(undefined);
    try {
      const current = await api.releaseState(workflow.id);
      setReleaseState(current);
      if (current.workflow_id !== workflow.id || current.release?.state !== "active" || current.release.workflow_version !== publishedVersion)
        throw new Error(`Activate published revision v${publishedVersion} before starting procurement.`);
      // One durable start per active release; retries cannot duplicate a run or
      // reuse a failed attempt made before this release was activated.
      const result = await api.request("execute_workflow", { workflow_id: workflow.id, workflow_version: publishedVersion, inputs: {} }, `procurement_start_${current.release.release_id}`);
      if (["failed", "blocked", "rejected", "cancelled"].includes(result.run.status))
        throw new Error(`Procurement run ${result.run.run_id} ${result.run.status}. Open Execution to inspect the failed step before trying again.`);
      setStartRun(`${result.run.run_id} · ${result.run.status}`);
      setOpen(false);onStarted?.();
      try { setStatus(await api.procurementStatus(plan.project_id)); setNotStarted(false); }
      catch (failure) { if (failure instanceof ApiError && failure.error.error_code === "PROCUREMENT_PROJECT_NOT_FOUND") setNotStarted(true); else throw failure; }
    } catch (e) { setError(e instanceof Error ? e : new Error("Procurement could not be started.")); }
    finally { pending.current = false; setBusy(false); }
  };
  const load = async () => {
    if (pending.current) return;
    pending.current = true; setError(undefined);
    setBusy(true);
    try {
      // Recover the session/capabilities after a local backend restart.
      await backend.initialize();
      try { setReleaseState(await api.releaseState(workflow.id)); setReleaseError(false); }
      catch { setReleaseError(true); }
      setStatus(await api.procurementStatus(plan.project_id));
      setNotStarted(false);
    } catch (e) {
      const absent = e instanceof ApiError && e.error.error_code === "PROCUREMENT_PROJECT_NOT_FOUND";
      setNotStarted(absent);
      setError(absent ? undefined : e instanceof Error ? e : new Error("Could not load procurement status."));
    } finally { pending.current = false; setBusy(false); }
  };
  const save = async () => {
    if (!workflow.canonical || pending.current || !backend.can("workflow.edit")) return;
    pending.current = true; setBusy(true); setError(undefined);
    try {
      const state = useMesh.getState(); const current = state.workflows.find(item => item.id === workflow.id) ?? workflow;
      const snapshot = editSnapshot(current, state.agents);
      const document = toCanonical(current, state.agents);
      document.metadata["procurement_plan"] = draft;
      const result = await api.request("save_workflow_version", { workflow_id: document.workflow_id,
        workflow_version: document.version, base_version: workflow.serverVersion ?? 0, workflow: document });
      acceptConfirmed(result.workflow, snapshot);
    } catch (e) { setError(e instanceof Error ? e : new Error("Could not save project settings.")); }
    finally { pending.current = false; setBusy(false); }
  };
  const reviewSuppliers = async (decision: "approved" | "rejected") => {
    if (!status?.shortlist_digest || pending.current || !backend.can("workflow.approve")) return;
    pending.current = true; setBusy(true); setError(undefined);
    try {
      await api.procurementSuppliersReview(plan.project_id, decision, selected, status.shortlist_digest);
      setStatus(await api.procurementStatus(plan.project_id));
    } catch (e) { setError(e instanceof Error ? e : new Error("Supplier selection could not be saved.")); }
    finally { pending.current = false; setBusy(false); }
  };
  const activateFulfilment = async () => {
    if (pending.current || !publishedVersion || !backend.can("workflow.approve")) return;
    pending.current = true; setBusy(true); setError(undefined);
    try {
      if (typeof api.procurementFulfilmentActivate !== "function") {
        throw new Error("The frontend API client is out of date. Restart the frontend and reload this page, then activate fulfilment again.");
      }
      await api.procurementFulfilmentActivate(plan.project_id, workflow.id, publishedVersion, status?.fulfilment_policy?.revision ?? 0, fulfilment);
      setStatus(await api.procurementStatus(plan.project_id));
    } catch (e) { setError(e instanceof Error ? e : new Error("Could not activate fulfilment.")); }
    finally { pending.current = false; setBusy(false); }
  };
  const fulfilmentInputs = (value: FulfilmentSettings, change: (next: FulfilmentSettings) => void, disabled: boolean) => <>
    {(["buyer_email", "manager_email"] as const).map(field => <label className="block" key={field}>{field === "buyer_email" ? "Buyer receiving email" : "Manager notification email"}
      <input type="email" disabled={disabled} className="mt-1 w-full rounded-lg border bg-background px-3 py-2" value={value[field]} onChange={e => change({ ...value, [field]: e.target.value })} /></label>)}
    {(["acceptance_hours", "reminder_hours"] as const).map(field => <label className="block" key={field}>{field.replaceAll("_", " ")}
      <input type="number" min={1} max={720} disabled={disabled} className="mt-1 w-full rounded-lg border bg-background px-3 py-2" value={value[field]} onChange={e => change({ ...value, [field]: Number(e.target.value) })} /></label>)}
    <label className="block"><input type="checkbox" disabled={disabled} checked={value.allow_delivery_reschedule}
      onChange={e => change({ ...value, allow_delivery_reschedule: e.target.checked })} /> Allow reported delivery dates within the original required deadline</label>
  </>;
  return <Dialog open={open} onOpenChange={next=>{setOpen(next);if(next){setTab('overview');void load();}}}>
    <DialogTrigger className="inline-flex items-center gap-2 rounded-lg border bg-background px-3 py-2 text-sm hover:bg-muted"><Settings2 className="h-4 w-4"/>Procurement setup &amp; status</DialogTrigger>
    <DialogContent className="flex h-[92dvh] w-[96vw] max-w-5xl flex-col gap-0 overflow-hidden p-0 sm:rounded-2xl">
      <div className="border-b bg-background px-6 py-5 pr-12"><p className="mb-2 text-[10px] font-semibold uppercase tracking-[.2em] text-primary">Procurement workspace</p><DialogTitle className="text-xl">{displayText(draft.name)}</DialogTitle><DialogDescription className="mt-2 text-xs">{draft.simulation?'Simulation':'Real procurement'} · {draft.action_mode==='automatic'?'Automatic action policy':'Approval-based actions'} · source spreadsheet stays unchanged</DialogDescription></div>
      <nav aria-label="Procurement sections" className="flex shrink-0 gap-1 overflow-x-auto border-b bg-background px-4 py-2">{(['overview','setup','vendors','orders','activity'] as const).map(item=><button key={item} onClick={()=>setTab(item)} aria-pressed={tab===item} className={`whitespace-nowrap rounded-lg px-4 py-2 text-sm ${tab===item?'bg-primary/5 font-medium text-primary':'text-muted-foreground hover:bg-muted'}`}>{item==='vendors'?'Vendors & quotes':item.charAt(0).toUpperCase()+item.slice(1)}</button>)}</nav>
      <div className="min-h-0 flex-1 overflow-y-auto bg-muted/15 p-4 sm:p-6">
      <div hidden={tab!=='setup'} className="space-y-5 rounded-2xl border bg-background p-5">
      <p className="text-sm">Review source mappings and project terms before publishing. {draft.action_mode === "automatic"
        ? "Publication authorizes automatic supplier selection, tracking writes, drafts and RFQ sends for this project."
        : "Each spreadsheet write, Gmail draft and RFQ send has its own approval."}</p>
      <p className="text-sm">{draft.simulation ? "Simulation project" : "Real procurement project"}</p>
      <p className="text-sm">Supplier mode: {draft.supplier_mode ?? "supplied"}{draft.supplier_mode !== "supplied" && draft.supplier_mode ? " · DDGS keyless research" : ""}</p>
      {(["requirements", "vendors"] as const).map(kind => { const source = draft[kind]; return source ? <div key={kind} className="text-sm">
        <p className="font-medium capitalize">{kind}</p><p className="break-all">{source.spreadsheet_url}</p>
        <label className="block">Table range<input disabled={!editable || busy} className="mt-1 w-full rounded-lg border bg-background px-3 py-2" value={source.range}
          onChange={e => setDraft({ ...draft, [kind]: { ...source, range: e.target.value } })} /></label>
        {Object.entries(source.columns).map(([field, header]) => <label key={field} className="mt-1 flex items-center justify-between gap-2">
          <span>{field}</span><input disabled={!editable || busy} className="w-1/2 rounded border p-1" value={header}
            onChange={e => setDraft({ ...draft, [kind]: { ...source, columns: { ...source.columns, [field]: e.target.value } } })} /></label>)}
      </div> : null; })}
      {Object.entries(draft.context).map(([field, value]) => <label key={field} className="block text-sm">
        {field.replaceAll("_", " ")}<input disabled={!editable || busy} className="mt-1 w-full rounded-lg border bg-background px-3 py-2" value={value ?? ""}
          placeholder="Required project information" onChange={e => setDraft({ ...draft, context: { ...draft.context, [field]: e.target.value || null } })} />
      </label>)}
      {draft.phase2 && <section className="space-y-2 rounded border p-2 text-sm">
        <p className="font-medium">Quotation comparison and purchase orders</p>
        <p>{draft.action_mode === "automatic" ? "Automatic simulation awards and PO release use the published project spending limit." : "Award and PO emails require action approval."}</p>
        <label className="block">Calendar<input disabled={!editable || busy} className="mt-1 w-full rounded-lg border bg-background px-3 py-2" value={draft.phase2.calendar_id}
          onChange={e => setDraft({ ...draft, phase2: { ...draft.phase2!, calendar_id: e.target.value } })} /></label>
        <label className="block">Reminder minutes<input type="number" min={0} max={40320} disabled={!editable || busy} className="mt-1 w-full rounded-lg border bg-background px-3 py-2" value={draft.phase2.reminder_minutes}
          onChange={e => setDraft({ ...draft, phase2: { ...draft.phase2!, reminder_minutes: Number(e.target.value) } })} /></label>
        <label className="block">Total project spending limit ({displayText(draft.context["comparison_currency"])})<input disabled={!editable || busy} className="mt-1 w-full rounded-lg border bg-background px-3 py-2" value={draft.phase2.purchasing_limit ?? ""}
          onChange={e => setDraft({ ...draft, phase2: { ...draft.phase2!, purchasing_limit: e.target.value || null } })} /></label>
        <label className="block"><input type="checkbox" disabled={!editable || busy} checked={draft.phase2.allow_single_offer}
          onChange={e => setDraft({ ...draft, phase2: { ...draft.phase2!, allow_single_offer: e.target.checked } })} /> Permit a sole qualifying offer</label>
      </section>}
      {editable && draft.phase2 && <section className="space-y-2 rounded border p-2 text-sm">
        <label><input type="checkbox" checked={!!draft.phase3} onChange={e => setDraft({ ...draft, phase3: e.target.checked ? fulfilment : null })} /> Enable Phase 3 after PO release</label>
        {draft.phase3 && fulfilmentInputs(draft.phase3, next => setDraft({ ...draft, phase3: next }), busy)}
      </section>}
      {editable && <button disabled={busy} onClick={() => void save()} className="rounded border px-3 py-1 text-sm">Save project settings</button>}
      </div>
      <div hidden={tab!=='overview'} className="space-y-3">
      {!backend.can("workflow.edit") && <p className="text-xs">workflow.edit permission is required to save project settings.</p>}
      {!backend.can("workflow.execute") && <p className="text-xs">workflow.execute permission is required to start procurement.</p>}
      {!backend.can("workflow.approve") && <p className="text-xs">workflow.approve permission is required for supplier and fulfilment approvals.</p>}
      {startRun && <p role="status" className="text-sm">Submitted run {startRun}. Check Runs for its progress.</p>}
      <details open={!status||status.phase==='NOT_STARTED'} className="rounded-xl border bg-background p-4"><summary className="cursor-pointer text-xs font-medium">Start & release information</summary><div className="mt-3 space-y-3">
      <p className="text-sm">This workflow starts manually. No new spreadsheet row is needed. Publish and activate, then start procurement here. Runs, Agent communication and Approvals show the actual actions.</p>
      {startReason && <p role="status" className="text-sm">{displayText(startReason)}</p>}
      <button disabled={busy || !!startReason || !backend.can("workflow.execute") || !backend.session?.runtime_available} onClick={() => void start()} className="rounded border px-3 py-1 text-sm disabled:opacity-40">{busy ? "Working…" : "Start procurement"}</button>

      {notStarted && activeRelease && <p role="status" className="text-sm">{startRun ? "The submitted run has not created the project yet. Refresh status after the worker advances it." : "Ready to start. Click Start procurement to read the source sheets and create the project."}</p>}
      </div></details>
      {!status&&!busy&&<div className="rounded-xl border bg-background p-5 text-sm text-muted-foreground">Project status has not been recorded yet. Review Setup, publish and activate the workflow, then start procurement.</div>}
      </div>
      {status && <div className="space-y-4 text-sm">
        <div hidden={tab!=='overview'} className="space-y-4"><ProcurementOverview status={status}/>
        <details className="rounded-xl border bg-background p-4"><summary className="cursor-pointer text-xs font-medium">Recorded phase and counts</summary><p className="mt-2">{status.phase}</p><p className="mt-1 text-xs">{Object.entries(status.record_counts).map(([kind,count])=>`${kind}: ${count}`).join(' · ')}</p></details>
        </div>
        <div hidden={tab!=='vendors'} className="space-y-3"><h3 className="text-base font-semibold">Supplier offers & selection</h3><ProcurementVendors status={status}/><p className="text-xs text-muted-foreground">Recommendations reflect the backend comparison. An RFQ submission is separate from a qualifying quotation.</p>
        {(status.recommendations ?? []).map(r => <p key={r.scope_digest}>{r.item_ids.join(", ")}: {displayText(r.reason.replaceAll("_", " "))}{r.amount ? ` · ${r.amount} ${r.currency}` : ""}{r.quotation_id ? ` · ${r.quotation_id}` : ""}</p>)}
        {status.phase === "SHORTLIST_REVIEW" && <section className="space-y-2 rounded border p-2">
          <p className="font-medium">Review supplier shortlist</p>
          <p>Published contacts and product claims require your review. Availability and delivery are not verified quotations.</p>
          {status.candidates.map(c => <div key={c.candidate_id} className="rounded border p-2">
            <label><input type="checkbox" disabled={!c.email || busy} checked={selected.includes(c.candidate_id)}
              onChange={e => setSelected(e.target.checked ? [...selected, c.candidate_id] : selected.filter(id => id !== c.candidate_id))} /> {displayText(c.name)}</label>
            <p>{c.email ?? "No published email — cannot contact"} · {c.categories.join(", ")}</p><p>{c.assessment}</p>
            {c.evidence.map((ev, i) => <p key={i}><a href={ev.url.startsWith("https://") ? ev.url : undefined} target="_blank" rel="noreferrer" className="text-primary underline">Source</a>: {ev.quote}</p>)}
          </div>)}
          {!status.candidates.length && <p>No evidence-backed candidates found. Use a new project with supplied vendors or clearer research requirements.</p>}
          <button disabled={busy || !backend.can("workflow.approve")} className="rounded border px-2 py-1" onClick={() => void reviewSuppliers("approved")}>Approve selected suppliers</button>
          <button disabled={busy || !backend.can("workflow.approve")} className="ml-2 rounded border px-2 py-1" onClick={() => void reviewSuppliers("rejected")}>Reject shortlist</button>
        </section>}
        {!status.recommendations?.length&&<p className="rounded-xl border bg-background p-5 text-sm text-muted-foreground">No comparison recommendations recorded yet. Check the RFQs and Quotations tabs in the tracking spreadsheet.</p>}
        </div>
        <div hidden={tab!=='overview'} className="space-y-3">
        <details className="rounded-xl border bg-background p-4"><summary className="cursor-pointer text-xs font-medium">Calendar milestones · {Object.keys(status.calendar_events??{}).length}</summary>
        {Object.entries(status.calendar_events ?? {}).map(([key, id]) => <p key={key}>Calendar: {key.replaceAll("_", " ")} · {id}</p>)}
        </details>
        {status.phase === "PO_RELEASED" && !status.fulfilment_policy && <section className="space-y-2 rounded border p-2">
          <p className="font-medium">Activate Phase 3 for these existing POs</p>
          <p>Configure buyer confirmation and manager notifications. Existing POs will be reused.</p>
          {fulfilmentInputs(fulfilment, setFulfilment, busy)}
          <button disabled={busy || !backend.can("workflow.approve") || !fulfilment.buyer_email || !fulfilment.manager_email} className="rounded border px-2 py-1"
            onClick={() => void activateFulfilment()}>Activate fulfilment monitoring</button>
        </section>}
        {status.fulfilment_policy && <p>Fulfilment policy v{status.fulfilment_policy.revision} · buyer {status.fulfilment_policy.settings.buyer_email} · manager {status.fulfilment_policy.settings.manager_email}</p>}
        </div>
        <div hidden={tab!=='orders'} className="space-y-4"><h3 className="text-base font-semibold">Purchase orders & fulfilment</h3><p className="text-xs text-muted-foreground">Supplier delivery stays open until the configured buyer confirms receipt, acceptance and resolution.</p>
        {!status.orders?.length&&<p className="rounded-xl border bg-background p-5 text-muted-foreground">No purchase orders released yet.</p>}
        {(status.orders ?? []).map(po => <section key={po.po_id} className="rounded-2xl border bg-background p-5 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-2"><p className="font-semibold">{po.po_number}</p><span className="rounded-full border px-2.5 py-1 text-[10px]">{po.status.replaceAll('_',' ')}</span></div><PurchaseOrderProgress status={po.status}/>
          <div className="overflow-x-auto"><table className="w-full text-left text-xs"><thead><tr className="border-b text-muted-foreground">{['Item','Ordered','Packed','Dispatched','Delivered','Accepted','Unit'].map(h=><th key={h} className="px-2 py-2 font-medium">{h}</th>)}</tr></thead><tbody>{po.items.map(i=><tr key={i.item_id} className="border-b last:border-0">{[i.item_id,i.ordered_quantity,i.packed_quantity,i.dispatched_quantity,i.delivered_quantity,i.buyer_accepted_quantity,i.unit].map((v,index)=><td key={index} className="px-2 py-3">{v}</td>)}</tr>)}</tbody></table></div>
          {po.tracking_references.length > 0 && <p>Tracking: {po.tracking_references.join(", ")}</p>}
          {po.unresolved_exception_ids.length > 0 && <p>Unresolved exceptions: {po.unresolved_exception_ids.join(", ")}</p>}
        </section>)}
        {Object.values(status.fulfilment_review ?? {}).map((item, i) => <p key={i}>Clarification requested: {item.po_id} · {displayText(item.reason)}</p>)}
        </div>
        <div hidden={tab!=='activity'} className="space-y-3"><div className="flex flex-wrap items-center justify-between gap-3"><h3 className="text-base font-semibold">Recorded activity</h3><input aria-label="Search activity" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search events, orders or messages…" className="rounded-lg border bg-background px-3 py-2 text-xs"/></div>
        {!(status.activity??[]).length&&<p className="rounded-xl border bg-background p-5 text-muted-foreground">No fulfilment events yet. Activity appears after a valid supplier or buyer reply is processed.</p>}
        {[...(status.activity ?? [])].reverse().filter(e=>JSON.stringify(e).toLowerCase().includes(search.toLowerCase())).map(event => <article key={event.event_id} className="rounded-xl border bg-background p-4"><div className="flex flex-wrap justify-between gap-2"><p className="font-medium capitalize">{event.event_kind.replaceAll('_',' ').toLowerCase()}</p><time className="text-[10px] text-muted-foreground">{new Date(event.observed_at).toLocaleString()}</time></div><p className="mt-2 text-xs leading-5">{event.note}</p><p className="mt-2 text-[10px] text-muted-foreground">{event.actor_role} · {event.purchase_order_id}</p></article>)}
        <details className="rounded-xl border bg-background p-4"><summary className="cursor-pointer text-xs font-medium">All recorded actions & run references</summary>
        {Object.entries(status.actions).map(([name, action]) => <p key={name}>{displayText(name)}: {action.state}{action.run_id ? ` · ${action.run_id}` : ""}</p>)}
        </details></div>
        <a href="/app/approvals" className="block text-primary underline">Open action approvals</a>
      </div>}
      {error && <ApiFeedback error={error} />}
      </div>
      <div className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-t bg-background px-6 py-3"><button disabled={busy} onClick={()=>void load()} className="inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-xs hover:bg-muted disabled:opacity-50"><RefreshCw className={`h-3.5 w-3.5 ${busy?'animate-spin':''}`}/>Refresh project status</button><div className="flex items-center gap-2 text-xs">{status&&status.resources.filter(r=>r.provider==='google_sheets'&&r.resource_type==='spreadsheet').map(r=><a key={r.resource_id} href={`https://docs.google.com/spreadsheets/d/${encodeURIComponent(r.resource_id)}/edit`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-medium text-primary">Open tracking spreadsheet<ArrowUpRight className="h-3.5 w-3.5"/></a>)}</div></div>
    </DialogContent>
  </Dialog>;
}
