import {fireEvent,render,screen,waitFor} from "@testing-library/react";
import {afterEach,beforeEach,expect,it,vi} from "vitest";
import {api} from "@/api/client";
import {semanticViewSchema} from "@/api/semantic-kg";
import fixture from "../../../e2e/fixtures/semantic-kg.json";
import Relationships from "./Relationships";
const view=()=>semanticViewSchema.parse(structuredClone(fixture));
beforeEach(()=>{vi.spyOn(api,"knowledgeGraph").mockResolvedValue(view());vi.spyOn(api,"dataRefresh").mockResolvedValue({version:1,items:[]});});
afterEach(()=>vi.restoreAllMocks());
it("exposes one semantic KG and removes separate schema graph navigation",async()=>{
 render(<Relationships canManage/>);
 expect(await screen.findByRole("img",{name:"Semantic Intelligence"})).toBeVisible();
 expect(screen.queryByRole("button",{name:"Relationship map"})).not.toBeInTheDocument();
 expect(screen.queryByRole("button",{name:"Detailed Semantic Intelligence"})).not.toBeInTheDocument();
 expect(screen.queryByRole("button",{name:"Entity types"})).not.toBeInTheDocument();
 expect(screen.queryByRole("button",{name:"Actual records"})).not.toBeInTheDocument();
});
it("rebuilds structural evidence without invoking semantic confirmation or cloud record reads",async()=>{
 const call=vi.spyOn(api,"relationships").mockResolvedValue({graph:null,stale:false,build_status:"queued",last_error:null});
 const records=vi.spyOn(api,"knowledgeRecords");render(<Relationships canManage/>);
 await screen.findByRole("img",{name:"Semantic Intelligence"});
 fireEvent.click(screen.getByRole("button",{name:"Regenerate Semantic Intelligence"}));
 await waitFor(()=>expect(call).toHaveBeenCalledWith("build"));expect(records).not.toHaveBeenCalled();
});
it("keeps semantic and source edits disabled for viewers",async()=>{
 render(<Relationships canManage={false}/>);
 await screen.findByRole("img",{name:"Semantic Intelligence"});
 expect(screen.queryByRole("button",{name:"Generate semantic relationships"})).not.toBeInTheDocument();
 expect(screen.getByRole("button",{name:"Regenerate Semantic Intelligence"})).toBeDisabled();
});

it("mounts source review only on explicit navigation and retains viewer denial",async()=>{
 const read=vi.spyOn(api,"relationships").mockResolvedValue({graph:null,stale:true,build_status:"ready",last_error:null});
 render(<Relationships canManage={false}/>);
 await screen.findByRole("img",{name:"Semantic Intelligence"});
 expect(read).not.toHaveBeenCalled();
 fireEvent.click(screen.getByText("Review source links and mappings"));
 fireEvent.click(screen.getByRole("button",{name:"Source relationships"}));
 await screen.findByRole("button",{name:"Build relationships"});
 expect(screen.getByRole("button",{name:"Build relationships"})).toBeDisabled();
 expect(read).toHaveBeenCalledWith();
});
