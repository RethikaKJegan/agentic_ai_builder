"use client";
import { useEffect, useState } from "react";
import { api } from "@/api/client";
import { useBackend } from "@/api/state";
import { objectInput, type AutomationRecord } from "@/api/orchestration";
import { type CanonicalWorkflow } from "@/api/contracts.generated";
import { GoogleAccountSelect } from "@/features/workflows/GoogleWorkflowConnection";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";
import { SavedDetails, Outcome } from "./LifecyclePanels";
import { actionButton } from "./ConnectedPlan";
import { useOrchestrationCommand } from "./useOrchestrationCommand";

const field = "mt-1 w-full rounded-lg border bg-background p-2 text-sm";
export function epochDisplay(value: unknown) {
  return typeof value === "number" ? new Date(value * 1000).toISOString() : "Not recorded";
}
type Target = { caseId: string; waitId: string; stageId: string };
export function AutomationPanel({ target }: { target?: Target | undefined }) {
  const session = useBackend((s) => s.session);
  if (!session) return null;
  return (
    <AutomationWorkspace
      key={
        session.auth.subject.workspace_id +
        ":" +
        session.auth.subject.subject_id +
        ":" +
        (target?.caseId ?? "")
      }
      target={target}
    />
  );
}
function AutomationWorkspace({ target }: { target?: Target | undefined }) {
  const backend = useBackend();
  const command = useOrchestrationCommand();
  const [records, setRecords] = useState<AutomationRecord[]>([]);
  const [jobs, setJobs] = useState<Record<string, unknown>[]>([]);
  const [health, setHealth] = useState<Record<string, unknown>>({});
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(true);
  const [refresh, setRefresh] = useState(0);
  const [cursor, setCursor] = useState<string | null>(null);
  const [pages, setPages] = useState<string[]>([]);
  const [workflows, setWorkflows] = useState<CanonicalWorkflow[]>([]);
  const [kind, setKind] = useState<"subscriptions" | "authorizations" | "schedules" | "timers">(
    "schedules",
  );
  const [google, setGoogle] = useState("");
  const [workflow, setWorkflow] = useState("");
  const [consent, setConsent] = useState("");
  const [cron, setCron] = useState("");
  const [timezone, setTimezone] = useState("Etc/UTC");
  const [purpose, setPurpose] = useState("");
  const [content, setContent] = useState("");
  const [expires, setExpires] = useState("");
  const [maxRuns, setMaxRuns] = useState(10);
  const [maxActions, setMaxActions] = useState(8);
  const [operations, setOperations] = useState("{}");
  const [inputs, setInputs] = useState("{}");
  const [missed, setMissed] = useState("skip");
  const [overlap, setOverlap] = useState("forbid");
  const [participants, setParticipants] = useState("");
  const [thread, setThread] = useState("");
  const [message, setMessage] = useState("");
  const [rfc, setRfc] = useState("");
  const [mapping, setMapping] = useState("{}");
  const [timerPurpose, setTimerPurpose] = useState("reply_deadline");
  const [review, setReview] = useState<Record<string, unknown> | null>(null);
  const [created, setCreated] = useState<AutomationRecord | null>(null);
  useEffect(() => {
    let live = true;
    let timer: ReturnType<typeof setTimeout>;
    async function read() {
      try {
        const data = await api.automationRecords(pages.at(-1));
        if (!live) return;
        setRecords(data.items);
        setCursor(data.next_cursor);
        setJobs(data.jobs);
        setHealth(data.health);
        setError(null);
        timer = setTimeout(() => void read(), 5000);
      } catch (e) {
        if (live) setError(e as Error);
      } finally {
        if (live) setLoading(false);
      }
    }
    void read();
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [refresh, pages]);
  useEffect(() => {
    let live = true;
    api
      .request("list_workflows", {})
      .then((data) => {
        if (live)
          setWorkflows(data.items.filter((w) => ["approved", "published"].includes(w.status)));
      })
      .catch((e) => {
        if (live) setError(e as Error);
      });
    return () => {
      live = false;
    };
  }, [refresh]);
  const canExecute = backend.can("workflow.execute");
  const canApprove = backend.can("workflow.approve");
  const permitted = !command.busy && !command.unknown && canExecute;
  const eligibleWorkflows =
    kind === "schedules" ? workflows.filter((w) => !w.metadata["adaptive_control"]) : workflows;
  function prepare() {
    try {
      const selected = eligibleWorkflows.find((w) => `${w.workflow_id}:${w.version}` === workflow);
      const ref = selected
        ? { workflow_id: selected.workflow_id, workflow_version: selected.version }
        : null;
      const deadline = new Date(expires).getTime() / 1000;
      if (
        ["subscriptions", "authorizations", "timers"].includes(kind) &&
        (!/(Z|[+-]\d{2}:\d{2})$/.test(expires) ||
          !Number.isFinite(deadline) ||
          deadline <= Date.now() / 1000)
      )
        throw new Error("Choose a future deadline with a timezone.");
      let request: Record<string, unknown>;
      if (kind === "authorizations")
        request = {
          connection_id: google,
          operations: objectInput(operations),
          purpose,
          content_scope: content,
          schedule: { cron, timezone },
          limits: { max_occurrences: maxRuns, max_actions_per_occurrence: maxActions },
          expires_at: deadline,
        };
      else if (kind === "schedules") {
        if (!ref) throw new Error("Select an approved workflow revision.");
        request = {
          workflow: ref,
          authorization_id: consent,
          cron,
          timezone,
          missed_run_policy: missed,
          overlap_policy: overlap,
          inputs: objectInput(inputs),
        };
      } else {
        if (!target) throw new Error("Open the saved case and select its current wait.");
        request = {
          case_id: target.caseId,
          wait_id: target.waitId,
          stage_id: target.stageId,
          ...(kind === "timers"
            ? { due: deadline, purpose: timerPurpose }
            : {
                provider: "gmail",
                connection_id: google,
                correlation: { thread_id: thread, sent_message_id: message, rfc_message_id: rfc },
                participants: participants
                  .split(",")
                  .map((v) => v.trim())
                  .filter(Boolean),
                expected_information: purpose,
                payload_mapping: objectInput(mapping),
                deadline,
                poll_workflow: ref,
              }),
        };
        if (kind === "subscriptions" && !ref)
          throw new Error("Select an approved Gmail thread-reading workflow.");
      }
      setReview(request);
      command.setError(null);
    } catch (e) {
      command.setError(e as Error);
    }
  }
  const visible = records.filter((r) => !target || r.request["case_id"] === target.caseId);
  return (
    <section className="min-w-0 space-y-4 rounded-xl border p-4" aria-label="Background automation">
      <h2 className="font-semibold">Background continuation & recurring automation</h2>
      <p className="text-sm text-muted-foreground">
        A Gmail reply resumes its existing case. A schedule creates a new execution occurrence with
        fresh source reads.
      </p>
      <button
        className={actionButton}
        disabled={command.busy}
        onClick={() => setRefresh((n) => n + 1)}
      >
        Refresh automation
      </button>
      <ApiFeedback error={error ?? command.error} />
      {command.unknown && (
        <p role="alert">
          Outcome unconfirmed. Inspect saved records before retrying the unchanged reviewed request.
        </p>
      )}
      {loading ? (
        <p role="status">Loading saved automation…</p>
      ) : visible.length === 0 ? (
        <p className="text-sm">No automation records on this page.</p>
      ) : (
        visible.map((r) => (
          <article key={r.id} className="min-w-0 space-y-2 rounded-lg border p-3">
            <h3 className="break-all text-sm font-medium">
              {r.kind} · {r.id}
            </h3>
            <Outcome value={r.state} />
            <p className="text-xs">
              Next due: {epochDisplay(r["due"])} · Latest occurrence on this page:{" "}
              {epochDisplay(
                records
                  .filter((o) => o.kind === "occurrence" && o["schedule_id"] === r.id)
                  .sort((a, b) => Number(b["due"]) - Number(a["due"]))[0]?.["due"],
              )}
            </p>
            {!!r["last_error_code"] && (
              <p role="alert" className="text-sm">
                {String(r["last_error_code"])}
              </p>
            )}
            <SavedDetails label="Saved scope, history and receipt references" value={r} />
            {r.kind === "occurrence" && typeof r["run_id"] === "string" && (
              <a
                className="text-sm text-primary underline"
                href={"/app/runs?run=" + encodeURIComponent(r["run_id"])}
              >
                Inspect occurrence run and actual receipts
              </a>
            )}
            {!["occurrence", "control"].includes(r.kind) && (
              <div className="flex flex-wrap gap-2">
                {(r.kind === "authorization"
                  ? ["revoke"]
                  : r.state === "paused"
                    ? ["resume", "cancel"]
                    : r.state === "active"
                      ? ["pause", "cancel"]
                      : []
                ).map((action) => (
                  <button
                    key={action}
                    className={actionButton}
                    disabled={!permitted || (r.kind === "authorization" && !canApprove)}
                    onClick={() =>
                      void command.act(
                        "control:" + r.id,
                        { action, state: r.state, updated_at: r["updated_at"] ?? null },
                        async (body) => {
                          await api.controlAutomation(r.id, {
                            action,
                            request_key: body["request_key"],
                          });
                          setRefresh((n) => n + 1);
                        },
                      )
                    }
                  >
                    {action[0]?.toUpperCase() + action.slice(1)}
                  </button>
                ))}
              </div>
            )}
          </article>
        ))
      )}
      <div className="flex gap-2">
        <button
          className={actionButton}
          disabled={!pages.length}
          onClick={() => setPages((p) => p.slice(0, -1))}
        >
          Newer records
        </button>
        <button
          className={actionButton}
          disabled={!cursor}
          onClick={() => cursor && setPages((p) => [...p, cursor])}
        >
          Older records
        </button>
      </div>
      <SavedDetails
        label="Worker status and recent continuation jobs"
        value={{ health, jobs: target ? jobs.filter((j) => j["case_id"] === target.caseId) : jobs }}
      />
      <details>
        <summary className="cursor-pointer text-sm font-medium">
          Configure reviewed automation
        </summary>
        <form
          className="mt-4 space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            prepare();
          }}
        >
          <fieldset disabled={command.busy || !!review} className="space-y-3">
            <label className="block text-sm">
              Automation type
              <select
                className={field}
                aria-label="Automation type"
                value={kind}
                onChange={(e) => {
                  setKind(e.target.value as typeof kind);
                  setCreated(null);
                }}
              >
                <option value="schedules">Recurring schedule</option>
                <option value="authorizations">Recurring business consent</option>
                {target && (
                  <>
                    <option value="subscriptions">Gmail reply subscription</option>
                    <option value="timers">Case timer</option>
                  </>
                )}
              </select>
            </label>
            {["authorizations", "subscriptions"].includes(kind) && (
              <GoogleAccountSelect value={google} onChange={setGoogle} />
            )}
            {["subscriptions", "schedules"].includes(kind) && (
              <label className="block text-sm">
                Approved workflow revision
                <select
                  className={field}
                  aria-label="Approved workflow revision"
                  required
                  value={workflow}
                  onChange={(e) => setWorkflow(e.target.value)}
                >
                  <option value="">Select a pinned revision</option>
                  {eligibleWorkflows.map((w) => (
                    <option
                      key={`${w.workflow_id}:${w.version}`}
                      value={`${w.workflow_id}:${w.version}`}
                    >
                      {w.name} · v{w.version}
                    </option>
                  ))}
                </select>
              </label>
            )}
            {["schedules", "authorizations"].includes(kind) && (
              <>
                <label className="block text-sm">
                  Five-field cron
                  <input
                    className={field}
                    aria-label="Five-field cron"
                    required
                    value={cron}
                    placeholder="0 9 * * *"
                    onChange={(e) => setCron(e.target.value)}
                  />
                </label>
                <label className="block text-sm">
                  IANA timezone
                  <input
                    className={field}
                    aria-label="IANA timezone"
                    required
                    value={timezone}
                    onChange={(e) => setTimezone(e.target.value)}
                  />
                </label>
              </>
            )}
            {["authorizations", "subscriptions", "timers"].includes(kind) && (
              <label className="block text-sm">
                {kind === "authorizations" ? "Consent expiry" : "Reply deadline / timer due"} (ISO
                with timezone)
                <input
                  className={field}
                  aria-label="Deadline"
                  required
                  value={expires}
                  placeholder="2026-12-01T18:00:00Z"
                  onChange={(e) => setExpires(e.target.value)}
                />
              </label>
            )}
            {["authorizations", "subscriptions"].includes(kind) && (
              <label className="block text-sm">
                {kind === "authorizations" ? "Business purpose" : "Expected reply information"}
                <textarea
                  className={field}
                  aria-label="Business purpose"
                  required
                  maxLength={1000}
                  value={purpose}
                  onChange={(e) => setPurpose(e.target.value)}
                />
              </label>
            )}
            {kind === "authorizations" && (
              <>
                <label className="block text-sm">
                  Authorized content scope
                  <textarea
                    className={field}
                    required
                    aria-label="Authorized content scope"
                    maxLength={2000}
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                  />
                </label>
                <label className="block text-sm">
                  Maximum occurrences
                  <input
                    className={field}
                    type="number"
                    min={1}
                    max={10000}
                    required
                    aria-label="Maximum occurrences"
                    value={maxRuns}
                    onChange={(e) => setMaxRuns(Number(e.target.value))}
                  />
                </label>
                <label className="block text-sm">
                  Maximum actions per occurrence
                  <input
                    className={field}
                    type="number"
                    min={1}
                    max={16}
                    required
                    aria-label="Maximum actions per occurrence"
                    value={maxActions}
                    onChange={(e) => setMaxActions(Number(e.target.value))}
                  />
                </label>
                <label className="block text-sm">
                  Permitted operations and exact recipient/resource restrictions
                  <textarea
                    className={field + " font-mono"}
                    aria-label="Permitted operations"
                    rows={6}
                    value={operations}
                    onChange={(e) => setOperations(e.target.value)}
                  />
                </label>
                <p className="text-xs text-muted-foreground">
                  An approver must specify registered operation IDs and local input schemas.
                  Recipients and resource identities require explicit const or enum restrictions.
                  Account access alone grants no recurring consent.
                </p>
              </>
            )}
            {kind === "schedules" && (
              <>
                <label className="block text-sm">
                  Saved recurring consent ID
                  <input
                    className={field}
                    required
                    aria-label="Recurring consent ID"
                    value={consent}
                    onChange={(e) => setConsent(e.target.value)}
                  />
                </label>
                <label className="block text-sm">
                  Missed runs
                  <select
                    className={field}
                    aria-label="Missed runs"
                    value={missed}
                    onChange={(e) => setMissed(e.target.value)}
                  >
                    <option value="skip">Skip</option>
                    <option value="coalesce">Coalesce</option>
                    <option value="catch_up">Bounded catch-up</option>
                  </select>
                </label>
                <label className="block text-sm">
                  Overlapping runs
                  <select
                    className={field}
                    aria-label="Overlapping runs"
                    value={overlap}
                    onChange={(e) => setOverlap(e.target.value)}
                  >
                    <option value="forbid">Forbid overlap</option>
                    <option value="allow">Allow overlap</option>
                  </select>
                </label>
                <label className="block text-sm">
                  Execution inputs
                  <textarea
                    className={field}
                    aria-label="Execution inputs"
                    value={inputs}
                    onChange={(e) => setInputs(e.target.value)}
                  />
                </label>
              </>
            )}
            {kind === "subscriptions" && (
              <>
                <p className="text-xs">
                  Use identifiers from the completed Gmail send receipt. A subscription never sends
                  a message.
                </p>
                {[
                  ["Expected reply senders", participants, setParticipants],
                  ["Gmail thread ID", thread, setThread],
                  ["Sent Gmail message ID", message, setMessage],
                  ["Sent RFC Message-ID", rfc, setRfc],
                ].map(([label, value, set]) => (
                  <label key={String(label)} className="block text-sm">
                    {String(label)}
                    <input
                      className={field}
                      aria-label={String(label)}
                      required
                      value={String(value)}
                      onChange={(e) => (set as (value: string) => void)(e.target.value)}
                    />
                  </label>
                ))}
                <label className="block text-sm">
                  Reply fields for the saved wait
                  <textarea
                    className={field}
                    aria-label="Reply field mapping"
                    value={mapping}
                    onChange={(e) => setMapping(e.target.value)}
                  />
                </label>
              </>
            )}
            {kind === "timers" && (
              <label className="block text-sm">
                Timer purpose
                <select
                  className={field}
                  value={timerPurpose}
                  onChange={(e) => setTimerPurpose(e.target.value)}
                >
                  {[
                    "follow_up",
                    "reply_deadline",
                    "approval_deadline",
                    "escalation",
                    "delayed_continuation",
                    "retry_after",
                  ].map((v) => (
                    <option key={v} value={v}>
                      {v.replaceAll("_", " ")}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </fieldset>
          {!review && (
            <button
              className={actionButton}
              disabled={
                !permitted ||
                (kind === "authorizations" && !canApprove) ||
                (kind === "subscriptions" && !backend.can("events.ingest"))
              }
            >
              Review automation scope
            </button>
          )}
        </form>
        {review && (
          <div className="mt-4 space-y-3">
            <SavedDetails label="Exact automation scope to authorize" value={review} />
            <p className="text-xs">
              Review account, destinations, limits, purpose and times before confirming. Backend
              authorization remains mandatory.
            </p>
            <button
              className={actionButton}
              disabled={command.busy}
              onClick={() => {
                if (!command.unknown) setReview(null);
              }}
            >
              Edit scope
            </button>
            <button
              className={actionButton}
              disabled={command.busy || !canExecute || (kind === "authorizations" && !canApprove)}
              onClick={() =>
                void command.act("automation:" + kind, review, async (body) => {
                  const result = await api.createAutomation(kind, body);
                  setCreated(result);
                  if (result.kind === "authorization") setConsent(result.id);
                  setReview(null);
                  setRefresh((n) => n + 1);
                })
              }
            >
              {command.unknown
                ? "Retry identical reviewed request"
                : "Confirm reviewed " +
                  (kind === "authorizations" ? "recurring consent" : "automation")}
            </button>
          </div>
        )}
        {created && (
          <p role="status" className="mt-3 break-all text-sm">
            Saved {created.kind}: {created.id} · {created.state}
          </p>
        )}
      </details>
    </section>
  );
}
