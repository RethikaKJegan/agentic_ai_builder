import {fireEvent,render,screen,waitFor} from "@testing-library/react";
import {afterEach,expect,it,vi} from "vitest";
import {api} from "@/api/client";
import {semanticViewSchema} from "@/api/semantic-kg";
import {detailedViewSchema} from "@/api/data-relationships";
import fixture from "../../../e2e/fixtures/semantic-kg.json";
import detailed from "../../../e2e/fixtures/detailed-graph.json";
import {KGSourceReview,KGTechnicalReview} from "./KGSourceReview";
afterEach(()=>vi.restoreAllMocks());
it("confirms a business concept with current structural revision without granting a join",async()=>{
 const view=semanticViewSchema.parse(fixture);const entity=view.entities.find(e=>e.sources.some(s=>s.kind==="dataset"))!;const source=entity.sources.find(s=>s.kind==="dataset")!;
 const call=vi.spyOn(api,"detailedGraph").mockResolvedValue(detailedViewSchema.parse(detailed));
 const changed=vi.fn();render(<KGSourceReview source={source} entityName={entity.label} revision={view.graph_revision} disabled={false} onChanged={changed}/>);
 fireEvent.change(screen.getByLabelText(`Business concept ${source.node_id}`),{target:{value:"Account"}});
 fireEvent.click(screen.getByRole("button",{name:"Confirm concept mapping"}));
 await waitFor(()=>expect(call).toHaveBeenCalledWith(source.node_id,{revision:view.graph_revision,entity_name:"Account",role:"represents",status:"confirmed"}));expect(changed).toHaveBeenCalled();
});
it("technical join review is explicit and independently versioned",async()=>{
 const view=semanticViewSchema.parse(fixture);const edge=view.relationships.find(e=>e.technical_status==="proposed")!;
 const call=vi.spyOn(api,"relationships").mockResolvedValue({graph:null,stale:false,build_status:"ready",last_error:null});
 render(<KGTechnicalReview edge={edge} revision={view.graph_revision} disabled={false} onChanged={()=>{}}/>);
 fireEvent.click(screen.getByRole("button",{name:"Accept technical link"}));
 await waitFor(()=>expect(call).toHaveBeenCalledWith("review",edge.technical_relationship_id,{revision:view.graph_revision,status:"accepted"}));
});
