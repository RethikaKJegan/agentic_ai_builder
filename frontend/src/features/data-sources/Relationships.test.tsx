import {cleanup, fireEvent, render, screen, waitFor} from "@testing-library/react";
import {afterEach, expect, it, vi} from "vitest";
import {api} from "@/api/client";
import {type RelationshipView} from "@/api/data-relationships";
import Relationships from "./Relationships";

const fixture = (): RelationshipView => ({stale:false,build_status:"ready",last_error:null,graph:{revision:1,built_at:"2026-10-18T00:00:00Z",sources:[{connection_id:"pg",revision:1,generation:1},{connection_id:"mongo",revision:1,generation:1}],warnings:[],nodes:[
  {node_id:"pg",kind:"connection",label:"Supabase",connection_id:"pg",parent_id:null,types:[],discovery_method:"declared",description:""},
  {node_id:"mongo",kind:"connection",label:"Atlas",connection_id:"mongo",parent_id:null,types:[],discovery_method:"declared",description:""},
  {node_id:"orders",kind:"dataset",label:"northwind.orders",connection_id:"pg",parent_id:"pg",types:[],discovery_method:"declared",description:""},
  {node_id:"customers",kind:"dataset",label:"customers",connection_id:"mongo",parent_id:"mongo",types:[],discovery_method:"sampled",description:""},
  {node_id:"of",kind:"field",label:"customerID",connection_id:"pg",parent_id:"orders",types:["text"],discovery_method:"declared",description:""},
  {node_id:"cf",kind:"field",label:"customerID",connection_id:"mongo",parent_id:"customers",types:["string"],discovery_method:"sampled",description:""},
],relationships:[{relationship_id:"r",kind:"suggested",source_dataset_id:"orders",target_dataset_id:"customers",field_pairs:[{source_field_id:"of",target_field_id:"cf"}],evidence:["Matching identifier and compatible scalar types. Values unverified."],evidence_hash:"hash",status:"proposed",reviewed_at:null}]}});
afterEach(()=>{cleanup();vi.restoreAllMocks();});
it("reviews a proposal with the displayed revision and shows evidence", async()=>{
  const data=fixture();const saved=fixture();saved.graph!.revision=2;saved.graph!.relationships[0]!.status="accepted";
  const call=vi.spyOn(api,"relationships").mockResolvedValueOnce(data).mockResolvedValue(saved);
  render(<Relationships canManage/>);
  expect(await screen.findByText("proposed", {selector:"span"})).toBeVisible();
  fireEvent.click(screen.getByText("Evidence and limitations"));expect(screen.getByText(/Values unverified/)).toBeVisible();
  fireEvent.click(screen.getByRole("button",{name:"Accept"}));
  await waitFor(()=>expect(call).toHaveBeenCalledWith("review","r",{revision:1,status:"accepted"}));
  expect(await screen.findByText("accepted", {selector:"span"})).toBeVisible();
});
it("disables edits for stale metadata and readers",async()=>{
  const data=fixture();data.stale=true;vi.spyOn(api,"relationships").mockResolvedValue(data);
  const {rerender}=render(<Relationships canManage/>);
  expect(await screen.findByRole("button",{name:"Accept"})).toBeDisabled();
  expect(screen.getByText(/This graph is historical/)).toBeVisible();
  rerender(<Relationships canManage={false}/>);expect(screen.getByRole("button",{name:"Build relationships"})).toBeDisabled();
});
it("saves manual descriptions and navigates to fields",async()=>{
  const call=vi.spyOn(api,"relationships").mockResolvedValue(fixture());render(<Relationships canManage/>);
  await screen.findByText("proposed", {selector:"span"});fireEvent.change(screen.getByLabelText("Explore dataset"),{target:{value:"orders"}});
  fireEvent.change(screen.getByLabelText("Business description"),{target:{value:"Customer sales orders"}});
  fireEvent.click(screen.getByRole("button",{name:"Save description"}));
  await waitFor(()=>expect(call).toHaveBeenCalledWith("annotation","orders",{revision:1,description:"Customer sales orders"}));
  fireEvent.click(screen.getByRole("button",{name:"customerID · text"}));expect(screen.getByRole("heading",{name:"customerID"})).toBeVisible();
});
it("shows empty catalog and build failure honestly",async()=>{
  vi.spyOn(api,"relationships").mockResolvedValue({graph:null,stale:false,build_status:"failed",last_error:"Worker unavailable"});render(<Relationships canManage/>);
  expect(await screen.findByText("Worker unavailable")).toBeVisible();expect(screen.getByText(/Build relationships from your successful/)).toBeVisible();
});
it("shows mapped columns, zooms, fits and selects a column from the map",async()=>{
  vi.spyOn(api,"relationships").mockResolvedValue(fixture());render(<Relationships canManage/>);
  const map=await screen.findByRole("img",{name:"Dataset relationship map"});
  expect(screen.getByRole("button",{name:"Inspect northwind.orders.customerID"})).toBeVisible();
  expect(map).toHaveTextContent("matches name/type (unverified) · proposed");
  const fitted=map.getAttribute("viewBox");
  fireEvent.click(screen.getByRole("button",{name:"Zoom in"}));expect(map.getAttribute("viewBox")).not.toBe(fitted);
  fireEvent.click(screen.getByRole("button",{name:"Fit all"}));expect(map.getAttribute("viewBox")).toBe(fitted);
  fireEvent.click(screen.getByRole("button",{name:"Zoom out"}));expect(map.getAttribute("viewBox")).not.toBe(fitted);
  fireEvent.click(screen.getByRole("button",{name:"Inspect northwind.orders.customerID"}));expect(screen.getByRole("heading",{name:"customerID"})).toBeVisible();
});
it("hides rejected map links while retaining declared field references",async()=>{
  const data=fixture();data.graph!.relationships[0]!.status="rejected";
  data.graph!.relationships.push({...data.graph!.relationships[0]!,relationship_id:"declared",kind:"declared",status:"declared"});
  vi.spyOn(api,"relationships").mockResolvedValue(data);render(<Relationships canManage/>);
  const map=await screen.findByRole("img",{name:"Dataset relationship map"});
  expect(map).toHaveTextContent("references · declared");expect(map).not.toHaveTextContent("rejected");
  expect(map.querySelectorAll("path[marker-end]")).toHaveLength(1);
});
