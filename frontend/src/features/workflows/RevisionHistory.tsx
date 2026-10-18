"use client";
import { displayText } from "@/lib/display-text";
import { useRef, useState } from "react";
import { api } from "@/api/client";
import type { CanonicalWorkflow } from "@/api/contracts.generated";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { ApiFeedback } from "./ApiFeedback";
export function RevisionHistory({ workflowId, latest, open, onClose }: { workflowId: string; latest: number; open: boolean; onClose: () => void }) {
  const [version, setVersion] = useState(String(latest)); const [document, setDocument] = useState<CanonicalWorkflow>();
  const [busy, setBusy] = useState(false); const pending = useRef(false); const [error, setError] = useState<Error>();
  const load = async () => {
    const number = Number(version); if (pending.current) return;
    if (!Number.isSafeInteger(number) || number < 1 || number > latest) { setError(new Error(`Choose a saved revision from 1 to ${latest}.`)); return; }
    pending.current = true; setBusy(true); setError(undefined);
    try { setDocument((await api.request("get_workflow", { workflow_id: workflowId, workflow_version: number })).workflow); }
    catch (caught) { setError(caught instanceof Error ? caught : new Error("The revision could not be loaded.")); }
    finally { pending.current = false; setBusy(false); }
  };
  return <Dialog open={open} onOpenChange={value => { if (!value) onClose(); }}><DialogContent className="max-h-[85vh] w-[calc(100vw-2rem)] overflow-y-auto"><DialogHeader><DialogTitle>Saved workflow revisions</DialogTitle><DialogDescription>View server revisions without replacing your current draft. Latest saved revision: v{latest}.</DialogDescription></DialogHeader>
    <form onSubmit={event => { event.preventDefault(); void load(); }} className="flex flex-wrap items-end gap-2"><label className="text-sm">Revision<input aria-label="Saved revision number" type="number" min={1} max={latest} value={version} onChange={event => setVersion(event.target.value)} className="mt-1 block w-24 rounded border bg-background p-2" /></label><button disabled={busy} className="rounded border px-3 py-2 text-sm">{busy ? "Loading…" : "View revision"}</button></form>
    <ApiFeedback error={error} />{document && <div><p role="status">v{document.version} · {document.status} · {document.nodes.length} steps</p><pre aria-label="Saved revision document" className="mt-2 max-h-80 overflow-auto whitespace-pre-wrap rounded bg-muted p-3 text-xs">{displayText(JSON.stringify(document, null, 2))}</pre></div>}
  </DialogContent></Dialog>;
}
