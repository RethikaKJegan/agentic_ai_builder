"use client";
import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/api/client";
import { objectInput } from "@/api/orchestration";
import { useBackend } from "@/api/state";
import { GoogleAccountSelect } from "@/features/workflows/GoogleWorkflowConnection";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";
import { Link } from "@/lib/navigation";
import { InvestigationContext, type InvestigationContextValue } from "./InvestigationContext";
import { ConnectedPlan, actionButton } from "./ConnectedPlan";
import { AutomationPanel } from "./DurableAutomation";
import { useOrchestrationCommand } from "./useOrchestrationCommand";

export default function ConnectedInvestigation() {
  const backend = useBackend();
  const session = backend.session;
  if (!session || backend.status !== "connected")
    return <p className="p-5">Connect to the backend to open business investigations.</p>;
  const scope = session.auth.subject.workspace_id + ":" + session.auth.subject.subject_id;
  return <ConnectedWorkspace key={scope} />;
}
function ConnectedWorkspace() {
  const search = useSearchParams();
  const router = useRouter();
  const id = search.get("composition");
  const run = search.get("run");
  const backend = useBackend();
  const command = useOrchestrationCommand();
  const [goal, setGoal] = useState("");
  const [google, setGoogle] = useState("");
  const [recipient, setRecipient] = useState("");
  const [values, setValues] = useState("{}");
  const [context, setContext] = useState<InvestigationContextValue>({});
  const [localError, setLocalError] = useState<Error | null>(null);
  const navigate = (cid: string, rid?: string) =>
    router.replace(
      "/app/workflows/investigate?" +
        new URLSearchParams({ connected: "1", composition: cid, ...(rid ? { run: rid } : {}) }),
    );
  return (
    <div className="h-full overflow-auto bg-background p-4 md:p-6">
      <div className="mx-auto max-w-5xl space-y-5">
        <Link to="/app/workflows" className="text-sm text-primary">
          Back to workflows
        </Link>
        <h1 className="text-xl font-semibold">Business investigation</h1>
        <p className="text-sm text-muted-foreground">
          Describe your goal. Review the connected plan before running it. For adaptive
          continuation, open a prepared case below Workflow → Business investigations.
        </p>
        {!id ? (
          <form
            className="space-y-4 rounded-xl border p-4"
            onSubmit={(e) => {
              e.preventDefault();
              setLocalError(null);
              try {
                const user_values = { ...objectInput(values), ...(recipient ? { recipient } : {}) };
                void command.act(
                  "plan",
                  {
                    objective: goal,
                    google_connection_id: google || undefined,
                    business_request: context,
                    user_values,
                  },
                  async (body) => {
                    const doc = await api.createActionPlan(body);
                    navigate(doc.composition_id);
                  },
                );
              } catch (error) {
                setLocalError(error as Error);
              }
            }}
          >
            <label className="block text-sm">
              Business goal
              <textarea
                aria-label="Business goal"
                required
                maxLength={4000}
                rows={3}
                className="mt-2 w-full rounded-lg border bg-background p-3"
                value={goal}
                disabled={command.busy || command.unknown}
                onChange={(e) => setGoal(e.target.value)}
                placeholder="Investigate a complaint, report findings and contact the assigned engineer…"
              />
            </label>
            <fieldset disabled={command.busy || command.unknown} className="space-y-3">
              <GoogleAccountSelect value={google} onChange={setGoogle} />
              <label className="block text-sm">
                Authorized recipient (when required)
                <input
                  aria-label="Authorized recipient"
                  type="email"
                  value={recipient}
                  onChange={(e) => setRecipient(e.target.value)}
                  className="mt-1 w-full rounded-lg border bg-background p-2"
                />
              </label>
              <InvestigationContext value={context} onChange={setContext} objective={goal} />
              <details>
                <summary className="cursor-pointer text-sm">Additional resource inputs</summary>
                <label className="mt-2 block text-xs">
                  Explicit user values (JSON object)
                  <textarea
                    aria-label="Explicit user values"
                    rows={4}
                    value={values}
                    onChange={(e) => setValues(e.target.value)}
                    className="mt-1 w-full rounded-lg border bg-background p-2 font-mono"
                  />
                </label>
                <p className="text-xs text-muted-foreground">
                  Supply resource IDs, calendar times and report identifiers when requested.
                  Generated content cannot supply identities or permissions.
                </p>
              </details>
            </fieldset>
            <ApiFeedback error={localError ?? command.error} />
            {command.unknown && (
              <p role="alert">
                Planning outcome unconfirmed. Retry this unchanged request with its original key; no
                execution was requested.
              </p>
            )}
            <button
              className={actionButton}
              disabled={command.busy || !backend.can("workflow.plan") || !goal.trim()}
            >
              {command.busy
                ? "Requesting plan…"
                : command.unknown
                  ? "Retry identical planning request"
                  : "Propose connected plan"}
            </button>
          </form>
        ) : (
          <ConnectedPlan id={id} runId={run ?? undefined} onRun={(rid) => navigate(id, rid)} />
        )}
        <AutomationPanel />
      </div>
    </div>
  );
}
