import { displayText } from "@/lib/display-text";
import { useEffect, useState } from "react";
import { api } from "@/api/client";
import { ApiFeedback } from "./ApiFeedback";
import type { Workflow } from "@/domain/types";
import { useMesh } from "@/domain/store";
import { useBackend } from "@/api/state";
import { hasWorkflowEdits } from "@/api/mapping";
import { Link } from "@/lib/navigation";
export function LifecycleJourney({ workflow }: { workflow: Workflow }) {
  const agents = useMesh((s) => s.agents);
  const backend = useBackend();
  const dirty = hasWorkflowEdits(workflow, agents);
  const status = workflow.canonical?.status;
  const live = backend.overview[workflow.id];
  const review = backend.reviews[workflow.id];
  const exactReview = review?.workflow_version === workflow.serverVersion ? review : undefined;
  const [releaseState, setReleaseState] = useState<Awaited<ReturnType<typeof api.releaseState>>>();
  const [releaseError, setReleaseError] = useState<Error>();
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (backend.status !== "connected") return;
    let disposed = false;
    api
      .releaseState(workflow.id)
      .then((result) => {
        if (!disposed) {
          setReleaseState(result);
          setReleaseError(undefined);
        }
      })
      .catch((error) => {
        if (!disposed) {
          setReleaseState(undefined);
          setReleaseError(error instanceof Error ? error : new Error("Release state unavailable."));
        }
      });
    return () => {
      disposed = true;
    };
  }, [
    workflow.id,
    workflow.serverVersion,
    live?.release_id,
    live?.activation_state,
    backend.status,
    attempt,
  ]);
  const release =
    releaseState?.workflow_id === workflow.id &&
    (!live?.release_id || releaseState.release?.release_id === live.release_id)
      ? releaseState.release
      : null;
  const currentActive =
    release?.state === "active" && release.workflow_version === workflow.serverVersion;
  const saved = !!workflow.serverVersion && !dirty;
  const validated = saved && ["validated", "approved", "published"].includes(status ?? "");
  const approved = saved && ["approved", "published"].includes(status ?? "");
  const published = status === "published" && saved;
  const publishedVersion = live?.published_version ?? (status === "published" ? workflow.serverVersion : undefined);
  const stages: { title: string; done?: boolean; unavailable?: boolean; reason: string }[] = [
    {
      title: "Describe process",
      done: !!workflow.description,
      reason: "Describe the goal, source and expected outcome.",
    },
    {
      title: "Generate workflow",
      done: !!workflow.canonical,
      reason: "Generate from Overview, or continue a manually created draft.",
    },
    {
      title: "Review plan",
      reason: "Open Review workflow plan and confirm the proposed automation.",
    },
    {
      title: "Edit design and agents",
      reason: "Review steps, tools, branches, responsibilities and approval gates in Design.",
    },
    {
      title: "Configure integrations and triggers",
      done: !!exactReview?.ready,
      reason:
        exactReview && !exactReview.ready
          ? `Registry requirements: ${exactReview.reason_codes.join(", ")}`
          : "Review provider setup, trigger metadata and current Registry requirements. Validation checks readiness.",
    },
    {
      title: "Save revision",
      done: saved,
      reason: dirty
        ? "Save draft to persist your working changes; existing releases remain independent."
        : "Revision is confirmed by the server.",
    },
    {
      title: "Validate revision",
      done: validated,
      reason: !saved
        ? "Save the draft first."
        : "Use Prepare & Activate and resolve any validation or Registry errors.",
    },
    {
      title: "Simulate safely",
      unavailable: true,
      reason:
        "Unavailable: no supported side-effect-free runtime simulation is connected. Validation checks structure and is not a simulated run.",
    },
    {
      title: "Obtain approval",
      done: approved,
      reason: !validated
        ? "Validate first, then Submit for approval or ask an authorized approver."
        : "Prepare & Activate submits this revision and continues when the current reviewer has approval authority.",
    },
    {
      title: "Publish approved revision",
      done: published,
      reason: !approved
        ? "An approved saved revision is required."
        : "Publish explicitly; publication does not activate triggers.",
    },
    {
      title: "Activate release",
      done: currentActive,
      reason: !publishedVersion
        ? "Publish a reviewed revision first."
        : "Activate explicitly after reviewing trigger setup. Server revalidates policy and provider readiness.",
    },
    {
      title: "Execute or receive event",
      done: !!live?.latest_run_id,
      reason:
        "Use Run in this editor for the active manual release, or wait for a configured active trigger event.",
    },
    {
      title: "Monitor run",
      reason: live?.latest_run_id
        ? "Open Execution and select the recorded run."
        : "A persisted run is required.",
    },
    {
      title: "Review outputs and recovery",
      reason:
        "Inspect recorded node evidence and failures in Execution. Missing evidence does not imply completion.",
    },
  ];
  const next = dirty
    ? "Review changes, then choose Prepare & Activate."
    : !validated
      ? "Review the plan and configuration, then choose Prepare & Activate."
      : !approved
        ? "Choose Prepare & Activate to continue approval."
        : !published
          ? "Choose Prepare & Activate to publish and activate."
          : !currentActive
            ? "Review trigger setup, then choose Prepare & Activate."
            : "Use Run here to start the active release and open Execution.";
  const currentIndex = dirty
    ? 5
    : !validated
      ? 6
      : !approved
        ? 8
        : !published
          ? 9
          : !currentActive
            ? 10
            : 12;
  return (
    <details
      aria-label="Workflow lifecycle"
      className="shrink-0 border-b border-border bg-background px-4 py-3 text-xs"
    >
      <summary className="cursor-pointer font-medium text-muted-foreground">Next: {next}</summary><div className="max-h-72 overflow-y-auto pt-3">
      <p className="mt-1 text-muted-foreground">
        Draft revision:{" "}
        {workflow.serverVersion ? `v${workflow.serverVersion} · ${status}` : "browser-local"}
        {dirty ? " · Unsaved changes" : ""} · Published revision:{" "}
        {publishedVersion ? `v${publishedVersion}` : live ? "none recorded" : "not loaded"} · Release:{" "}
        {release
          ? `${release.state} · v${release.workflow_version} · ${release.trigger_binding_count} trigger bindings`
          : releaseError
            ? "state unavailable"
            : releaseState
              ? "not activated"
              : "checking"}
      </p>
      <ol aria-label="Lifecycle progress" className="mt-2 flex flex-wrap gap-2">
        {[3, 5, 6, 8, 9, 10, 12].map((i) => (
          <li
            key={i}
            aria-current={i === currentIndex ? "step" : undefined}
            className={`rounded-full border px-2 py-1 ${i === currentIndex ? "border-primary bg-highlight" : "border-border"}`}
          >
            {displayText(stages[i]!.title)} ·{" "}
            {stages[i]!.done ? "completed" : i === currentIndex ? "current" : "blocked"}
          </li>
        ))}
      </ol>
      <ApiFeedback error={releaseError} />
      {releaseError && (
        <button type="button" onClick={() => setAttempt((n) => n + 1)} className="mt-1 underline">
          Retry release state
        </button>
      )}
      <details className="mt-2">
        <summary className="cursor-pointer font-medium">Workflow lifecycle · 14 stages</summary>
        <ol className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {stages.map((s, i) => {
            const state = s.unavailable
              ? "unavailable"
              : s.done
                ? "completed"
                : i === currentIndex
                  ? "current"
                  : "blocked";
            return (
              <li
                key={s.title}
                aria-current={state === "current" ? "step" : undefined}
                className="rounded-lg border border-border p-2"
              >
                <p className="font-medium">
                  {i + 1}. {displayText(s.title)} · {state}
                </p>
                <p className="mt-1 text-muted-foreground">{displayText(s.reason)}</p>
              </li>
            );
          })}
        </ol>
        <p className="mt-2">
          Simulation is optional and unavailable; it never grants approval.{" "}
          <Link to="/app/integrations" className="text-primary underline">
            Review integrations
          </Link>{" "}
          ·{" "}
          <Link to="/app/approvals" className="text-primary underline">
            Approval queue
          </Link>{" "}
          ·{" "}
          <Link to="/app/workflows" className="text-primary underline">
            Workflows and manual runs
          </Link>
        </p>
      </details>
      </div>
    </details>
  );
}
