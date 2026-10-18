import { displayText } from "@/lib/display-text";
import { Cpu, ShieldAlert } from "lucide-react";
import { getModel } from "@/domain/models";
import type { RunStep } from "@/domain/types";
import { StatusPill } from "@/features/shell/StatusPill";
import { NODE_META } from "@/features/builder/nodeMeta";

export function RunTrace({ steps }: { steps: RunStep[] }) {
  return (
    <ol className="space-y-2">
      {steps.map((s, i) => {
        const M = NODE_META[s.kind];
        return (
          <li key={`${s.nodeId}-${i}`} className={`rounded-lg border border-border ${s.delegatedBy ? "ml-4 border-l-2 border-l-primary/40" : ""} bg-background p-2.5`}>
            <div className="flex items-center gap-2">
              <M.icon className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="min-w-0 flex-1 truncate text-sm font-medium">{displayText(s.label)}{s.delegatedBy && <span className="block truncate text-[10px] font-normal text-primary">delegated by {s.delegatedBy}</span>}</span>
              <StatusPill status={s.status} />
            </div>
            <p className="mt-1 text-xs text-muted-foreground">{s.output}</p>
            <div className="mt-1 flex flex-wrap gap-x-3 font-mono text-[10px] text-muted-foreground">
              <span>{s.latencyMs}ms</span>
              {s.modelId && <span className="flex items-center gap-1"><Cpu className="h-3 w-3" />{displayText(getModel(s.modelId).name)} (sim)</span>}
              {s.tokens > 0 && <span>{s.tokens} tok · ${s.cost.toFixed(4)}</span>}
            </div>
            {s.guardrail && <p className="mt-1 flex items-center gap-1 text-[11px] text-warning"><ShieldAlert className="h-3 w-3" />{s.guardrail}</p>}
          </li>
        );
      })}
    </ol>
  );
}

export const PageHeader = ({ title, sub, children }: { title: string; sub: string; children?: React.ReactNode }) => (
  <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
    <div>
      <h1 className="font-display text-3xl font-semibold tracking-tight">{displayText(title)}</h1>
      <p className="mt-1 text-sm text-muted-foreground">{sub}</p>
    </div>
    {children}
  </div>
);
