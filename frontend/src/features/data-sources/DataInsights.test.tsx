import {render,screen,fireEvent,waitFor} from "@testing-library/react";
import {afterEach,expect,it,vi} from "vitest";
import {api} from "@/api/client";
import type {DatabaseConnection,DatabaseMetadata} from "@/api/data-sources";
import {semanticViewSchema} from "@/api/semantic-kg";
import fixture from "../../../e2e/fixtures/semantic-kg.json";
import DataInsights from "./DataInsights";
const connection:DatabaseConnection={connection_id:"pg",name:"Supabase",engine:"postgresql",host:"test",database:"demo",schemas:["public"],description:"",mode:"direct",connection_status:"connected",profiling_status:"ready",generation:1,metadata_revision:1,created_at:"2026-10-18T00:00:00Z",updated_at:"2026-10-18T00:00:00Z",last_verified_at:null,last_profiled_at:null,last_error_code:null,last_error_message:null};
const metadata:DatabaseMetadata={connection,snapshot:{connection_id:"pg",engine:"postgresql",revision:1,discovered_at:connection.created_at,datasets:[{dataset_id:"pg_orders",name:"orders",database:"demo",schema:"public",kind:"table",fields:[{field_id:"id",name:"id",types:["integer"],discovery_method:"declared"}],indexes:[],constraints:[],sample_count:0,discovery_method:"declared"}],warnings:[],coverage:"declared",limits:{},changes:{added:[],removed:[],changed:[]}}};
afterEach(()=>vi.restoreAllMocks());
it("shows metadata counts and reloads only when revisions change or refresh is requested",async()=>{
 const read=vi.spyOn(api,"databaseMetadata").mockResolvedValue(metadata);vi.spyOn(api,"knowledgeGraph").mockResolvedValue(semanticViewSchema.parse(fixture));
 const {rerender}=render(<DataInsights connections={[connection]}/>);
 await waitFor(()=>expect(screen.getByLabelText("Discovered fields")).toHaveTextContent("1"));
 expect(screen.getByText("Metadata overview · No business-row analysis")).toBeVisible();
 rerender(<DataInsights connections={[{...connection}]}/>);expect(read).toHaveBeenCalledTimes(1);
 rerender(<DataInsights connections={[{...connection,metadata_revision:2}]}/>);await waitFor(()=>expect(read).toHaveBeenCalledTimes(2));
 await waitFor(()=>expect(screen.getByRole("button",{name:"Refresh insights"})).toBeEnabled());
 fireEvent.click(screen.getByRole("button",{name:"Refresh insights"}));await waitFor(()=>expect(read).toHaveBeenCalledTimes(3));
});
it("shows explicit unavailable and empty states without fabricated metrics",async()=>{
 vi.spyOn(api,"databaseMetadata").mockRejectedValue(new Error("unavailable"));vi.spyOn(api,"knowledgeGraph").mockRejectedValue(new Error("unavailable"));
 render(<DataInsights connections={[connection]}/>);
 expect(await screen.findByText("Your data story starts here")).toBeVisible();
 expect(screen.getByText("Metadata unavailable for Supabase.")).toBeVisible();
 expect(screen.getByLabelText("Discovered fields")).toHaveTextContent("0");
 expect(screen.getByLabelText("Semantic Intelligence relationships")).toHaveTextContent("—");
});
