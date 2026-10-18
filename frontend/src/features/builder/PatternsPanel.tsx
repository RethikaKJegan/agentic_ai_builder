import { displayText } from "@/lib/display-text";
import { useState } from "react";
import { ArrowRight, ChevronsLeft, GitBranch, LayoutGrid, Network, Rows3, ShieldCheck, Split } from "lucide-react";
import { PATTERNS, type PatternKind } from "@/domain/patterns";

export const PATTERN_MIME = "application/x-mesh-pattern";
const ICONS: Record<PatternKind, typeof Rows3> = { sequential: ArrowRight, parallel: Split, conditional: GitBranch, approval: ShieldCheck, supervisor: Network };

/** Narrow, collapsible list of draggable workflow patterns. Enter/click inserts at canvas centre. */
export function PatternsPanel({ onInsert }: { onInsert: (k: PatternKind) => void }) {
  const [open, setOpen] = useState(false);
  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="absolute left-3 top-3 z-10 flex h-9 items-center gap-1.5 rounded-lg border border-border bg-background px-2.5 text-xs font-medium shadow-soft hover:border-primary hover:text-primary" aria-label="Show patterns">
        <LayoutGrid className="h-3.5 w-3.5" />Patterns
      </button>
    );
  }
  return (
    <aside className="absolute left-3 top-3 z-10 w-[188px] rounded-xl border border-border bg-background/95 p-2 shadow-soft backdrop-blur" aria-label="Workflow patterns">
      <div className="mb-1 flex items-center justify-between px-1">
        <p className="text-xs font-medium">Patterns</p>
        <button onClick={() => setOpen(false)} className="rounded p-0.5 text-muted-foreground hover:bg-muted" aria-label="Hide patterns"><ChevronsLeft className="h-3.5 w-3.5" /></button>
      </div>
      <ul className="space-y-1">
        {PATTERNS.map((p) => {
          const I = ICONS[p.id];
          return (
            <li key={p.id}>
              <button
                draggable
                onDragStart={(e) => { e.dataTransfer.setData(PATTERN_MIME, p.id); e.dataTransfer.effectAllowed = "copy"; }}
                onClick={() => onInsert(p.id)}
                title="Drag onto the canvas, or press Enter to insert"
                className="flex w-full cursor-grab items-start gap-2 rounded-lg border border-transparent px-2 py-1.5 text-left hover:border-border-accent hover:bg-canvas active:cursor-grabbing"
              >
                <I className={`mt-0.5 h-3.5 w-3.5 shrink-0 ${p.id === "supervisor" ? "text-primary" : "text-muted-foreground"}`} />
                <span className="min-w-0"><span className="block text-[12px] font-medium leading-tight">{displayText(p.name)}</span><span className="block text-[10px] leading-snug text-muted-foreground">{displayText(p.description)}</span></span>
              </button>
            </li>
          );
        })}
      </ul>
      <p className="mt-1.5 px-1 text-[10px] text-muted-foreground">Drag onto canvas</p>
    </aside>
  );
}
