"use client";
import { confirmDraftNavigation } from "@/features/workflows/unsaved";
import { displayText } from "@/lib/display-text";
import { usePathname } from "next/navigation";
import { Link, useNavigate } from "@/lib/navigation";
import { useCallback, useState, type ReactNode } from "react";
import { Database, History, Settings as SettingsIcon, ShieldCheck, Plug, Store, Bell, Bot, ChevronsLeft, ChevronsRight, LayoutGrid, RotateCcw, Search, Workflow as WfIcon } from "lucide-react";
import { LogoMark } from "@/components/mesh/Logo";
import { CommandPalette } from "@/features/shell/CommandPalette";
import { ShortcutsDialog, useGlobalShortcuts } from "@/features/shell/Shortcuts";
import { Skeleton } from "@/components/ui/skeleton";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Keyboard, Menu } from "lucide-react";
import { useMeshHydrated } from "@/features/shell/useHydrated";
import { useMesh } from "@/domain/store";
import { useBackend } from "@/api/state";
import { roleLabel } from "@/domain/governance";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { toast } from "sonner";



const NAV = [
  { group: "Workspace", items: [
    { to: "/app", label: "Overview", icon: LayoutGrid, exact: true },
    { to: "/app/workflows", label: "Workflows", icon: WfIcon, exact: false },
    { to: "/app/agents", label: "Agents", icon: Bot, exact: false },
    { to: "/app/marketplace", label: "Marketplace", icon: Store, exact: false },
  ] },
  { group: "Control", items: [
    { to: "/app/integrations", label: "Integrations", icon: Plug, exact: false },
    { to: "/app/data-intelligence", label: "Data Intelligence", icon: Database, exact: false },
  ] },
  { group: "Operate", items: [
    { to: "/app/runs", label: "Runs", icon: History, exact: false },
    { to: "/app/governance", label: "Governance", icon: ShieldCheck, exact: false },
    { to: "/app/settings", label: "Settings", icon: SettingsIcon, exact: false },
  ] },
] as const;

export default function AppShell({ children }: { children: ReactNode }) {
  const ready = useMeshHydrated();
  const [collapsed, setCollapsed] = useState(false);
  const [cmd, setCmd] = useState(false);
  const [help, setHelp] = useState(false);
  const [more, setMore] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  async function signOut() {
    if (signingOut || !confirmDraftNavigation()) return;
    setSigningOut(true);
    try {
      const response = await fetch("/api/workspace-auth/logout", { method: "POST" });
      if (!response.ok) throw new Error("Sign-out failed. Please try again.");
      window.location.assign("/login");
    } catch {
      toast.error("Unable to sign out. Please try again.");
      setSigningOut(false);
    }
  }
  const openHelp = useCallback(() => setHelp(true), []);
  useGlobalShortcuts(openHelp);
  const pathname = usePathname();
  const navigate = useNavigate();
  const activity = useMesh((s) => s.activity);
  const role = useMesh((s) => s.role);
  const localPending = useMesh((s) => s.runs.filter((r) => r.status === "paused").length);
  const serverPending = useBackend((s) => Object.values(s.overview).reduce((total, item) => total + item.pending_approval_count, 0));
  const pending = Math.max(localPending, serverPending);
  const inBuilder = /^\/app\/workflows\/[^/]+$/.test(pathname);
  const crumbs = pathname.split("/").filter(Boolean).slice(1);

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <aside className={`hidden shrink-0 flex-col border-r border-border bg-sidebar transition-[width] duration-200 md:flex ${collapsed || inBuilder ? "w-[60px]" : "w-[60px] lg:w-60"}`}>
        <div className="flex min-h-24 items-center justify-center px-3 py-5 lg:justify-start lg:px-4">
          <Link to="/" aria-label="PraxilonAI home" title="PraxilonAI" className="flex min-w-0 items-center gap-3">
            <LogoMark className="h-9 w-9 shrink-0" />
            {!(collapsed || inBuilder) && <div className="hidden min-w-0 lg:block">
              <span className="block font-display text-xl font-semibold tracking-tight">PraxilonAI</span>
            </div>}
          </Link>
        </div>
        <nav className="flex-1 space-y-5 px-3 pt-3">
          {NAV.map((g) => (
            <div key={g.group}>
              {!(collapsed || inBuilder) && <p className="mb-1.5 hidden lg:block px-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">{g.group}</p>}
              {g.items.map((it) => (
                <Link
                  key={it.to}
                  to={it.to}
                  activeOptions={{ exact: it.exact }}
                  title={displayText(it.label)}
                  className="flex h-9 items-center gap-2.5 rounded-lg px-2.5 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                  activeProps={{ className: "bg-sidebar-accent !text-sidebar-accent-foreground font-medium" }}
                >
                  <it.icon className="h-4 w-4 shrink-0" />
                  {!(collapsed || inBuilder) && <span className="hidden flex-1 lg:inline">{displayText(it.label)}</span>}
                </Link>
              ))}
            </div>
          ))}
        </nav>
        {!inBuilder && (
          <button onClick={() => setCollapsed((c) => !c)} className="m-3 hidden h-8 items-center lg:flex justify-center rounded-lg text-muted-foreground hover:bg-muted" aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}>
            {collapsed ? <ChevronsRight className="h-4 w-4" /> : <ChevronsLeft className="h-4 w-4" />}
          </button>
        )}
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center gap-3 border-b border-border px-4">
          <Link to="/app" className="flex min-w-0 items-center gap-2 md:hidden" aria-label="PraxilonAI workspace"><LogoMark className="h-8 w-8 shrink-0" /><span className="min-w-0"><span className="block font-display text-sm font-semibold">PraxilonAI</span></span></Link>
          <span className="hidden rounded-md border border-border px-2 py-1 text-xs font-medium sm:inline">Local workspace</span>
          <nav aria-label="Breadcrumb" className="hidden min-w-0 items-center gap-1.5 truncate text-sm text-muted-foreground sm:flex">
            <span>/</span>
            <span className="capitalize text-foreground">{crumbs[0] ?? "overview"}</span>
            {crumbs[1] && <><span>/</span><span className="truncate">editor</span></>}
          </nav>
          <div className="flex-1" />
          <button onClick={() => setCmd(true)} className="flex h-8 items-center gap-2 rounded-lg border border-border bg-canvas px-2.5 text-sm text-muted-foreground transition-colors hover:border-border-accent sm:w-64">
            <Search className="h-3.5 w-3.5" />
            <span className="hidden flex-1 text-left sm:inline">Search or jump to…</span>
            <kbd className="hidden rounded border border-border bg-background px-1.5 font-mono text-[10px] sm:inline">⌘K</kbd>
          </button>
          <button onClick={() => setHelp(true)} className="hidden h-8 w-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted md:flex" aria-label="Keyboard shortcuts"><Keyboard className="h-4 w-4" /></button>
          <Popover>
            <PopoverTrigger className="relative flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted" aria-label="Notifications">
              <Bell className="h-4 w-4" />
              {ready && pending > 0 && <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-warning" />}
            </PopoverTrigger>
            <PopoverContent align="end" className="w-80 p-0">
              {pending > 0 && <Link to="/app/approvals" className="flex items-center justify-between border-b border-border bg-warning/10 px-4 py-2.5 text-sm font-medium hover:bg-warning/15">{pending} run{pending > 1 ? "s" : ""} waiting for approval<span className="text-primary">Review →</span></Link>}
              <p className="border-b border-border px-4 py-2.5 text-sm font-medium">Activity</p>
              <div className="max-h-80 overflow-auto">
                {activity.length === 0 && <p className="p-4 text-sm text-muted-foreground">Nothing yet.</p>}
                {activity.slice(0, 8).map((a) => (
                  <button key={a.id} disabled={!a.workflowId} onClick={() => a.workflowId && navigate({ to: "/app/workflows/$id", params: { id: a.workflowId } })} className="block w-full border-b border-border px-4 py-2.5 text-left text-sm last:border-0 hover:bg-canvas">
                    <p>{displayText(a.message)}</p>
                    <p className="text-xs text-muted-foreground">{new Date(a.at).toLocaleString()}</p>
                  </button>
                ))}
              </div>
            </PopoverContent>
          </Popover>
          <DropdownMenu>
            <DropdownMenuTrigger className="flex h-8 w-8 items-center justify-center rounded-full bg-foreground text-xs font-medium text-background" aria-label="User menu">P</DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>
                <p>Local workspace</p>
                <p className="truncate text-xs font-normal text-muted-foreground" title="engineering@bellcorpstudio.com">engineering@bellcorpstudio.com</p>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild><Link to="/">Back to website</Link></DropdownMenuItem>
              <DropdownMenuItem disabled={signingOut} onSelect={() => void signOut()}>{signingOut ? "Signing out…" : "Sign out"}</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>
        <main key={ready ? "r" : "l"} className={`page-enter min-h-0 flex-1 ${inBuilder ? "overflow-hidden" : "overflow-y-auto"}`}>
          {ready ? children : <div className="mx-auto max-w-5xl space-y-4 p-6 md:p-10" aria-label="Loading workspace"><Skeleton className="h-9 w-72" /><Skeleton className="h-4 w-96 max-w-full" /><div className="grid gap-3 md:grid-cols-3"><Skeleton className="h-28" /><Skeleton className="h-28" /><Skeleton className="h-28" /></div><Skeleton className="h-64" /></div>}
        </main>
        <nav className="flex border-t border-border md:hidden">
          {NAV.flatMap((g) => [...g.items]).filter((it) => ["/app", "/app/workflows", "/app/agents", "/app/approvals", "/app/runs"].includes(it.to)).map((it) => (
            <Link key={it.to} to={it.to} activeOptions={{ exact: it.exact }} className="flex flex-1 flex-col items-center gap-0.5 py-2 text-[11px] text-muted-foreground" activeProps={{ className: "!text-primary" }}>
              <it.icon className="h-4 w-4" />{displayText(it.label)}
            </Link>
          ))}
          <button onClick={() => setMore(true)} className="flex flex-1 flex-col items-center gap-0.5 py-2 text-[11px] text-muted-foreground"><Menu className="h-4 w-4" />More</button>
        </nav>
        <Sheet open={more} onOpenChange={setMore}>
          <SheetContent side="bottom" className="max-h-[80vh] overflow-y-auto">
            <SheetHeader><SheetTitle>All pages</SheetTitle></SheetHeader>
            {NAV.map((g) => (
              <div key={g.group} className="mt-3">
                <p className="mb-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">{g.group}</p>
                <div className="grid grid-cols-2 gap-1">
                  {g.items.map((it) => (
                    <Link key={it.to} to={it.to} activeOptions={{ exact: it.exact }} onClick={() => setMore(false)} className="flex items-center gap-2 rounded-lg px-2.5 py-2.5 text-sm hover:bg-muted" activeProps={{ className: "bg-sidebar-accent text-sidebar-accent-foreground font-medium" }}>
                      <it.icon className="h-4 w-4" />{displayText(it.label)}
                    </Link>
                  ))}
                </div>
              </div>
            ))}
          </SheetContent>
        </Sheet>
      </div>
      {ready && <CommandPalette open={cmd} onOpenChange={setCmd} />}
      <ShortcutsDialog open={help} onOpenChange={setHelp} />
    </div>
  );
}
