"use client";
import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { useMesh } from "@/domain/store";
import { can, effectivePolicy, roleLabel, type GuardrailKey, type Policy, type PolicyRule } from "@/domain/governance";
import { MODELS, getModel } from "@/domain/models";
import { uid } from "@/domain/ids";
import { PageHeader } from "@/features/runs/RunTrace";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AgentControlTab } from "@/features/governance/AgentControlTab";
import { LiveRuntimePanel } from "@/screens/app.monitoring";



const GUARDS: Record<GuardrailKey, string> = { piiRedaction: "PII redaction", injectionDetection: "Prompt-injection detection", outputValidation: "Output validation" };

function describe(r: PolicyRule) {
  if (r.type === "require-guardrail") return `Require ${GUARDS[r.guardrail]}`;
  if (r.type === "block-model") return `Block ${getModel(r.modelId).name}`;
  return `Cap each run at $${r.usd}`;
}

export default function Governance() {
  const { policies, role, upsertPolicy, removePolicy, audit } = useMesh();
  const allowed = can(role, "policy.manage");
  const eff = effectivePolicy(policies);
  const [type, setType] = useState<PolicyRule["type"]>("block-model");
  const [modelId, setModelId] = useState("gpt-5");
  const [guard, setGuard] = useState<GuardrailKey>("outputValidation");
  const [usd, setUsd] = useState("0.5");

  const add = () => {
    const rule: PolicyRule = type === "block-model" ? { type, modelId } : type === "require-guardrail" ? { type, guardrail: guard } : { type, usd: Math.max(0.001, Number(usd) || 0.5) };
    const p: Policy = { id: uid("pol"), scope: "workspace", name: describe(rule), description: "Added by workspace admin.", rule, enabled: true };
    upsertPolicy(p);
    toast.success("Workspace policy added");
  };

  const Section = ({ scope }: { scope: Policy["scope"] }) => (
    <div className="rounded-2xl border border-border">
      <p className="border-b border-border px-4 py-3 text-sm font-medium capitalize">{scope === "organization" ? "Organization · Local organization" : "Workspace · Local workspace"}</p>
      <div className="divide-y divide-border">
        {policies.filter((p) => p.scope === scope).map((p) => (
          <div key={p.id} className="flex items-center gap-3 px-4 py-3">
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium">{p.name}</p>
              <p className="text-xs text-muted-foreground">{describe(p.rule)} · {p.description}</p>
            </div>
            <Switch checked={p.enabled} disabled={!allowed} onCheckedChange={(v) => upsertPolicy({ ...p, enabled: v })} aria-label={`Toggle ${p.name}`} />
            {scope === "workspace" && allowed && <button onClick={() => removePolicy(p.id)} className="rounded p-1 text-muted-foreground hover:text-destructive" aria-label={`Delete ${p.name}`}><Trash2 className="h-4 w-4" /></button>}
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <div className="mx-auto max-w-5xl p-6 md:p-10">
      <PageHeader title="Governance" sub="Live server guardrails and audit records, alongside local policy drafts." />
      {!allowed && <p className="mb-4 rounded-lg border border-border bg-canvas p-3 text-sm text-muted-foreground">Read-only: only Organization Admins can change policies.</p>}
      <Tabs defaultValue="usage">
        <TabsList className="flex-wrap"><TabsTrigger value="control">Draft agent controls</TabsTrigger><TabsTrigger value="usage">Live governance & usage</TabsTrigger><TabsTrigger value="policies">Draft policies</TabsTrigger><TabsTrigger value="effective">Draft rules</TabsTrigger><TabsTrigger value="audit">Draft audit log</TabsTrigger></TabsList>
        <TabsContent value="control" className="mt-4"><AgentControlTab /></TabsContent>
        <TabsContent value="usage" className="mt-4"><LiveRuntimePanel /></TabsContent>
        <TabsContent value="policies" className="mt-4 space-y-4">
          <Section scope="organization" />
          <Section scope="workspace" />
          {allowed && (
            <div className="flex flex-wrap items-end gap-2 rounded-2xl border border-dashed border-border p-4">
              <label className="text-xs text-muted-foreground">Rule<select value={type} onChange={(e) => setType(e.target.value as PolicyRule["type"])} className="mt-1 block h-9 rounded-lg border border-border bg-background px-2 text-sm text-foreground"><option value="block-model">Block a model</option><option value="require-guardrail">Require a guardrail</option><option value="max-run-cost">Cap run cost</option></select></label>
              {type === "block-model" && <label className="text-xs text-muted-foreground">Model<select value={modelId} onChange={(e) => setModelId(e.target.value)} className="mt-1 block h-9 rounded-lg border border-border bg-background px-2 text-sm text-foreground">{MODELS.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}</select></label>}
              {type === "require-guardrail" && <label className="text-xs text-muted-foreground">Guardrail<select value={guard} onChange={(e) => setGuard(e.target.value as GuardrailKey)} className="mt-1 block h-9 rounded-lg border border-border bg-background px-2 text-sm text-foreground">{Object.entries(GUARDS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>}
              {type === "max-run-cost" && <label className="text-xs text-muted-foreground">USD per run<input value={usd} onChange={(e) => setUsd(e.target.value)} inputMode="decimal" className="mt-1 block h-9 w-28 rounded-lg border border-border bg-background px-2 text-sm text-foreground" /></label>}
              <button onClick={add} className="flex h-9 items-center gap-1.5 rounded-lg bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary-deep"><Plus className="h-4 w-4" />Add workspace policy</button>
            </div>
          )}
        </TabsContent>
        <TabsContent value="effective" className="mt-4">
          <div className="grid gap-3 md:grid-cols-3">
            <div className="rounded-2xl border border-border p-4"><p className="text-xs text-muted-foreground">Requested guardrails</p>{Object.entries(eff.guardrails).filter(([, v]) => v).map(([k]) => <p key={k} className="mt-1 text-sm font-medium">{GUARDS[k as GuardrailKey]}</p>)}{!Object.values(eff.guardrails).some(Boolean) && <p className="mt-1 text-sm">None</p>}</div>
            <div className="rounded-2xl border border-border p-4"><p className="text-xs text-muted-foreground">Blocked models</p><p className="mt-1 text-sm font-medium">{eff.blockedModels.length ? eff.blockedModels.map((m) => getModel(m).name).join(", ") : "None"}</p></div>
            <div className="rounded-2xl border border-border p-4"><p className="text-xs text-muted-foreground">Run cost cap</p><p className="mt-1 font-display text-2xl font-semibold">{eff.maxRunCost === null ? "None" : `$${eff.maxRunCost}`}</p></div>
          </div>
          <div className="mt-4 divide-y divide-border rounded-2xl border border-border">
            {eff.sources.map((s, i) => <div key={i} className="flex justify-between gap-3 px-4 py-2.5 text-sm"><span>{s.setting}</span><span className="text-muted-foreground">{s.policy} · <span className="capitalize">{s.scope}</span></span></div>)}
          </div>
        </TabsContent>
        <TabsContent value="audit" className="mt-4">
          <div className="divide-y divide-border rounded-2xl border border-border">
            {audit.length === 0 && <p className="p-6 text-center text-sm text-muted-foreground">No audit events yet.</p>}
            {audit.map((a) => (
              <div key={a.id} className="flex flex-wrap items-center gap-x-3 px-4 py-2.5 text-sm">
                <span className="w-40 text-xs text-muted-foreground">{new Date(a.at).toLocaleString()}</span>
                <span className="font-medium">{a.action}</span>
                <span className="min-w-0 flex-1 truncate text-muted-foreground">{a.target}</span>
                <span className="text-xs text-muted-foreground">{a.actor} · {roleLabel(a.role)}</span>
              </div>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
