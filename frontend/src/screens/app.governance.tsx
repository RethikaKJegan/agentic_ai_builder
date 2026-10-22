"use client";
import { useEffect, useState, type ReactNode } from "react";
import { ArrowRight, BookOpen, ChevronRight, FileText, Search, ShieldCheck, SlidersHorizontal } from "lucide-react";
import { api } from "@/api/client";
import { UsageLimits } from "@/features/governance/UsageLimits";
import { Link } from "@/lib/navigation";
import { displayText } from "@/lib/display-text";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";

type Monitoring = Awaited<ReturnType<typeof api.monitoring>>;
type AuditEvent = NonNullable<Monitoring["audit"]>[number];
const sections = [
  { id: "approvals", label: "Human approvals", note: "Review consequential actions before execution." },
  { id: "ai", label: "Agent safeguards", note: "Use bounded execution, validated inputs and controlled tool access." },
  { id: "access", label: "Tool access", note: "Limit access to the tools and connected services required for each task." },
  { id: "data", label: "Data handling", note: "Use only the data necessary for the workflow’s purpose." },
] as const;
type Section = typeof sections[number]["id"];
const cell = "px-4 py-3 text-left align-top text-sm";
function Empty({ children }: { children: ReactNode }) { return <p className="rounded-xl border border-dashed p-6 text-sm leading-6 text-muted-foreground">{children}</p>; }
function Tag({ children }: { children: ReactNode }) { return <span className="inline-flex rounded-md border bg-muted/40 px-2 py-0.5 text-[11px] font-medium text-muted-foreground">{children}</span>; }
function Value({ label, children }: { label: string; children: ReactNode }) { return <div className="grid gap-1 border-b py-3 last:border-0 sm:grid-cols-[150px_1fr]"><dt className="text-xs text-muted-foreground">{label}</dt><dd className="min-w-0 break-words text-sm">{children}</dd></div>; }
function runHref(id: string) { return `/app/runs?run=${encodeURIComponent(id)}`; }

export default function Governance() {
  const [data, setData] = useState<Monitoring>();
  const [error, setError] = useState<Error>();
  const [loading, setLoading] = useState(true);
  const [retrieved, setRetrieved] = useState("");
  const [revision, setRevision] = useState(0);
  const [cursor, setCursor] = useState<string>();
  const [section, setSection] = useState<Section>("approvals");
  const [search, setSearch] = useState("");
  const [eventType, setEventType] = useState("");
  const [selected, setSelected] = useState<AuditEvent>();
  useEffect(() => {
    let cancelled = false;
    setLoading(true);setError(undefined);setData(undefined);setSelected(undefined);
    void api.monitoring(cursor ? { policy_cursor: cursor } : {}).then(result => {
      if (!cancelled) { setData(result);setRetrieved(new Date().toLocaleString()); }
    }).catch(caught => { if (!cancelled) setError(caught instanceof Error ? caught : new Error("Governance evidence is unavailable.")); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [cursor, revision]);
  const events = data?.audit ?? [];
  const types = [...new Set(events.map(event => event.event_type))].sort();
  const filtered = events.filter(event => (!eventType || event.event_type === eventType) &&
    `${event.event_id} ${event.event_type} ${event.run_id} ${event.timestamp}`.toLowerCase().includes(search.toLowerCase().trim()));
  const policies = data?.policies ?? [];
  const selectedSection = sections.find(item => item.id === section)!;
  return <div className="mx-auto max-w-6xl p-5 md:p-10">
    <div className="mb-7 flex flex-wrap items-start justify-between gap-4">
      <div><p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-primary">Organization governance</p><h1 className="font-display text-3xl font-semibold tracking-tight">Governance</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">A clear reference for policies, usage boundaries and execution evidence.</p></div>
      <div className="flex items-center gap-3"><Tag>Read-only</Tag><button type="button" disabled={loading} onClick={() => setRevision(value => value + 1)} className="rounded-lg border px-3 py-2 text-xs font-medium hover:bg-muted disabled:opacity-50">{loading ? "Loading…" : "Refresh evidence"}</button></div>
    </div>
    <Tabs defaultValue="policies">
      <TabsList className="mb-6 grid h-auto w-full grid-cols-1 gap-1 rounded-xl bg-muted/50 p-1 sm:grid-cols-3">
        <TabsTrigger className="justify-start gap-2 whitespace-normal px-3 py-3 sm:justify-center" value="policies"><BookOpen className="h-4 w-4 shrink-0"/>Organization Policies</TabsTrigger>
        <TabsTrigger className="justify-start gap-2 whitespace-normal px-3 py-3 sm:justify-center" value="limits"><SlidersHorizontal className="h-4 w-4 shrink-0"/>Usage &amp; Limits</TabsTrigger>
        <TabsTrigger className="justify-start gap-2 whitespace-normal px-3 py-3 sm:justify-center" value="oversight"><ShieldCheck className="h-4 w-4 shrink-0"/>Oversight &amp; Accountability</TabsTrigger>
      </TabsList>
      <ApiFeedback error={error}/>
      {loading && <p role="status" className="mb-4 text-sm text-muted-foreground">Loading reported policies and activity…</p>}
      <TabsContent value="policies" className="mt-0">
        <div className="grid gap-6 lg:grid-cols-[225px_minmax(0,1fr)]">
          <nav aria-label="Policy sections" className="space-y-1 lg:border-r lg:pr-5"><p className="mb-3 px-3 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Policy reference</p>{sections.map(item => <button type="button" key={item.id} aria-current={section === item.id ? "page" : undefined} onClick={() => setSection(item.id)} className={`flex w-full items-center justify-between gap-2 rounded-lg px-3 py-3 text-left text-sm transition-colors ${section === item.id ? "bg-primary/5 font-medium text-primary" : "text-muted-foreground hover:bg-muted"}`}>{item.label}<ChevronRight className="h-3.5 w-3.5"/></button>)}</nav>
          <section aria-label={selectedSection.label} className="min-w-0">
            <div className="mb-5 border-b pb-5"><div className="flex items-center gap-2"><FileText className="h-4 w-4 text-primary"/><p className="text-xs text-muted-foreground">Policies / {selectedSection.label}</p></div><h2 className="mt-3 text-xl font-semibold">{selectedSection.label}</h2><p className="mt-2 text-sm leading-6 text-muted-foreground">{selectedSection.note}</p></div>
            {section === "approvals" && <><h3 className="text-sm font-semibold">Action review requirements</h3><p className="mb-5 mt-2 text-sm leading-6 text-muted-foreground">Inspect approval requirements reported for each workflow revision. A revision-level flag does not describe every tool permission or approval outcome.</p>{policies.map(policy => <article key={`${policy.workflow_id}:${policy.version}`} className="mb-3 rounded-xl border p-4"><div className="flex flex-wrap items-center justify-between gap-2"><h4 className="break-all text-sm font-medium">{policy.workflow_id} · v{policy.version}</h4><Tag>Reported revision</Tag></div><dl className="mt-2"><Value label="Action review">{policy.action_approval_required ? "Required for this revision" : "No workflow action approval gate reported"}</Value>{policy.scope&&<Value label="Scope">{policy.scope}</Value>}{policy.enforcement&&<Value label="Enforcement">{policy.enforcement}</Value>}{policy.policy_version!=null&&<Value label="Policy version">{policy.policy_version}</Value>}</dl></article>)}</>}
            {section === "ai" && <><h3 className="text-sm font-semibold">Agent safeguards</h3><p className="mb-5 mt-2 text-sm leading-6 text-muted-foreground">Values below come from reported workflow revisions. “On” and “Off” reflect the reported configuration; they are not a compliance certification.</p>{policies.map(policy => <article key={`${policy.workflow_id}:${policy.version}`} className="mb-4 rounded-xl border"><h4 className="border-b px-4 py-3 text-sm font-medium break-all">{policy.workflow_id} · v{policy.version}</h4>{policy.agents.length ? policy.agents.map(agent => <details key={agent.agent_id} className="border-b px-4 py-3 last:border-0"><summary className="cursor-pointer break-all text-sm font-medium">{agent.agent_id}</summary><dl className="mt-3">{Object.entries(agent.guardrails).map(([key, enabled]) => <Value key={key} label={displayText(key)}>{enabled ? "On" : "Off"}</Value>)}{!Object.keys(agent.guardrails).length && <Value label="Safeguards">Review agent configuration before execution.</Value>}</dl></details>) : <p className="p-4 text-sm text-muted-foreground">No agent safeguards reported for this revision.</p>}</article>)}</>}
            {(section === "ai" || section === "approvals") && !loading && !error && !policies.length && <Empty>No workflow policy records are available in this response. Organization-wide enforcement cannot be inferred.</Empty>}
            {(section === "ai" || section === "approvals") && data && <div className="mt-5 flex flex-wrap gap-2">{cursor && <button className="rounded-lg border px-3 py-2 text-xs" onClick={() => setCursor(undefined)}>First policy page</button>}{data.policy_next_cursor && <button className="rounded-lg border px-3 py-2 text-xs" onClick={() => setCursor(data.policy_next_cursor ?? undefined)}>More policy records</button>}</div>}
            {section === "access" && <><h3 className="text-sm font-semibold">Access to tools and integrations</h3><dl className="my-4"><Value label="Access principle">Limit access to the tools and connected services required for each task.</Value><Value label="Account review">Review connected accounts and granted capabilities before using them in a workflow.</Value></dl><p className="text-sm text-muted-foreground">Manage connected services in <Link to="/app/integrations" className="text-primary underline underline-offset-4">Integrations</Link>.</p></>}
            {section === "data" && <><h3 className="text-sm font-semibold">Data handling principles</h3><dl className="my-4"><Value label="Data retention">Retain operational records according to business and review requirements.</Value><Value label="Data residency">Consider the hosting region of each connected service when selecting data sources.</Value><Value label="Classification">Handle credentials, personal information and confidential business records as sensitive data.</Value><Value label="Policy exceptions">Document the reason, scope and responsible owner for each exception.</Value></dl></>}

          </section>
        </div>
      </TabsContent>
      <TabsContent value="limits" className="mt-0"><UsageLimits data={data} loading={loading} failed={!!error} retrieved={retrieved} pagination={<div className="flex flex-wrap gap-2">{cursor && <button className="rounded-lg border px-3 py-2 text-xs" onClick={() => setCursor(undefined)}>First policy page</button>}{data?.policy_next_cursor && <button className="rounded-lg border px-3 py-2 text-xs" onClick={() => setCursor(data.policy_next_cursor ?? undefined)}>More policy records</button>}</div>}/></TabsContent>
      <TabsContent value="oversight" className="mt-0 space-y-5">
        <div className="border-b pb-5"><h2 className="text-xl font-semibold">Oversight &amp; accountability</h2><p className="mt-2 text-sm leading-6 text-muted-foreground">Review the runtime events returned by the current service. Search applies to the loaded records; this is not an organization-wide audit archive.</p></div>
        <div className="flex flex-wrap gap-3"><div className="relative min-w-0 flex-1"><Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted-foreground"/><input aria-label="Search governance activity" value={search} onChange={event => setSearch(event.target.value)} placeholder="Search event, run or identifier…" className="h-10 w-full rounded-lg border bg-background pl-9 pr-3 text-sm"/></div><select aria-label="Filter activity type" value={eventType} onChange={event => setEventType(event.target.value)} className="h-10 max-w-full rounded-lg border bg-background px-3 text-sm"><option value="">All event types</option>{types.map(type => <option key={type} value={type}>{type}</option>)}</select></div>
        {data && <p className="text-xs text-muted-foreground">Showing {filtered.length} of {events.length} returned events</p>}
        <div className="divide-y rounded-xl border">{filtered.map(event => <button key={event.event_id} type="button" onClick={() => setSelected(event)} className="flex w-full items-start gap-3 p-4 text-left hover:bg-muted/40"><span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-primary/60"/><span className="min-w-0 flex-1"><span className="block break-words text-sm font-medium">{displayText(event.event_type)}</span><span className="mt-1 block break-all text-xs text-muted-foreground">{event.timestamp} · {event.run_id}</span><span className="mt-1 block break-all font-mono text-[11px] text-muted-foreground">{event.event_id}</span></span><ArrowRight className="mt-1 h-4 w-4 shrink-0 text-muted-foreground"/></button>)}</div>
        {!loading && !error && !filtered.length && <Empty>{events.length ? "No events match your search or filter." : "No runtime audit events were returned. Browser-local activity is not included."}</Empty>}
        <p className="text-xs leading-5 text-muted-foreground">Actor identity and a separate outcome field are not supplied in these event records. Inspect the linked run for further execution evidence.</p>
      </TabsContent>
    </Tabs>
    {data && <p className="mt-8 border-t pt-4 text-xs text-muted-foreground">Evidence retrieved {retrieved} · Read-only snapshot · Source: existing runtime monitoring service</p>}
    <Sheet open={!!selected} onOpenChange={open => { if (!open) setSelected(undefined); }}><SheetContent className="w-full overflow-y-auto sm:max-w-lg"><SheetHeader><SheetTitle>Event evidence</SheetTitle><SheetDescription>Original fields returned by the runtime service.</SheetDescription></SheetHeader>{selected && <div className="mt-6"><dl><Value label="Event ID">{selected.event_id}</Value><Value label="Event type">{selected.event_type}</Value><Value label="Timestamp">{selected.timestamp}</Value><Value label="Run ID">{selected.run_id}</Value><Value label="Actor">Not supplied</Value><Value label="Outcome">Not supplied separately</Value></dl><Link to={runHref(selected.run_id)} className="mt-6 inline-flex items-center gap-2 text-sm font-medium text-primary">Inspect run<ArrowRight className="h-4 w-4"/></Link><details className="mt-6 rounded-lg border p-3"><summary className="cursor-pointer text-xs font-medium">Original event record</summary><pre className="mt-3 whitespace-pre-wrap break-all text-xs text-muted-foreground">{JSON.stringify(selected, null, 2)}</pre></details></div>}</SheetContent></Sheet>
  </div>;
}
