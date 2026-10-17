"use client";
import { InputError } from "@/api/feedback";
import { useEffect, useRef, useState } from "react";
import { PageHeader } from "@/features/runs/RunTrace";
import { api } from "@/api/client";
import { useBackend } from "@/api/state";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";
export default function Screen() {
  const backend = useBackend(); const [value, setValue] = useState(""); const [saved, setSaved] = useState("");
  const [timestamp, setTimestamp] = useState(""); const [loaded, setLoaded] = useState(false); const [reload, setReload] = useState(0); const [loading, setLoading] = useState(true); const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error>(); const [success, setSuccess] = useState(""); const pending = useRef(false);
  const administrative = backend.session?.auth.decision === "allow" && backend.session.auth.roles.includes("admin") && backend.session.auth.scopes.includes("workspace:write");
  useEffect(() => {
    if (backend.status !== "connected") return;
    let active = true;
    api.settings().then(result => {
      if (!active) return;
      const item = result.items.find(item => item.key === "notifications");
      if (item && typeof item.value !== "string") throw new InputError("The notification setting is not text. Ask the administrator to correct it.");
      const initial = typeof item?.value === "string" ? item.value : "";
      setLoaded(true); setValue(initial); setSaved(initial); setTimestamp(item?.updated_at ?? ""); setError(undefined);
    }).catch(caught => { if (active) setError(caught instanceof Error ? caught : new InputError("Settings could not be loaded.")); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [backend.status, reload]);
  const save = async () => {
    if (pending.current || !loaded || loading || !administrative || value === saved) return;
    pending.current = true; setBusy(true); setError(undefined); setSuccess("");
    try { const item = await api.saveNotification(value); setSaved(item.value); setTimestamp(item.updated_at); setSuccess("Setting saved on the server."); }
    catch (caught) { setError(caught instanceof Error ? caught : new InputError("The setting was not saved.")); }
    finally { pending.current = false; setBusy(false); }
  };
  return <div className="mx-auto max-w-5xl space-y-5 p-6 md:p-10"><PageHeader title="Settings" sub="Persisted workspace settings." />
    <ApiFeedback error={error ?? backend.error} />
    <button type="button" disabled={busy || backend.status !== "connected"} onClick={() => { if (value !== saved && !window.confirm("Reload settings and discard unsaved changes?")) return; setLoading(true); setReload(current => current + 1); }} className="rounded border px-3 py-2 text-sm disabled:opacity-40">Reload settings</button>
    <form onSubmit={event => { event.preventDefault(); void save(); }} className="rounded-2xl border border-border p-4">
      <label className="text-sm">Notification preference<input disabled={!loaded || loading || busy || !administrative} value={value} maxLength={2000} onChange={event => { setValue(event.target.value); setSuccess(""); }} className="mt-2 block w-full rounded-lg border border-border bg-background p-2 disabled:opacity-40" placeholder="email" /></label>
      <p role="status" className="mt-2 text-xs text-muted-foreground">{loading ? "Loading confirmed settings…" : value !== saved ? "Unsaved changes" : timestamp ? `Saved ${new Date(timestamp).toLocaleString()}` : "No notification preference saved yet."}</p>
      {!administrative && <p className="mt-2 text-sm text-muted-foreground">Workspace administrator access is required to save settings.</p>}
      <button type="submit" disabled={!loaded || loading || busy || !administrative || value === saved} className="mt-3 rounded-lg bg-primary px-3 py-2 text-sm text-primary-foreground disabled:opacity-40">{busy ? "Saving…" : "Save setting"}</button>
      {success && <p role="status" className="mt-2 text-sm text-emerald-700">{success}</p>}
    </form></div>;
}
