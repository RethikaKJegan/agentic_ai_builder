import { readFileSync } from "node:fs";
import path from "node:path";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api, ApiError, type Session } from "@/api/client";
import { CanonicalWorkflowSchema, type CanonicalWorkflow } from "@/api/contracts.generated";
import { useMesh } from "@/domain/store";
import { useBackend } from "@/api/state";
import { EditorWorkflowActions } from "./EditorWorkflowActions";
vi.mock("./ProcurementReview", () => ({ ProcurementReview: () => null }));
vi.mock("./SheetAccessReview", () => ({ SheetAccessReview: () => null }));
vi.mock("./CustomerAutomationReview", () => ({ CustomerAutomationReview: () => null }));
vi.mock("@/lib/navigation", () => ({
  Link: ({ children }: { children: React.ReactNode }) => <span>{children}</span>,
}));
let document: CanonicalWorkflow;
let release: Awaited<ReturnType<typeof api.releaseState>>["release"];
const permissions = [
  "workflow.view",
  "workflow.edit",
  "workflow.validate",
  "workflow.approve",
  "workflow.publish",
  "workflow.execute",
  "runs.view",
];
const started = vi.fn();
function View() {
  const workflow = useMesh((state) => state.workflows[0]);
  return workflow ? (
    <EditorWorkflowActions workflow={workflow} onStarted={started} onExecution={vi.fn()} />
  ) : null;
}
beforeEach(() => {
  document = CanonicalWorkflowSchema.parse(
    JSON.parse(
      readFileSync(
        path.resolve(process.cwd(), "../shared/contracts/examples/workflows/support-triage.json"),
        "utf8",
      ),
    ),
  );
  document.status = "draft";
  document.inputs = [];
  document.metadata = {};
  release = null;
  started.mockReset();
  useMesh.setState({ workflows: [], agents: [] });
  useMesh.getState().acceptWorkflow(document);
  useBackend.setState({
    status: "connected",
    overview: {},
    reviews: {},
    session: {
      runtime_available: true,
      auth: { roles: ["admin"], decision: "allow", permissions },
    } as unknown as Session,
    can: (p) => permissions.includes(p),
    refreshOverview: vi.fn().mockResolvedValue(undefined),
  });
  vi.spyOn(api, "releaseState").mockImplementation(
    async () =>
      ({ workflow_id: document.workflow_id, release }) as Awaited<
        ReturnType<typeof api.releaseState>
      >,
  );
  vi.spyOn(api, "submitApproval").mockImplementation(
    async () =>
      ({
        workflow: (document = {
          ...document,
          metadata: { approval_submission: { workflow_version: document.version } },
        }),
      }) as Awaited<ReturnType<typeof api.submitApproval>>,
  );
  vi.spyOn(api, "activateRelease").mockImplementation(async (payload) => {
    release = {
      release_id: "active-release",
      workflow_version: payload.workflow_version,
      state: "active",
      trigger_binding_count: 0,
    };
    return {
      operation: { state: "succeeded" },
      release: { release_id: "active-release" },
    } as Awaited<ReturnType<typeof api.activateRelease>>;
  });
  vi.spyOn(api, "request").mockImplementation((async (
    operation: Parameters<typeof api.request>[0],
    payload: Parameters<typeof api.request>[1],
  ) => {
    if (operation === "get_workflow") return { workflow: structuredClone(document) };
    if (operation === "save_workflow_version") {
      document = structuredClone((payload as { workflow: CanonicalWorkflow }).workflow);
      return { workflow: structuredClone(document) };
    }
    if (operation === "approve_workflow")
      document = {
        ...document,
        status: (payload as { action: string }).action === "approve" ? "approved" : "published",
      };
    if (operation === "execute_workflow")
      return {
        run: {
          run_id: "run-accepted",
          workflow_id: document.workflow_id,
          workflow_version: (payload as { workflow_version: number }).workflow_version,
          status: "queued",
          approvals: [],
        },
      };
    return { workflow: structuredClone(document) };
  }) as never);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
it("runs a saved draft directly without standalone validation, publication or automatic approval", async () => {
 render(<View/>);expect(screen.queryByRole('button',{name:'Validate'})).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'Run'}));
 await waitFor(()=>expect(started).toHaveBeenCalledOnce());
 expect(vi.mocked(api.request).mock.calls.map(call=>call[0])).toEqual(['get_workflow','execute_workflow']);
 expect(api.activateRelease).not.toHaveBeenCalled();
});
it("saves edited content before Run and keeps the exact saved revision", async () => {
 useMesh.getState().renameWorkflow(document.workflow_id,'Edited run');
 render(<View/>);fireEvent.click(screen.getByRole('button',{name:'Run'}));
 await waitFor(()=>expect(started).toHaveBeenCalledOnce());
 expect(vi.mocked(api.request).mock.calls.map(call=>call[0])).toEqual(['save_workflow_version','execute_workflow']);
 expect(vi.mocked(api.request).mock.calls[1]?.[1]).toMatchObject({workflow_version:2});
});
it("keeps required workflow approval explicitly human after automatic Run checks", async () => {
 const normal=vi.mocked(api.request).getMockImplementation()!;
 vi.mocked(api.request).mockImplementation((async(op,payload,key)=>{
  if(op==='execute_workflow'&&document.status==='draft')throw new ApiError({error_code:'WORKFLOW_APPROVAL_REQUIRED',message:'Awaiting approval.',request_id:'pending',retryable:false},undefined,{outcome:'rejected',httpStatus:409});
  return normal(op,payload,key);
 }) as typeof api.request);
 render(<View/>);fireEvent.click(screen.getByRole('button',{name:'Run'}));
 const approve=await screen.findByRole('button',{name:'Approve workflow'});
 expect(vi.mocked(api.request).mock.calls.some(call=>call[0]==='approve_workflow')).toBe(false);
 fireEvent.click(approve);await waitFor(()=>expect(started).toHaveBeenCalledOnce());
 expect(vi.mocked(api.request).mock.calls.map(call=>call[0])).toEqual(['get_workflow','execute_workflow','approve_workflow','execute_workflow']);
 const runs=vi.mocked(api.request).mock.calls.filter(call=>call[0]==='execute_workflow');expect(runs[0]?.[2]).toBe(runs[1]?.[2]);
});
it("does not submit when runtime execution permission is missing", async () => {
 useBackend.setState({can:()=>false});render(<View/>);
 expect(screen.getByRole('button',{name:'Run'})).toBeDisabled();expect(api.request).not.toHaveBeenCalled();
});
