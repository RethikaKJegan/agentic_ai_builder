"use client";
import { useState } from "react";
import { motion } from "motion/react";
import { Plus, ArrowRight } from "lucide-react";
import { Link, useNavigate } from "@/lib/navigation";
import { useMesh } from "@/domain/store";
import { api } from "@/api/client";
import { useBackend } from "@/api/state";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";
export default function Overview() {
  const navigate = useNavigate();
  const create = useMesh((s) => s.createBlankWorkflow);
  const workflows = useMesh((s) => s.workflows);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const backend = useBackend();
  const [planning, setPlanning] = useState(false);
  const [apiError, setApiError] = useState<Error | null>(null);
  const plan = async () => {
    if (planning || !description.trim()) return;
    setPlanning(true); setApiError(null);
    try {
      const result = await api.request("plan_workflow", { objective: description.trim() });
      const saved = await api.request("save_workflow_version", { workflow_id: result.workflow.workflow_id,
        workflow_version: result.workflow.version, base_version: 0, workflow: result.workflow });
      useMesh.getState().acceptWorkflow(saved.workflow);
      navigate({ to: "/app/workflows/$id", params: { id: result.workflow.workflow_id } });
    } catch (caught) { setApiError(caught instanceof Error ? caught : new Error("Planning failed.")); }
    finally { setPlanning(false); }
  };
  const submit = () => {
    if (!name.trim()) { setError("Enter a workflow name."); return; }
    const id = create(name, description.trim());
    navigate({ to: "/app/workflows/$id", params: { id } });
  };
  return <div className="mx-auto max-w-5xl px-6 py-12 md:py-16">
    <motion.h1 initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="text-4xl font-semibold md:text-5xl">What should we automate today?</motion.h1>
    <p className="mt-3 text-muted-foreground">Start a workflow draft and build its steps visually.</p>
    <form onSubmit={(e) => { e.preventDefault(); submit(); }} className="mt-8 rounded-2xl border border-border-accent bg-background p-5 shadow-lift">
      <label htmlFor="workflow-name" className="text-sm font-medium">Workflow name</label>
      <input id="workflow-name" value={name} onChange={(e) => { setName(e.target.value); setError(""); }} placeholder="Name your workflow" maxLength={200} className="mt-2 h-11 w-full rounded-lg border border-border px-3 outline-none focus:border-primary" />
      <label htmlFor="composer" className="mt-4 block text-sm font-medium">Process description</label>
      <textarea id="composer" value={description} onChange={(e) => setDescription(e.target.value)} rows={4} placeholder="Describe the steps, decisions and approvals you want to design." className="mt-2 w-full resize-none rounded-lg border border-border px-3 py-3 outline-none focus:border-primary" />
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-muted-foreground">{backend.status === "connected" ? "Create a local draft or request a planner proposal. Save a revision to persist it on the server." : "Local drafts are saved in this browser. The workflow API is unavailable."}</p>
        {backend.can("workflow.plan") && backend.session?.planning_available && <button type="button" disabled={planning || !description.trim()} onClick={() => void plan()} className="rounded-xl border border-border px-4 py-2 text-sm disabled:opacity-40">{planning ? "Planning…" : "Plan workflow"}</button>}
        <button type="submit" className="inline-flex h-10 items-center gap-2 rounded-xl bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary-deep"><Plus className="h-4 w-4" />Create draft</button>
      </div>
      {error && <p role="alert" className="mt-2 text-sm text-destructive">{error}</p>}
      <ApiFeedback error={apiError} />
    </form>
    <section className="mt-14">
      <div className="mb-3 flex items-center justify-between"><h2 className="text-lg font-medium">Recent workflows</h2><Link to="/app/workflows" className="text-sm text-primary">View all</Link></div>
      {workflows.length === 0 ? <p className="rounded-xl border border-dashed border-border p-6 text-sm text-muted-foreground">No drafts yet. Create your first workflow above.</p> : <div className="divide-y divide-border rounded-xl border border-border">{workflows.slice(0, 5).map((w) => <Link key={w.id} to="/app/workflows/$id" params={{ id: w.id }} className="flex items-center justify-between px-4 py-3 hover:bg-canvas"><span><span className="block font-medium">{w.name}</span><span className="text-xs text-muted-foreground">{w.nodes.length} steps · {w.serverVersion ? `server v${w.serverVersion}` : "local draft"}</span></span><ArrowRight className="h-4 w-4 text-primary" /></Link>)}</div>}
    </section>
  </div>;
}
