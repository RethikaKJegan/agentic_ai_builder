import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import type { KnowledgePreview } from "@/api/knowledge-graph";
import { KnowledgeSourcePreview } from "./KnowledgeSourcePreview";
const view:KnowledgePreview={version:1,revision:"r1",indexed_at:"2026-10-18T08:00:00Z",coverage:{connections:2,datasets:154,matched_datasets:2,candidate_limit:12,source_limit:4,metadata_only:true},query_terms:["order"],requires_selection:false,graph_stale:false,source_ids:["orders","customers"],candidates:[{dataset_id:"orders",connection_id:"pg",label:"Supabase / orders",engine:"postgresql",score:15,selected:true,reasons:["dataset name matches order"],fields:["orderID","customerID"],operations:["query"]},{dataset_id:"customers",connection_id:"mongo",label:"Atlas / customers",engine:"mongodb",score:10,selected:true,reasons:["confirmed concept Customer"],fields:["customerID"],operations:["query"]}],relationships:[{relationship_id:"r",source_dataset_id:"orders",target_dataset_id:"customers",status:"accepted",field_pairs:[{source_field_id:"orders_customerID",target_field_id:"customers_customerID"}]}],warnings:[],tools:[{tool_id:"database_read_query",capability:"database.read_query",approval_required:false,description:"Validated read query"}]};
it("shows real shortlist reasons, source paths, field evidence, coverage and configured tools",()=>{
 render(<KnowledgeSourcePreview view={view}/>);
 expect(screen.getByText(/154 datasets/)).toBeVisible();
 expect(screen.getByText(/dataset name matches order/)).toBeVisible();
 expect(screen.getByLabelText("Selected relationship paths")).toHaveTextContent("orders_customerID → customers_customerID");
 fireEvent.click(screen.getByText(/Available configured tools/));
 expect(screen.getByText("database_read_query")).toBeVisible();
 expect(screen.getAllByRole("checkbox").every(e=>(e as HTMLInputElement).disabled)).toBe(true);
});
it("allows an explicit source choice and exposes ambiguity before generation",()=>{
 const choose=vi.fn();render(<KnowledgeSourcePreview view={{...view,requires_selection:true}} selected={["orders"]} onSelect={choose}/>);
 expect(screen.getByRole("status")).toHaveTextContent("Choose the intended sources");
 fireEvent.click(screen.getByRole("checkbox",{name:"Atlas / customers"}));
 expect(choose).toHaveBeenCalledWith(["orders","customers"]);
});
it("shows missing data and warnings without fabricating paths",()=>{
 render(<KnowledgeSourcePreview view={{...view,candidates:[],source_ids:[],relationships:[],warnings:["No confirmed relationship"]}}/>);
 expect(screen.getByText(/No database source was selected/)).toBeVisible();
 expect(screen.getByText(/No executable relationship path/)).toBeVisible();
 expect(screen.getByText("No confirmed relationship")).toBeVisible();
});
