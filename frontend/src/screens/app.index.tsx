"use client";
import { useState } from "react";
import { motion } from "motion/react";
import { ArrowRight, Check, FileText, Headphones, Sparkles, Target, UserRound } from "lucide-react";
import { Link, useNavigate } from "@/lib/navigation";
import { useMesh } from "@/domain/store";
import { api } from "@/api/client";
import { useBackend } from "@/api/state";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";

const QUICK_STARTS = [
  ["Customer complaint resolution", "When a customer complaint arrives, analyse severity, look up the account, draft a reply and escalate critical cases for approval.", Headphones],
  ["Invoice review and approval", "Read an invoice, validate the supplier and amount, then request approval before posting the result.", FileText],
  ["Lead research and qualification", "Research a new lead, classify priority, and notify the sales team when follow-up is needed.", Target],
  ["Employee onboarding", "Collect the new employee details, prepare onboarding tasks, and send the welcome message after approval.", UserRound],
] as const;

export default function Overview() {
  const navigate = useNavigate();
  const create = useMesh((s) => s.createBlankWorkflow);
  const workflows = useMesh((s) => s.workflows);
  const [description, setDescription] = useState("");
  const [mode, setMode] = useState<"hierarchy" | "linear">("hierarchy");
  const [planning, setPlanning] = useState(false);
  const [apiError, setApiError] = useState<Error | null>(null);
  const backend = useBackend();
  const generate = async () => {
    const prompt = description.trim();
    if (planning || !prompt) return;
    setPlanning(true); setApiError(null);
    try {
      if (mode === "hierarchy") {
        if (!(backend.can("workflow.plan") && backend.session?.planning_available)) throw new Error("The workflow planner is unavailable.");
        const result = await api.request("plan_workflow", { objective: prompt, context: { generation_mode: "hierarchy" } });
        const saved = await api.request("save_workflow_version", { workflow_id: result.workflow.workflow_id, workflow_version: result.workflow.version, base_version: 0, workflow: result.workflow });
        useMesh.getState().acceptWorkflow(saved.workflow);
        navigate({ to: "/app/workflows/$id", params: { id: result.workflow.workflow_id } });
      } else if (backend.can("workflow.plan") && backend.session?.planning_available) {
        const result = await api.request("plan_workflow", { objective: prompt, context: { generation_mode: "linear" } });
        const saved = await api.request("save_workflow_version", { workflow_id: result.workflow.workflow_id, workflow_version: result.workflow.version, base_version: 0, workflow: result.workflow });
        useMesh.getState().acceptWorkflow(saved.workflow);
        navigate({ to: "/app/workflows/$id", params: { id: result.workflow.workflow_id } });
      } else {
        const id = create(prompt.slice(0, 80), prompt);
        navigate({ to: "/app/workflows/$id", params: { id } });
      }
    } catch (caught) { setApiError(caught instanceof Error ? caught : new Error("Workflow generation failed.")); }
    finally { setPlanning(false); }
  };
  return <div className="mx-auto max-w-6xl px-6 py-12 md:py-16">
    <motion.h1 initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="text-5xl font-semibold tracking-tight md:text-6xl">What should we automate today?</motion.h1>
    <p className="mt-3 text-lg text-muted-foreground">Describe a process in plain English. MESH drafts the agents, tools and approvals.</p>
    <section className="mt-10 rounded-3xl border border-border-accent bg-background p-6 shadow-lift md:p-7">
      <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={4} placeholder="e.g. When a customer complaint arrives, analyse severity, look up the account, draft a reply and escalate critical cases for approval." className="w-full resize-none border-0 bg-transparent text-lg outline-none placeholder:text-muted-foreground/80" aria-label="Process description" />
      <div className="mt-6 flex flex-wrap items-center gap-3"><div className="inline-flex rounded-xl border border-border p-1" role="group" aria-label="Workflow generation mode">
        <button type="button" onClick={() => setMode("hierarchy")} className={`rounded-lg px-3 py-2 text-sm ${mode === "hierarchy" ? "bg-primary/10 font-medium text-primary" : "text-muted-foreground"}`}>Master + sub-agents</button>
        <button type="button" onClick={() => setMode("linear")} className={`rounded-lg px-3 py-2 text-sm ${mode === "linear" ? "bg-primary/10 font-medium text-primary" : "text-muted-foreground"}`}>Linear steps</button>
      </div><span className="text-xs text-muted-foreground">{mode === "hierarchy" ? "Delegates work and combines results" : "Runs steps in sequence"}</span>
      <button type="button" disabled={planning || !description.trim()} onClick={() => void generate()} className="ml-auto inline-flex h-12 items-center gap-2 rounded-xl bg-primary px-5 font-medium text-primary-foreground hover:bg-primary-deep disabled:opacity-40"><Sparkles className="h-4 w-4" />{planning ? "Generating…" : "Generate workflow"}</button></div><ApiFeedback error={apiError} />
    </section>
    <section className="mt-8 rounded-2xl border border-border bg-canvas/40 p-5"><p className="font-medium">Investor demo · 2/6</p><div className="mt-3 grid gap-2 text-sm md:grid-cols-2">{["Generate a workflow from a prompt", "Edit it with an instruction", "Switch an agent's model", "Run a simulated test", "Decide a human approval", "Publish a version", "Review results in Monitoring"].map((item, index) => <span key={item} className="flex items-center gap-2"><span className={`flex h-5 w-5 items-center justify-center rounded-full text-xs ${index === 0 || index === 4 ? "bg-emerald-500 text-white" : "border border-border text-muted-foreground"}`}>{index === 0 || index === 4 ? <Check className="h-3 w-3" /> : index + 1}</span>{item}</span>)}</div></section>
    <section className="mt-8 grid gap-3 md:grid-cols-4">{QUICK_STARTS.map(([title, prompt, Icon]) => <button key={title} type="button" onClick={() => setDescription(prompt)} className="rounded-2xl border border-border p-5 text-left transition hover:border-primary hover:bg-canvas"><Icon className="h-5 w-5 text-primary" /><p className="mt-4 font-medium">{title}</p><p className="mt-1 text-xs text-muted-foreground">Use this starting point</p></button>)}</section>
    <section className="mt-12"><div className="mb-3 flex items-center justify-between"><h2 className="text-lg font-medium">Recent workflows</h2><Link to="/app/workflows" className="text-sm text-primary">View all</Link></div>{workflows.length === 0 ? <p className="rounded-xl border border-dashed border-border p-6 text-sm text-muted-foreground">Generate a workflow above to see it here.</p> : <div className="divide-y divide-border rounded-xl border border-border">{workflows.slice(0, 5).map((w) => <Link key={w.id} to="/app/workflows/$id" params={{ id: w.id }} className="flex items-center justify-between px-4 py-3 hover:bg-canvas"><span><span className="block font-medium">{w.name}</span><span className="text-xs text-muted-foreground">{w.nodes.length} steps · {w.serverVersion ? `server v${w.serverVersion}` : "local draft"}</span></span><ArrowRight className="h-4 w-4 text-primary" /></Link>)}</div>}</section>
  </div>;
}
