import { create } from "zustand";
import { api, ApiError, type Session, type ToolRecord, type RegistryReview, type WorkflowOverview } from "./client";
import { useMesh } from "@/domain/store";

interface BackendState {
  status: "loading" | "connected" | "unavailable";
  session: Session | null;
  tools: ToolRecord[];
  error: ApiError | null;
  reviews: Record<string, RegistryReview>;
  overview: Record<string, WorkflowOverview>;
  overviewSequence: number;
  liveStatus: "connecting" | "live" | "stale";
  lastOverviewUpdate: string | null;
  acceptReview: (review: RegistryReview) => void;
  refreshOverview: () => Promise<void>;
  initialize: () => Promise<void>;
  can: (permission: string) => boolean;
}
let initialization: Promise<void> | null = null;
export const useBackend = create<BackendState>((set, get) => ({
  status: "loading", session: null, tools: [], error: null, reviews: {}, overview: {}, overviewSequence: 0,
  liveStatus: "connecting", lastOverviewUpdate: null,
  acceptReview: (review) => set((s) => ({ reviews: { ...s.reviews, [review.workflow_id]: review } })),
  can: (permission) => get().session?.auth.decision === "allow" && !!get().session?.auth.permissions.includes(permission),
  refreshOverview: async () => {
    try {
      const snapshot = await api.overview();
      const overview = Object.fromEntries(snapshot.items.map((item) => [item.workflow_id, item]));
      set({ overview, overviewSequence: Math.max(get().overviewSequence, snapshot.next_sequence), liveStatus: "live", lastOverviewUpdate: new Date().toISOString(),
        error: get().error?.error.error_code === "AUTHENTICATION_REQUIRED" ? null : get().error });
    } catch (error) {
      set({ liveStatus: "stale", error: error instanceof ApiError ? error : get().error });
    }
  },
  initialize: () => {
    if (initialization) return initialization;
    initialization = (async () => {
      try {
        const session = await api.session();
        set({ session, status: "connected", error: null });
        const results = await Promise.allSettled([api.request("list_workflows", {}), api.request("list_tools", {}), api.overview()]);
        const workflows = results[0];
        const tools = results[1];
        if (workflows?.status === "fulfilled") workflows.value.items.forEach((w) => useMesh.getState().acceptWorkflow(w));
        if (tools?.status === "fulfilled") set({ tools: tools.value.items });
        const overview = results[2];
        if (overview?.status === "fulfilled") set({ overview: Object.fromEntries(overview.value.items.map((item) => [item.workflow_id, item])),
          overviewSequence: overview.value.next_sequence, liveStatus: "live", lastOverviewUpdate: new Date().toISOString() });
        else set({ liveStatus: "stale" });
        for (const result of results) if (result.status === "rejected" && result.reason instanceof ApiError) set({ error: result.reason });
      } catch (error) {
        set({ status: "unavailable", session: null, error: error instanceof ApiError ? error : null });
      } finally { initialization = null; }
    })();
    return initialization;
  },
}));
