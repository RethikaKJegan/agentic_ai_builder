"use client";
import { RunKnowledge, RecoveryEvidence, OperationalAlerts } from "./ReliabilityEvidence";
import { subwayDisplay, subwayDisplayJson } from "@/domain/subway-presentation";
import { useBackend } from "@/api/state";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { taskStateLabels, type CompositionView, type CompositionTask } from "@/api/compositions";
const object = (v: unknown): Record<string, unknown> =>
  v && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : {};
const words = (s: string) => s.replaceAll("_", " ").replace(/([a-z])([A-Z])/g, "$1 $2");
const show = (v: unknown) => (typeof v === "string" ? v : JSON.stringify(v));
function Details({ value, label = "Technical details" }: { value: unknown; label?: string }) {
  const workspace = useBackend((s) => s.session?.auth.subject.workspace_id);
  return (
    <details className="rounded-lg border p-3">
      <summary className="cursor-pointer text-sm">{label}</summary>
      <pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap break-all text-xs">
        {subwayDisplayJson(value, workspace)}
      </pre>
    </details>
  );
}
export function ToolReceipt({
  value,
  fallbackTool,
}: {
  value: unknown;
  fallbackTool?: string | undefined;
}) {
  const entry = value && typeof value === "object" ? (value as Record<string, unknown>) : {};
  const receipt =
    entry["receipt"] && typeof entry["receipt"] === "object"
      ? (entry["receipt"] as Record<string, unknown>)
      : {};
  const tool = typeof entry["tool_id"] === "string" ? entry["tool_id"] : fallbackTool;
  const labels: Record<string, string> = {
    business_retrieve_evidence: "Database read",
    database_read_query: "Database query",
    database_read_record: "Database record read",
    extension_sheets_create_report: "Google Sheets report",
    extension_mail_send: "Gmail send",
    extension_mail_draft: "Gmail draft",
    extension_calendar_create: "Google Calendar event",
  };
  const count = receipt["returned_records"];
  const websites = Array.isArray(receipt["web_sources"]) ? receipt["web_sources"].map(object) : [];
  const collections = Array.isArray(receipt["collections"])
    ? receipt["collections"].filter((c): c is string => typeof c === "string")
    : [];
  return (
    <article className="space-y-2 rounded-lg border p-3 text-sm">
      <p className="font-medium">
        {tool ? (labels[tool] ?? words(tool)) : "Recorded tool execution"}
      </p>
      {typeof count === "number" && (
        <p>{count === 0 ? "No matching records." : `${count} record(s) retrieved.`}</p>
      )}
      {collections.length > 0 && <p>Source collections: {collections.map(words).join(", ")}</p>}
      {(["rows", "messages", "events"] as const).map((kind) =>
        typeof receipt["returned_" + kind] === "number" ? (
          <p key={kind}>
            {receipt["returned_" + kind] as number} {kind} returned.
          </p>
        ) : null,
      )}
      {websites.map((site, i) => {
        const url =
          typeof site["url"] === "string" && /^https?:\/\//.test(site["url"]) ? site["url"] : null;
        return (
          <section key={i} className="space-y-2 rounded-lg bg-muted/30 p-3">
            <h4 className="font-medium">
              {typeof site["title"] === "string" ? site["title"] : "Website source"}
            </h4>
            {url && (
              <a
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className="block break-all text-xs text-primary underline"
              >
                {url}
              </a>
            )}
            {typeof site["snippet"] === "string" && (
              <div>
                <p className="text-xs font-medium">Search result snippet</p>
                <p className="mt-1 whitespace-pre-wrap text-sm">{site["snippet"]}</p>
              </div>
            )}
            {typeof site["text"] === "string" ? (
              <details>
                <summary className="cursor-pointer text-xs font-medium">
                  Extracted page content
                </summary>
                <p className="mt-2 max-h-72 overflow-auto whitespace-pre-wrap break-words text-xs">
                  {site["text"]}
                </p>
                {site["truncated"] === true && (
                  <p className="text-xs text-muted-foreground">
                    Content was truncated during retrieval.
                  </p>
                )}
              </details>
            ) : (
              <p className="text-xs text-muted-foreground">
                Search snippet only; no page content recorded in this receipt.
              </p>
            )}
            {typeof site["retrieved_at"] === "string" && (
              <p className="text-xs text-muted-foreground">Retrieved {site["retrieved_at"]}</p>
            )}
          </section>
        );
      })}
      {Object.keys(receipt).length > 0 ? (
        <Details
          value={{ ...(tool ? { tool_id: tool } : {}), receipt }}
          label="Tool response receipt"
        />
      ) : (
        <p className="text-muted-foreground">No receipt details were recorded for this tool.</p>
      )}
    </article>
  );
}
export function TaskResult({
  task: sourceTask,
  onSource,
}: {
  task: CompositionTask;
  onSource?: (id: string) => void;
}) {
  const workspace = useBackend((s) => s.session?.auth.subject.workspace_id);
  const task = subwayDisplay(sourceTask, workspace);
  const result = task.result;
  if (!result)
    return (
      <p className="text-sm text-muted-foreground">
        {["failed", "blocked", "cancelled", "interrupted"].includes(task.state)
          ? "No result recorded. Review the task status and errors below."
          : "Awaiting execution. Results will appear here."}
      </p>
    );
  return (
    <div className="space-y-4">
      {result.summary && (
        <p className="text-sm leading-relaxed">
          {result.classification === "query_clarification"
            ? "The query was blocked before execution because required meaning or supported query capability was unavailable."
            : result.summary}
        </p>
      )}
      {result.findings?.map((f, i) => (
        <article key={i} className="rounded-lg border p-3 text-sm">
          <p>{f.statement}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {f.references.map((r, j) =>
              onSource ? (
                <button
                  key={j}
                  className="text-xs text-primary underline"
                  onClick={() => onSource(r.record_id)}
                >
                  Source {j + 1}
                </button>
              ) : (
                <span key={j} className="text-xs text-muted-foreground">
                  Source {j + 1}
                </span>
              ),
            )}
          </div>
        </article>
      ))}
      {!!result.records.length && (
        <p className="text-sm">Retrieved {result.records.length} mapped source record(s).</p>
      )}
      {!!result.missing_information?.length && (
        <section>
          <h3 className="text-sm font-medium">
            {workspace === "client-subway" ? "Evidence notes" : "Evidence limitations"}
          </h3>
          <p className="mt-2 text-sm">
            Required evidence or query meaning has not been established. This task remains limited
            or blocked; no additional answer is requested here.
          </p>
        </section>
      )}
      {!!result.tool_receipts.length && (
        <section>
          <h3 className="text-sm font-medium">Connected tool results</h3>
          {result.tool_receipts.map((receipt, i) => (
            <ToolReceipt key={i} value={receipt} fallbackTool={task.tools[0]} />
          ))}
        </section>
      )}
      {result.records.length === 0 &&
        task.kind === "retrieval" &&
        task.tools.some((t) => /database|query|retrieve/.test(t)) && (
          <p className="text-sm text-muted-foreground">
            No individual records attached. Aggregate results, when available, appear in the
            recorded output.
          </p>
        )}
      {result.rule_results.length > 0 && (
        <Details value={result.rule_results} label="Applied rule results" />
      )}
      {result.rule_results.length === 0 && (
        <p className="text-xs text-muted-foreground">
          No business rule results attached to this task.
        </p>
      )}
      {result.coverage && (
        <Details value={result.coverage} label="Evidence requirements and readiness" />
      )}
    </div>
  );
}
export function CompositionReport({ view: sourceView }: { view: CompositionView }) {
  const workspace = useBackend((s) => s.session?.auth.subject.workspace_id);
  const view = subwayDisplay(sourceView, workspace);
  const results = view.tasks.filter((t) => t.result);
  const gaps = [...new Set(results.flatMap((t) => t.result?.missing_information ?? []))];
  const blocked = results.some(
    (t) => t.state === "needs_input" || t.result?.coverage?.["conclusion_ready"] === false,
  );
  const records = [
    ...new Map(
      results.flatMap((t) => t.result?.records ?? []).map((r) => [r.record_id, r]),
    ).values(),
  ];
  return (
    <article className="mx-auto max-w-5xl space-y-7 p-5 md:p-8">
      <header>
        <h2 className="text-xl font-semibold">
          {view.run?.status === "completed"
            ? gaps.length || blocked
              ? "Investigation completed — additional evidence required"
              : "Investigation completed"
            : "Investigation results so far"}
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Source observations, model interpretations and business authorization remain distinct.
        </p>
      </header>
      {results.map((t) => (
        <section key={t.id} className="space-y-3">
          <h3 className="font-medium">{t.label}</h3>
          <TaskResult
            task={t}
            onSource={(id) => {
              const source = document.getElementById("source-" + id) as HTMLDetailsElement | null;
              if (source) {
                source.open = true;
                source.scrollIntoView({ behavior: "smooth", block: "center" });
              }
            }}
          />
        </section>
      ))}
      <section>
        <h3 className="mb-3 font-medium">Supporting source records</h3>
        {records.map((r) => (
          <details
            id={"source-" + r.record_id}
            key={r.record_id}
            className="mb-3 rounded-lg border p-3"
          >
            <summary className="cursor-pointer text-sm">
              {words(r.collection ?? "Source")} · {r.record_id}
            </summary>
            <dl className="mt-3 space-y-2 text-xs">
              {Object.entries(r.values).map(([k, v]) => (
                <div key={k}>
                  <dt className="text-muted-foreground">{words(k.replace(/^mapping:/, ""))}</dt>
                  <dd className="mt-1 whitespace-pre-wrap break-words">{show(v)}</dd>
                </div>
              ))}
            </dl>
            {r.read_at && <p className="mt-3 text-xs text-muted-foreground">Read at {r.read_at}</p>}
          </details>
        ))}
        {!records.length && (
          <p className="text-sm text-muted-foreground">
            No individual records are attached to this report. Aggregate query results are shown
            separately.
          </p>
        )}
      </section>
      {!!view.run?.actions.length && (
        <section>
          <h3 className="font-medium">Tool execution receipts</h3>
          {view.run.actions.map((a) => (
            <div key={a.node_id} className="mt-3 rounded-lg border p-3 text-sm">
              <p>
                {a.label} · {taskStateLabels[a.state] ?? a.state}
              </p>
              {Object.keys(a.receipt).length > 0 ? (
                <Details value={a.receipt} label="Recorded tool result" />
              ) : (
                <p className="mt-2 text-muted-foreground">
                  {["pending", "queued", "running", "executing", "paused_for_approval"].includes(
                    a.state,
                  )
                    ? "Tool has not returned a result yet."
                    : "No receipt details were recorded for this tool."}
                </p>
              )}
            </div>
          ))}
        </section>
      )}
      {view.run?.outcome && (
        <Details value={view.run.outcome} label="Outcome, duration and usage" />
      )}
    </article>
  );
}
export function CompositionInspector({
  view: sourceView,
  section,
  onClose,
}: {
  view: CompositionView;
  section: string | null;
  onClose: () => void;
}) {
  const backend = useBackend();
  const view = subwayDisplay(sourceView, backend.session?.auth.subject.workspace_id);
  const diagnosticScope = JSON.stringify(backend.session?.auth ?? null);
  const task = view.tasks.find((t) => t.id === section || t.approval_gate?.id === section);
  const title =
    (task?.approval_gate?.id === section ? task.approval_gate.label : task?.label) ??
    (section === "knowledge"
      ? "Business knowledge and evidence"
      : section === "memory"
        ? "Memory and recovery"
        : section === "agents"
          ? "Agents and tools"
          : "Goal coordinator");
  const knowledgeTasks = Object.values(
    (view.knowledge["tasks"] ?? {}) as Record<string, Record<string, unknown>>,
  );
  const concepts = knowledgeTasks.flatMap((t) =>
    Array.isArray(t["concepts"]) ? (t["concepts"] as Record<string, unknown>[]) : [],
  );
  const uniqueConcepts = [...new Map(concepts.map((c) => [String(c["id"]), c])).values()];
  return (
    <Sheet
      open={section !== null}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <SheetContent className="w-full overflow-y-auto sm:max-w-xl">
        <SheetHeader>
          <SheetTitle>{title}</SheetTitle>
          {task?.detail_error&&<p role="alert" className="text-sm text-destructive">{task.detail_error}</p>}
          {task?.unparsed_result!==undefined&&<Details value={task.unparsed_result} label="Unparsed saved details"/>}
          <SheetDescription>
            {task?.result?.classification === "query_clarification"
              ? "Query blocked"
              : task
                ? (taskStateLabels[task.state] ?? task.state)
                : "Saved context and actual execution state for this workflow."}
          </SheetDescription>
        </SheetHeader>
        <div className="mt-6 space-y-5">
          {task && (
            <>
              <TaskResult task={task} />
              <section>
                <h3 className="text-sm font-medium">Dependencies</h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  {task.depends_on
                    .map((id) => view.tasks.find((t) => t.id === id)?.label ?? id)
                    .join(" · ") || "No preceding specialist task"}
                </p>
              </section>
              <section>
                <h3 className="text-sm font-medium">Tools</h3>
                <p className="mt-2 text-sm">
                  {task.tools.map(words).join(", ") || "Analysis only"}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Execution requires current Registry authorization.
                </p>
              </section>
              {(task.result?.classification === "query_clarification" ? [] : task.errors).map(
                (e, i) => (
                  <div
                    key={i}
                    role="alert"
                    className="rounded-lg border border-destructive/30 p-3 text-sm"
                  >
                    <p>{words(e.category)}</p>
                    <p className="mt-1 text-xs">{words(e.recovery_strategy)}</p>
                  </div>
                ),
              )}
              <section className="space-y-2 text-sm">
                <h3 className="font-medium">Task configuration</h3>
                <p>Capability: {words(task.capability_id)}</p>
                {task.agent_id && (
                  <p className="text-xs text-muted-foreground">Agent: {task.agent_id}</p>
                )}
                <p className="text-xs text-muted-foreground">
                  {task.required_evidence.length
                    ? `${task.required_evidence.length} evidence requirement(s)`
                    : "No separate evidence requirements configured."}
                </p>
                {task.completion_criteria.map((criterion, i) => (
                  <p key={i} className="text-xs">
                    {criterion}
                  </p>
                ))}
              </section>
              {view.run?.action_instances?.[task.id] && (
                <Details
                  value={view.run.action_instances[task.id]}
                  label="Recorded inputs, output and provenance"
                />
              )}
              <Details
                value={{
                  ...(task.agent_id ? { agent_id: task.agent_id } : {}),
                  capability: task.capability_id,
                  ...(task.required_evidence.length
                    ? { required_evidence: task.required_evidence }
                    : {}),
                  completion_criteria: task.completion_criteria,
                  ...(task.result
                    ? {
                        result: Object.fromEntries(
                          Object.entries(task.result).filter(
                            ([, v]) => v !== null && (!Array.isArray(v) || v.length > 0),
                          ),
                        ),
                      }
                    : {}),
                }}
              />
            </>
          )}
          {section === "knowledge" && (
            <>
              {view.run && <RunKnowledge key={diagnosticScope} runId={view.run.run_id} />}
              <h3 className="font-medium">Concepts selected for this goal</h3>
              <div className="flex flex-wrap gap-2">
                {uniqueConcepts.map((c) => (
                  <span key={String(c["id"])} className="rounded-full border px-3 py-1 text-xs">
                    {words(String(c["label"] ?? c["id"]))}
                  </span>
                ))}
              </div>
              <p className="text-sm text-muted-foreground">
                The backend resolves required relationships, field mappings and evidence before
                planning. Exact definitions and version pins are available below.
              </p>
              <Details value={view.knowledge} />
            </>
          )}
          {section === "agents" && (
            <>
              <p className="text-sm">
                The coordinator delegates ready tasks to these task-specific specialists.
              </p>
              {view.tasks.map((t) => (
                <article
                  key={t.id}
                  className="block w-full rounded-lg border p-3 text-left text-sm"
                >
                  <span className="font-medium">{t.label}</span>
                  <span className="mt-1 block text-xs text-muted-foreground">
                    {t.tools.map(words).join(", ") || "Evidence analysis"} ·{" "}
                    {taskStateLabels[t.state] ?? t.state}
                  </span>
                </article>
              ))}
              <Details
                value={{
                  master: view.master,
                  tasks: view.tasks.map((t) => ({
                    agent_id: t.agent_id,
                    capability: t.capability_id,
                    depends_on: t.depends_on,
                    tools: t.tools,
                  })),
                }}
                label="Agent configuration and hierarchy"
              />
            </>
          )}
          {section === "memory" && (
            <>
              {view.run && <RecoveryEvidence key={diagnosticScope} runId={view.run.run_id} />}
              <p className="text-sm text-muted-foreground">
                Working memory tracks this run. Reusable experience is available to relevant agents
                only after validation; it does not supply business facts or permissions.
              </p>
              {!view.run && (
                <p className="text-sm">
                  Run the investigation to inspect its working memory and recovery history.
                </p>
              )}
              {view.run && (
                <>
                  <p className="text-sm">Recovery attempts: {view.run.recovery_history.length}</p>
                  <p className="text-sm">{view.recovery.reason}</p>
                  {view.run.failures.map((f, i) => (
                    <p key={i} className="rounded-lg border p-3 text-sm">
                      {words(f.category)} · {words(f.recovery_strategy)}
                    </p>
                  ))}
                  <Details value={view.memory} label="Scoped working memory" />
                  <Details value={view.run.recovery_history} label="Recovery history" />
                  <Details value={view.run.outcome} label="Outcome evaluation" />
                  {backend.session?.auth.roles.includes("admin") && <OperationalAlerts />}
                </>
              )}
            </>
          )}
          {section === "coordinator" && (
            <>
              <p className="text-sm">
                The coordinator starts independent ready tasks, waits for dependencies and combines
                their actual results.
              </p>
              <section className="space-y-4 rounded-xl border p-4">
                <div>
                  <h3 className="text-sm font-semibold">Workflow goal</h3>
                  <p className="mt-2 text-sm">{view.objective}</p>
                </div>
                <p className="text-sm">
                  Status:{" "}
                  {taskStateLabels[view.run?.status ?? view.workflow_status ?? view.state] ??
                    words(view.run?.status ?? view.workflow_status ?? view.state)}
                </p>
                <p className="text-xs text-muted-foreground">
                  {view.master
                    ? "Saved coordinator agent configuration is available below."
                    : "This node represents the saved workflow plan. Execution follows the task dependencies below."}
                </p>
                <h3 className="text-sm font-semibold">Task dependencies</h3>
                {view.tasks.map((t) => (
                  <div key={t.id} className="rounded-lg bg-muted/40 p-3 text-sm">
                    <p className="font-medium">{t.label}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {t.depends_on.length
                        ? "After: " +
                          t.depends_on
                            .map((id) => view.tasks.find((task) => task.id === id)?.label ?? id)
                            .join(", ")
                        : "Ready independently when execution starts"}{" "}
                      · {taskStateLabels[t.state] ?? t.state}
                    </p>
                  </div>
                ))}
              </section>
              {view.master && (
                <Details value={view.master} label="Coordinator agent configuration" />
              )}
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
