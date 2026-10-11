"use client";
import { useState } from "react";
import { motion } from "motion/react";
import { ArrowRight, Sparkles } from "lucide-react";
import { Link, useNavigate } from "@/lib/navigation";
import { useMesh } from "@/domain/store";
import { createWorkflow } from "@/api/create-workflow";
import { toast } from "sonner";
import { useBackend } from "@/api/state";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";

export default function Overview() {
  const navigate = useNavigate();
  const workflows = useMesh((s) => s.workflows);
  const [description, setDescription] = useState("");
  const [googleSheetsResource, setGoogleSheetsResource] = useState("");
  const [planning, setPlanning] = useState(false);
  const [apiError, setApiError] = useState<Error | null>(null);
  const backend = useBackend();
  const generate = async () => {
    const prompt = description.trim();
    if (planning || !prompt) return;
    setPlanning(true); setApiError(null);
    try {
      const needsGoogleSheet = /google\s*sheets?|spreadsheet|\bnew\s+row\b/i.test(prompt);
      if (needsGoogleSheet && !googleSheetsResource.trim()) {
        throw new Error("Paste the Google Sheets URL or spreadsheet ID that this workflow should watch.");
      }
      const context = {
        generation_mode: "hierarchy",
        ...(googleSheetsResource.trim() ? { google_sheets_resource: googleSheetsResource.trim() } : {}),
      };
      if (!(backend.can("workflow.plan") && backend.session?.planning_available)) throw new Error("The workflow planner is unavailable.");
      const saved = await createWorkflow({ objective: prompt, context });
      if (saved.existing) toast.info("Opened the existing saved workflow for this request. Your previous revision was preserved.");
      useMesh.getState().acceptWorkflow(saved.workflow);
      navigate({ to: "/app/workflows/$id", params: { id: saved.workflow.workflow_id } });
    } catch (caught) { setApiError(caught instanceof Error ? caught : new Error("Workflow generation failed.")); }
    finally { setPlanning(false); }
  };
  return <div className="mx-auto max-w-6xl px-6 py-12 md:py-16">
    <motion.h1 initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="text-5xl font-semibold tracking-tight md:text-6xl">What should we automate today?</motion.h1>
    <p className="mt-3 text-lg text-muted-foreground">Describe a process in plain English. MESH drafts the agents, tools and approvals.</p>
    <section className="mt-10 rounded-3xl border border-border-accent bg-background p-6 shadow-lift md:p-7">
      <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={4} placeholder="e.g. When a customer complaint arrives, analyse severity, look up the account, draft a reply and escalate critical cases for approval." className="w-full resize-none border-0 bg-transparent text-lg outline-none placeholder:text-muted-foreground/80" aria-label="Process description" />
      <label className="mt-4 block text-sm font-medium text-foreground">Google Sheets URL or ID <span className="font-normal text-muted-foreground">(required only for a new-row workflow)</span>
        <input value={googleSheetsResource} onChange={(e) => setGoogleSheetsResource(e.target.value)} placeholder="https://docs.google.com/spreadsheets/d/..." className="mt-2 block w-full rounded-lg border border-border bg-canvas px-3 py-2 text-sm font-normal outline-none placeholder:text-muted-foreground focus:border-primary" aria-label="Google Sheets URL or ID" />
      </label>
      <div className="mt-6 flex flex-wrap items-center gap-3">
      <button type="button" disabled={planning || !description.trim()} onClick={() => void generate()} className="ml-auto inline-flex h-12 items-center gap-2 rounded-xl bg-primary px-5 font-medium text-primary-foreground hover:bg-primary-deep disabled:opacity-40"><Sparkles className="h-4 w-4" />{planning ? "Generating…" : "Generate workflow"}</button></div><ApiFeedback error={apiError} />
    </section>
    <section className="mt-12"><div className="mb-3 flex items-center justify-between"><h2 className="text-lg font-medium">Recent workflows</h2><Link to="/app/workflows" className="text-sm text-primary">View all</Link></div>{workflows.length === 0 ? <p className="rounded-xl border border-dashed border-border p-6 text-sm text-muted-foreground">Generate a workflow above to see it here.</p> : <div className="divide-y divide-border rounded-xl border border-border">{workflows.slice(0, 5).map((w) => <Link key={w.id} to="/app/workflows/$id" params={{ id: w.id }} className="flex items-center justify-between px-4 py-3 hover:bg-canvas"><span><span className="block font-medium">{w.name}</span><span className="text-xs text-muted-foreground">{w.nodes.length} steps · {w.serverVersion ? `server v${w.serverVersion}` : "local draft"}</span></span><ArrowRight className="h-4 w-4 text-primary" /></Link>)}</div>}</section>
  </div>;
}
