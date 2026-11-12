import {describe,it,expect,vi} from 'vitest';
import {subwayDisplay,subwayDisplayJson,compactDemoText} from './subway-presentation';
import {loadWorkflowKnowledge} from './load-workflow-knowledge';
import {businessOntologySchema} from '@/api/business-ontology';
import {knowledgeFixture} from '@/test/fixtures/knowledge-map';
const banner='MODELED SUBWAY DEMONSTRATION — generated records and illustrative policies; not actual Subway operations or official company policy.';
describe('Subway presentation and pinned knowledge',()=>{
 it('compacts old reports and traces without changing canonical data or exact approval payloads',()=>{
  const raw={summary:banner,body:banner,tabs:[{rows:[[1,5900,banner],[2,4012,'query_123']]}],trace:{label:banner},resolved_payload:{body:banner}};
  const before=structuredClone(raw);const shown=subwayDisplay(raw,'client-subway');
  expect(shown.summary).toBe('');expect(shown.trace.label).toBe('');expect(shown.tabs[0]!.rows[0]).toEqual([1,5900,'']);
  expect(shown.resolved_payload).toBe(raw.resolved_payload);expect(raw).toEqual(before);
  expect(subwayDisplay(raw,'client-simpsons')).toBe(raw);
 });
 it('accepts a registered revision-zero ontology and rejects negative revisions',()=>{
  const {ontology}=knowledgeFixture('client-subway');ontology.versions[0]!.revision=0;
  expect(businessOntologySchema.parse(ontology).versions[0]!.revision).toBe(0);
  ontology.versions[0]!.revision=-1;expect(businessOntologySchema.safeParse(ontology).success).toBe(false);
 });
 it('loads the exact authorized pin when workspace overview is unavailable',async()=>{
  const {snapshot}=knowledgeFixture('client-subway');const source={businessOntology:vi.fn().mockRejectedValue(new Error('list unavailable')),knowledgeSnapshot:vi.fn().mockResolvedValue(snapshot)};
  expect((await loadWorkflowKnowledge(source,snapshot.version_id)).snapshot).toBe(snapshot);
  expect(source.knowledgeSnapshot).toHaveBeenCalledExactlyOnceWith(snapshot.version_id);
 });
 it('never silently replaces an inaccessible or mismatched saved pin',async()=>{
  const {snapshot,ontology}=knowledgeFixture();const source={businessOntology:vi.fn().mockResolvedValue(ontology),knowledgeSnapshot:vi.fn().mockRejectedValue(new Error('403'))};
  await expect(loadWorkflowKnowledge(source,'missing',true)).rejects.toThrow('403');expect(source.knowledgeSnapshot).toHaveBeenCalledTimes(1);
  source.knowledgeSnapshot.mockResolvedValue(snapshot);await expect(loadWorkflowKnowledge(source,'other',true)).rejects.toThrow('Snapshot reference mismatch');
 });
});

it('cleans supplier, node and relationship names while retaining currency notes and evidence gaps',()=>{
 const raw={title:'Demo data · Purchase order report',supplier:'Demo Supplier 2',label:'Demo finance.purchaseorders vendor',body:'Limitations: This is Demo data. Currency conversion was not applied, so amounts must not be combined across currency groups. The result provides descriptive measures only and does not establish policy or operational outcomes.',missing:'Missing approval evidence.',amount:5900,currency:1,id:'subway-demonstration-v1'};
 const saved=structuredClone(raw);const shown=subwayDisplay(raw,'client-subway');
 expect(shown.title).toBe('Purchase order report');expect(shown.supplier).toBe('Supplier 2');expect(shown.label).toBe('finance.purchaseorders vendor');
 expect(shown.body).toBe('Notes: Currency conversion was not applied, so amounts must not be combined across currency groups.');
 expect(shown.missing).toBe(raw.missing);expect(shown.amount).toBe(5900);expect(shown.currency).toBe(1);expect(shown.id).toBe(raw.id);expect(raw).toEqual(saved);
 expect(subwayDisplay(raw,'client-simpsons')).toBe(raw);
});
it('formats expanded technical details without changing IDs or payloads used for execution',()=>{
 const raw={classification:'modeled_demonstration',demo_context:{dataset_id:'subway-demonstration-v1'},source_limitations:['This is Demo data.','Missing invoice currency.'],resolved_payload:{body:'Demo data report',to:'person@example.test'}};
 const saved=structuredClone(raw);const text=subwayDisplayJson(raw,'client-subway')!;
 expect(text).not.toMatch(/demo|limitation/i);expect(text).toContain('Missing invoice currency.');expect(raw).toEqual(saved);
 expect(subwayDisplay(raw,'client-subway').resolved_payload).toBe(raw.resolved_payload);
});
it('retains sentence boundaries and figures when removing a legacy disclaimer',()=>{
 expect(compactDemoText('Demo data report: 8 orders.\n\nCurrency 1: 5900. Currency 2: 4012.')).toBe('report: 8 orders.\n\nCurrency 1: 5900. Currency 2: 4012.');
});
