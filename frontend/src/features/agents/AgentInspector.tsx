import { useState } from "react";
import { Check, ChevronDown } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { useMesh } from "@/domain/store";
import { getModel, MODELS, TOOL_CATALOG } from "@/domain/models";
import type { Agent } from "@/domain/types";
import { AgentControlsCard } from "./AgentControlsCard";
import { toast } from "sonner";
import { Link } from "@/lib/navigation";
import { useBackend } from "@/api/state";

const field = "w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none transition-colors focus:border-primary";
const lbl = "mb-1.5 block text-xs font-medium text-muted-foreground";

export function AgentInspector({ agent }: { agent: Agent }) {
  const update = useMesh((s) => s.updateAgent);
  const log = useMesh((s) => s.log);
  const [advanced, setAdvanced] = useState(false);
  const backend = useBackend();
  const assignmentReview = Object.values(backend.reviews).find((review) =>
    agent.id === `${review.workflow_id}::${agent.canonicalId}` && agent.version === review.workflow_version);
  const connectors = useMesh((s) => s.connectors);
  const knowledge = useMesh((s) => s.knowledge);
  const toolStatus = (t: string) => connectors.find((c) => c.tools.includes(t) && c.status === "demo-connected") ? "connected" : connectors.find((c) => c.tools.includes(t))?.status === "error" ? "error" : "not connected";
  const set = (patch: Partial<Agent>) => update(agent.id, patch);
  const toggle = (key: "tools" | "knowledge", v: string) =>
    set({ [key]: agent[key].includes(v) ? agent[key].filter((x) => x !== v) : [...agent[key], v] } as Partial<Agent>);

  const pickModel = (id: string) => {
    if (id === agent.modelId) return;
    set({ modelId: id });
    log({ kind: "agent.updated", message: `${agent.name} switched to ${getModel(id).name}` });
    toast.success(`${agent.name} now uses ${getModel(id).name}`, { description: "Saved to the local agent draft." });
  };

  return (
    <>
    {agent.origin !== "backend" && <AgentControlsCard agent={agent} />}
    <Tabs defaultValue="general" className="w-full">
      <TabsList className="grid w-full grid-cols-5">
        {["general", "intelligence", "tools", "knowledge", "safety"].map((t) => (
          <TabsTrigger key={t} value={t} className="px-1 text-[11px] capitalize">{t}</TabsTrigger>
        ))}
      </TabsList>

      <TabsContent value="general" className="space-y-4 pt-4">
        <div><label className={lbl} htmlFor="ag-name">Name</label><input id="ag-name" className={field} disabled={agent.origin === "backend"} value={agent.name} onChange={(e) => set({ name: e.target.value })} /></div>
        <div><label className={lbl} htmlFor="ag-role">Role</label><input id="ag-role" className={field} value={agent.role} onChange={(e) => set({ role: e.target.value })} /></div>
        <div><label className={lbl} htmlFor="ag-purpose">Purpose</label><textarea id="ag-purpose" rows={2} className={field} value={agent.purpose} onChange={(e) => set({ purpose: e.target.value })} /></div>
        <div><label className={lbl} htmlFor="ag-ins">Instructions</label><textarea id="ag-ins" rows={6} className={`${field} font-mono text-xs leading-relaxed`} value={agent.instructions} onChange={(e) => set({ instructions: e.target.value })} /></div>
        <p className="text-xs text-muted-foreground">v{agent.version} · {agent.status} · {agent.origin === "backend" ? "Save the workflow revision to persist agent edits" : "saved in this browser"}</p>
      </TabsContent>

      <TabsContent value="intelligence" className="space-y-4 pt-4">
        <div>
          <span className={lbl}>Model</span>
          {agent.origin === "backend" && <p className="mb-2 text-xs text-muted-foreground">Current draft model: {agent.modelId}</p>}
          <div className="space-y-1.5" role="radiogroup" aria-label="Model">
            {MODELS.map((m) => {
              const sel = m.id === agent.modelId;
              return (
                <button key={m.id} role="radio" aria-checked={sel} onClick={() => pickModel(m.id)} className={`flex w-full items-center gap-3 rounded-lg border p-2.5 text-left transition-colors ${sel ? "border-primary bg-highlight" : "border-border hover:border-border-accent"}`}>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium">{m.name} <span className="text-xs font-normal text-muted-foreground">· {m.provider}</span></p>
                    <p className="mt-0.5 truncate text-[11px] text-muted-foreground">{m.capabilities.join(" · ")}</p>
                  </div>
                  <span className="font-mono text-xs text-muted-foreground">{m.costTier}</span>
                  {sel && <Check className="h-4 w-4 text-primary" />}
                </button>
              );
            })}
          </div>
          <p className="mt-2 text-[11px] text-muted-foreground">Local configuration draft. Provider availability and authorization must be validated by the backend.</p>
        </div>
        <div>
          <span className={lbl}>Temperature · {agent.temperature.toFixed(1)}</span>
          <Slider value={[agent.temperature]} min={0} max={1} step={0.1} onValueChange={([v]) => set({ temperature: v ?? 0 })} aria-label="Temperature" />
        </div>
        <button onClick={() => setAdvanced((a) => !a)} className="flex items-center gap-1 text-xs font-medium text-primary">
          Advanced <ChevronDown className={`h-3 w-3 transition-transform ${advanced ? "rotate-180" : ""}`} />
        </button>
        {advanced && (
          <div className="space-y-4">
            <div><label className={lbl} htmlFor="ag-max">Max tokens</label><input id="ag-max" type="number" min={64} max={32000} className={field} value={agent.maxTokens} onChange={(e) => set({ maxTokens: Math.max(64, Number(e.target.value) || 64) })} /></div>
            {agent.origin !== "backend" && <><div><label className={lbl} htmlFor="ag-fb">Fallback model</label>
              <select id="ag-fb" className={field} value={agent.fallbackModelId} onChange={(e) => set({ fallbackModelId: e.target.value })}>
                {MODELS.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
              </select>
            </div></>}
            <div><label className={lbl} htmlFor="ag-mem">Memory</label>
              <select id="ag-mem" className={field} disabled={agent.origin === "backend"} value={agent.memory} onChange={(e) => set({ memory: e.target.value as Agent["memory"] })}>
                <option value="none">None</option><option value="session">Per run</option><option value="long-term">Long-term</option>
              </select>
            </div>
            <div><label className={lbl} htmlFor="ag-schema">Output schema</label><textarea id="ag-schema" rows={3} className={`${field} font-mono text-xs`} value={agent.outputSchema} onChange={(e) => set({ outputSchema: e.target.value })} /></div>
          </div>
        )}
      </TabsContent>

      <TabsContent value="tools" className="space-y-1.5 pt-4">
        {assignmentReview?.items.filter((item) => item.agent_id === agent.canonicalId).map((item, index) =>
          <div key={index} className="rounded-lg border border-border p-3 text-xs">
            <p>{item.capability ?? "Agent registration"} · {item.tool_id ?? "No assigned tool"}</p>
            <p className="mt-1">{item.authorization_state}{item.approval_required ? " · Approval required" : ""}</p>
            {!!item.reason_codes.length && <p className="mt-1 text-muted-foreground">{item.reason_codes.join(", ")}</p>}
          </div>)}
        {agent.origin === "backend" && <div className="rounded-lg border border-border p-3 text-xs"><p>Requested capabilities: {agent.capabilities?.join(", ") || "None"}</p><p className="mt-1">Assigned tools: {agent.tools.join(", ") || "None"}</p><p className="mt-1 text-muted-foreground">Declared permissions: {agent.declaredPermissions?.join(", ") || "None"}</p></div>}
        {backend.status === "connected" ? <>{backend.tools.map((t) => <div key={t.tool_id} className="rounded-lg border border-border p-3 text-xs"><p className="font-medium">{t.definition.capability} · {t.definition.provider_id}</p><p className="mt-1 text-muted-foreground">{t.definition.availability} · {t.definition.risk_level} risk · {t.authorization_state}{t.definition.approval_required ? " · Approval required" : ""}</p></div>)}{!backend.tools.length && <p className="text-xs text-muted-foreground">No authorized tool metadata is available for this session.</p>}<p className="text-xs text-muted-foreground">Requested and assigned tools remain separate. Executable assignments require the trusted registry.</p></> : TOOL_CATALOG.map((t) => (
          <label key={t} className="flex cursor-pointer items-center justify-between rounded-lg border border-border px-3 py-2 text-sm hover:bg-canvas">
            <span>{t} <span className={`text-[11px] ${toolStatus(t) === "connected" ? "text-success" : toolStatus(t) === "error" ? "text-destructive" : "text-muted-foreground"}`}>· {toolStatus(t)}</span></span>
            <Switch checked={agent.tools.includes(t)} onCheckedChange={() => toggle("tools", t)} />
          </label>
        ))}
        <p className="pt-2 text-[11px] text-muted-foreground">Tool selections are draft requests; registry authorization is pending. <Link to="/app/integrations" className="text-primary">Manage integrations</Link></p>
      </TabsContent>

      <TabsContent value="knowledge" className="space-y-1.5 pt-4">
        {knowledge.map((k) => (
          <label key={k.id} className="flex cursor-pointer items-center justify-between rounded-lg border border-border px-3 py-2 text-sm hover:bg-canvas">
            <span>{k.name} <span className="text-[11px] text-muted-foreground">· {k.collection}{k.status !== "ready" ? ` · ${k.status}` : ""}</span></span>
            <Switch checked={agent.knowledge.includes(k.name)} disabled={k.status === "failed"} onCheckedChange={() => toggle("knowledge", k.name)} />
          </label>
        ))}
        <p className="pt-2 text-[11px] text-muted-foreground">Knowledge ingestion is not connected. <Link to="/app/knowledge" className="text-primary">Open knowledge library</Link></p>
      </TabsContent>

      <TabsContent value="safety" className="space-y-1.5 pt-4">
        {agent.origin === "backend" && <p className="text-xs text-muted-foreground">Guardrails are controlled by the accepted agent definition and server policy.</p>}
        {agent.origin !== "backend" && ([
          ["piiRedaction", "PII redaction", "Mask emails and phone numbers before model calls"],
          ["injectionDetection", "Prompt-injection detection", "Block runs whose input tries to override instructions"],
          ["outputValidation", "Output validation", "Check output against schema"],
        ] as const).map(([k, l, d]) => (
          <label key={k} className="flex cursor-pointer items-start justify-between gap-3 rounded-lg border border-border px-3 py-2.5 hover:bg-canvas">
            <span><span className="block text-sm">{l}</span><span className="text-xs text-muted-foreground">{d}</span></span>
            <Switch checked={agent.guardrails[k]} disabled={agent.origin === "backend"} onCheckedChange={(v) => set({ guardrails: { ...agent.guardrails, [k]: v } })} />
          </label>
        ))}
      </TabsContent>
    </Tabs>
    </>
  );
}
