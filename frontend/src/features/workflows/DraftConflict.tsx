import { displayText } from "@/lib/display-text";
import { useRef, useState } from "react";
import { api } from "@/api/client";
import { fromCanonical, ownsAgent, hasWorkflowEdits, workflowEditSnapshot } from "@/api/mapping";
import { useMesh } from "@/domain/store";
import type { Workflow } from "@/domain/types";
import { rebaseDraft } from "./rebase";
import { ApiFeedback } from "./ApiFeedback";
import { InputError } from "@/api/feedback";
export function DraftConflict({
  workflow,
  recoveryOnly = false,
}: {
  workflow: Workflow;
  recoveryOnly?: boolean;
}) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState<Error>(),
    [paths, setPaths] = useState<string[]>([]),
    [exported, setExported] = useState("");
  const pending = useRef(false);
  if (!workflow.remote && !workflow.tabConflict && !recoveryOnly) return null;
  const run = async (action: "check" | "reload" | "rebase") => {
    if (pending.current) return;
    const state = useMesh.getState(),
      current = state.workflows.find((w) => w.id === workflow.id);
    if (!current) return;
    if (
      action === "reload" &&
      hasWorkflowEdits(current, state.agents) &&
      !window.confirm(
        "Discard this working draft and load the latest server revision? Export it first if you want to keep a separate copy.",
      )
    )
      return;
    const submitted = workflowEditSnapshot(current, state.agents);
    pending.current = true;
    setBusy(true);
    setError(undefined);
    setPaths([]);
    try {
      const response = await api.request("get_workflow", { workflow_id: workflow.id });
      const latestState = useMesh.getState();
      const latest = latestState.workflows.find((w) => w.id === workflow.id);
      if (!latest) return;
      if (action === "reload") {
        if (workflowEditSnapshot(latest, latestState.agents) !== submitted)
          throw new InputError(
            "Your draft changed while reload was loading. New edits were retained; confirm reload again.",
          );
        latestState.acceptWorkflow(response.workflow);
      } else if (action === "check") latestState.observeWorkflows([response.workflow]);
      else {
        const result = rebaseDraft(latest, latestState.agents, response.workflow);
        if (result.conflicts.length) {
          setPaths(result.conflicts);
          throw new InputError(
            "These fields changed in both drafts. Export your working draft, then reload and reapply the intended values.",
          );
        }
        const mapped = fromCanonical(result.workflow!);
        useMesh.setState({
          workflows: latestState.workflows.map((w) =>
            w.id === workflow.id
              ? {
                  ...mapped.workflow,
                  canonical: structuredClone(response.workflow),
                  serverVersion: response.workflow.version,
                  status: response.workflow.status,
                  remote: undefined,
                  tabConflict: undefined,
                }
              : w,
          ),
          agents: [...mapped.agents, ...latestState.agents.filter((a) => !ownsAgent(latest, a))],
        });
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught : new Error("Read failed."));
    } finally {
      pending.current = false;
      setBusy(false);
    }
  };
  return (
    <section
      aria-label="Draft conflict resolution"
      className="shrink-0 space-y-2 border-b border-warning p-3 text-xs"
    >
      <p role="alert">
        {workflow.remote
          ? `Server revision v${workflow.remote.version} (${workflow.remote.status}) differs from your loaded baseline v${workflow.serverVersion ?? 0}.`
          : recoveryOnly
            ? "Browser draft backup is unavailable."
            : "Another tab changed shared draft storage."}{" "}
        Your working edits are retained.
      </p>
      <p>
        Compare or export before resolving. Rebase applies only non-overlapping changes; it does not
        save, approve, publish or change the active release.
      </p>
      <div className="flex flex-wrap gap-2">
        {workflow.tabConflict && !workflow.remote && (
          <button
            type="button"
            onClick={() =>
              useMesh.setState((s) => ({
                workflows: s.workflows.map((w) =>
                  w.id === workflow.id ? { ...w, tabConflict: undefined } : w,
                ),
              }))
            }
            className="rounded border p-2"
          >
            Keep this tab's draft
          </button>
        )}
        <button
          type="button"
          disabled={busy}
          onClick={() => void run("check")}
          className="rounded border p-2"
        >
          Check latest revision
        </button>
        <button
          type="button"
          disabled={busy || !workflow.remote || !workflow.canonical}
          onClick={() => void run("rebase")}
          className="rounded border p-2 disabled:opacity-40"
        >
          Rebase non-overlapping edits
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => void run("reload")}
          className="rounded border p-2"
        >
          Discard and reload latest
        </button>
        <button
          type="button"
          onClick={() => {
            try {
              const state = useMesh.getState();
              setExported(
                JSON.stringify(
                  {
                    format: "mesh-working-draft-recovery-v1",
                    workflow,
                    agents: state.agents.filter((a) => ownsAgent(workflow, a)),
                  },
                  null,
                  2,
                ),
              );
            } catch (caught) {
              setError(caught instanceof Error ? caught : new Error("Export unavailable."));
            }
          }}
          className="rounded border p-2"
        >
          Export working draft
        </button>
      </div>
      {workflow.remote && (
        <details>
          <summary>Compare server and loaded baseline</summary>
          <div className="grid max-h-64 gap-2 overflow-auto sm:grid-cols-2">
            <pre className="overflow-auto">{displayText(JSON.stringify(workflow.canonical, null, 2))}</pre>
            <pre className="overflow-auto">{displayText(JSON.stringify(workflow.remote, null, 2))}</pre>
          </div>
        </details>
      )}
      {exported && (
        <label className="block">
          Working draft export (copy this JSON)
          <textarea
            aria-label="Working draft export"
            readOnly
            value={exported}
            rows={6}
            className="mt-1 w-full rounded border p-2"
          />
        </label>
      )}
      {!!paths.length && (
        <ul aria-label="Overlapping changes">
          {paths.map((path) => (
            <li key={path}>{path}</li>
          ))}
        </ul>
      )}
      <ApiFeedback error={error} />
    </section>
  );
}
