import { render,screen,fireEvent,waitFor,cleanup } from "@testing-library/react";
import { afterEach,beforeEach,it,expect,vi } from "vitest";
import { RenameWorkflowDialog } from "./RenameWorkflowDialog";
import { useBackend } from "@/api/state";
import { useMesh } from "@/domain/store";
import { api,type Session } from "@/api/client";
import type { Workflow } from "@/domain/types";
import { readFileSync } from "node:fs";
import { fromCanonical } from "@/api/mapping";
const workflow=fromCanonical(JSON.parse(readFileSync("../shared/contracts/examples/workflows/support-triage.json","utf8"))).workflow;
beforeEach(()=>{
 useMesh.setState({workflows:[workflow]});
 useBackend.setState({session:{auth:{decision:"allow",permissions:["workflow.edit"]}} as Session});
 vi.spyOn(useBackend.getState(),"refreshOverview").mockResolvedValue();
});
afterEach(()=>{cleanup();vi.restoreAllMocks();});
it("renames the selected server workflow without changing its revision",async()=>{
 const close=vi.fn(),save=vi.spyOn(api,"renameWorkflow").mockResolvedValue({workflow_id:workflow.id,name:"Purchasing"});
 render(<RenameWorkflowDialog workflow={workflow} onClose={close}/>);
 fireEvent.change(screen.getByLabelText("Workflow name"),{target:{value:"Purchasing"}});
 fireEvent.click(screen.getByRole("button",{name:"Save name"}));
 await waitFor(()=>expect(close).toHaveBeenCalledOnce());
 expect(save).toHaveBeenCalledExactlyOnceWith(workflow.id,"Purchasing",workflow.name);
 expect(useMesh.getState().workflows[0]?.name).toBe("Purchasing");
 expect(useMesh.getState().workflows[0]?.serverVersion).toBe(1);
});
it("blocks empty names and supports cancellation without saving",()=>{
 const close=vi.fn(),save=vi.spyOn(api,"renameWorkflow");
 render(<RenameWorkflowDialog workflow={workflow} onClose={close}/>);
 fireEvent.change(screen.getByLabelText("Workflow name"),{target:{value:"  "}});
 expect(screen.getByRole("button",{name:"Save name"})).toBeDisabled();
 fireEvent.click(screen.getByRole("button",{name:"Cancel"}));
 expect(close).toHaveBeenCalledOnce();expect(save).not.toHaveBeenCalled();
});
it("renames local drafts without calling the server",async()=>{
 const local:Workflow={...workflow};delete local.serverVersion;const save=vi.spyOn(api,"renameWorkflow");
 render(<RenameWorkflowDialog workflow={local} onClose={vi.fn()}/>);
 fireEvent.change(screen.getByLabelText("Workflow name"),{target:{value:"Local title"}});
 fireEvent.click(screen.getByRole("button",{name:"Save name"}));
 await waitFor(()=>expect(useMesh.getState().workflows[0]?.name).toBe("Local title"));
 expect(save).not.toHaveBeenCalled();
});
