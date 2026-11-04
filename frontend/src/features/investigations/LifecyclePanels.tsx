import { useState } from "react";
import { type BusinessCase, type EvidenceValue, words } from "@/api/business-lifecycle";
import { containsSecret } from "@/api/client";

export function SavedDetails({
  value,
  label = "Saved details",
}: {
  value: unknown;
  label?: string;
}) {
  return (
    <details className="min-w-0 rounded-lg border p-3 text-sm">
      <summary className="cursor-pointer font-medium">{label}</summary>
      <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap break-words text-xs">
        {containsSecret(value) ? "Sensitive data withheld." : JSON.stringify(value, null, 2)}
      </pre>
    </details>
  );
}
export function Outcome({ value }: { value: string }) {
  return (
    <span
      className={`inline-block rounded-full border px-2 py-0.5 text-xs ${["FAILED", "BLOCKED"].includes(value) ? "border-destructive/40 text-destructive" : value.includes("PROVISIONAL") ? "border-warning/40" : "border-border"}`}
    >
      {words(value)}
    </span>
  );
}
export function EvidenceEntry({ name, entry }: { name: string; entry: EvidenceValue }) {
  return (
    <article className="min-w-0 rounded-lg border p-3">
      <div className="flex flex-wrap items-center gap-2">
        <h4 className="text-sm font-medium">{words(name)}</h4>
        <Outcome value={entry.provenance_type} />
      </div>
      <p className="mt-2 whitespace-pre-wrap break-words text-sm">
        {containsSecret(entry.value)
          ? "Sensitive data withheld."
          : typeof entry.value === "string"
            ? entry.value
            : JSON.stringify(entry.value)}
      </p>
      <p className="mt-2 text-xs text-muted-foreground">
        {words(entry.generation_method)}
        {entry.confidence !== null ? ` · Confidence ${entry.confidence}` : ""}
      </p>
      {entry.assumptions.map((a, i) => (
        <p className="mt-1 text-xs" key={i}>
          Assumption: {a}
        </p>
      ))}
      {entry.limitations.map((a, i) => (
        <p className="mt-1 text-xs text-muted-foreground" key={i}>
          {a}
        </p>
      ))}
      <div className="mt-3">
        <SavedDetails label="Sources and mapping references" value={entry.source_references} />
      </div>
    </article>
  );
}
export function LifecycleStages({ value }: { value: BusinessCase }) {
  return (
    <div className="space-y-3">
      {value.process_definition.stages.map((definition, index) => {
        const stage = value.stages[definition.stage_instance_id];
        if (!stage)
          return (
            <p role="alert" key={definition.stage_instance_id}>
              Pinned stage state is unavailable.
            </p>
          );
        const waits = Object.values(value.waits).filter(
          (w) => w["stage_instance_id"] === definition.stage_instance_id,
        );
        return (
          <details
            data-testid="lifecycle-stage"
            key={definition.stage_instance_id}
            className="min-w-0 rounded-xl border p-4"
          >
            <summary className="cursor-pointer">
              <span className="mr-2 text-xs text-muted-foreground">{index + 1}.</span>
              <span className="text-sm font-medium">{definition.name}</span>
              <span className="ml-3 inline-flex">
                <Outcome
                  value={
                    stage.business_outcome_status === "SKIPPED" ? "SKIPPED" : stage.execution_status
                  }
                />
              </span>
            </summary>
            <div className="mt-4 space-y-3 text-sm">
              <p>
                Business outcome: <Outcome value={stage.business_outcome_status} />
              </p>
              <p>Real-world activity: {words(stage.real_world_status)}</p>
              <p>
                Capabilities:{" "}
                {definition.required_capabilities.join(", ") || "Structured analytical stage"}
              </p>
              <p>
                Dependencies:{" "}
                {definition.dependency_definitions
                  .map((id) => value.stages[id]?.definition.name ?? id)
                  .join(" · ") || "None"}
              </p>
              <p>
                Inputs available: {Object.keys(stage.resolved_inputs).length} · Outputs available:{" "}
                {Object.keys(stage.outputs).length}
              </p>
              <p className="text-xs text-muted-foreground">
                {stage.created_at ? `Created ${stage.created_at}` : ""}
                {stage.updated_at ? ` · Updated ${stage.updated_at}` : ""}
                {value.execution_history.find(
                  (e) =>
                    e["stage_instance_id"] === definition.stage_instance_id &&
                    e["target"] === "RUNNING",
                )?.["timestamp"]
                  ? ` · Started ${String(value.execution_history.find((e) => e["stage_instance_id"] === definition.stage_instance_id && e["target"] === "RUNNING")?.["timestamp"])}`
                  : ""}
                {stage.completed_at ? ` · Completed ${stage.completed_at}` : ""}
              </p>
              {Object.entries(stage.outputs).map(([name, entry]) => (
                <EvidenceEntry key={name} name={name} entry={entry} />
              ))}
              {waits.length > 0 && <SavedDetails label="Stage events and waits" value={waits} />}
              <SavedDetails label="Inputs and provenance" value={stage.resolved_inputs} />
              {(stage.errors.length > 0 || stage.retry_history.length > 0) && (
                <SavedDetails
                  label="Errors and recovery"
                  value={{ errors: stage.errors, recovery: stage.retry_history }}
                />
              )}
            </div>
          </details>
        );
      })}
    </div>
  );
}
export function LifecycleEvidence({ value }: { value: BusinessCase }) {
  return (
    <section className="space-y-4">
      <h3 className="text-lg font-medium">Evidence and assumptions</h3>
      <p className="text-sm text-muted-foreground">
        ACTUAL records an identified source or user assertion. DERIVED is calculated. INFERRED is
        interpretation. SYNTHETIC is a case-local assumption. These labels do not independently
        confirm physical activity.
      </p>
      {value.process_definition.stages.map((d) => (
        <details key={d.stage_instance_id} className="rounded-xl border p-4">
          <summary className="cursor-pointer text-sm font-medium">{d.name}</summary>
          <div className="mt-3 grid min-w-0 gap-3 lg:grid-cols-2">
            {Object.entries(value.stages[d.stage_instance_id]?.resolved_inputs ?? {}).map(
              ([name, entry]) => (
                <EvidenceEntry key={name} name={name} entry={entry} />
              ),
            )}
          </div>
        </details>
      ))}
      <SavedDetails value={value.conflicts} label="Conflicts and stale conclusions" />
    </section>
  );
}
export function LifecycleReport({
  value,
  report,
}: {
  value: BusinessCase;
  report: Record<string, unknown>;
}) {
  return (
    <section className="space-y-4">
      <h3 className="text-lg font-medium">Analytical lifecycle report</h3>
      <p className="text-sm">{value.original_user_goal}</p>
      <p className="break-words text-xs text-muted-foreground">
        Case {value.case_id} · {value.client_id} · {value.process_definition_id} v
        {value.process_definition_version}
      </p>
      <div className="flex flex-wrap gap-3">
        <p className="text-sm">
          Execution: <Outcome value={value.execution_status} />
        </p>
        <p className="text-sm">
          Business outcome: <Outcome value={value.business_outcome_status} />
        </p>
      </div>
      <p className="rounded-lg border border-warning/30 p-3 text-sm">
        {String(
          report["qualification"] ??
            "Analytical results retain their provenance. Physical activities and business authority require actual confirmation.",
        )}
      </p>
      <LifecycleStages value={value} />
      <SavedDetails label="Evidence sources" value={report["evidence_references"]} />
      <SavedDetails label="Generated assumptions" value={report["generated_assumptions"]} />
      <SavedDetails
        label="Pending real-world activities"
        value={report["pending_real_world_waits"]}
      />
      <SavedDetails
        label="Recovery and reassessment history"
        value={{ timeline: report["timeline"], reassessments: report["reassessments"] }}
      />
    </section>
  );
}
export function EventForm({
  wait,
  onSubmit,
  disabled,
}: {
  wait: Record<string, unknown>;
  onSubmit: (body: Record<string, unknown>) => void;
  disabled: boolean;
}) {
  const [eventId, setEventId] = useState("");
  const [payload, setPayload] = useState("");
  const [error, setError] = useState("");
  return (
    <form
      className="mt-3 space-y-3"
      onSubmit={(e) => {
        e.preventDefault();
        try {
          const parsed: unknown = JSON.parse(payload);
          if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error();
          setError("");
          onSubmit({
            event_id: eventId,
            event_type: wait["event_type"],
            source: wait["expected_source"],
            correlation_keys: wait["correlation_keys"],
            payload: parsed,
          });
        } catch {
          setError(
            "Provide an actual source event ID and a JSON object matching the saved event schema.",
          );
        }
      }}
    >
      <label className="block text-xs">
        Source event ID
        <input
          required
          maxLength={128}
          value={eventId}
          onChange={(e) => setEventId(e.target.value)}
          className="mt-1 w-full rounded-lg border bg-background p-2"
        />
      </label>
      <label className="block text-xs">
        Actual event payload
        <textarea
          required
          value={payload}
          onChange={(e) => setPayload(e.target.value)}
          rows={3}
          className="mt-1 w-full rounded-lg border bg-background p-2 font-mono"
        />
      </label>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      <button
        disabled={disabled}
        className="rounded-lg border px-3 py-2 text-sm disabled:opacity-40"
      >
        Record source event
      </button>
    </form>
  );
}
