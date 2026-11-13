"use client";
import { displayText } from "@/lib/display-text";
import { InputError } from "@/api/feedback";
import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { Sparkles } from "lucide-react";
import { useNavigate } from "@/lib/navigation";
import { useMesh } from "@/domain/store";
import { createWorkflow } from "@/api/create-workflow";
import { api, ApiError, type PlanningJob } from "@/api/client";
import { toast } from "sonner";
import { useBackend } from "@/api/state";
import { hasWorkflowEdits } from "@/api/mapping";
import { useRef } from "react";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";
import { isInvestigationPrompt } from "@/api/investigations";
import {
  type InvestigationContextValue,
} from "@/features/investigations/InvestigationContext";
import {
  CompositionOptions,
  emptyCompositionOptions,
} from "@/features/investigations/CompositionOptions";
import { overviewStorageKey, type OverviewResult } from "@/api/overview-automation";

export default function Overview() {
  const backend = useBackend();
  const [overview, setOverview] = useState<OverviewResult | null>(null);
  const openWhenPrepared = useRef(false);
  const restoreGeneration = useRef(0);
  const navigate = useNavigate();
  const [description, setDescription] = useState("");
  const [workflowMode] = useState("auto");
  const [toolOptions, setToolOptions] = useState(emptyCompositionOptions);
  const [businessValues, setBusinessValues] = useState<Record<string, unknown>>({});
  const [evidenceContext] = useState<InvestigationContextValue>({});
  const investigationKey = useRef<{ prompt: string; key: string } | null>(null);
  const generationLock = useRef(false);
  const [planning, setPlanning] = useState(false);
  const [planningJob, setPlanningJob] = useState<PlanningJob | null>(null);
  const latestPlanningJob = useRef<PlanningJob | null>(null);
  const currentPlanningState = () => latestPlanningJob.current?.state;
  const [cancelling, setCancelling] = useState(false);
  useEffect(
    () =>
      api.subscribePlanning((job) => {
        latestPlanningJob.current = job;
        setPlanningJob(job);
      }),
    [],
  );
  const activeJob = planningJob ?? overview?.planning_job;
  const generating = planning || overview?.state === "planning";
  const cancel = async () => {
    if (!activeJob || cancelling) return;
    setCancelling(true);
    try {
      await api.cancelPlanning(activeJob.job_id);
      if (overview?.request_key) {
        setOverview(await api.overviewIntent({ operation: "get", request_key: overview.request_key }));
      }
    } catch (error) {
      setApiError(
        error instanceof Error
          ? error
          : new InputError("Cancellation could not be confirmed. Check the job status."),
      );
    } finally {
      setCancelling(false);
    }
  };
  const [apiError, setApiError] = useState<Error | null>(null);
  const overviewScope = backend.session?.overview_routing_available
    ? backend.session.auth.subject
    : undefined;
  const reviewStorage = overviewScope
    ? overviewStorageKey(overviewScope.workspace_id, overviewScope.subject_id)
    : null;
  useEffect(() => {
    let live = true;
    const generation = restoreGeneration.current;
    openWhenPrepared.current = false;
    setOverview(null);
    if (reviewStorage) {
      const key = localStorage.getItem(reviewStorage);
      if (key)
        void api
          .overviewIntent({ operation: "get", request_key: key })
          .then((value) => {
            if (live && generation === restoreGeneration.current) {
              openWhenPrepared.current = value.state === "planning";
              setOverview(value);
            }
          })
          .catch((error) => {
            if (live && generation === restoreGeneration.current) setApiError(error as Error);
          });
    }
    return () => {
      live = false;
    };
  }, [reviewStorage]);
  useEffect(() => {
    if (!openWhenPrepared.current || overview?.state !== "prepared" || !overview.composition_id)
      return;
    if (
      overview.workspace &&
      (overview.workspace.workspace_id !== overviewScope?.workspace_id ||
        overview.workspace.subject_id !== overviewScope?.subject_id)
    )
      return;
    openWhenPrepared.current = false;
    navigate({
      to: "/app/workflows/investigate",
      search: {
        connected: "1",
        composition: overview.composition_id,
        overview: overview.request_key,
      },
    });
  }, [overview, overviewScope?.workspace_id, overviewScope?.subject_id, navigate]);
  useEffect(() => {
    if (overview?.state !== "planning" || !overview.request_key) return;
    if (overview.workspace && (
      overview.workspace.workspace_id !== overviewScope?.workspace_id ||
      overview.workspace.subject_id !== overviewScope?.subject_id
    )) return;
    let live = true;
    const generation = restoreGeneration.current;
    const timer = setInterval(() => {
      void api.overviewIntent({ operation: "get", request_key: overview.request_key })
        .then((value) => {
          if (live && generation === restoreGeneration.current) setOverview(value);
        })
        .catch((error) => {
          if (live && generation === restoreGeneration.current) setApiError(error as Error);
        });
    }, 2000);
    return () => { live = false; clearInterval(timer); };
  }, [overview?.state, overview?.request_key, overview?.workspace, overviewScope?.workspace_id, overviewScope?.subject_id]);
  const communicationAnswers = useRef<{ objective: string; values: Record<string, string> }>({
    objective: "",
    values: {},
  });
  const generate = async (answers?: Record<string, string>) => {
    const prompt = description.trim();
    if (communicationAnswers.current.objective !== prompt)
      communicationAnswers.current = { objective: prompt, values: {} };
    if (answers)
      communicationAnswers.current.values = { ...communicationAnswers.current.values, ...answers };
    const resolvedValues = { ...businessValues, ...communicationAnswers.current.values };
    if (generationLock.current || generating || !prompt) return;
    generationLock.current = true;
    restoreGeneration.current++;
    latestPlanningJob.current = null;
    openWhenPrepared.current = false;
    setOverview(null);
    setPlanning(true);
    setPlanningJob(null);
    setApiError(null);
    try {
      const context = {
        generation_mode: "hierarchy",
        delegation_mode: "runtime_v1",
        execution_input_mode: "automatic",
      };
      await useBackend.getState().initialize();
      const currentBackend = useBackend.getState();
      if (currentBackend.status !== "connected")
        throw (
          currentBackend.error ??
          new InputError("Could not connect to the workflow API. Retry when it is connected.")
        );
      if (!currentBackend.can("workflow.plan"))
        throw new InputError(
          "Your current account does not have permission to generate workflows.",
        );
      if (!currentBackend.session?.planning_available)
        throw new InputError(
          "The backend has not enabled the workflow planner. Check its model configuration.",
        );
      if (currentBackend.session.overview_routing_available && workflowMode === "auto") {
        const contextKey =
          prompt +
          JSON.stringify(evidenceContext) +
          JSON.stringify(toolOptions) +
          JSON.stringify(resolvedValues);
        if (investigationKey.current?.prompt !== contextKey)
          investigationKey.current = { prompt: contextKey, key: crypto.randomUUID() };
        const key = investigationKey.current.key;
        const subject = currentBackend.session.auth.subject;
        localStorage.setItem(overviewStorageKey(subject.workspace_id, subject.subject_id), key);
        const result = await api.overviewIntent({
          operation: "prepare",
          objective: prompt,
          request_key: key,
          business_request: evidenceContext,
          user_values: resolvedValues,
          ...(toolOptions.google ? { google_connection_id: toolOptions.google } : {}),
        });
        if (result.state !== "legacy") {
          openWhenPrepared.current = true;
          setOverview(result);
          if (["clarification", "unsupported", "cancelled"].includes(result.state)) {
            setApiError(new InputError(
              result.clarifications?.map((item) => item.question).join(" ") ||
              result.questions?.join(" ") ||
              "Update your request with the needed details and generate again.",
            ));
          }
          return;
        }
      }
      if (
        isInvestigationPrompt(prompt, workflowMode) ||
        (workflowMode !== "automation" &&
          currentBackend.session?.dynamic_composition_available === true) ||
        toolOptions.packageId
      ) {
        const contextKey =
          prompt +
          JSON.stringify(evidenceContext) +
          JSON.stringify(toolOptions) +
          JSON.stringify(resolvedValues);
        if (investigationKey.current?.prompt !== contextKey)
          investigationKey.current = { prompt: contextKey, key: crypto.randomUUID() };
        const key = investigationKey.current.key;
        const doc = await api.createActionPlan({
          objective: prompt,
          request_key: key,
          automatic_inputs: true,
          business_request: evidenceContext,
          user_values: resolvedValues,
          ...(toolOptions.google ? { google_connection_id: toolOptions.google } : {}),
        });
        navigate({
          to: "/app/workflows/investigate",
          search: { connected: "1", composition: doc.composition_id },
        });
        return;
      }
      const saved = await createWorkflow({
        objective: prompt,
        context: {
          ...context,
          ...(toolOptions.google ? { google_connection_id: toolOptions.google } : {}),
        },
      });
      if (saved.existing)
        toast.info(
          "Opened the existing saved workflow for this request. Your previous revision was preserved.",
        );
      const state = useMesh.getState();
      const current = state.workflows.find(
        (workflow) => workflow.id === saved.workflow.workflow_id,
      );
      if (!current || !hasWorkflowEdits(current, state.agents))
        state.acceptWorkflow(saved.workflow);
      navigate({ to: "/app/workflows/$id", params: { id: saved.workflow.workflow_id } });
    } catch (caught) {
      if (
        (caught instanceof ApiError && caught.error.error_code === "PLANNING_CANCELLED") ||
        ["failed", "cancelled"].includes(currentPlanningState() ?? "")
      )
        investigationKey.current = null;
      setApiError(caught instanceof Error ? caught : new InputError("Workflow generation failed."));
    } finally {
      generationLock.current = false;
      setPlanning(false);
    }
  };
  return (
    <div className="w-full min-w-0 px-4 py-6 md:px-6 md:py-8">
      <motion.h1
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-3xl font-semibold tracking-tight md:text-4xl"
      >
        What should we automate today?
      </motion.h1>
      <p className="mt-2 text-sm text-muted-foreground">Turn your request into a workflow.</p>
      <section aria-label="Workflow prompt" className="mt-5 rounded-2xl border border-border-accent bg-background p-5 shadow-lift">
        <textarea
          value={description}
          disabled={generating}
          onChange={(e) => {
            setDescription(e.target.value);
            setBusinessValues({});
            setApiError(null);
          }}
          rows={4}
          className="min-h-[120px] max-h-[35dvh] w-full resize-y border-0 bg-transparent text-lg outline-none placeholder:text-muted-foreground/80"
          aria-label="Process description"
        />
        <CompositionOptions
          value={toolOptions}
          onChange={(value) => {
            setToolOptions(value);
            setBusinessValues({});
            setApiError(null);
          }}
        />
        <div className="mt-6 flex flex-wrap items-center gap-3">
          {generating && activeJob && ["queued", "running"].includes(activeJob.state) && (
            <button
              type="button"
              disabled={cancelling}
              onClick={() => void cancel()}
              className="rounded-xl border border-border px-4 py-3 text-sm disabled:opacity-40"
            >
              {cancelling ? "Cancelling…" : "Cancel generation"}
            </button>
          )}
          <button
            type="button"
            aria-busy={generating}
            aria-label={generating ? "Generating workflow" : undefined}
            disabled={generating || !description.trim()}
            onClick={() => void generate()}
            className={`ml-auto inline-flex h-12 min-w-[190px] items-center justify-center gap-2 rounded-xl bg-primary px-5 font-medium text-primary-foreground hover:bg-primary-deep ${generating ? "disabled:opacity-100" : "disabled:opacity-40"}`}
          >
            {generating ? (
              <span role="status" className="inline-flex items-center gap-1.5">
                <span className="sr-only">Generating workflow</span>
                {[0, 1, 2].map((dot) => (
                  <span
                    key={dot}
                    aria-hidden="true"
                    className="h-2 w-2 animate-bounce rounded-full bg-current motion-reduce:animate-none"
                    style={{ animationDelay: `${dot * 150}ms`, animationDuration: "1s" }}
                  />
                ))}
              </span>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                {apiError ? "Retry generation" : "Generate workflow"}
              </>
            )}
          </button>
        </div>
        {overview?.state === "planning" && !planning && (
          <p role="status" className="mt-3 text-sm text-muted-foreground">Preparing your workflow…</p>
        )}
        {planningJob && (
          <p role="status" className="mt-3 break-all text-xs text-muted-foreground">
            Generation {planningJob.state} · Job {planningJob.job_id}
          </p>
        )}
        {planningJob?.state === "cancelled" && (
          <p className="mt-1 text-xs text-muted-foreground">
            Cancellation discards the result. Model usage already incurred cannot be undone.
          </p>
        )}
        <ApiFeedback error={apiError} />

      </section>
    </div>
  );
}
