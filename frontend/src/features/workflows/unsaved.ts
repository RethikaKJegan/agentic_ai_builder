import { useEffect } from "react";
import { useMesh } from "@/domain/store";
import { hasWorkflowEdits } from "@/api/mapping";
let editor: string | null = null;
const registrations=new Map<string,number>();
export function editorIsDirty() {
  const state = useMesh.getState(); const workflow = state.workflows.find(item => item.id === editor);
  return !!workflow && hasWorkflowEdits(workflow, state.agents);
}
export function confirmDraftNavigation() {
  return !editorIsDirty() || window.confirm("This workflow has unsaved changes. Leave the editor? Your draft will remain in this browser; use Save draft to persist it on the server.");
}
export function useUnsavedWorkflow(workflowId: string) {
  useEffect(() => {
    editor = workflowId; registrations.set(workflowId,(registrations.get(workflowId)??0)+1);
    const editorUrl = window.location.href; const editorHistory = window.history.state;
    const back = (event: PopStateEvent) => {
      if (window.location.href === editorUrl || !editorIsDirty()) return;
      if (!confirmDraftNavigation()) {
        event.stopImmediatePropagation();
        window.history.pushState(editorHistory, "", editorUrl);
      }
    };
    window.addEventListener("popstate", back, true);
    const unload = (event: BeforeUnloadEvent) => { if (editorIsDirty()) { event.preventDefault(); event.returnValue = ""; } };
    window.addEventListener("beforeunload", unload);
    return () => { const remaining=(registrations.get(workflowId)??1)-1;registrations.set(workflowId,remaining);if (editor === workflowId && !remaining) editor = null; window.removeEventListener("beforeunload", unload); window.removeEventListener("popstate", back, true); };
  }, [workflowId]);
}
