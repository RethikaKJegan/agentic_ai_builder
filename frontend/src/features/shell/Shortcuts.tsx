import { displayText } from "@/lib/display-text";
import { useNavigate } from "@/lib/navigation";
import { useEffect, useRef } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

const JUMPS = { o: "/app", w: "/app/workflows", a: "/app/agents", r: "/app/runs", m: "/app/monitoring", p: "/app/approvals", g: "/app/governance" } as const;

export const SHORTCUTS: { keys: string; label: string; group: string }[] = [
  { keys: "⌘/Ctrl K", label: "Search or jump to…", group: "Global" },
  { keys: "?", label: "Show keyboard shortcuts", group: "Global" },
  { keys: "G then O", label: "Go to Overview", group: "Global" },
  { keys: "G then W", label: "Go to Workflows", group: "Global" },
  { keys: "G then A", label: "Go to Agents", group: "Global" },
  { keys: "G then P", label: "Go to Approvals", group: "Global" },
  { keys: "G then R", label: "Go to Runs", group: "Global" },
  { keys: "G then M", label: "Go to Monitoring", group: "Global" },
  { keys: "G then G", label: "Go to Governance", group: "Global" },
  { keys: "⌘/Ctrl Z", label: "Undo", group: "Workflow editor" },
  { keys: "⌘/Ctrl ⇧ Z", label: "Redo", group: "Workflow editor" },
  { keys: "Delete", label: "Remove selected step", group: "Workflow editor" },
  { keys: "F", label: "Fit the view", group: "Workflow editor" },
  { keys: "Esc", label: "Close side panel", group: "Workflow editor" },
];

export function useGlobalShortcuts(openHelp: () => void) {
  const navigate = useNavigate();
  const pendingG = useRef(0);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      if (e.metaKey || e.ctrlKey || e.altKey || t.closest("input, textarea, select, [contenteditable], [role=dialog]")) return;
      const k = e.key.toLowerCase();
      if (e.key === "?") { e.preventDefault(); openHelp(); return; }
      if (Date.now() - pendingG.current < 1200 && k in JUMPS) {
        pendingG.current = 0;
        e.preventDefault();
        navigate({ to: JUMPS[k as keyof typeof JUMPS] });
        return;
      }
      if (k === "g") pendingG.current = Date.now();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [navigate, openHelp]);
}

export function ShortcutsDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  const groups = [...new Set(SHORTCUTS.map((s) => s.group))];
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader><DialogTitle>Keyboard shortcuts</DialogTitle></DialogHeader>
        {groups.map((g) => (
          <div key={g}>
            <p className="mb-1 text-xs font-medium uppercase tracking-wider text-muted-foreground">{g}</p>
            <div className="divide-y divide-border">
              {SHORTCUTS.filter((s) => s.group === g).map((s) => (
                <div key={s.keys} className="flex items-center justify-between py-1.5 text-sm">
                  <span>{displayText(s.label)}</span>
                  <kbd className="rounded border border-border bg-canvas px-1.5 py-0.5 font-mono text-[11px]">{s.keys}</kbd>
                </div>
              ))}
            </div>
          </div>
        ))}
      </DialogContent>
    </Dialog>
  );
}
