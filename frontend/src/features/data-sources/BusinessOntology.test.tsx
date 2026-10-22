import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import type { SemanticView as OntologyView } from "@/api/semantic-kg";
import fixture from "../../../e2e/fixtures/semantic-kg.json";
import BusinessOntology from "./BusinessOntology";
import AutomaticRefresh from "./AutomaticRefresh";

const view = () => structuredClone(fixture) as OntologyView;
beforeEach(() => {
  vi.spyOn(api, "dataRefresh").mockResolvedValue({ version: 1, items: [] });
});
afterEach(() => vi.restoreAllMocks());

it("shows only essential KG controls and retains graph navigation", async () => {
  vi.spyOn(api, "knowledgeGraph").mockResolvedValue(view());
  render(<BusinessOntology canManage />);
  await screen.findByRole("img", {name:"Semantic Intelligence"});
  for (const name of ["Actual records", "Entity types", "Generate semantic relationships", "Confirm relationship"])
    expect(screen.queryByRole("button", {name})).not.toBeInTheDocument();
  expect(screen.getByLabelText("Semantic Intelligence details")).toHaveTextContent("Inspect");
  fireEvent.click(screen.getByRole("button", {name:"Zoom Semantic Intelligence in"}));
  expect(screen.getByLabelText("Semantic Intelligence zoom")).toHaveTextContent("130%");
  fireEvent.click(screen.getByRole("button", {name:"Fit Semantic Intelligence"}));
  expect(screen.getByLabelText("Semantic Intelligence zoom")).toHaveTextContent("100%");
});

it("scopes physical relationships to one connection and restores combined links", async () => {
  vi.spyOn(api,"knowledgeGraph").mockResolvedValue(view());
  const {container}=render(<BusinessOntology canManage />);
  await screen.findByRole("img",{name:"Semantic Intelligence"});
  const count=()=>container.querySelectorAll('g[aria-label^="Relationship "]').length;
  expect(count()).toBe(4);
  fireEvent.change(screen.getByLabelText("Semantic Intelligence connection"), {target:{value:"pg"}});
  expect(count()).toBe(1);
  fireEvent.change(screen.getByLabelText("Semantic Intelligence connection"), {target:{value:"mongo"}});
  expect(count()).toBe(0);
  fireEvent.change(screen.getByLabelText("Semantic Intelligence connection"), {target:{value:""}});
  expect(count()).toBe(4);
  fireEvent.change(screen.getByLabelText("Semantic relationship status"), {target:{value:"inferred"}});
  expect(count()).toBe(1);
  fireEvent.change(screen.getByLabelText("Search Semantic Intelligence"), {target:{value:"unrelated-payroll"}});
  expect(count()).toBe(0);
  expect(screen.getByText(/No entities match/)).toBeVisible();
});

it("saves per-connection refresh settings and exposes stale-data failure status", async () => {
  const item = {
    connection_id: "pg",
    name: "Supabase",
    enabled: true,
    interval_seconds: 300,
    next_check_at: 1000,
    last_attempt_at: null,
    last_success_at: null,
    last_change_at: null,
    consecutive_failures: 1,
    profiling_status: "failed",
    connection_status: "connected",
    metadata_revision: 2,
    last_error_message: "Connection check failed.",
  };
  const call = vi.mocked(api.dataRefresh).mockResolvedValue({ version: 1, items: [item] });
  render(<AutomaticRefresh canManage />);
  await screen.findByLabelText("Refresh interval seconds");
  fireEvent.change(screen.getByLabelText("Refresh interval seconds"), { target: { value: "60" } });
  fireEvent.click(screen.getByRole("checkbox", { name: "Automatic metadata refresh" }));
  fireEvent.click(screen.getByRole("button", { name: "Save refresh settings" }));
  await waitFor(() =>
    expect(call).toHaveBeenCalledWith("pg", { enabled: false, interval_seconds: 60 }),
  );
  expect(screen.getByText(/Previous successful metadata is retained/)).toBeVisible();
});

it("inspects relationship provenance and clears details excluded by filters", async () => {
  const v=view(); vi.spyOn(api,"knowledgeGraph").mockResolvedValue(v);
  render(<BusinessOntology canManage />);
  const relationship=v.relationships[0]!;
  const names=new Map(v.entities.map(e=>[e.entity_id,e.label]));
  fireEvent.click(await screen.findByRole("button", {name:`Relationship ${names.get(relationship.source_entity_id)} ${relationship.predicate} ${names.get(relationship.target_entity_id)}`}));
  const details=screen.getByLabelText("Semantic Intelligence details");
  expect(details).toHaveTextContent("Evidence trace");
  expect(details).toHaveTextContent("structural_relationship_id");
  expect(details).toHaveTextContent(relationship.relationship_id);
  expect(details).toHaveTextContent("Business: inferred");
  expect(screen.getByRole("button",{name:"Confirm relationship"})).toBeEnabled();
  fireEvent.change(screen.getByLabelText("Semantic Intelligence connection"),{target:{value:"mongo"}});
  expect(details).not.toHaveTextContent("Evidence trace");
  expect(details).toHaveTextContent("Select a node or relationship");
  const node=screen.getByRole("button",{name:"Entity Customer"});
  fireEvent.keyDown(node,{key:"Enter"});
  expect(details).toHaveTextContent("Atlas");
  expect(details).not.toHaveTextContent("Postgres");
});

for (const status of ["ambiguous", "needs_review"] as const) it(`corrects ${status} meaning using the current revision`, async () => {
  const v=view(); const target=v.relationships[1]!;target.status=status;target.predicate=null;
  const updated=structuredClone(v);updated.relationships[1]!.predicate="matches";updated.relationships[1]!.status="confirmed";updated.revision="reviewed";
  const call=vi.spyOn(api,"knowledgeGraph").mockImplementation(async id=>id?updated:v);
  render(<BusinessOntology canManage />);
  fireEvent.click((await screen.findAllByRole("button",{name:/^Relationship .*meaning needs review/}))[0]!);
  fireEvent.change(screen.getByLabelText("Relationship label"),{target:{value:"matches"}});
  fireEvent.click(screen.getByLabelText("Reverse business direction"));
  fireEvent.click(screen.getByRole("button",{name:"Confirm relationship"}));
  await waitFor(()=>expect(call).toHaveBeenCalledWith(target.relationship_id,{revision:v.revision,predicate:"matches",reversed:!target.reversed,status:"confirmed"}));
  expect(await screen.findByText(/Business relationship review saved/)).toBeVisible();
  expect(screen.getByLabelText("Semantic Intelligence details")).toHaveTextContent("Business: confirmed");
});

for (const stale of [false,true]) it(`disables review for ${stale?"stale":"read-only"} graphs`,async()=>{
  vi.spyOn(api,"knowledgeGraph").mockResolvedValue({...view(),stale});
  render(<BusinessOntology canManage={stale}/>);
  fireEvent.click((await screen.findAllByRole("button",{name:/^Relationship /}))[0]!);
  expect(screen.getByRole("button",{name:"Confirm relationship"})).toBeDisabled();
  expect(screen.getByLabelText("Relationship label")).toBeDisabled();
});

it("inspects membership evidence without offering a business-relationship review", async()=>{
  const v=view(), call=vi.spyOn(api,"knowledgeGraph").mockResolvedValue(v);
  render(<BusinessOntology canManage />);
  const links=await screen.findAllByRole("button",{name:/^Source link .*includes source/});
  fireEvent.click(links[0]!);
  const details=screen.getByLabelText("Semantic Intelligence details");
  expect(details).toHaveTextContent("Metadata evidence");
  expect(details).toHaveTextContent("membership");
  expect(screen.queryByRole("button",{name:"Confirm relationship"})).not.toBeInTheDocument();
  expect(call.mock.calls.every(args=>args[0]===undefined)).toBe(true);
});
