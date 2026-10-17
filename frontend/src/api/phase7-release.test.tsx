import { readFileSync } from "node:fs";
import path from "node:path";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { fromCanonical } from "./mapping";
import { CanonicalWorkflowSchema } from "./contracts.generated";
import { ExecutionView } from "@/features/builder/ExecutionView";
import type { WorkflowTrace } from "@/features/builder/useWorkflowTrace";
afterEach(cleanup);
it("keeps whole-project communication reachable without substituting a draft execution graph",()=>{
 const document=JSON.parse(readFileSync(path.resolve(process.cwd(),"e2e/fixtures/multitask-delegation.json"),"utf8")).workflow;
 document.metadata={...document.metadata,procurement_plan:{project_id:"phase7_project"}};
 const workflow=fromCanonical(CanonicalWorkflowSchema.parse(document)).workflow;
 const trace:WorkflowTrace={available:true,runs:[],runId:"",run:null,revision:null,events:[],runState:{},activeEdges:new Set(),error:null,loading:false,selectRun:()=>{},retry:()=>{},hasMoreRuns:false,loadMoreRuns:()=>{},hasMoreEvents:false,loadMoreEvents:()=>{}};
 const view=render(<ExecutionView workflow={workflow} trace={trace} onDesign={()=>{}} />);
 expect(screen.getByRole("button",{name:"Agent communication"})).toBeVisible();
 expect(screen.getByText(/No persisted runs for this workflow/)).toBeVisible();
 expect(view.container.querySelector('.react-flow')).toBeNull();
});
