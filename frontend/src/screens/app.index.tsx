"use client";
import { InputError } from "@/api/feedback";
import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { ArrowRight, Sparkles } from "lucide-react";
import { Link, useNavigate } from "@/lib/navigation";
import { useMesh } from "@/domain/store";
import { createWorkflow } from "@/api/create-workflow";
import { api, type PlanningJob } from "@/api/client";
import { toast } from "sonner";
import { useBackend } from "@/api/state";
import { hasWorkflowEdits } from "@/api/mapping";
import { useRef } from "react";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";

export default function Overview() {
  const navigate = useNavigate();
  const workflows = useMesh((s) => s.workflows);
  const [description, setDescription] = useState("");
  const generationLock = useRef(false);
  const [planning, setPlanning] = useState(false);
  const [planningJob, setPlanningJob] = useState<PlanningJob | null>(null);
  const [cancelling, setCancelling] = useState(false);
  useEffect(() => api.subscribePlanning(setPlanningJob), []);
  const cancel = async () => {
    if (!planningJob || cancelling) return;
    setCancelling(true);
    try { await api.cancelPlanning(planningJob.job_id); }
    catch (error) { setApiError(error instanceof Error ? error : new InputError("Cancellation could not be confirmed. Check the job status.")); }
    finally { setCancelling(false); }
  };
  const [apiError, setApiError] = useState<Error | null>(null);
  const generate = async () => {
    const prompt = description.trim();
    if (generationLock.current || !prompt) return;
    generationLock.current = true;
    setPlanning(true); setPlanningJob(null); setApiError(null);
    try {
      const context = {
        generation_mode: "hierarchy",
        delegation_mode: "runtime_v1",
        execution_input_mode: "automatic",
      };
      await useBackend.getState().initialize();
      const currentBackend = useBackend.getState();
      if (currentBackend.status !== "connected") throw currentBackend.error ?? new InputError("Could not connect to the workflow API. Retry when it is connected.");
      if (!currentBackend.can("workflow.plan")) throw new InputError("Your current account does not have permission to generate workflows.");
      if (!currentBackend.session?.planning_available) throw new InputError("The backend has not enabled the workflow planner. Check its model configuration.");
      const saved = await createWorkflow({ objective: prompt, context });
      if (saved.existing) toast.info("Opened the existing saved workflow for this request. Your previous revision was preserved.");
      const state = useMesh.getState();
      const current = state.workflows.find(workflow => workflow.id === saved.workflow.workflow_id);
      if (!current || !hasWorkflowEdits(current, state.agents)) state.acceptWorkflow(saved.workflow);
      navigate({to: "/app/workflows/$id", params: {id: saved.workflow.workflow_id}});
    } catch (caught) { setApiError(caught instanceof Error ? caught : new InputError("Workflow generation failed.")); }
    finally { generationLock.current = false; setPlanning(false); }
  };
  return <div className="mx-auto max-w-6xl px-6 py-12 md:py-16">
    <motion.h1 initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="text-5xl font-semibold tracking-tight md:text-6xl">What should we automate today?</motion.h1>
    <p className="mt-3 text-lg text-muted-foreground">Describe your requirement in one prompt. MESH uses available sources and knowledge to draft the workflow, agents, tools and approvals.</p>
    <section className="mt-10 rounded-3xl border border-border-accent bg-background p-6 shadow-lift md:p-7">
          <textarea value={description} disabled={planning} onChange={(e) => setDescription(e.target.value)} rows={4} placeholder="e.g. When a customer complaint arrives, analyse severity, look up the account, draft a reply and escalate critical cases for approval." className="w-full resize-none border-0 bg-transparent text-lg outline-none placeholder:text-muted-foreground/80" aria-label="Process description" />
      <p className="mt-4 text-sm text-muted-foreground">Describe what you need. MESH identifies relevant connected sources and saved knowledge automatically. Include any additional source links or details in your prompt.</p>
      <div className="mt-6 flex flex-wrap items-center gap-3">
      {planning && planningJob && ["queued", "running"].includes(planningJob.state) &&
        <button type="button" disabled={cancelling} onClick={() => void cancel()} className="rounded-xl border border-border px-4 py-3 text-sm disabled:opacity-40">{cancelling ? "Cancelling…" : "Cancel generation"}</button>}
      <button type="button" disabled={planning || !description.trim()} onClick={() => void generate()} className="ml-auto inline-flex h-12 items-center gap-2 rounded-xl bg-primary px-5 font-medium text-primary-foreground hover:bg-primary-deep disabled:opacity-40"><Sparkles className="h-4 w-4" />{planning ? "Generating…" : apiError ? "Retry generation" : "Generate workflow"}</button></div>
      {planningJob && <p role="status" className="mt-3 break-all text-xs text-muted-foreground">Generation {planningJob.state} · Job {planningJob.job_id}</p>}
      {planningJob?.state === "cancelled" && <p className="mt-1 text-xs text-muted-foreground">Cancellation discards the result. Model usage already incurred cannot be undone.</p>}
      <ApiFeedback error={apiError} />
    </section>
    <section className="mt-12"><div className="mb-3 flex items-center justify-between"><h2 className="text-lg font-medium">Recent workflows</h2><Link to="/app/workflows" className="text-sm text-primary">View all</Link></div>{workflows.length === 0 ? <p className="rounded-xl border border-dashed border-border p-6 text-sm text-muted-foreground">Generate a workflow above to see it here.</p> : <div className="divide-y divide-border rounded-xl border border-border">{workflows.slice(0, 5).map((w) => <Link key={w.id} to="/app/workflows/$id" params={{ id: w.id }} className="flex items-center justify-between px-4 py-3 hover:bg-canvas"><span><span className="block font-medium">{w.name}</span><span className="text-xs text-muted-foreground">{w.nodes.length} steps · {w.serverVersion ? `server v${w.serverVersion}` : "local draft"}</span></span><ArrowRight className="h-4 w-4 text-primary" /></Link>)}</div>}</section>
  </div>;
}
