import {fireEvent,render,screen,waitFor} from "@testing-library/react";
import {afterEach,expect,it,vi} from "vitest";
import {api} from "@/api/client";
import {semanticViewSchema,recordGraphSchema} from "@/api/semantic-kg";
import schema from "../../../e2e/fixtures/kg-record-schema.json";
import records from "../../../e2e/fixtures/kg-records.json";
import {KGRecordExplorer} from "./KGRecordExplorer";
afterEach(()=>vi.restoreAllMocks());
it("reads only after explicit identity selection and renders real labels and provenance",async()=>{
 const call=vi.spyOn(api,"knowledgeRecords").mockResolvedValue(recordGraphSchema.parse(records));
 const view=semanticViewSchema.parse(schema);render(<KGRecordExplorer view={view} canRead/>);
 expect(call).not.toHaveBeenCalled();expect(screen.getByRole("button",{name:"Explore actual records"})).toBeDisabled();
 fireEvent.change(screen.getByLabelText("Dataset"),{target:{value:"mongo_categories"}});
 fireEvent.change(screen.getByLabelText("Identity field",{exact:true}),{target:{value:"mongo_categories_categoryID"}});
 fireEvent.change(screen.getByLabelText("Record label field",{exact:true}),{target:{value:"mongo_categories_name"}});
 fireEvent.change(screen.getByLabelText("Identity value"),{target:{value:"1"}});
 fireEvent.click(screen.getByRole("button",{name:"Explore actual records"}));
 await waitFor(()=>expect(call).toHaveBeenCalledWith(expect.objectContaining({revision:view.revision,dataset_id:"mongo_categories",identity_value:1,relationship_id:""})));
 expect(await screen.findByText(/categories: Food/)).toBeVisible();
 expect(screen.getByText("Actual query and source evidence")).toBeVisible();
});
it("does not read for a viewer",async()=>{
 const call=vi.spyOn(api,"knowledgeRecords");render(<KGRecordExplorer view={semanticViewSchema.parse(schema)} canRead={false}/>);
 expect(screen.getByRole("button",{name:"Explore actual records"})).toBeDisabled();expect(call).not.toHaveBeenCalled();
});
