"use client";
import { displayText } from "@/lib/display-text";
import { Link, useRouteSearch } from "@/lib/navigation";
import { useNavigate } from "@/lib/navigation";
import { useMemo, useState } from "react";
import { Bot, Building2, Check, Plug, Search, ShieldCheck, Workflow as WfIcon } from "lucide-react";
import { toast } from "sonner";
import { MARKETPLACE } from "@/domain/catalog";
import { TEMPLATES } from "@/domain/templates";
import { useMesh } from "@/domain/store";
import { getModel } from "@/domain/models";
import type { AssetKind, MarketplaceAsset } from "@/domain/types";
import { NODE_META } from "@/features/builder/nodeMeta";



const KINDS: { id: AssetKind | "all"; label: string }[] = [
  { id: "all", label: "All" },
  { id: "agent", label: "Agents" },
  { id: "workflow", label: "Workflow templates" },
  { id: "tool", label: "Tools & integrations" },
  { id: "guardrail", label: "Guardrail packs" },
];
const KIND_ICON = { agent: Bot, workflow: WfIcon, tool: Plug, guardrail: ShieldCheck };
const KIND_LABEL = { agent: "Agent", workflow: "Workflow template", tool: "Integration", guardrail: "Guardrail pack" };

export default function Marketplace() {
  const { asset: selId } = useRouteSearch();
  const navigate = useNavigate({ from: "/app/marketplace" });
  const goTo = useNavigate();
  const [q, setQ] = useState("");
  const [kind, setKind] = useState<AssetKind | "all">("all");
  const [orgOnly, setOrgOnly] = useState(false);
  const installed = useMesh((s) => s.installed);
  const connectors = useMesh((s) => s.connectors);
  const install = useMesh((s) => s.installAsset);

  const list = useMemo(
    () => MARKETPLACE.filter((a) => (kind === "all" || a.kind === kind) && (!orgOnly || a.orgOwned) && `${a.name} ${a.domain} ${a.description}`.toLowerCase().includes(q.toLowerCase())),
    [q, kind, orgOnly],
  );
  const sel = MARKETPLACE.find((a) => a.id === selId) ?? list[0];

  const isInstalled = (a: MarketplaceAsset) =>
    a.kind === "tool" ? connectors.find((c) => c.id === a.ref)?.status === "demo-connected" : a.kind !== "workflow" && a.kind !== "agent" ? !!installed[a.id] : false;
  const timesInstalled = (a: MarketplaceAsset) => (installed[a.id] ? 1 : 0);

  const doInstall = (a: MarketplaceAsset) => {
    const r = install(a);
    toast.success(r.message, {
      action: r.target?.type === "workflow"
        ? { label: "Open", onClick: () => goTo({ to: "/app/workflows/$id", params: { id: r.target!.id } }) }
        : r.target?.type === "agent"
          ? { label: "Open", onClick: () => goTo({ to: "/app/agents", search: { agent: r.target!.id } }) }
          : undefined,
    });
  };

  return (
    <div className="flex h-full flex-col lg:flex-row">
      <div className="min-w-0 flex-1 overflow-y-auto px-6 py-10">
        <h1 className="text-3xl font-semibold">Marketplace</h1>
        <p className="mt-2 text-sm text-muted-foreground">Discover tools here and connect your accounts in Integrations. Templates and agents become editable local drafts.</p>

        <div className="mt-6 flex flex-wrap items-center gap-2">
          <div className="relative min-w-[200px] flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input aria-label="Search marketplace" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search assets…" className="h-9 w-full rounded-lg border border-border bg-background pl-9 pr-3 text-sm outline-none focus:border-primary" />
          </div>
          <button onClick={() => setOrgOnly((o) => !o)} className={`inline-flex h-9 items-center gap-1.5 rounded-lg border px-3 text-sm ${orgOnly ? "border-primary bg-highlight text-primary-deep" : "border-border text-muted-foreground"}`}>
            <Building2 className="h-4 w-4" /> Workspace library only
          </button>
        </div>
        <div className="mt-3 flex flex-wrap gap-1.5" role="tablist">
          {KINDS.map((k) => (
            <button key={k.id} role="tab" aria-selected={kind === k.id} onClick={() => setKind(k.id)} className={`rounded-full px-3 py-1 text-sm transition-colors ${kind === k.id ? "bg-foreground text-background" : "text-muted-foreground hover:bg-muted"}`}>{displayText(k.label)}</button>
          ))}
        </div>

        {kind === "tool" && <Link to="/app/integrations" className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground"><Plug className="h-4 w-4" />Connect Google</Link>}
        {list.length === 0 ? (
          <p className="mt-8 rounded-xl border border-dashed border-border p-6 text-sm text-muted-foreground">No assets match. Try a different search or category.</p>
        ) : (
          <div className="mt-6 divide-y divide-border rounded-xl border border-border">
            {list.map((a) => {
              const Icon = KIND_ICON[a.kind];
              return (
                <button key={a.id} onClick={() => a.kind === "tool" ? goTo({ to: "/app/integrations" }) : navigate({ search: { asset: a.id } })} className={`flex w-full items-center gap-4 px-4 py-3.5 text-left transition-colors ${sel?.id === a.id ? "bg-highlight" : "hover:bg-canvas"}`}>
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-border-accent bg-background text-primary"><Icon className="h-4 w-4" /></span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{displayText(a.name)}</p>
                    <p className="truncate text-xs text-muted-foreground">{displayText(KIND_LABEL[a.kind])} · {a.domain}</p>
                  </div>
                  {a.orgOwned && <span className="hidden rounded-full bg-muted px-2 py-0.5 text-[11px] text-muted-foreground sm:inline">Workspace library</span>}
                  {isInstalled(a) && <span className="flex items-center gap-1 text-xs text-success"><Check className="h-3.5 w-3.5" />Installed</span>}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {sel && (
        <aside className="w-full shrink-0 overflow-y-auto border-t border-border p-6 lg:w-[400px] lg:border-l lg:border-t-0">
          <p className="text-xs font-medium text-primary">{displayText(KIND_LABEL[sel.kind])}</p>
          <h2 className="mt-2 text-2xl font-semibold">{displayText(sel.name)}</h2>
          <p className="mt-1 text-xs text-muted-foreground">by {sel.publisher} · {sel.domain}</p>
          <p className="mt-4 text-sm leading-relaxed">{displayText(sel.description)}</p>
          {sel.kind === "tool" && <Link to="/app/integrations" className="mt-5 inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground"><Plug className="h-4 w-4" />Connect Google</Link>}

          {sel.kind === "workflow" && <TemplatePreview templateId={sel.ref} />}
          {sel.kind === "agent" && sel.agent && (
            <dl className="mt-5 space-y-2 rounded-xl border border-border p-4 text-sm">
              <div className="flex justify-between"><dt className="text-muted-foreground">Role</dt><dd>{sel.agent.role}</dd></div>
              <div className="flex justify-between"><dt className="text-muted-foreground">Default model</dt><dd>{displayText(getModel(sel.agent.modelId).name)}</dd></div>
              <div><dt className="text-muted-foreground">Instructions</dt><dd className="mt-1 font-mono text-xs leading-relaxed">{sel.agent.instructions}</dd></div>
            </dl>
          )}
          {sel.kind === "guardrail" && sel.guardrails && (
            <ul className="mt-5 space-y-1.5 text-sm">
              {Object.keys(sel.guardrails).map((g) => <li key={g} className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-primary" />{({ piiRedaction: "PII redaction", injectionDetection: "Prompt-injection detection", outputValidation: "Output validation" } as Record<string, string>)[g]}</li>)}
            </ul>
          )}

          <div className="mt-5">
            <p className="text-xs font-medium text-muted-foreground">Dependencies</p>
            {sel.dependencies.length === 0 ? <p className="mt-1 text-sm text-muted-foreground">None</p> : (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {sel.dependencies.map((d) => {
                  const ok = connectors.some((c) => c.tools.includes(d) && c.status === "demo-connected");
                  return <span key={d} className={`rounded-full px-2.5 py-0.5 text-xs ${ok ? "bg-success/10 text-success" : "bg-muted text-muted-foreground"}`}>{d}{ok ? "" : " · not connected"}</span>;
                })}
              </div>
            )}
          </div>

          {sel.kind !== "tool" && <button onClick={() => doInstall(sel)} disabled={isInstalled(sel)} className="mt-6 flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-primary text-sm font-medium text-primary-foreground transition-colors hover:bg-primary-deep disabled:bg-muted disabled:text-muted-foreground">
            {isInstalled(sel) ? <><Check className="h-4 w-4" />Installed</> : sel.kind === "workflow" ? "Use template" : sel.kind === "guardrail" ? "Apply to drafts" : "Add to drafts"}
          </button>}
          {(sel.kind === "workflow" || sel.kind === "agent") && timesInstalled(sel) > 0 && <p className="mt-2 text-center text-xs text-muted-foreground">Already added once — installing again creates another copy.</p>}
        </aside>
      )}
    </div>
  );
}

function TemplatePreview({ templateId }: { templateId?: string | undefined }) {
  const t = TEMPLATES.find((x) => x.id === templateId);
  if (!t) return null;
  return (
    <div className="mt-5 rounded-xl border border-border bg-canvas bg-grid p-4">
      <p className="mb-3 text-xs font-medium text-muted-foreground">Example workflow · {t.steps.length} steps</p>
      <ol className="space-y-1.5">
        {t.steps.map((s, i) => {
          const M = NODE_META[s.kind];
          return (
            <li key={s.key} className="flex items-center gap-2.5">
              <span className="w-4 text-right font-mono text-[10px] text-muted-foreground">{i + 1}</span>
              <span className={`flex h-6 w-6 items-center justify-center rounded-md ${M.tone}`}><M.icon className="h-3 w-3" /></span>
              <span className="text-sm">{displayText(s.label)}</span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
