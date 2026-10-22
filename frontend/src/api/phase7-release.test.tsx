import { readFileSync } from "node:fs";
import path from "node:path";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { fromCanonical } from "./mapping";
import { CanonicalWorkflowSchema } from "./contracts.generated";
import { ExecutionView } from "@/features/builder/ExecutionView";
import type { WorkflowTrace } from "@/features/builder/useWorkflowTrace";
vi.mock("@/features/builder/ProcurementProjectCommunication",()=>({ProcurementProjectCommunication:()=> <section aria-label="Project communication">Project history</section>}));
afterEach(cleanup);
function setup(){
 const document=JSON.parse(readFileSync(path.resolve(process.cwd(),"e2e/fixtures/multitask-delegation.json"),"utf8")).workflow;
 document.metadata={...document.metadata,procurement_plan:{project_id:"phase7_project"}};
 const workflow=fromCanonical(CanonicalWorkflowSchema.parse(document)).workflow;
 const trace:WorkflowTrace={available:true,runs:[],runId:"",run:null,revision:null,events:[],runState:{},activeEdges:new Set(),error:null,loading:false,selectRun:()=>{},retry:()=>{},hasMoreRuns:false,loadMoreRuns:()=>{},hasMoreEvents:false,loadMoreEvents:()=>{}};
 return {workflow,trace};
}
it("keeps whole-project communication reachable without substituting a draft execution graph",()=>{
 const {workflow,trace}=setup();const view=render(<ExecutionView workflow={workflow} trace={trace} onDesign={()=>{}}/>);
 expect(screen.getByRole("region",{name:"Project communication"})).toBeVisible();
 fireEvent.click(screen.getByRole("button",{name:"Inspect parent run"}));
 expect(screen.getByRole("region",{name:"Recorded execution"})).toBeVisible();
 expect(screen.getByText(/No persisted runs for this workflow/)).toBeVisible();
 expect(view.container.querySelector('.react-flow')).toBeNull();
});
it("opens the run first after an editor submission while preserving the project view",()=>{
 const {workflow,trace}=setup();render(<ExecutionView workflow={workflow} trace={trace} preferRun onDesign={()=>{}}/>);
 expect(screen.getByRole("region",{name:"Recorded execution"})).toBeVisible();
 fireEvent.click(screen.getByRole("button",{name:"Entire project"}));
 expect(screen.getByRole("region",{name:"Project communication"})).toBeVisible();
});
