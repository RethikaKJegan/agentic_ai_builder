import { useNavigate } from "@/lib/navigation";
import { useEffect } from "react";
import { Database, Activity, Bot, BookOpen, History, Inbox, LayoutGrid, Plug, Plus, Settings, ShieldCheck, Store, Workflow as WfIcon } from "lucide-react";
import { CommandDialog, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { useMesh } from "@/domain/store";

export function CommandPalette({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  const navigate = useNavigate();
  const workflows = useMesh((s) => s.workflows);
  const agents = useMesh((s) => s.agents);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        onOpenChange(!open);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onOpenChange]);

  const go = (fn: () => void) => {
    onOpenChange(false);
    fn();
  };

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <CommandInput placeholder="Search workflows, agents, or actions…" />
      <CommandList>
        <CommandEmpty>No results.</CommandEmpty>
        <CommandGroup heading="Actions">
          <CommandItem onSelect={() => go(() => navigate({ to: "/app" }))}>
            <Plus className="mr-2 h-4 w-4" /> Create draft
          </CommandItem>
        </CommandGroup>
        <CommandGroup heading="Navigate">
          <CommandItem onSelect={() => go(() => navigate({ to: "/app" }))}><LayoutGrid className="mr-2 h-4 w-4" /> Overview</CommandItem>
          <CommandItem onSelect={() => go(() => navigate({ to: "/app/workflows" }))}><WfIcon className="mr-2 h-4 w-4" /> Workflows</CommandItem>
          <CommandItem onSelect={() => go(() => navigate({ to: "/app/agents" }))}><Bot className="mr-2 h-4 w-4" /> Agents</CommandItem>
          <CommandItem onSelect={() => go(() => navigate({ to: "/app/marketplace" }))}><Store className="mr-2 h-4 w-4" /> Marketplace</CommandItem>
          <CommandItem onSelect={() => go(() => navigate({ to: "/app/integrations" }))}><Plug className="mr-2 h-4 w-4" /> Integrations</CommandItem>
          <CommandItem onSelect={() => go(() => navigate({ to: "/app/data-intelligence" }))}><Database className="mr-2 h-4 w-4" /> Data Intelligence</CommandItem>
          <CommandItem onSelect={() => go(() => navigate({ to: "/app/knowledge" }))}><BookOpen className="mr-2 h-4 w-4" /> Knowledge</CommandItem>
          <CommandItem onSelect={() => go(() => navigate({ to: "/app/approvals" }))}><Inbox className="mr-2 h-4 w-4" /> Approvals</CommandItem>
          <CommandItem onSelect={() => go(() => navigate({ to: "/app/runs" }))}><History className="mr-2 h-4 w-4" /> Runs</CommandItem>
          <CommandItem onSelect={() => go(() => navigate({ to: "/app/monitoring" }))}><Activity className="mr-2 h-4 w-4" /> Monitoring</CommandItem>
          <CommandItem onSelect={() => go(() => navigate({ to: "/app/governance" }))}><ShieldCheck className="mr-2 h-4 w-4" /> Governance</CommandItem>
          <CommandItem onSelect={() => go(() => navigate({ to: "/app/settings" }))}><Settings className="mr-2 h-4 w-4" /> Settings</CommandItem>
        </CommandGroup>
        {workflows.length > 0 && (
          <CommandGroup heading="Workflows">
            {workflows.map((w) => (
              <CommandItem key={w.id} value={`wf ${w.name} ${w.id}`} onSelect={() => go(() => navigate({ to: "/app/workflows/$id", params: { id: w.id } }))}>
                <WfIcon className="mr-2 h-4 w-4" /> {w.name}
              </CommandItem>
            ))}
          </CommandGroup>
        )}
        {agents.length > 0 && (
          <CommandGroup heading="Agents">
            {agents.map((a) => (
              <CommandItem key={a.id} value={`agent ${a.name} ${a.id}`} onSelect={() => go(() => navigate({ to: "/app/agents", search: { agent: a.id } }))}>
                <Bot className="mr-2 h-4 w-4" /> {a.name}
              </CommandItem>
            ))}
          </CommandGroup>
        )}
      </CommandList>
    </CommandDialog>
  );
}
