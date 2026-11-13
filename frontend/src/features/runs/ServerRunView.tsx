"use client";
import { StopRun, RunSafety } from "./StopRun";
import { displayText } from "@/lib/display-text";
import { useEffect, useRef, useState } from "react";
import { api, ApiError, type ApprovalRecord, type RunRecord } from "@/api/client";
import { useBackend } from "@/api/state";
import { useRunFeed } from "./useRunFeed";
import { unsafeText } from "@/api/feedback";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";
import { StatusPill } from "@/features/shell/StatusPill";
import { DatabaseApprovalPreview } from "@/features/workflows/DatabaseWorkflowReview";

export function ApprovalControl({
  approval,
  emailPreview,
  databaseOperationId,
  onUpdated,
}: {
  approval: ApprovalRecord;
  emailPreview?: unknown;
  databaseOperationId?: string | undefined;
  onUpdated?: (() => void) | undefined;
}) {
  const backend = useBackend();
  const [record, setRecord] = useState(approval);
  const decisionPending = useRef(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [databaseReviewed, setDatabaseReviewed] = useState(false);
  const decide = async (decision: "approved" | "rejected") => {
    if (
      decisionPending.current ||
      !backend.can("workflow.approve") ||
      !record.allowed_decisions.includes(decision)
    )
      return;
    if (decision === "approved" && databaseOperationId && !databaseReviewed) return;
    decisionPending.current = true;
    setBusy(true);
    setError(null);
    try {
      const result = await api.request("decide_approval", {
        approval_id: record.approval_id,
        workflow_id: record.workflow_id,
        workflow_version: record.workflow_version,
        decision,
      });
      setRecord(result);
      onUpdated?.();
    } catch (caught) {
      setError(caught instanceof Error ? caught : new Error("The decision failed."));
    } finally {
      decisionPending.current = false;
      setBusy(false);
    }
  };
  return (
    <div className="space-y-2 rounded-lg border border-border p-3">
      <p className="text-sm">
        Approval {record.approval_id} · {record.status} · v{record.workflow_version}
      </p>
      <p className="text-xs text-muted-foreground">
        Required roles: {record.required_roles?.join(", ") || "Determined by the server gate"}
      </p>
      <p className="text-xs text-muted-foreground">
        Workflow {record.workflow_id}
        {record.action_digest ? ` · approved action ${record.action_digest.slice(0, 12)}…` : ""}
      </p>
      {record.tool_id && (
        <p className="text-xs">
          Tool: {record.tool_id} · {record.operation}
        </p>
      )}
      {record.expires_at && (
        <p className="text-xs">Expires: {new Date(record.expires_at * 1000).toLocaleString()}</p>
      )}
      {record.resolved_payload && (
        <details className="text-xs">
          <summary>Exact proposed action</summary>
          <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-all">
            {displayText(JSON.stringify(record.resolved_payload, null, 2))}
          </pre>
        </details>
      )}
      {emailPreview != null && (
        <pre
          aria-label="Email awaiting approval"
          className="whitespace-pre-wrap break-words rounded-lg bg-muted p-3 text-xs"
        >
          {displayText(JSON.stringify(emailPreview, null, 2))}
        </pre>
      )}
      {databaseOperationId && record.status === "pending" && (
        <DatabaseApprovalPreview
          key={databaseOperationId}
          operationId={databaseOperationId}
          onReviewed={setDatabaseReviewed}
        />
      )}
      {record.status === "pending" &&
        backend.session?.approval_service_available &&
        backend.can("runs.view") &&
        backend.can("workflow.approve") && (
          <div className="flex gap-2">
            {record.allowed_decisions.map((decision) => (
              <button
                key={decision}
                className="rounded-lg border border-border px-3 py-1.5 text-xs disabled:opacity-40"
                disabled={
                  busy || (decision === "approved" && !!databaseOperationId && !databaseReviewed)
                }
                onClick={() => void decide(decision)}
              >
                {decision === "approved" ? "Approve" : "Reject"}
              </button>
            ))}
          </div>
        )}
      {record.status === "pending" &&
        (!backend.can("workflow.approve") || !record.allowed_decisions.length) && (
          <p className="text-xs text-muted-foreground">
            The exact gate role, workflow.approve permission and workspace membership are required
            to decide this approval.
          </p>
        )}
      {record.status === "unmatched" && (
        <p className="text-xs text-muted-foreground">
          This approval does not match the current workflow revision.
        </p>
      )}
      <ApiFeedback error={error} />
    </div>
  );
}

export function ServerRunView({
  approvalsOnly = false,
  summaryStatus,
}: {
  approvalsOnly?: boolean;
  summaryStatus?: string;
}) {
  const backend = useBackend();
  const [runId, setRunId] = useState("");
  const [selected, setSelected] = useState("");
  const feed = useRunFeed(
    selected,
    backend.status === "connected" &&
      !!backend.session?.runtime_available &&
      backend.can("runs.view"),
  );
  const { run, events } = feed;
  const busy = feed.loading;
  const [availableRuns, setAvailableRuns] = useState<RunRecord[]>([]);
  const [error, setError] = useState<Error | null>(null);
  const [filters, setFilters] = useState({
    workflow_id: "",
    status: "",
    from_date: "",
    to_date: "",
    search: "",
    sort: "newest",
  });
  useEffect(() => {
    if (summaryStatus !== undefined) {
      setCursor(undefined);
      setFilters((f) => (f.status === summaryStatus ? f : { ...f, status: summaryStatus }));
    }
  }, [summaryStatus]);
  const [listLoading, setListLoading] = useState(true);
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  const [cursor, setCursor] = useState<string | undefined>();
  const [next, setNext] = useState<string | null>(null);
  const loadRun = async (id: string) => {
    setRunId(id);
    if (id === selected) feed.refresh();
    else setSelected(id);
  };
  const load = async () => loadRun(runId.trim());
  useEffect(() => {
    if (backend.status !== "connected" || !backend.session?.runtime_available) return;
    const selected = new URL(window.location.href).searchParams.get("run");
    if (selected) {
      setRunId(selected);
      void loadRun(selected);
    }
    // Load the explicit run link once after the session becomes available.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [backend.status, backend.session?.runtime_available]);
  const canViewRuns = backend.can("runs.view");
  useEffect(() => {
    if (backend.status !== "connected" || !canViewRuns) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    setListLoading(true);
    const refresh = async () => {
      try {
        const collection = await api.runs({
          ...filters,
          limit: 50,
          cursor,
          pending_only: approvalsOnly,
        });
        if (!cancelled) {
          setAvailableRuns(collection.items);
          setNext(collection.next_cursor ?? null);
          setError(null);
        }
      } catch (caught) {
        if (!cancelled)
          setError(caught instanceof ApiError ? caught : new Error("Unable to load server runs."));
      } finally {
        if (!cancelled) setListLoading(false);
        if (!cancelled) timer = setTimeout(() => void refresh(), 15000);
      }
    };
    void refresh();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [approvalsOnly, backend.status, canViewRuns, filters, cursor]);
  if (!backend.session?.runtime_available)
    return (
      <p className="rounded-2xl border border-dashed border-border p-10 text-center text-sm text-muted-foreground">
        The runtime API is not connected. No{" "}
        {approvalsOnly ? "approval requests" : "execution records"} are available.
      </p>
    );
  return (
    <div className="space-y-4">
      <p className="text-xs text-muted-foreground">
        Select a run to inspect its results, approvals and history.
      </p>
      <div className="flex flex-wrap gap-2" aria-label="Run filters">
        <label className="text-xs">
          Search workflows
          <input
            aria-label="Search workflow names"
            placeholder="Workflow name"
            value={filters.search}
            onChange={(e) => {
              setCursor(undefined);
              setFilters({ ...filters, search: e.target.value });
            }}
            className="block rounded border bg-background p-2"
          />
        </label>
        <label className="text-xs">
          Workflow ID
          <input
            aria-label="Filter workflow"
            value={filters.workflow_id}
            onChange={(e) => {
              setCursor(undefined);
              setFilters({ ...filters, workflow_id: e.target.value });
            }}
            className="block rounded border bg-background p-2"
          />
        </label>
        <label className="text-xs">
          Status
          <select
            aria-label="Filter status"
            value={filters.status}
            onChange={(e) => {
              setCursor(undefined);
              setFilters({ ...filters, status: e.target.value });
            }}
            className="block rounded border bg-background p-2"
          >
            <option value="">All statuses</option>
            {[
              "active",
              "needs_attention",
              "queued",
              "running",
              "paused_for_approval",
              "completed",
              "failed",
              "blocked",
              "rejected",
              "cancelled",
            ].map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs">
          From
          <input
            aria-label="Filter from date"
            type="date"
            value={filters.from_date}
            onChange={(e) => {
              setCursor(undefined);
              setFilters({ ...filters, from_date: e.target.value });
            }}
            className="block rounded border bg-background p-2"
          />
        </label>
        <label className="text-xs">
          Until
          <input
            aria-label="Filter to date"
            type="date"
            value={filters.to_date.slice(0, 10)}
            onChange={(e) => {
              setCursor(undefined);
              setFilters({
                ...filters,
                to_date: e.target.value ? e.target.value + "T23:59:59.999Z" : "",
              });
            }}
            className="block rounded border bg-background p-2"
          />
        </label>
        <label className="text-xs">
          Sort
          <select
            aria-label="Sort runs"
            value={filters.sort}
            onChange={(e) => {
              setCursor(undefined);
              setFilters({ ...filters, sort: e.target.value });
            }}
            className="block rounded border bg-background p-2"
          >
            <option value="newest">Newest first</option>
            <option value="oldest">Oldest first</option>
          </select>
        </label>
      </div>
      <div
        className="overflow-x-auto rounded-xl border"
        aria-label={approvalsOnly ? "Pending approvals" : "Recent runs"}
      >
        {listLoading && (
          <p role="status" className="p-4 text-sm">
            Loading runs…
          </p>
        )}
        {!listLoading && availableRuns.length === 0 && (
          <p className="p-5 text-sm text-muted-foreground">
            {approvalsOnly ? "No pending approvals." : "No runs match these filters."}
          </p>
        )}
        {availableRuns.length > 0 && (
          <table className="w-full min-w-[680px] text-left text-sm">
            <thead className="bg-muted/40 text-xs text-muted-foreground">
              <tr>
                {["Workflow", "Status", "Started", "Duration", "Result"].map((title) => (
                  <th key={title} className="p-3 font-medium">
                    {title}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {availableRuns.map((item) => {
                const seconds =
                  item.duration_seconds ??
                  (item.created_at &&
                  (item.finished_at ||
                    ["queued", "running", "paused_for_approval"].includes(item.status))
                    ? Math.max(0, (item.finished_at ?? now / 1000) - item.created_at)
                    : null);
                return (
                  <tr
                    key={item.run_id}
                    className={selected === item.run_id ? "bg-primary/5" : "hover:bg-muted/30"}
                  >
                    <td className="p-3">
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => void loadRun(item.run_id)}
                        className="text-left font-medium text-primary"
                        aria-label={`${item.workflow_name ?? item.workflow_id} · ${item.run_id} · ${item.status}`}
                      >
                        {displayText(item.workflow_name ?? item.workflow_id)}
                      </button>
                      <p className="mt-1 text-xs text-muted-foreground">
                        v{item.workflow_version} · {item.run_id.slice(-8)}
                      </p>
                    </td>
                    <td className="p-3">
                      <StatusPill status={item.status} />
                    </td>
                    <td className="p-3 text-xs">
                      {item.created_at
                        ? new Date(item.created_at * 1000).toLocaleString()
                        : "Not recorded"}
                    </td>
                    <td className="p-3 text-xs">
                      {seconds === null
                        ? "Not recorded"
                        : `${Math.floor(seconds / 60)}m ${Math.floor(seconds % 60)}s`}
                    </td>
                    <td className="max-w-60 p-3 text-xs">
                      {displayText(
                        item.result_summary ??
                          (item.approvals.some((a) => a.status === "pending")
                            ? "Awaiting approval"
                            : "Inspect run"),
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
      <div className="flex gap-2">
        <button
          type="button"
          disabled={!cursor}
          onClick={() => setCursor(undefined)}
          className="rounded border px-3 py-2 text-xs disabled:opacity-40"
        >
          Newest runs
        </button>
        <button
          type="button"
          disabled={!next}
          onClick={() => setCursor(next ?? undefined)}
          className="rounded border px-3 py-2 text-xs disabled:opacity-40"
        >
          Older runs
        </button>
      </div>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void load();
        }}
        className="flex gap-2"
      >
        <input
          aria-label="Run ID"
          disabled={busy}
          value={runId}
          onChange={(event) => setRunId(event.target.value)}
          className="min-w-0 flex-1 rounded-lg border border-border px-3 py-2 text-sm"
          placeholder="Run ID from an execution response"
        />
        <button
          disabled={busy || !runId.trim()}
          className="rounded-lg border border-border px-4 text-sm disabled:opacity-40"
        >
          {busy ? "Loading…" : "Load run"}
        </button>
      </form>
      <ApiFeedback error={error ?? feed.error} />
      {run && (
        <>
          {run.composition_id && (
            <a
              className="inline-block rounded-lg border px-3 py-2 text-sm text-primary"
              href={`/app/workflows/investigate?connected=1&composition=${encodeURIComponent(run.composition_id)}&run=${encodeURIComponent(run.run_id)}`}
            >
              Open workflow, ontology and run again
            </a>
          )}
          <p className="text-sm">
            {run.run_id} · {run.workflow_id} · v{run.workflow_version}{" "}
            <StatusPill status={run.status} />
          </p>
          <StopRun run={run} onStopped={feed.refresh} />
          <RunSafety run={run} />
          {run.approvals.map((approval) => {
            const matched =
              approval.workflow_id === run.workflow_id &&
              approval.workflow_version === run.workflow_version;
            const record = matched
              ? approval
              : { ...approval, status: "unmatched" as const, allowed_decisions: [] };
            const preview = events.find(
              (event) =>
                event.event_type === "approval.pending" &&
                event.details?.["approval_id"] === record.approval_id,
            )?.details?.["email_preview"];
            const operationId = events.find(
              (event) =>
                event.event_type === "approval.pending" &&
                event.details?.["approval_id"] === record.approval_id,
            )?.details?.["database_operation_id"];
            return (
              <ApprovalControl
                key={`${record.approval_id}:${record.status}`}
                approval={record}
                emailPreview={preview}
                databaseOperationId={typeof operationId === "string" ? operationId : undefined}
                onUpdated={() => void loadRun(run.run_id)}
              />
            );
          })}
          {events
            .filter((event) => event.event_type === "node.failed")
            .map((event) => (
              <p key={event.event_id} className="text-sm text-destructive">
                Failed node: {String(event.details?.["node_id"] ?? "unknown")} ·{" "}
                {displayText(
                  typeof event.details?.["error_code"] === "string" &&
                    !unsafeText(event.details["error_code"])
                    ? event.details["error_code"]
                    : "Inspect the recorded failure reference",
                )}
              </p>
            ))}
          {feed.hasMore && (
            <p role="status" className="text-xs">
              Loading the next recorded event page…
            </p>
          )}
          {!approvalsOnly && (
            <ol
              className="divide-y divide-border rounded-xl border border-border"
              aria-label="Run events"
            >
              {events.map((event) => (
                <li key={event.event_id} className="p-3">
                  <p className="text-sm">{event.event_type}</p>
                  <p className="text-xs text-muted-foreground">
                    {event.timestamp} · {event.source} · {event.event_id} · v
                    {event.workflow_version}
                  </p>
                  {event.details && (
                    <details className="mt-2 text-xs">
                      <summary>Recorded inputs, source usage and results</summary>
                      <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-all">
                        {displayText(JSON.stringify(event.details, null, 2))}
                      </pre>
                    </details>
                  )}
                </li>
              ))}
            </ol>
          )}
        </>
      )}
    </div>
  );
}
