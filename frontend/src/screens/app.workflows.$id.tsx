"use client";
import { useRouteParams } from "@/lib/navigation";
import { Link } from "@/lib/navigation";
import { ClientOnly } from "@/lib/navigation";
import { lazy, Suspense, useEffect, useState } from "react";
import { useMesh } from "@/domain/store";
import { api } from "@/api/client";
import { useBackend } from "@/api/state";
import { ApiFeedback } from "@/features/workflows/ApiFeedback";

const Builder = lazy(() => import("@/features/builder/Builder"));



export default function WorkflowEditor() {
  const { id } = useRouteParams();
  const workflow = useMesh((s) => s.workflows.find((w) => w.id === id));
  const backendStatus = useBackend((s) => s.status);
  const [error, setError] = useState<Error | null>(null);
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    let active = true;
    const existing = useMesh.getState().workflows.find((w) => w.id === id);
    if (backendStatus !== "connected" || (existing && !existing.serverVersion)) return;
    api.request("get_workflow", { workflow_id: id }).then((result) => {
      if (active) { useMesh.getState().acceptWorkflow(result.workflow); setLoaded(true); }
    }).catch((caught) => { if (active) { setError(caught instanceof Error ? caught : new Error("Workflow loading failed.")); setLoaded(true); } });
    return () => { active = false; };
  }, [id, backendStatus]);
  if (!workflow) {
    if (backendStatus === "loading" || (backendStatus === "connected" && !loaded)) return <p className="p-6 text-sm text-muted-foreground">Loading workflow…</p>;
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
        <p className="font-display text-xl font-medium">Workflow not found</p>
        <p className="text-sm text-muted-foreground">This workflow could not be loaded from the server or this browser.</p>
        <ApiFeedback error={error} />
        <Link to="/app/workflows" className="text-sm text-primary">Back to workflows</Link>
      </div>
    );
  }
  const fallback = <div className="flex h-full items-center justify-center bg-canvas text-sm text-muted-foreground">Loading canvas…</div>;
  return (
    <ClientOnly fallback={fallback}>
      <Suspense fallback={fallback}>
        <Builder workflow={workflow} />
      </Suspense>
    </ClientOnly>
  );
}
