import { useEffect, useState } from "react";
import { useBackend } from "@/api/state";
import { api, ApiError } from "@/api/client";
import { useMesh } from "@/domain/store";
import { hasWorkflowEdits } from "@/api/mapping";
export function useDraftSync(workflowId: string) {
  const [error, setError] = useState<Error>();
  const [storageFailed, setStorageFailed] = useState(false);
  useEffect(() => {
    let disposed = false,
      pending = false,
      refreshAgain = false;
    let timer: ReturnType<typeof setTimeout>;
    const refresh = async () => {
      const current = useMesh.getState().workflows.find((w) => w.id === workflowId);
      if (!current || !useBackend.getState().can("workflow.view")) return;
      if (pending) {
        refreshAgain = true;
        return;
      }
      pending = true;
      try {
        const result = await api.request("get_workflow", { workflow_id: workflowId });
        if (!disposed) {
          useMesh.getState().observeWorkflows([result.workflow]);
          setError(undefined);
        }
      } catch (caught) {
        if (!disposed)
          setError(
            !current.serverVersion &&
              caught instanceof ApiError &&
              caught.error.error_code === "WORKFLOW_NOT_FOUND"
              ? undefined
              : caught instanceof Error
                ? caught
                : new Error("Read failed."),
          );
      } finally {
        pending = false;
        if (refreshAgain && !disposed) {
          refreshAgain = false;
          void refresh();
        }
      }
    };
    const tick = async () => {
      await refresh();
      if (!disposed) timer = setTimeout(() => void tick(), 30000);
    };
    const focus = () => {
      void refresh();
    };
    const storage = (event: StorageEvent) => {
      if (event.key !== "mesh-local-drafts-v1") return;
      const state = useMesh.getState();
      const current = state.workflows.find((w) => w.id === workflowId);
      if (current && hasWorkflowEdits(current, state.agents) && !current.tabConflict)
        useMesh.setState({
          workflows: state.workflows.map((w) =>
            w.id === workflowId ? { ...w, tabConflict: true } : w,
          ),
        });
      void refresh();
    };
    const failed = () => setStorageFailed(true);
    void tick();
    window.addEventListener("focus", focus);
    window.addEventListener("storage", storage);
    window.addEventListener("mesh-draft-storage-error", failed);
    return () => {
      disposed = true;
      clearTimeout(timer);
      window.removeEventListener("focus", focus);
      window.removeEventListener("storage", storage);
      window.removeEventListener("mesh-draft-storage-error", failed);
    };
  }, [workflowId]);
  return { error, storageFailed };
}
