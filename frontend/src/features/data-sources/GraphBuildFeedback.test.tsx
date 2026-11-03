import {act,cleanup,fireEvent,render,screen} from "@testing-library/react";
import {afterEach,expect,it,vi} from "vitest";
import {api} from "@/api/client";
import {semanticViewSchema} from "@/api/semantic-kg";
import fixture from "../../../e2e/fixtures/semantic-kg.json";
import Relationships from "./Relationships";
afterEach(()=>{cleanup();vi.useRealTimers();vi.restoreAllMocks();});
it.each(["ready","failed"] as const)("updates metadata rebuild feedback to %s without changing connection selection",async state=>{
 vi.useFakeTimers();let view=semanticViewSchema.parse(structuredClone(fixture));
 vi.spyOn(api,"knowledgeGraph").mockImplementation(async()=>view);
 vi.spyOn(api,"dataRefresh").mockResolvedValue({version:1,items:[]});
 const rebuild=vi.spyOn(api,"relationships").mockImplementation(async()=>{
  view={...view,build_status:"queued",stale:true};
  return {graph:null,build_status:"queued",stale:true,last_error:null};
 });
 const inference=vi.spyOn(api,"inferKnowledgeGraph");
 render(<Relationships canManage/>);await act(async()=>{});
 fireEvent.change(screen.getByLabelText("Semantic Intelligence connection"),{target:{value:"pg"}});
 fireEvent.click(screen.getByRole("button",{name:"Regenerate Semantic Intelligence"}));await act(async()=>{});
 expect(rebuild).toHaveBeenCalledWith("build");
 expect(screen.getByRole("button",{name:"Updating metadata graph…"})).toBeDisabled();
 view={...view,build_status:state,stale:false,last_error:state==="failed"?"Graph rebuild failed; retry.":null};
 await act(async()=>{await vi.advanceTimersByTimeAsync(2000);});
 expect(screen.getByRole("button",{name:"Regenerate Semantic Intelligence"})).toBeEnabled();
 expect(screen.getByLabelText("Semantic Intelligence connection")).toHaveValue("pg");
 expect(screen.getByRole("img",{name:"Semantic Intelligence"})).toBeVisible();
 expect(inference).not.toHaveBeenCalled();
 if(state==="failed")expect(screen.getByRole("alert")).toHaveTextContent("Graph rebuild failed");
});
