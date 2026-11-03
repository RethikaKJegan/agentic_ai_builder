import {act,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';
import {api} from '@/api/client';
import {businessWarrantyAssessmentSchema} from '@/api/business-ontology';
import {policyLibrary} from '@/test/fixtures/business-policy';
import {warrantyAssessment} from '@/test/fixtures/business-assessment';
import {sourceGraph} from '@/test/fixtures/business-graph';
import BusinessPolicyComparisonPanel from './BusinessPolicyComparisonPanel';
afterEach(()=>vi.restoreAllMocks());
async function selectCase(){await screen.findByRole('button',{name:'Assess saved warranty case'});for(const [name,value] of [['Policy revision to compare','p1'],['Complaint for policy comparison','node1'],['Assessment date and time','2026-06-01T12:00'],['Assessment timezone offset','+05:30']])fireEvent.change(screen.getByLabelText(name!),{target:{value}});}
it('assesses only on explicit action and distinguishes draft calculations from final eligibility',async()=>{
 vi.spyOn(api,'businessPolicies').mockResolvedValue(policyLibrary(true));const assess=vi.spyOn(api,'assessBusinessWarranty').mockResolvedValue(warrantyAssessment());render(<BusinessPolicyComparisonPanel graph={sourceGraph()} onInspect={()=>{}}/>);await selectCase();expect(assess).not.toHaveBeenCalled();fireEvent.click(screen.getByRole('button',{name:'Assess saved warranty case'}));
 expect(await screen.findByRole('region',{name:'Warranty assessment result'})).toBeVisible();expect(screen.getByText('Requires Review · No final eligibility decision')).toBeVisible();expect(screen.getByText('Draft calculation: incomplete evidence')).toBeVisible();expect(screen.getByText('operating hours: unknown')).toBeVisible();expect(assess).toHaveBeenCalledExactlyOnceWith('v2','g1',{policy_id:'p1',ticket_node_id:'node1',invoice_node_id:null,assessment_at:'2026-06-01T12:00:00+05:30'});
 fireEvent.change(screen.getByLabelText('Assessment timezone offset'),{target:{value:'Z'}});expect(screen.queryByRole('region',{name:'Warranty assessment result'})).not.toBeInTheDocument();
});
it('rejects a final approval or denial with unverified evidence in the client contract',()=>{
 for(const classification of ['Warranty Eligible','Warranty Not Eligible'])expect(()=>businessWarrantyAssessmentSchema.parse({...warrantyAssessment(),classification})).toThrow();
});
it('discards a late assessment after the selected graph changes',async()=>{
 vi.spyOn(api,'businessPolicies').mockResolvedValue(policyLibrary(true));let finish:(r:ReturnType<typeof warrantyAssessment>)=>void=()=>{};vi.spyOn(api,'assessBusinessWarranty').mockImplementation(()=>new Promise(resolve=>{finish=resolve;}));const view=render(<BusinessPolicyComparisonPanel graph={sourceGraph()} onInspect={()=>{}}/>);await selectCase();fireEvent.click(screen.getByRole('button',{name:'Assess saved warranty case'}));view.rerender(<BusinessPolicyComparisonPanel graph={{...sourceGraph('v3'),graph_id:'g2'}} onInspect={()=>{}}/>);await act(async()=>finish(warrantyAssessment()));expect(screen.queryByRole('region',{name:'Warranty assessment result'})).not.toBeInTheDocument();
});
it('shows a safe error without silently treating assessment failure as an empty decision',async()=>{
 vi.spyOn(api,'businessPolicies').mockResolvedValue(policyLibrary(true));vi.spyOn(api,'assessBusinessWarranty').mockRejectedValue(new Error('Unavailable'));render(<BusinessPolicyComparisonPanel graph={sourceGraph()} onInspect={()=>{}}/>);await selectCase();fireEvent.click(screen.getByRole('button',{name:'Assess saved warranty case'}));await waitFor(()=>expect(screen.getByRole('button',{name:'Retry read'})).toBeVisible());expect(screen.queryByRole('region',{name:'Warranty assessment result'})).not.toBeInTheDocument();
});

it('assesses a missing policy without forcing a fabricated policy selection',async()=>{
 const {missingPolicyAssessment}=await import('@/test/fixtures/business-assessment');vi.spyOn(api,'businessPolicies').mockResolvedValue(policyLibrary());const assess=vi.spyOn(api,'assessBusinessWarranty').mockResolvedValue(missingPolicyAssessment());render(<BusinessPolicyComparisonPanel graph={sourceGraph()} onInspect={()=>{}}/>);
 await screen.findByRole('button',{name:'Assess saved warranty case'});for(const [name,value] of [['Complaint for policy comparison','node1'],['Assessment date and time','2026-06-01T12:00'],['Assessment timezone offset','Z']])fireEvent.change(screen.getByLabelText(name!),{target:{value}});
 expect(screen.getByRole('button',{name:'Compare saved policy scope'})).toBeDisabled();fireEvent.click(screen.getByRole('button',{name:'Assess saved warranty case'}));expect(await screen.findByText(/Missing policy requires review/)).toBeVisible();expect(assess).toHaveBeenCalledWith('v2','g1',{policy_id:null,ticket_node_id:'node1',invoice_node_id:null,assessment_at:'2026-06-01T12:00:00Z'});
});
