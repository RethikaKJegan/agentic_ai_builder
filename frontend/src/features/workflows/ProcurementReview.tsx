"use client";
import { useEffect, useState } from "react";
import { api, ApiError } from "@/api/client";
import { useBackend } from "@/api/state";
import { useMesh } from "@/domain/store";
import type { Workflow } from "@/domain/types";
import { ApiFeedback } from "./ApiFeedback";

type Plan = { project_id: string; name: string; simulation: boolean;
  context: Record<string, string | null>; requirements: { spreadsheet_url: string; range: string; columns: Record<string, string> };
  vendors: { spreadsheet_url: string; range: string; columns: Record<string, string> } | null;
  supplier_mode?: "supplied" | "discover" | "combined"; search_region?: string; action_mode?: "approval" | "automatic";
  phase2?: { enabled: true; calendar_id: string; reminder_minutes: number; purchasing_limit: string | null; allow_single_offer: boolean } | null };
export function ProcurementReview({ workflow }: { workflow: Workflow }) {
  const backend = useBackend();
  const raw = workflow.canonical?.metadata["procurement_plan"];
  const plan = raw && typeof raw === "object" && "project_id" in raw ? raw as Plan : null;
  const [draft, setDraft] = useState<Plan | null>(plan);
  const [status, setStatus] = useState<Awaited<ReturnType<typeof api.procurementStatus>>>();
  const [error, setError] = useState<Error>();
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);
  const [notStarted, setNotStarted] = useState(false);
  useEffect(() => { setDraft(plan); }, [raw]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!plan || !draft) return null;
  const editable = workflow.canonical?.status === "draft" || workflow.canonical?.status === "validated";
  const publishedVersion = backend.overview[workflow.id]?.published_version;
  const start = async () => {
    if (busy || !publishedVersion) return;
    setBusy(true); setError(undefined);
    try {
      await api.request("execute_workflow", { workflow_id: workflow.id, workflow_version: publishedVersion, inputs: {} }, crypto.randomUUID());
      setStatus(await api.procurementStatus(plan.project_id));
      setNotStarted(false);
    } catch (e) { setError(e instanceof Error ? e : new Error("Procurement could not be started.")); }
    finally { setBusy(false); }
  };
  const load = async () => {
    setError(undefined);
    setBusy(true);
    try {
      // Recover the session/capabilities after a local backend restart.
      await backend.initialize();
      setStatus(await api.procurementStatus(plan.project_id));
      setNotStarted(false);
    } catch (e) {
      const absent = e instanceof ApiError && e.error.error_code === "PROCUREMENT_PROJECT_NOT_FOUND";
      setNotStarted(absent);
      setError(absent ? undefined : e instanceof Error ? e : new Error("Could not load procurement status."));
    } finally { setBusy(false); }
  };
  const save = async () => {
    if (!workflow.canonical || busy) return;
    setBusy(true); setError(undefined);
    try {
      const document = structuredClone(workflow.canonical);
      document.version = (workflow.serverVersion ?? document.version) + 1;
      document.status = "draft";
      document.metadata["procurement_plan"] = draft;
      const result = await api.request("save_workflow_version", { workflow_id: document.workflow_id,
        workflow_version: document.version, base_version: workflow.serverVersion ?? 0, workflow: document });
      useMesh.getState().acceptWorkflow(result.workflow);
    } catch (e) { setError(e instanceof Error ? e : new Error("Could not save project settings.")); }
    finally { setBusy(false); }
  };
  const reviewSuppliers = async (decision: "approved" | "rejected") => {
    if (!status?.shortlist_digest || busy) return;
    setBusy(true); setError(undefined);
    try {
      await api.procurementSuppliersReview(plan.project_id, decision, selected, status.shortlist_digest);
      setStatus(await api.procurementStatus(plan.project_id));
    } catch (e) { setError(e instanceof Error ? e : new Error("Supplier selection could not be saved.")); }
    finally { setBusy(false); }
  };
  return <details className="relative">
    <summary className="cursor-pointer rounded-lg border px-2.5 py-1 text-sm">Procurement setup &amp; status</summary>
    <div className="fixed inset-x-3 top-36 z-40 max-h-[70vh] sm:absolute sm:inset-x-auto sm:right-0 sm:top-10 sm:max-h-[75vh] sm:w-[min(30rem,90vw)] space-y-3 overflow-y-auto rounded-xl border bg-background p-4 shadow-lg">
      <div className="flex items-center justify-between gap-2">
        <p className="font-medium">{draft.name}</p>
        <button className="rounded border px-2 py-1 text-xs" onClick={e => e.currentTarget.closest("details")?.removeAttribute("open")}>Close project setup</button>
      </div>
      <p className="text-sm">Review source mappings and project terms before publishing. {draft.action_mode === "automatic"
        ? "Publication authorizes automatic supplier selection, tracking writes, drafts and RFQ sends for this project."
        : "Each spreadsheet write, Gmail draft and RFQ send has its own approval."}</p>
      <p className="text-sm">{draft.simulation ? "Simulation project" : "Real procurement project"}</p>
      <p className="text-sm">Supplier mode: {draft.supplier_mode ?? "supplied"}{draft.supplier_mode !== "supplied" && draft.supplier_mode ? " · DDGS keyless research" : ""}</p>
      {(["requirements", "vendors"] as const).map(kind => { const source = draft[kind]; return source ? <div key={kind} className="text-sm">
        <p className="font-medium capitalize">{kind}</p><p className="break-all">{source.spreadsheet_url}</p>
        <label className="block">Table range<input disabled={!editable} className="mt-1 w-full rounded border p-1" value={source.range}
          onChange={e => setDraft({ ...draft, [kind]: { ...source, range: e.target.value } })} /></label>
        {Object.entries(source.columns).map(([field, header]) => <label key={field} className="mt-1 flex items-center justify-between gap-2">
          <span>{field}</span><input disabled={!editable} className="w-1/2 rounded border p-1" value={header}
            onChange={e => setDraft({ ...draft, [kind]: { ...source, columns: { ...source.columns, [field]: e.target.value } } })} /></label>)}
      </div> : null; })}
      {Object.entries(draft.context).map(([field, value]) => <label key={field} className="block text-sm">
        {field.replaceAll("_", " ")}<input disabled={!editable} className="mt-1 w-full rounded border p-1" value={value ?? ""}
          placeholder="Required project information" onChange={e => setDraft({ ...draft, context: { ...draft.context, [field]: e.target.value || null } })} />
      </label>)}
      {draft.phase2 && <section className="space-y-2 rounded border p-2 text-sm">
        <p className="font-medium">Quotation comparison and purchase orders</p>
        <p>{draft.action_mode === "automatic" ? "Automatic simulation awards and PO release use the published project spending limit." : "Award and PO emails require action approval."}</p>
        <label className="block">Calendar<input disabled={!editable} className="w-full rounded border p-1" value={draft.phase2.calendar_id}
          onChange={e => setDraft({ ...draft, phase2: { ...draft.phase2!, calendar_id: e.target.value } })} /></label>
        <label className="block">Reminder minutes<input type="number" min={0} max={40320} disabled={!editable} className="w-full rounded border p-1" value={draft.phase2.reminder_minutes}
          onChange={e => setDraft({ ...draft, phase2: { ...draft.phase2!, reminder_minutes: Number(e.target.value) } })} /></label>
        <label className="block">Total project spending limit ({draft.context["comparison_currency"]})<input disabled={!editable} className="w-full rounded border p-1" value={draft.phase2.purchasing_limit ?? ""}
          onChange={e => setDraft({ ...draft, phase2: { ...draft.phase2!, purchasing_limit: e.target.value || null } })} /></label>
        <label className="block"><input type="checkbox" disabled={!editable} checked={draft.phase2.allow_single_offer}
          onChange={e => setDraft({ ...draft, phase2: { ...draft.phase2!, allow_single_offer: e.target.checked } })} /> Permit a sole qualifying offer</label>
      </section>}
      {editable && <button disabled={busy} onClick={() => void save()} className="rounded border px-3 py-1 text-sm">Save project settings</button>}
      <p className="text-sm">This workflow starts manually. No new spreadsheet row is needed. Publish, then start procurement here. Runs, Agent communication and Approvals show the actual actions.</p>
      <button disabled={busy || !publishedVersion || !backend.can("workflow.execute")} onClick={() => void start()} className="rounded border px-3 py-1 text-sm disabled:opacity-40">{busy ? "Working…" : "Start procurement"}</button>
      <button disabled={busy} onClick={() => void load()} className="rounded border px-3 py-1 text-sm">Refresh project status</button>
      {notStarted && <p role="status" className="text-sm">Ready to start. Click Start procurement to read the source sheets and create the project.</p>}
      {status && <div className="space-y-2 text-sm"><p className="font-medium">{status.phase}</p>
        <p>{Object.entries(status.record_counts).map(([kind, count]) => `${kind}: ${count}`).join(" · ")}</p>
        {status.issues.map(issue => <p key={issue}>{issue}</p>)}
        {(status.recommendations ?? []).map(r => <p key={r.scope_digest}>{r.item_ids.join(", ")}: {r.reason.replaceAll("_", " ")}{r.amount ? ` · ${r.amount} ${r.currency}` : ""}{r.quotation_id ? ` · ${r.quotation_id}` : ""}</p>)}
        {Object.entries(status.calendar_events ?? {}).map(([key, id]) => <p key={key}>Calendar: {key.replaceAll("_", " ")} · {id}</p>)}
        {status.phase === "SHORTLIST_REVIEW" && <section className="space-y-2 rounded border p-2">
          <p className="font-medium">Review supplier shortlist</p>
          <p>Published contacts and product claims require your review. Availability and delivery are not verified quotations.</p>
          {status.candidates.map(c => <div key={c.candidate_id} className="rounded border p-2">
            <label><input type="checkbox" disabled={!c.email || busy} checked={selected.includes(c.candidate_id)}
              onChange={e => setSelected(e.target.checked ? [...selected, c.candidate_id] : selected.filter(id => id !== c.candidate_id))} /> {c.name}</label>
            <p>{c.email ?? "No published email — cannot contact"} · {c.categories.join(", ")}</p><p>{c.assessment}</p>
            {c.evidence.map((ev, i) => <p key={i}><a href={ev.url.startsWith("https://") ? ev.url : undefined} target="_blank" rel="noreferrer" className="text-primary underline">Source</a>: {ev.quote}</p>)}
          </div>)}
          {!status.candidates.length && <p>No evidence-backed candidates found. Use a new project with supplied vendors or clearer research requirements.</p>}
          <button disabled={busy || !backend.can("workflow.approve")} className="rounded border px-2 py-1" onClick={() => void reviewSuppliers("approved")}>Approve selected suppliers</button>
          <button disabled={busy || !backend.can("workflow.approve")} className="ml-2 rounded border px-2 py-1" onClick={() => void reviewSuppliers("rejected")}>Reject shortlist</button>
        </section>}
        {status.resources.filter(r => r.provider === "google_sheets" && r.resource_type === "spreadsheet").map(r =>
          <a className="block text-primary underline" key={r.resource_id} href={`https://docs.google.com/spreadsheets/d/${encodeURIComponent(r.resource_id)}/edit`} target="_blank" rel="noreferrer">Open tracking spreadsheet</a>)}
        {Object.entries(status.actions).map(([name, action]) => <p key={name}>{name}: {action.state}{action.run_id ? ` · ${action.run_id}` : ""}</p>)}
        <a href="/app/approvals" className="block text-primary underline">Open action approvals</a>
      </div>}
      {error && <ApiFeedback error={error} />}
    </div>
  </details>;
}
