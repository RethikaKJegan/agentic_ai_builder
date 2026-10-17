import { readFileSync } from "node:fs";
import path from "node:path";
import { cleanup, render, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { api } from "./client";
import { useBackend } from "./state";
import { useMesh } from "@/domain/store";
import WorkflowEditor from "@/screens/app.workflows.$id";
vi.mock("@/lib/navigation",()=>({useRouteParams:()=>({id:"phase7_registry"}),Link:({children}:{children:React.ReactNode})=><span>{children}</span>,ClientOnly:({children}:{children:React.ReactNode})=><>{children}</>}));
vi.mock("@/features/builder/Builder",()=>({default:()=> <p>Editor mounted</p>}));
afterEach(()=>{cleanup();vi.restoreAllMocks();});
it("retains the authoritative Registry blockers returned by an existing workflow read",async()=>{
 const workflow=JSON.parse(readFileSync(path.resolve(process.cwd(),"../shared/contracts/examples/workflows/support-triage.json"),"utf8"));workflow.workflow_id="phase7_registry";
 const review={workflow_id:workflow.workflow_id,workflow_version:workflow.version,ready:false,reason_codes:["APPROVAL_REQUIRED"],items:[]};
 useMesh.setState({workflows:[],agents:[]});useBackend.setState({status:"connected",reviews:{}});
 vi.spyOn(api,"request").mockResolvedValue({workflow,registry_review:review} as never);
 render(<WorkflowEditor />);await waitFor(()=>expect(useBackend.getState().reviews[workflow.workflow_id]).toEqual(review));
 expect(useMesh.getState().workflows[0]?.canonical?.workflow_id).toBe(workflow.workflow_id);
});
