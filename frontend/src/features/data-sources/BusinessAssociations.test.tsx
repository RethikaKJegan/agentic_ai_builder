import {act,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';
import {api} from '@/api/client';
import {sourceGraph} from '@/test/fixtures/business-graph';
import {associationReport} from '@/test/fixtures/business-identity';
import BusinessAssociationsPanel from './BusinessAssociationsPanel';
afterEach(()=>vi.restoreAllMocks());
it('requires explicit saved-case selection and keeps cross-source candidates unresolved',async()=>{
 const resolve=vi.spyOn(api,'businessAssociations').mockResolvedValue(associationReport()),inspect=vi.fn();render(<BusinessAssociationsPanel graph={sourceGraph()} onInspect={inspect}/>);
 const button=screen.getByRole('button',{name:'Resolve saved associations'});expect(button).toBeDisabled();fireEvent.change(screen.getByLabelText('Complaint for association checks'),{target:{value:'node1'}});expect(resolve).not.toHaveBeenCalled();fireEvent.click(button);
 expect(await screen.findByText('Requires Review · Physical-engine identity unresolved')).toBeVisible();expect(resolve).toHaveBeenCalledExactlyOnceWith('v2','g1','node1');expect(screen.getByText('claims · unresolved candidate')).toBeVisible();fireEvent.click(screen.getByRole('button',{name:'Inspect association source'}));expect(inspect).toHaveBeenCalledWith('node1');
 fireEvent.change(screen.getByLabelText('Complaint for association checks'),{target:{value:''}});expect(screen.queryByText(/Physical-engine identity unresolved/)).not.toBeInTheDocument();
});
it('offers no action without saved complaints',()=>{
 const g=sourceGraph();g.records=g.records.filter(r=>r.collection!=='tickets');const resolve=vi.spyOn(api,'businessAssociations');render(<BusinessAssociationsPanel graph={g} onInspect={()=>{}}/>);expect(screen.getByText(/No saved complaint records to resolve/)).toBeVisible();expect(screen.queryByRole('button',{name:'Resolve saved associations'})).not.toBeInTheDocument();expect(resolve).not.toHaveBeenCalled();
});
it('discards a late response after the saved graph/version changes',async()=>{
 let finish:(r:ReturnType<typeof associationReport>)=>void=()=>{};vi.spyOn(api,'businessAssociations').mockImplementation(()=>new Promise(resolve=>{finish=resolve;}));const view=render(<BusinessAssociationsPanel graph={sourceGraph()} onInspect={()=>{}}/>);fireEvent.change(screen.getByLabelText('Complaint for association checks'),{target:{value:'node1'}});fireEvent.click(screen.getByRole('button',{name:'Resolve saved associations'}));view.rerender(<BusinessAssociationsPanel graph={{...sourceGraph('v3'),graph_id:'g2'}} onInspect={()=>{}}/>);await act(async()=>finish(associationReport()));expect(screen.queryByText(/Physical-engine identity unresolved/)).not.toBeInTheDocument();
});
it('provides explicit safe retry without automatic source reads',async()=>{
 const resolve=vi.spyOn(api,'businessAssociations').mockRejectedValueOnce(new Error('Unavailable')).mockResolvedValue(associationReport());render(<BusinessAssociationsPanel graph={sourceGraph()} onInspect={()=>{}}/>);fireEvent.change(screen.getByLabelText('Complaint for association checks'),{target:{value:'node1'}});fireEvent.click(screen.getByRole('button',{name:'Resolve saved associations'}));fireEvent.click(await screen.findByRole('button',{name:'Retry read'}));expect(await screen.findByText(/Physical-engine identity unresolved/)).toBeVisible();await waitFor(()=>expect(resolve).toHaveBeenCalledTimes(2));
});
