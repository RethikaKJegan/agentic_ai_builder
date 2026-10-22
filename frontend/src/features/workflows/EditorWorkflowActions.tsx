"use client";
import { useEffect, useRef, useState } from "react";
import { api, type RunRecord } from "@/api/client";
import { useBackend } from "@/api/state";
import { useMesh } from "@/domain/store";
import { hasWorkflowEdits, toCanonical } from "@/api/mapping";
import { assertWorkflowReferences } from "@/api/control";
import { InputError } from "@/api/feedback";
import type { CanonicalWorkflow } from "@/api/contracts.generated";
import type { Workflow } from "@/domain/types";
import { acceptConfirmed, editSnapshot } from "./workflow-state";
import { ApiFeedback } from "./ApiFeedback";
import { RunWorkflowDialog } from "./RunWorkflowDialog";
import { SheetAccessReview } from "./SheetAccessReview";
import { CustomerAutomationReview } from "./CustomerAutomationReview";
import { ProcurementReview } from "./ProcurementReview";

type Release = Awaited<ReturnType<typeof api.releaseState>>["release"];
const stages = ["Saved", "Validated", "Approved", "Published", "Active"] as const;
type Stage = (typeof stages)[number];
export function EditorWorkflowActions({
  workflow,
  onStarted,
  onExecution,
}: {
  workflow: Workflow;
  onStarted: (run: RunRecord) => void;
  onExecution: () => void;
}) {
  const backend = useBackend();
  const agents = useMesh((state) => state.agents);
  const [release, setRelease] = useState<Release>();
  const [releaseError, setReleaseError] = useState<Error>();
  const [busy, setBusy] = useState("");
  const lock = useRef(false);
  const [error, setError] = useState<Error>();
  const [message, setMessage] = useState("");
  const [progress, setProgress] = useState<Partial<Record<Stage, string>>>({});
  const [runDocument, setRunDocument] = useState<CanonicalWorkflow>();
  const runRelease = useRef<string | undefined>(undefined);
  const [attempt, setAttempt] = useState(0);
  const dirty = hasWorkflowEdits(workflow, agents);
  const releaseId = backend.overview[workflow.id]?.release_id;
  const activationState = backend.overview[workflow.id]?.activation_state;
  useEffect(() => {
    let alive = true;
    if (backend.status !== "connected") return;
    void (
      workflow.serverVersion ? api.releaseState(workflow.id) : Promise.resolve({ release: null })
    )
      .then((result) => {
        if (alive) {
          setRelease(result.release);
          setReleaseError(undefined);
        }
      })
      .catch((caught) => {
        if (alive) {
          setRelease(undefined);
          setReleaseError(
            caught instanceof Error ? caught : new Error("Release state unavailable."),
          );
        }
      });
    return () => {
      alive = false;
    };
  }, [workflow.id, workflow.serverVersion, backend.status, releaseId, activationState, attempt]);
  const active = release?.state === "active" ? release : undefined;
  const currentActive = !!active && !dirty && active.workflow_version === workflow.serverVersion;
  const requirePermission = (permission: string) => {
    if (!useBackend.getState().can(permission))
      throw new InputError(`${permission} permission is required to continue.`);
  };
  const current = () => {
    const state = useMesh.getState();
    return { state, item: state.workflows.find((item) => item.id === workflow.id) ?? workflow };
  };
  const confirmUnedited = () => {
    const { state, item } = current();
    if (item.remote || hasWorkflowEdits(item, state.agents))
      throw new InputError(
        "The draft changed during preparation. Changes are retained. Review them, then choose Activate changes.",
      );
  };
  const mark = (stage: Stage, value: string) => setProgress((old) => ({ ...old, [stage]: value }));
  const prepare = async () => {
    if (lock.current) return;
    lock.current = true;
    setBusy("prepare");
    setError(undefined);
    setMessage("");
    setProgress({});
    try {
      requirePermission("workflow.view");
      let { state, item } = current();
      if (item.remote)
        throw new InputError("Resolve the newer server revision before preparing this draft.");
      const initialRelease = item.serverVersion
        ? await api.releaseState(workflow.id)
        : { release: null };
      setRelease(initialRelease.release);
      let document: CanonicalWorkflow | undefined = item.canonical;
      if (item.serverVersion) {
        const result = await api.request("get_workflow", { workflow_id: workflow.id });
        if (result.workflow.version !== item.serverVersion) {
          useMesh.getState().observeWorkflows([result.workflow]);
          throw new InputError(
            "A newer saved revision exists. Review the server revision before continuing.",
          );
        }
        if (!hasWorkflowEdits(item, state.agents))
          acceptConfirmed(result.workflow, editSnapshot(item, state.agents));
        document = result.workflow;
        if (result.registry_review) backend.acceptReview(result.registry_review);
      }
      ({ state, item } = current());
      if (hasWorkflowEdits(item, state.agents) || !item.serverVersion) {
        requirePermission("workflow.edit");
        mark("Saved", "running");
        assertWorkflowReferences(toCanonical(item, state.agents));
        const snapshot = editSnapshot(item, state.agents);
        const result = await api.request("save_workflow_version", {
          workflow_id: item.id,
          workflow_version: (item.serverVersion ?? 0) + 1,
          base_version: item.serverVersion ?? 0,
          workflow: toCanonical(item, state.agents),
        });
        acceptConfirmed(result.workflow, snapshot);
        document = result.workflow;
        if (result.registry_review) backend.acceptReview(result.registry_review);
      }
      if (!document) throw new InputError("Save the workflow before activation.");
      const version = document.version;
      mark("Saved", "done");
      confirmUnedited();
      const transition = async (
        operation: "validate_workflow" | "approve_workflow",
        stage: Stage,
        expected: CanonicalWorkflow["status"],
        action?: "approve" | "publish",
      ) => {
        confirmUnedited();
        mark(stage, "running");
        const { state, item } = current();
        const snapshot = editSnapshot(item, state.agents);
        const ref = { workflow_id: workflow.id, workflow_version: version };
        const result =
          operation === "validate_workflow"
            ? await api.request(operation, ref)
            : await api.request(operation, { ...ref, action: action! });
        if (result.workflow.workflow_id !== workflow.id || result.workflow.version !== version)
          throw new InputError(
            "The server returned a different revision. Refresh before continuing.",
          );
        acceptConfirmed(result.workflow, snapshot);
        if (result.registry_review) backend.acceptReview(result.registry_review);
        document = result.workflow;
        if (document.status !== expected)
          throw new InputError(
            `${stage} could not be confirmed. Resolve the validation and Registry requirements before continuing.`,
          );
        mark(stage, "done");
        confirmUnedited();
      };
      if (document.status === "draft") {
        requirePermission("workflow.validate");
        await transition("validate_workflow", "Validated", "validated");
      } else mark("Validated", "done");
      if (document.status === "validated") {
        if (!document.metadata["approval_submission"]) {
          requirePermission("workflow.validate");
          mark("Approved", "Awaiting approval");
          const { state, item } = current();
          const snapshot = editSnapshot(item, state.agents);
          const result = await api.submitApproval({
            workflow_id: workflow.id,
            workflow_version: version,
          });
          if (result.workflow.version !== version || result.workflow.workflow_id !== workflow.id)
            throw new InputError("Approval submission returned a different revision.");
          acceptConfirmed(result.workflow, snapshot);
          document = result.workflow;
          confirmUnedited();
        }
        if (!useBackend.getState().can("workflow.approve")) {
          mark("Approved", "Awaiting approval");
          setMessage(
            `Awaiting an authorized reviewer for v${version}. Review and continue here after approval.`,
          );
          return;
        }
        requirePermission("workflow.approve");
        await transition("approve_workflow", "Approved", "approved", "approve");
      } else mark("Approved", "done");
      if (document.status === "approved") {
        requirePermission("workflow.publish");
        requirePermission("workflow.approve");
        await transition("approve_workflow", "Published", "published", "publish");
      } else if (document.status === "published") mark("Published", "done");
      else throw new InputError("A published revision is required for activation.");
      confirmUnedited();
      requirePermission("workflow.publish");
      mark("Active", "running");
      if (
        initialRelease.release?.state === "active" &&
        initialRelease.release.workflow_version === version
      ) {
        mark("Active", "done");
        setMessage("");
        return;
      }
      const result = await api.activateRelease({
        workflow_id: workflow.id,
        workflow_version: version,
        expected_release_id:
          initialRelease.release?.state === "active" ? initialRelease.release.release_id : null,
        triggers: [],
      });
      const confirmed = await api.releaseState(workflow.id);
      setRelease(confirmed.release);
      if (
        result.operation.state !== "succeeded" ||
        confirmed.release?.state !== "active" ||
        confirmed.release.workflow_version !== version ||
        confirmed.release.release_id !== result.release.release_id
      )
        throw new InputError(
          "Activation is not confirmed active. Refresh release status before continuing.",
        );
      mark("Active", "done");
      setMessage("");
    } catch (caught) {
      setProgress((old) =>
        Object.fromEntries(
          Object.entries(old).map(([key, value]) => [key, value === "running" ? "failed" : value]),
        ),
      );
      setError(caught instanceof Error ? caught : new Error("Preparation could not be confirmed."));
    } finally {
      lock.current = false;
      setBusy("");
      await backend.refreshOverview();
      setAttempt((value) => value + 1);
    }
  };
  const openRun = async () => {
    if (lock.current) return;
    lock.current = true;
    setBusy("run");
    setError(undefined);
    try {
      requirePermission("workflow.execute");
      if (!useBackend.getState().session?.runtime_available)
        throw new InputError("The runtime is unavailable.");
      const currentRelease = await api.releaseState(workflow.id);
      setRelease(currentRelease.release);
      if (currentRelease.release?.state !== "active")
        throw new InputError("Activate a release before running this workflow.");
      const result = await api.request("get_workflow", {
        workflow_id: workflow.id,
        workflow_version: currentRelease.release.workflow_version,
      });
      if (
        result.workflow.status !== "published" ||
        result.workflow.version !== currentRelease.release.workflow_version ||
        result.workflow.workflow_id !== workflow.id
      )
        throw new InputError("The active revision could not be confirmed.");
      runRelease.current = currentRelease.release.release_id;
      setRunDocument(result.workflow);
    } catch (caught) {
      setError(caught instanceof Error ? caught : new Error("Active release could not be loaded."));
    } finally {
      lock.current = false;
      setBusy("");
    }
  };
  const reload = async () => {
    if (lock.current) return;
    if (dirty && !window.confirm("Reload the saved revision and discard these unsaved changes?"))
      return;
    lock.current = true;
    setBusy("reload");
    setError(undefined);
    try {
      requirePermission("workflow.view");
      const { state, item } = current();
      const snapshot = editSnapshot(item, state.agents);
      const result = await api.request("get_workflow", { workflow_id: workflow.id });
      const now = current();
      if (editSnapshot(now.item, now.state.agents) !== snapshot)
        throw new InputError("The draft changed while loading. Changes were retained.");
      useMesh.getState().acceptWorkflow(result.workflow);
      setAttempt((v) => v + 1);
    } catch (caught) {
      setError(caught instanceof Error ? caught : new Error("Reload failed."));
    } finally {
      lock.current = false;
      setBusy("");
    }
  };
  return (
    <section
      aria-label="Workflow launch actions"
      className="flex min-w-0 flex-wrap items-center gap-2"
    >
      <span className="text-[11px] text-muted-foreground">
        Editing {workflow.serverVersion ? `v${workflow.serverVersion}` : "new draft"}
        {dirty ? " · Unsaved changes" : ""} ·{" "}
        {active ? `Active v${active.workflow_version}` : "No active release"}
      </span>
      <ProcurementReview workflow={workflow} onStarted={onExecution} />
      <SheetAccessReview targets={workflow.canonical?.metadata["sheet_write_targets"]} />
      <CustomerAutomationReview
        policy={workflow.canonical?.metadata["customer_automation"]}
        emailPolicy={workflow.canonical?.metadata["email_recipient_policy"]}
      />
      {currentActive ? (
        <span className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-medium text-emerald-800">
          Active · v{active.workflow_version}
        </span>
      ) : (
        <button
          disabled={
            !!busy ||
            !!runDocument ||
            backend.status !== "connected" ||
            !backend.can("workflow.view")
          }
          onClick={() => void prepare()}
          className="rounded-lg bg-primary px-3 py-2 text-xs font-medium text-primary-foreground disabled:opacity-40"
        >
          {busy === "prepare" ? "Preparing…" : active ? "Activate changes" : "Prepare & Activate"}
        </button>
      )}
      <button
        disabled={
          !!busy ||
          !!runDocument ||
          !active ||
          !backend.can("workflow.execute") ||
          !backend.session?.runtime_available
        }
        onClick={() => void openRun()}
        className="rounded-lg border px-3 py-2 text-xs font-medium disabled:opacity-40"
      >
        {busy === "run"
          ? "Loading run…"
          : active && (dirty || active.workflow_version !== workflow.serverVersion)
            ? `Run active v${active.workflow_version}`
            : "Run"}
      </button>
      <details className="relative">
        <summary className="cursor-pointer rounded-lg border px-3 py-2 text-xs">Recovery</summary>
        <div className="absolute right-0 top-10 z-40 w-60 rounded-lg border bg-background p-3 shadow-lg">
          <button
            disabled={!!busy || !!runDocument}
            onClick={() => void reload()}
            className="text-xs underline disabled:opacity-40"
          >
            Reload server revision
          </button>
          <button
            disabled={!!busy}
            onClick={() => setAttempt((v) => v + 1)}
            className="mt-3 block text-xs underline"
          >
            Refresh release status
          </button>
        </div>
      </details>
      {!!Object.keys(progress).length && (
        <ol aria-label="Preparation progress" className="flex w-full flex-wrap gap-2 text-[11px]">
          {stages.map((stage) => (
            <li key={stage} className="rounded-md border px-2 py-1">
              {progress[stage] === "done"
                ? "✓"
                : progress[stage] === "running"
                  ? "●"
                  : progress[stage] === "failed"
                    ? "!"
                    : "○"}{" "}
              {progress[stage] === "Awaiting approval" ? "Awaiting approval" : stage}
              {progress[stage] === "failed" ? " · failed" : ""}
            </li>
          ))}
        </ol>
      )}
      {(error || releaseError || message) && (
        <div className="w-full">
          <ApiFeedback error={error ?? releaseError} />
          {message && (
            <p role="status" className="text-xs text-muted-foreground">
              {message}
            </p>
          )}
        </div>
      )}
      {runDocument && (
        <RunWorkflowDialog
          workflow={runDocument}
          autoStart={runDocument.inputs.length === 0}
          beforeRun={async () => {
            const latest = await api.releaseState(workflow.id);
            if (
              latest.release?.state !== "active" ||
              latest.release.release_id !== runRelease.current ||
              latest.release.workflow_version !== runDocument.version
            )
              throw new InputError(
                "The active release changed. Close this dialog and choose Run again.",
              );
          }}
          onStarted={(run) => {
            setRunDocument(undefined);
            onStarted(run);
          }}
          onClose={() => setRunDocument(undefined)}
        />
      )}
    </section>
  );
}
