"use client";
import { Link } from "@/lib/navigation";
import { Plus } from "lucide-react";
import { InvestigationList } from "@/features/investigations/InvestigationList";

export default function WorkflowsPage() {
  return <div className="mx-auto max-w-5xl px-6 py-10">
    <div className="flex items-center justify-between gap-4">
      <h1 className="text-3xl font-semibold">Workflows</h1>
      <Link to="/app" className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-primary px-3.5 text-sm font-medium text-primary-foreground hover:bg-primary-deep"><Plus className="h-4 w-4" /> New</Link>
    </div>
    <InvestigationList showHeader={false} />
  </div>;
}
