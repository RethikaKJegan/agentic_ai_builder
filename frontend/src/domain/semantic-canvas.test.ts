import { expect, it } from "vitest";
import { semanticCanvas, type SemanticCanvas } from "./semantic-canvas";
import type { SemanticView } from "@/api/semantic-kg";
import fixture from "../../e2e/fixtures/semantic-kg.json";
const view = () => structuredClone(fixture) as SemanticView;
function connected(graph: SemanticCanvas) {
  const adjacent = new Map(graph.entities.map(n => [n.entity_id, new Set<string>()]));
  for (const edge of graph.relationships) if (edge.status !== "rejected") {
    expect(adjacent.has(edge.source_entity_id)).toBe(true); expect(adjacent.has(edge.target_entity_id)).toBe(true);
    adjacent.get(edge.source_entity_id)!.add(edge.target_entity_id); adjacent.get(edge.target_entity_id)!.add(edge.source_entity_id);
  }
  const reached = new Set<string>(), stack = [graph.entities[0]!.entity_id];
  while (stack.length) { const id = stack.pop()!; if (reached.has(id)) continue; reached.add(id); stack.push(...adjacent.get(id)!); }
  expect(reached.size).toBe(graph.entities.length);
  expect([...adjacent.values()].every(neighbours => neighbours.size > 0)).toBe(true);
}
function references() {
  const v=view();v.entities=[];v.datasets=[];v.relationships=[];
  for (const [name,column] of [["handling_protocols","protocol_id"],["supplier_sites","site_id"]]) {
    const id=name!, field=`${name}.${column}`;
    v.datasets.push({dataset_id:id,label:id,connection_id:"pg",fields:[{field_id:field,name:column!,types:["integer"]}]});
    const constraints: Record<string,unknown>[] = [{kind:"primary_key",columns:[column]}];
    if(name==="supplier_sites") {
      constraints.push({kind:"foreign_key",columns:["protocol_id"],referenced_schema:"demo",referenced_table:"handling_protocols",referenced_columns:["protocol_id"]});
      v.datasets[1]!.fields.push({field_id:"supplier_sites.protocol_id",name:"protocol_id",types:["integer"]});
    }
    v.entities.push({entity_id:id,label:name==="handling_protocols"?"Handling Protocol":"Supplier Site",sources:[{node_id:id,connection_id:"pg",label:`Postgres / demo / ${name}`,kind:"dataset",role:"represents",status:"suggested",types:[],metadata:{schema:"demo",name,constraints},description:""}]});
  }
  v.entities.push({entity_id:"protocol",label:"Protocol",sources:["handling_protocols.protocol_id","supplier_sites.protocol_id"].map(node_id=>({node_id,connection_id:"pg",label:`Postgres / demo / ${node_id}`,kind:"field",role:"reference",status:"suggested" as const,types:["integer"],metadata:{name:"protocol_id"},description:""}))});
  return v;
}
it("connects unrelated datasets and field concepts using source evidence without changing API data",()=>{
  const input=view(),before=structuredClone(input),graph=semanticCanvas(input);
  connected(graph);expect(input).toEqual(before);
  expect(graph.relationships.filter(e=>e.kind==="business").every(e=>e.original && input.relationships.includes(e.original))).toBe(true);
  expect(graph.relationships.filter(e=>e.kind!=="business").every(e=>!e.original && e.evidence.length>0)).toBe(true);
});
it("resolves identifier concepts from primary/foreign keys, keeping all source mappings",()=>{
  const graph=semanticCanvas(references());
  expect(graph.entities.some(e=>e.entity_id==="protocol")).toBe(false);
  expect(graph.entities.find(e=>e.entity_id==="handling_protocols")!.sources).toHaveLength(3);
  expect(graph.resolvedIdentifiers).toBe(1);connected(graph);
});
it("does not merge a similar field name without a declared key",()=>{
  const v=references();v.entities[1]!.sources[0]!.metadata["constraints"]=[];
  const graph=semanticCanvas(v);expect(graph.entities.some(e=>e.entity_id==="protocol")).toBe(true);
  expect(graph.relationships.some(e=>e.kind==="ownership"&&e.target_entity_id==="protocol")).toBe(true);connected(graph);
});
it("does not choose one target for a concept with conflicting key evidence",()=>{
  const v=references();v.entities[1]!.sources[0]!.metadata["constraints"]=[{kind:"primary_key",columns:["protocol_id"]}];
  const graph=semanticCanvas(v);expect(graph.entities.some(e=>e.entity_id==="protocol")).toBe(true);connected(graph);
});
it("preserves source isolation under connection filters",()=>{
  const graph=semanticCanvas(view(),{connection:"mongo"});connected(graph);
  expect(graph.entities.flatMap(e=>e.sources).every(s=>s.connection_id==="mongo")).toBe(true);
  expect(graph.relationships.filter(e=>e.kind==="business")).toHaveLength(0);
});
it("search/status filtering still connects visible concepts, and no results stay empty",()=>{
  connected(semanticCanvas(view(),{search:"Customer",status:"confirmed"}));
  expect(semanticCanvas(view(),{search:"no-such-entity"}).entities).toHaveLength(0);
});
it("reverses only the exact existing supplier predicate, retaining original review evidence",()=>{
  const v=view(),edge=v.relationships[0]!;edge.predicate="is supplied by";
  const graph=semanticCanvas(v);const link=graph.relationships.find(e=>e.relationship_id===edge.relationship_id)!;
  expect(link.predicate).toBe("supplies");expect(link.source_entity_id).toBe(edge.target_entity_id);expect(link.target_entity_id).toBe(edge.source_entity_id);
  expect(link.original).toBe(edge);expect(edge.predicate).toBe("is supplied by");
});
it("does not present ambiguous or stale business wording as established meaning",()=>{
  const v=view(),edge=v.relationships[0]!;edge.status="needs_review";edge.predicate="is supplied by";
  const link=semanticCanvas(v).relationships.find(e=>e.relationship_id===edge.relationship_id)!;
  expect(link.predicate).toBe("references");expect(link.source_entity_id).toBe(edge.source_entity_id);
});
