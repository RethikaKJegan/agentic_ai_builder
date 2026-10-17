"use client";
import { DatabaseConnectionsSummary } from "@/features/data-sources/DataIntelligence";
import { useRef, useState } from "react";
import { api } from "@/api/client";
import { useBackend } from "@/api/state";
import { GoogleToolChecks } from "@/features/workflows/GoogleToolChecks";
import { GoogleConnections } from "@/features/workflows/GoogleConnections";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";
type Check = Awaited<ReturnType<typeof api.integrationCheck>>;
export default function Integrations() {
  const backend = useBackend(); const [checks, setChecks] = useState<Record<string, Check>>({});
  const [errors, setErrors] = useState<Record<string, Error>>({}); const [pending, setPending] = useState<Record<string, boolean>>({}); const locks = useRef(new Set<string>());
  const tools = [...new Map(backend.tools.map(tool => [tool.definition.provider_id, tool])).values()];
  const admin = backend.session?.auth.roles.includes("admin") && backend.session.auth.decision === "allow";
  const check = async (provider: string, mode: "configuration" | "connection") => {
    if (locks.current.has(provider) || !backend.can("tools.read") || (mode === "connection" && !admin)) return;
    locks.current.add(provider); setPending(current => ({ ...current, [provider]: true }));
    setErrors(current => { const next = { ...current }; delete next[provider]; return next; });
    if (mode === "connection") setChecks(current => { const next = { ...current }; delete next[provider]; return next; });
    try { const result = await api.integrationCheck(provider, mode); setChecks(current => ({ ...current, [provider]: result })); }
    catch (caught) {
      setChecks(current => { const next = { ...current }; delete next[provider]; return next; });
      setErrors(current => ({ ...current, [provider]: caught instanceof Error ? caught : new Error("The check could not be completed.") }));
    } finally { locks.current.delete(provider); setPending(current => ({ ...current, [provider]: false })); }
  };
  return <div className="mx-auto max-w-5xl px-6 py-10"><h1 className="text-3xl font-semibold">Integrations</h1>
    <p className="mt-2 text-sm text-muted-foreground">Configuration and verified connectivity are separate. Credentials remain on the server. Read-only checks never send email or modify provider resources.</p>
    <p className="mt-3 rounded-lg border p-3 text-sm">Setup: register each required tool, configure its server credential and source resource, review exact revision grants, then activate the published release. A configured or verified connection alone does not activate a trigger. See Monitoring for preparation, release and poll health.</p>
    <GoogleConnections />
    <GoogleToolChecks />
    <DatabaseConnectionsSummary />
    <ApiFeedback error={backend.error} />
    {backend.status !== "connected" && <p role="status" className="mt-4 text-sm text-muted-foreground">Connect to the backend to inspect registered integrations.</p>}
    <div className="mt-8 grid gap-4 md:grid-cols-2">{tools.map(tool => {
      const provider = tool.definition.provider_id; const result = checks[provider];
      const configured = tool.definition.availability === "enabled" && (tool.credential_configured || tool.definition.authentication.mode === "none");
      const label = result?.state === "verified" ? "Verified" : result?.state === "connection_failed" ? "Connection failed" : (result ? result.configured : configured) ? "Configured · not verified" : "Not configured";
      return <section key={provider} aria-label={`${provider} integration`} className="rounded-xl border border-border p-4"><div className="flex items-start justify-between gap-3"><h2 className="font-medium">{provider}</h2><span className={`rounded-full px-2 py-1 text-xs ${result?.verified ? "bg-emerald-500/10 text-emerald-700" : "bg-amber-500/10 text-amber-700"}`}>{label}</span></div>
        <p className="mt-3 text-sm text-muted-foreground">{tool.definition.description}</p><p className="mt-2 text-xs">{backend.tools.filter(item => item.definition.provider_id === provider).map(item => item.tool_id).join(", ")}</p>
        <button type="button" disabled={pending[provider] || !backend.can("tools.read")} className="mt-4 rounded-lg border px-3 py-2 text-xs disabled:opacity-40" onClick={() => void check(provider, "configuration")}>{pending[provider] ? "Checking…" : "Check configuration"}</button>
        {result?.live_test_supported && <button type="button" disabled={pending[provider] || !admin || !result.configured} className="ml-2 mt-4 rounded-lg border px-3 py-2 text-xs disabled:opacity-40" onClick={() => void check(provider, "connection")}>Verify connection</button>}
        {!backend.can("tools.read") && <p className="mt-2 text-xs">tools.read permission is required.</p>}
        {result?.live_test_supported && !admin && <p className="mt-2 text-xs">An administrator must verify connections.</p>}
        {!configured && <p className="mt-2 text-xs">Required setup: configure enabled server tools and their credentials, then check configuration again.</p>}
        {result && <p role="status" className="mt-2 text-xs text-muted-foreground">{result.message}</p>}
        <ApiFeedback error={errors[provider]} />
      </section>;
    })}{backend.status === "connected" && !tools.length && <p className="text-sm text-muted-foreground">No registered integrations are visible to your account.</p>}</div></div>;
}
