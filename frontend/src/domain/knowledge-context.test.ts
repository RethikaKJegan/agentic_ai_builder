import {describe,it,expect} from 'vitest';
import {knowledgeFixture} from '@/test/fixtures/knowledge-map';
import {workflowKnowledge} from './workflow-knowledge';
import {knowledgeContext} from './knowledge-context';

describe('Direct ontology context',()=>{
 it.each(['simpsons','subway','future-tenant'])('shows one-hop incoming and outgoing context for %s without changing usage',tenant=>{
  const f=knowledgeFixture(tenant);const model=workflowKnowledge(f.snapshot,f.doc,f.view,true);
  const anchor=model.nodes[0]!;const direct=model.nodes[1]!;
  model.nodes.push({...direct,id:'incoming'}, {...direct,id:'two_hops'}, {...direct,id:'unrelated'});
  model.edges.push({...model.edges[0]!,id:'incoming_edge',source:'incoming',target:anchor.id}, {...model.edges[0]!,id:'chain',source:direct.id,target:'two_hops'});
  const before=structuredClone(model);
  const overlay=knowledgeContext(model,'all');
  expect([...overlay.executed]).toEqual([anchor.id]);
  expect([...overlay.neighbours.keys()].sort()).toEqual([direct.id,'incoming'].sort());
  expect(overlay.neighbours.get(direct.id)).toEqual(new Set([anchor.id]));
  expect(model).toEqual(before);
 });
 it('does not spread highlights from planned-only concepts or other steps',()=>{
  const f=knowledgeFixture();const model=workflowKnowledge(f.snapshot,f.doc,f.view,true);
  expect(knowledgeContext(model,'other-step').neighbours.size).toBe(0);
  model.nodes[0]!.usage=model.nodes[0]!.usage.filter(u=>u.state==='planned');
  expect(knowledgeContext(model,'all').neighbours.size).toBe(0);
 });
 it('keeps two executed neighbours executed and ignores missing endpoints',()=>{
  const f=knowledgeFixture();const model=workflowKnowledge(f.snapshot,f.doc,f.view,true);
  model.nodes[1]!.usage=structuredClone(model.nodes[0]!.usage);
  model.edges.push({...model.edges[0]!,id:'missing',target:'missing'});
  const overlay=knowledgeContext(model,'all');expect(overlay.executed.size).toBe(2);expect(overlay.neighbours.size).toBe(0);
 });
});
