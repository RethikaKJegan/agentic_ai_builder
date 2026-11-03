import {act,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';
import {api} from '@/api/client';
import {businessPolicySchema} from '@/api/business-ontology';
import {policyLibrary,policyDraft,policyComparison} from '@/test/fixtures/business-policy';
import {sourceGraph} from '@/test/fixtures/business-graph';
import BusinessPolicyLibrary from './BusinessPolicyLibrary';
import BusinessPolicyComparisonPanel from './BusinessPolicyComparisonPanel';
afterEach(()=>vi.restoreAllMocks());
it('saves cited clauses explicitly, keeps unknowns null and retries with the same key',async()=>{
 vi.spyOn(api,'businessPolicies').mockResolvedValue(policyLibrary());const save=vi.spyOn(api,'saveBusinessPolicy').mockRejectedValueOnce(new Error('Unknown outcome')).mockResolvedValue(policyDraft());
 render(<BusinessPolicyLibrary canManage onData={()=>{}}/>);fireEvent.click(await screen.findByRole('button',{name:'Create policy draft'}));
 fireEvent.change(screen.getByLabelText('Policy series key'),{target:{value:'fixture-policy'}});fireEvent.change(screen.getByLabelText('Policy draft title'),{target:{value:'Fixture'}});fireEvent.change(screen.getByLabelText('Policy source document'),{target:{value:'policy_source_fixture'}});
 fireEvent.click(screen.getByText('Effective-date basis · Unknown'));expect(screen.getByRole('combobox',{name:'Effective-date basis'})).toBeVisible();
 fireEvent.click(screen.getByText('Source policy version · Unknown'));fireEvent.change(screen.getByLabelText('Source policy version',{exact:true}),{target:{value:'V1'}});fireEvent.change(screen.getByLabelText('Quotation for Source policy version'),{target:{value:'Fixture policy version V1.'}});
 expect(save).not.toHaveBeenCalled();fireEvent.click(screen.getByRole('button',{name:'Save policy draft revision'}));await screen.findByRole('button',{name:'Retry read'});fireEvent.click(screen.getByRole('button',{name:'Save policy draft revision'}));await screen.findByRole('article',{name:'Saved policy draft detail'});
 expect(save).toHaveBeenCalledTimes(2);expect(save.mock.calls[0]?.[0]).toEqual(save.mock.calls[1]?.[0]);expect(save.mock.calls[0]?.[0]).toMatchObject({expected_revision:0,policy:{clauses:{source_version:{value:'V1',quote:'Fixture policy version V1.'},max_hours:{value:null,quote:null}}}});
});
it('views immutable policy evidence and starts a new revision with the selected base revision',async()=>{
 vi.spyOn(api,'businessPolicies').mockResolvedValue(policyLibrary(true));vi.spyOn(api,'businessPolicy').mockResolvedValue(policyDraft());const save=vi.spyOn(api,'saveBusinessPolicy').mockResolvedValue({...policyDraft(),revision:2,policy_id:'p2'});
 render(<BusinessPolicyLibrary canManage onData={()=>{}}/>);fireEvent.change(await screen.findByLabelText('Saved policy revision'),{target:{value:'p1'}});const detail=await screen.findByRole('article',{name:'Saved policy draft detail'});expect(within(detail).getByText(/Authority not verified/)).toBeVisible();
 fireEvent.click(screen.getByRole('button',{name:'Start new policy revision'}));expect(screen.getByLabelText('Policy series key')).toBeDisabled();fireEvent.click(screen.getByRole('button',{name:'Save policy draft revision'}));await waitFor(()=>expect(save).toHaveBeenCalledTimes(1));expect(save.mock.calls[0]?.[0].expected_revision).toBe(1);
});
it('viewers can inspect policy revisions but have no draft or source mutations',async()=>{
 vi.spyOn(api,'businessPolicies').mockResolvedValue(policyLibrary(true));vi.spyOn(api,'businessPolicy').mockResolvedValue(policyDraft());const save=vi.spyOn(api,'saveBusinessPolicy');render(<BusinessPolicyLibrary canManage={false} onData={()=>{}}/>);
 fireEvent.change(await screen.findByLabelText('Saved policy revision'),{target:{value:'p1'}});await screen.findByRole('article',{name:'Saved policy draft detail'});expect(screen.queryByRole('button',{name:'Create policy draft'})).not.toBeInTheDocument();expect(screen.queryByText('Add warranty policy document')).not.toBeInTheDocument();expect(save).not.toHaveBeenCalled();
});
it('requires explicit policy, case and timezone input and clears the result when inputs change',async()=>{
 vi.spyOn(api,'businessPolicies').mockResolvedValue(policyLibrary(true));const compare=vi.spyOn(api,'compareBusinessPolicy').mockResolvedValue(policyComparison());render(<BusinessPolicyComparisonPanel graph={sourceGraph()} onInspect={()=>{}}/>);
 const button=await screen.findByRole('button',{name:'Compare saved policy scope'});expect(button).toBeDisabled();fireEvent.change(screen.getByLabelText('Policy revision to compare'),{target:{value:'p1'}});fireEvent.change(screen.getByLabelText('Complaint for policy comparison'),{target:{value:'node1'}});fireEvent.change(screen.getByLabelText('Assessment date and time'),{target:{value:'2026-06-01T12:00'}});fireEvent.change(screen.getByLabelText('Assessment timezone offset'),{target:{value:'+05:30'}});expect(compare).not.toHaveBeenCalled();fireEvent.click(button);
 expect(await screen.findByText('Requires Review · Eligibility not evaluated')).toBeVisible();expect(compare).toHaveBeenCalledExactlyOnceWith('v2','g1',{policy_id:'p1',ticket_node_id:'node1',invoice_node_id:null,assessment_at:'2026-06-01T12:00:00+05:30'});expect(screen.getByText('effective dates: match')).toBeVisible();fireEvent.change(screen.getByLabelText('Assessment timezone offset'),{target:{value:'Z'}});expect(screen.queryByText(/Eligibility not evaluated/)).not.toBeInTheDocument();expect(compare).toHaveBeenCalledTimes(1);
});
it('does not run a comparison when there are no policy drafts',async()=>{
 vi.spyOn(api,'businessPolicies').mockResolvedValue(policyLibrary());const compare=vi.spyOn(api,'compareBusinessPolicy');render(<BusinessPolicyComparisonPanel graph={sourceGraph()} onInspect={()=>{}}/>);expect(await screen.findByText(/No saved warranty interpretations available/)).toBeVisible();expect(screen.getByRole('button',{name:'Compare saved policy scope'})).toBeDisabled();expect(compare).not.toHaveBeenCalled();
});
it('discards late comparison responses when the graph version changes',async()=>{
 vi.spyOn(api,'businessPolicies').mockResolvedValue(policyLibrary(true));let finish:(value:ReturnType<typeof policyComparison>)=>void=()=>{};vi.spyOn(api,'compareBusinessPolicy').mockImplementation(()=>new Promise(resolve=>{finish=resolve;}));const view=render(<BusinessPolicyComparisonPanel graph={sourceGraph()} onInspect={()=>{}}/>);
 await screen.findByRole('button',{name:'Compare saved policy scope'});for(const [label,value] of [['Policy revision to compare','p1'],['Complaint for policy comparison','node1'],['Assessment date and time','2026-06-01T12:00'],['Assessment timezone offset','Z']])fireEvent.change(screen.getByLabelText(label!),{target:{value}});fireEvent.click(screen.getByRole('button',{name:'Compare saved policy scope'}));view.rerender(<BusinessPolicyComparisonPanel graph={{...sourceGraph('v3'),graph_id:'g2'}} onInspect={()=>{}}/>);await act(async()=>finish(policyComparison()));expect(screen.queryByText(/Eligibility not evaluated/)).not.toBeInTheDocument();
});

it('preserves immutable source metadata in policy exports',()=>{
 const original=policyDraft();const parsed=businessPolicySchema.parse({...original,source:{...original.source,created_at:'2026-11-01T12:00:00Z'}});
 expect(parsed.source['created_at']).toBe('2026-11-01T12:00:00Z');
});

it('keeps revision selection stable during slow reads and ignores stale responses',async()=>{
 const one=policyDraft(),two={...policyDraft(),policy_id:'p2',revision:2,title:'New revision'};const list=policyLibrary(true);list.items.push({...list.items[0]!,policy_id:'p2',revision:2,title:two.title});
 vi.spyOn(api,'businessPolicies').mockResolvedValue(list);let first:(v:typeof one)=>void=()=>{},second:(v:typeof two)=>void=()=>{};
 vi.spyOn(api,'businessPolicy').mockImplementation(id=>new Promise(resolve=>{if(id==='p1')first=resolve;else second=resolve;}));
 render(<BusinessPolicyLibrary canManage onData={()=>{}}/>);const select=await screen.findByLabelText('Saved policy revision');await waitFor(()=>expect(select).toBeEnabled());
 fireEvent.change(select,{target:{value:'p1'}});expect(select).toHaveValue('p1');expect(screen.getByText('Loading selected warranty revision…')).toBeVisible();
 fireEvent.change(select,{target:{value:'p2'}});expect(select).toHaveValue('p2');await act(async()=>second(two));expect(await screen.findByText('New revision · Revision 2')).toBeVisible();
 await act(async()=>first(one));expect(select).toHaveValue('p2');expect(screen.queryByText('Fixture policy draft · Revision 1')).not.toBeInTheDocument();
 fireEvent.change(select,{target:{value:''}});expect(screen.queryByRole('article',{name:'Saved policy draft detail'})).not.toBeInTheDocument();
});

it('disables an empty revision selector and imports source-qualified existing knowledge',async()=>{
 const {implementationLibrary,implementationDraft}=await import('@/test/fixtures/warranty-implementation');
 vi.spyOn(api,'businessPolicies').mockResolvedValue({...policyLibrary(),sources:[]});const imported=vi.spyOn(api,'importWarrantyImplementation').mockResolvedValue(implementationLibrary());vi.spyOn(api,'businessPolicy').mockResolvedValue(implementationDraft(0));const changed=vi.fn();
 render(<BusinessPolicyLibrary canManage onData={()=>{}} onChanged={changed}/>);expect(await screen.findByLabelText('Saved policy revision')).toBeDisabled();
 fireEvent.click(screen.getByRole('button',{name:'Import existing warranty logic'}));const knowledge=await screen.findByRole('region',{name:'Existing warranty logic'});expect(imported).toHaveBeenCalledTimes(1);expect(changed).toHaveBeenCalledTimes(1);expect(within(knowledge).getByText('Tractors and Farm Equipments Ltd')).toBeVisible();expect(screen.getByLabelText('Saved policy revision')).toBeEnabled();
 fireEvent.click(within(knowledge).getAllByRole('button',{name:'Read source and limits'})[0]!);expect(await screen.findByText(/Implementation-derived draft · Describes supplied code/)).toBeVisible();
});

it('refreshes case policy choices after the library changes without resetting the graph',async()=>{
 const {implementationLibrary}=await import('@/test/fixtures/warranty-implementation');vi.spyOn(api,'businessPolicies').mockResolvedValueOnce(policyLibrary()).mockResolvedValue(implementationLibrary());
 const view=render(<BusinessPolicyComparisonPanel graph={sourceGraph()} onInspect={()=>{}} refreshToken={0}/>);const select=await screen.findByLabelText('Policy revision to compare');expect(select).toBeDisabled();view.rerender(<BusinessPolicyComparisonPanel graph={sourceGraph()} onInspect={()=>{}} refreshToken={1}/>);await waitFor(()=>expect(select).toBeEnabled());expect(within(select).getAllByRole('option')).toHaveLength(5);
});
