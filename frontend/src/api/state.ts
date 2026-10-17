import { create } from "zustand";
import { api, ApiError, type Session, type ToolRecord, type RegistryReview, type WorkflowOverview } from "./client";
import { useMesh } from "@/domain/store";

interface BackendState {
  status: "loading" | "connected" | "unavailable";
  session: Session | null;
  tools: ToolRecord[];
  error: ApiError | null;
  overviewError: ApiError | null;
  reviews: Record<string, RegistryReview>;
  overview: Record<string, WorkflowOverview>;
  overviewSequence: number;
  liveStatus: "connecting" | "live" | "stale";
  lastOverviewUpdate: string | null;
  workflowCursor: string | null;
  workflowNextCursor: string | null;
  workflowTotal: number | null;
  workflowPageBusy: boolean;
  loadWorkflowPage: (cursor?: string | null) => Promise<void>;
  acceptReview: (review: RegistryReview) => void;
  refreshOverview: () => Promise<void>;
  initialize: () => Promise<void>;
  can: (permission: string) => boolean;
}
let initialization: Promise<void> | null = null;
let overviewRefresh: Promise<void> | null = null;
export const useBackend = create<BackendState>((set, get) => ({
  status: "loading", session: null, tools: [], error: null, reviews: {}, overview: {}, overviewSequence: 0,
  liveStatus: "connecting", lastOverviewUpdate: null, overviewError: null,
  workflowCursor: null, workflowNextCursor: null, workflowTotal: null, workflowPageBusy: false,
  loadWorkflowPage: async (cursor = null) => {
    if (get().workflowPageBusy) return;
    set({workflowPageBusy:true});
    try {
      const [page, snapshot] = await Promise.all([api.workflowsPage(cursor), api.overview(undefined,cursor)]);
      useMesh.getState().observeWorkflows(page.items);
      set({workflowCursor:cursor,workflowNextCursor:page.next_cursor ?? null,workflowTotal:page.total ?? page.items.length,
        overview:Object.fromEntries(snapshot.items.map(item=>[item.workflow_id,item])),overviewError:null,error:null,
        liveStatus:"live",lastOverviewUpdate:new Date().toISOString()});
    } catch(error) { if(error instanceof ApiError)set({error,overviewError:error}); }
    finally { set({workflowPageBusy:false}); }
  },
  acceptReview: (review) => set((s) => ({ reviews: { ...s.reviews, [review.workflow_id]: review } })),
  can: (permission) => get().session?.auth.decision === "allow" && !!get().session?.auth.permissions.includes(permission),
  refreshOverview: () => {
    if(overviewRefresh)return overviewRefresh;
    overviewRefresh=(async()=>{
    try {
      const cursor = get().workflowCursor;
      const snapshot = await api.overview(undefined,cursor);
      if (get().workflowCursor !== cursor) return;
      if ((get().status === "connected" || get().status === "unavailable") && !get().session && get().error?.error.error_code === "AUTHENTICATION_REQUIRED") {
        const session = await api.session();
        set({ session, status: "connected" });
      }
      const overview = Object.fromEntries(snapshot.items.map((item) => [item.workflow_id, item]));
      const previousOverviewError=get().overviewError;
      set({ overviewError:null, overview, overviewSequence: Math.max(get().overviewSequence, snapshot.next_sequence), liveStatus: "live", lastOverviewUpdate: new Date().toISOString(),
        error: get().error?.error.error_code === "AUTHENTICATION_REQUIRED" || get().error===previousOverviewError ? null : get().error });
    } catch (error) {
      const failure = error instanceof ApiError ? error : get().error;
      set({ liveStatus: "stale", error: failure, overviewError: failure,
        ...(failure?.error.error_code === "AUTHENTICATION_REQUIRED" ? { session: null, tools: [], reviews: {} } : {}) });
    }
    })().finally(()=>{overviewRefresh=null;});
    return overviewRefresh;
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
        if (workflows?.status === "fulfilled") {
          useMesh.getState().observeWorkflows(workflows.value.items);
          set({workflowCursor:null,workflowNextCursor:workflows.value.next_cursor ?? null,workflowTotal:workflows.value.total ?? workflows.value.items.length});
        }
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
