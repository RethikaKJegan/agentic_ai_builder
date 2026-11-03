import {act,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';
import {api} from '@/api/client';
import {sourceGraph} from '@/test/fixtures/business-graph';
import {warrantyReadiness} from '@/test/fixtures/business-warranty';
import BusinessWarrantyPanel from './BusinessWarrantyPanel';
afterEach(()=>vi.restoreAllMocks());
it('prepares one explicit case without substituting alternate hours and inspects sources',async()=>{
 const prepare=vi.spyOn(api,'businessWarrantyReadiness').mockResolvedValue(warrantyReadiness()),inspect=vi.fn();render(<BusinessWarrantyPanel graph={sourceGraph()} onInspect={inspect}/>);
 const button=screen.getByRole('button',{name:'Prepare warranty inputs'});expect(button).toBeDisabled();expect(prepare).not.toHaveBeenCalled();
 fireEvent.change(screen.getByLabelText('Complaint to prepare'),{target:{value:'node1'}});expect(prepare).not.toHaveBeenCalled();fireEvent.click(button);
 expect(await screen.findByText('Requires Review · Eligibility not evaluated')).toBeVisible();expect(prepare).toHaveBeenCalledExactlyOnceWith('v2','g1','node1');
 const primary=screen.getByRole('heading',{name:'Reported complaint hours'}).closest('article')!;expect(within(primary).getByText('not returned')).toBeVisible();expect(within(primary).queryByText('Normalized: 12')).not.toBeInTheDocument();
 const alternate=screen.getByRole('heading',{name:'Alternate ticket hours'}).closest('article')!;expect(within(alternate).getByText('Normalized: 12')).toBeVisible();
 fireEvent.click(within(primary).getByRole('button',{name:'Inspect input source record'}));expect(inspect).toHaveBeenCalledWith('node1');expect(screen.getByText(/No applicable policy configured/)).toBeVisible();
});
it('does not invent a complaint for invoice-only saved graphs',()=>{
 const graph=sourceGraph();graph.records=graph.records.filter(r=>r.collection!=='tickets');const prepare=vi.spyOn(api,'businessWarrantyReadiness');render(<BusinessWarrantyPanel graph={graph} onInspect={()=>{}}/>);
 expect(screen.getByText(/No complaint records in this saved graph/)).toBeVisible();expect(screen.queryByRole('button',{name:'Prepare warranty inputs'})).not.toBeInTheDocument();expect(prepare).not.toHaveBeenCalled();
});
it('drops late responses on case changes and preserves independent case selection',async()=>{
 const graph=sourceGraph();graph.records.push({...graph.records[0]!,node_id:'node3',key:{_id:'t2'}});
 let finish:(value:ReturnType<typeof warrantyReadiness>)=>void=()=>{};const prepare=vi.spyOn(api,'businessWarrantyReadiness').mockImplementation(()=>new Promise(resolve=>{finish=resolve;}));
 render(<BusinessWarrantyPanel graph={graph} onInspect={()=>{}}/>);fireEvent.change(screen.getByLabelText('Complaint to prepare'),{target:{value:'node1'}});fireEvent.click(screen.getByRole('button',{name:'Prepare warranty inputs'}));fireEvent.change(screen.getByLabelText('Complaint to prepare'),{target:{value:'node3'}});
 await act(async()=>finish(warrantyReadiness()));expect(screen.queryByText(/Eligibility not evaluated/)).not.toBeInTheDocument();prepare.mockResolvedValue(warrantyReadiness('node3'));fireEvent.click(screen.getByRole('button',{name:'Prepare warranty inputs'}));expect(await screen.findByText(/Eligibility not evaluated/)).toBeVisible();expect(prepare).toHaveBeenLastCalledWith('v2','g1','node3');
});
it('drops late results on graph/version changes',async()=>{
 let finish:(value:ReturnType<typeof warrantyReadiness>)=>void=()=>{};vi.spyOn(api,'businessWarrantyReadiness').mockImplementation(()=>new Promise(resolve=>{finish=resolve;}));const view=render(<BusinessWarrantyPanel graph={sourceGraph()} onInspect={()=>{}}/>);
 fireEvent.change(screen.getByLabelText('Complaint to prepare'),{target:{value:'node1'}});fireEvent.click(screen.getByRole('button',{name:'Prepare warranty inputs'}));view.rerender(<BusinessWarrantyPanel graph={{...sourceGraph('v3'),graph_id:'g2'}} onInspect={()=>{}}/>);
 await act(async()=>finish(warrantyReadiness()));expect(screen.queryByText(/Eligibility not evaluated/)).not.toBeInTheDocument();expect(screen.getByLabelText('Complaint to prepare')).toHaveValue('');
});
it('shows a read error and retries only on explicit action',async()=>{
 const prepare=vi.spyOn(api,'businessWarrantyReadiness').mockRejectedValueOnce(new Error('Unavailable')).mockResolvedValue(warrantyReadiness());render(<BusinessWarrantyPanel graph={sourceGraph()} onInspect={()=>{}}/>);fireEvent.change(screen.getByLabelText('Complaint to prepare'),{target:{value:'node1'}});fireEvent.click(screen.getByRole('button',{name:'Prepare warranty inputs'}));
 fireEvent.click(await screen.findByRole('button',{name:'Retry read'}));expect(await screen.findByText(/Eligibility not evaluated/)).toBeVisible();await waitFor(()=>expect(prepare).toHaveBeenCalledTimes(2));
});
