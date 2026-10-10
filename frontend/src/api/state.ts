import { create } from "zustand";
import { api, ApiError, type Session, type ToolRecord, type RegistryReview } from "./client";
import { useMesh } from "@/domain/store";

interface BackendState {
  status: "loading" | "connected" | "unavailable";
  session: Session | null;
  tools: ToolRecord[];
  error: ApiError | null;
  reviews: Record<string, RegistryReview>;
  acceptReview: (review: RegistryReview) => void;
  initialize: () => Promise<void>;
  can: (permission: string) => boolean;
}
let initialization: Promise<void> | null = null;
export const useBackend = create<BackendState>((set, get) => ({
  status: "loading", session: null, tools: [], error: null, reviews: {},
  acceptReview: (review) => set((s) => ({ reviews: { ...s.reviews, [review.workflow_id]: review } })),
  can: (permission) => get().session?.auth.decision === "allow" && !!get().session?.auth.permissions.includes(permission),
  initialize: () => {
    if (initialization) return initialization;
    initialization = (async () => {
      try {
        const session = await api.session();
        set({ session, status: "connected", error: null });
        const results = await Promise.allSettled([api.request("list_workflows", {}), api.request("list_tools", {})]);
        const workflows = results[0];
        const tools = results[1];
        if (workflows?.status === "fulfilled") workflows.value.items.forEach((w) => useMesh.getState().acceptWorkflow(w));
        if (tools?.status === "fulfilled") set({ tools: tools.value.items });
        for (const result of results) if (result.status === "rejected" && result.reason instanceof ApiError) set({ error: result.reason });
      } catch (error) {
        set({ status: "unavailable", session: null, error: error instanceof ApiError ? error : null });
      } finally { initialization = null; }
    })();
    return initialization;
  },
}));
