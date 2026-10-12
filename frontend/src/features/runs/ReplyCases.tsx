"use client";
import { useEffect, useState } from "react";
import { useBackend } from "@/api/state";

type Kind = "customer_followup" | "manager_notice" | "confirm_closure";
type Preview = { to: string; subject: string; body: string };
type Reply = { reply_id: string; from_email: string; body: string; decision: string; reason: string;
  previews: Partial<Record<Kind, Preview>>; actions: Partial<Record<Kind, string>>;
  job?: { state: string; error_code?: string } | null };
type Case = { case_id: string; review_id: string; order_id: string; customer_email: string;
  status: string; replies: Reply[]; automatic?: boolean };
type Envelope = { status: number; data: { items?: Case[]; monitor?: { state: string; error_code?: string }; error?: { message?: string } } };

const labels: Record<Kind, string> = {
  customer_followup: "Approve and send customer follow-up",
  manager_notice: "Approve and notify manager",
  confirm_closure: "Confirm closure and notify manager",
};

export function ReplyCases() {
  const backend = useBackend();
  const [cases, setCases] = useState<Case[]>([]);
  const [error, setError] = useState("");
  const [monitor, setMonitor] = useState("");
  const [busy, setBusy] = useState(false);
  const refresh = async () => {
    try {
      const response = await fetch("/api/backend/cases", { cache: "no-store" });
      const result = await response.json() as Envelope;
      if (!response.ok || !result.data.items) throw new Error(result.data.error?.message || "Cases unavailable");
      setCases(result.data.items); setMonitor(result.data.monitor?.state || "unknown"); setError("");
    } catch (failure) { setError(failure instanceof Error ? failure.message : "Cases unavailable"); }
  };
  useEffect(() => {
    if (backend.status !== "connected") return;
    void refresh();
    const timer = window.setInterval(() => void refresh(), 15000);
    return () => window.clearInterval(timer);
  }, [backend.status]);
  const act = async (caseId: string, replyId: string, kind: Kind) => {
    if (busy) return;
    setBusy(true);
    try {
      const response = await fetch(`/api/backend/cases/${encodeURIComponent(caseId)}/actions`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ reply_id: replyId, kind }),
      });
      const result = await response.json() as Envelope;
      if (!response.ok) throw new Error(result.data.error?.message || "Email submission failed");
      await refresh();
    } catch (failure) { setError(failure instanceof Error ? failure.message : "Email submission failed"); }
    finally { setBusy(false); }
  };
  if (backend.status !== "connected") return null;
  return <section className="mt-8 space-y-4" aria-label="Customer reply cases">
    <div className="flex items-center justify-between"><h2 className="text-xl font-semibold">Customer replies</h2>
      <button type="button" className="rounded border px-3 py-1 text-sm" onClick={() => void refresh()}>Refresh</button></div>
    {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
    {monitor === "error" && <p role="alert" className="text-sm text-red-600">Inbox polling failed. Check the backend Gmail IMAP connection.</p>}
    {cases.length === 0 && !error && <p className="text-sm text-muted-foreground">No sent customer cases yet.</p>}
    {cases.map((item) => <article key={item.case_id} className="space-y-3 rounded-lg border p-4">
      <p className="font-medium">{item.review_id || item.case_id} · {item.order_id} · {item.status}</p>
      <p className="text-sm">Customer: {item.customer_email}</p>
      {item.automatic && <p className="text-sm text-muted-foreground">Automatic handling · routine emails run under the published policy.</p>}
      {item.replies.length === 0 && <p className="text-sm text-muted-foreground">Waiting for a reply.</p>}
      {item.replies.map((reply) => <div key={reply.reply_id} className="space-y-3 rounded-lg bg-muted p-3">
        <p className="text-sm font-medium">Reply from {reply.from_email} · {reply.decision.replaceAll("_", " ")}</p>
        <p className="whitespace-pre-wrap text-sm">{reply.body}</p>
        <p className="text-sm">Assessment: {reply.reason}</p>
        {reply.job && <p className="text-xs">Processing: {reply.job.state}{reply.job.error_code ? ` · ${reply.job.error_code}` : ""}</p>}
        {(Object.entries(reply.previews) as [Kind, Preview][]).map(([kind, preview]) => <div key={kind} className="rounded border bg-background p-3">
          <p className="text-sm font-medium">{item.automatic ? kind.replaceAll("_", " ") : labels[kind]}</p>
          <p className="text-sm">To: {preview.to}</p><p className="text-sm">Subject: {preview.subject}</p>
          <p className="whitespace-pre-wrap text-sm">{preview.body}</p>
          {reply.actions[kind] ? <p className="text-xs">{reply.actions[kind]}</p> : item.automatic ?
            <p className="text-xs">{reply.job?.state === "blocked" ? "Needs operator attention" : "Handled by the published automation policy"}</p> :
            <button type="button" disabled={busy || !backend.can("workflow.approve")}
              onClick={() => void act(item.case_id, reply.reply_id, kind)}
              className="mt-2 rounded border px-3 py-1 text-sm disabled:opacity-50">{labels[kind]}</button>}
        </div>)}
      </div>)}
    </article>)}
  </section>;
}
