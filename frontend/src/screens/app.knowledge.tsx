"use client";
import { useEffect, useState } from "react";
import { PageHeader } from "@/features/runs/RunTrace";
import { api } from "@/api/client";
import { useBackend } from "@/api/state";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";
export default function Screen() {
  const backend = useBackend(); const [items, setItems] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState<Error>(); const [loading, setLoading] = useState(true); const [reload, setReload] = useState(0);
  useEffect(() => {
    if (backend.status !== "connected") return;
    let active = true;
    api.knowledge().then(result => { if (active) { setItems(result.items); setError(undefined); } })
      .catch(caught => { if (active) setError(caught instanceof Error ? caught : new Error("Knowledge sources could not be loaded.")); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [backend.status, reload]);
  return <div className="mx-auto max-w-5xl space-y-5 p-6 md:p-10"><PageHeader title="Knowledge" sub="Persisted workspace knowledge sources." />
    <ApiFeedback error={error ?? backend.error} /><button disabled={loading || backend.status !== "connected"} type="button" onClick={() => { setLoading(true); setReload(value => value + 1); }} className="rounded-lg border px-3 py-2 text-sm disabled:opacity-40">Refresh sources</button>
    {loading && <p role="status">Loading sources…</p>}<div className="rounded-2xl border border-border">{items.map((item, index) => <pre key={index} className="border-b border-border p-4 text-xs last:border-0">{JSON.stringify(item, null, 2)}</pre>)}
      {!loading && !error && !items.length && <p className="p-10 text-center text-sm text-muted-foreground">No knowledge sources available. Source ingestion is unavailable in this UI.</p>}
    </div></div>;
}
