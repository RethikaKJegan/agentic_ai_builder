"use client";
import { displayText } from "@/lib/display-text";
import { fieldMessages, InputError } from "@/api/feedback";
import { useRef, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { api, ApiError, type RunRecord } from "@/api/client";
import { useBackend } from "@/api/state";
import type { CanonicalWorkflow } from "@/api/contracts.generated";
import { Link } from "@/lib/navigation";
import { ApiFeedback } from "./ApiFeedback";
import { parseRunInputs, eventOnly } from "./run-inputs";

export function RunWorkflowDialog({ workflow, onClose }: { workflow: CanonicalWorkflow; onClose: () => void }) {
  const backend = useBackend(); const [values, setValues] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false); const [error, setError] = useState<Error>(); const [run, setRun] = useState<RunRecord>();
  const executionKey = useRef<string | undefined>(undefined);
  const submitting = useRef(false); const submittedPayload = useRef<string | undefined>(undefined);
  const automatic = eventOnly(workflow);
  const blocker = !backend.can("workflow.execute") ? "workflow.execute permission is required." : !backend.session?.runtime_available ? "The runtime is unavailable." : workflow.status !== "published" ? "A published revision is required." : automatic ? "This workflow waits for its configured event. Activate it, create an event in its source, then check Runs." : "";
  const submit = async () => {
    if (submitting.current || blocker || run) return;
    try {
      const inputs = parseRunInputs(workflow.inputs, values); const serialized = JSON.stringify(inputs);
      if (submittedPayload.current && submittedPayload.current !== serialized) throw new InputError("The earlier run request has an uncertain outcome. Keep these inputs and retry, or check Runs before starting different inputs.");
      submitting.current = true; setBusy(true); setError(undefined);
      submittedPayload.current = serialized;
      // One explicit dialog is one execution intent. Retries keep this key;
      // reopening Run must not return an older terminal run for identical inputs.
      executionKey.current ??= crypto.randomUUID();
      setRun((await api.request("execute_workflow", { workflow_id: workflow.workflow_id, workflow_version: workflow.version, inputs }, executionKey.current)).run);
      void backend.refreshOverview();
    } catch (caught) {
      if (caught instanceof ApiError && ["INVALID_INPUT", "OPERATION_NOT_AUTHORIZED", "REVISION_CONFLICT", "WORKFLOW_NOT_FOUND", "REVISION_NOT_PUBLISHED"].includes(caught.error.error_code)) submittedPayload.current = undefined;
      setError(caught instanceof Error ? caught : new InputError("Run submission failed."));
    }
    finally { submitting.current = false; setBusy(false); }
  };
  return <Dialog open onOpenChange={open => { if (!open && !submitting.current) onClose(); }}>
    <DialogContent className="max-h-[85vh] w-[calc(100vw-2rem)] overflow-y-auto" onEscapeKeyDown={event => { if (busy) event.preventDefault(); }} onPointerDownOutside={event => { if (busy) event.preventDefault(); }}>
      <DialogHeader><DialogTitle>Run {displayText(workflow.name)}</DialogTitle><DialogDescription>Published revision v{workflow.version}. Submission starts real execution subject to its approval and budget policies.</DialogDescription></DialogHeader>
      {blocker && <p role="status" className="text-sm text-muted-foreground">{blocker}</p>}
      {!run && !automatic && <form onSubmit={event => { event.preventDefault(); void submit(); }} className="space-y-3" noValidate>
        {workflow.inputs.map(field => <label key={field.name} className="block text-sm">{displayText(field.name)}{field.required ? " (required)" : " (optional)"}<span className="block text-xs text-muted-foreground">{displayText(field.description)} · {field.type}</span>
          {field.type === "boolean" ? <select aria-label={displayText(field.name)} aria-invalid={fieldMessages(error,`inputs.${field.name}`).length>0} aria-describedby={fieldMessages(error,`inputs.${field.name}`).length?`run-input-${field.name}-error`:undefined} disabled={busy} className="mt-1 w-full rounded border bg-background p-2" value={values[field.name] ?? ""} onChange={event => setValues(current => ({ ...current, [field.name]: event.target.value }))}><option value="">Choose…</option><option value="true">True</option><option value="false">False</option></select>
            : field.type === "array" || field.type === "object" ? <textarea aria-label={displayText(field.name)} aria-invalid={fieldMessages(error,`inputs.${field.name}`).length>0} aria-describedby={fieldMessages(error,`inputs.${field.name}`).length?`run-input-${field.name}-error`:undefined} disabled={busy} className="mt-1 w-full rounded border bg-background p-2 font-mono" value={values[field.name] ?? ""} placeholder={field.type === "array" ? "[]" : "{}"} onChange={event => setValues(current => ({ ...current, [field.name]: event.target.value }))} />
              : <input aria-label={displayText(field.name)} aria-invalid={fieldMessages(error,`inputs.${field.name}`).length>0} aria-describedby={fieldMessages(error,`inputs.${field.name}`).length?`run-input-${field.name}-error`:undefined} disabled={busy} inputMode={field.type === "integer" ? "numeric" : field.type === "number" ? "decimal" : "text"} className="mt-1 w-full rounded border bg-background p-2" value={values[field.name] ?? ""} onChange={event => setValues(current => ({ ...current, [field.name]: event.target.value }))} />}
          {fieldMessages(error,`inputs.${field.name}`).map((message,index)=><span key={index} id={`run-input-${field.name}-error`} className="mt-1 block text-xs text-destructive">{displayText(message)}</span>)}
        </label>)}
        <button type="submit" disabled={busy || !!blocker} className="rounded-lg bg-primary px-4 py-2 text-primary-foreground disabled:opacity-40">{busy ? "Submitting…" : "Start run"}</button>
      </form>}
      <ApiFeedback error={error} />
      {run && <p role="status" className="text-sm">Run {run.run_id} · {run.status}. <Link to="/app/runs" search={{ run: run.run_id }} className="text-primary underline">View run details</Link></p>}
      <button type="button" disabled={busy} onClick={onClose} className="rounded-lg border px-3 py-2 text-sm disabled:opacity-40">{run ? "Close" : "Cancel"}</button>
    </DialogContent>
  </Dialog>;
}
