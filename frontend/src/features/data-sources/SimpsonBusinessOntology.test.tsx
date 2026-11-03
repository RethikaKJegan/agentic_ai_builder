import {policyLibrary} from '@/test/fixtures/business-policy';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach,beforeEach, expect, it, vi } from 'vitest';
import { api } from '@/api/client';
import { businessOntologySchema } from '@/api/business-ontology';
import catalog from '@/test/fixtures/business-ontology.json';
import BusinessOntology from './SimpsonBusinessOntology';

const fixture=()=>businessOntologySchema.parse(structuredClone(catalog));
afterEach(()=>vi.restoreAllMocks());
it('navigates all five layers and twelve modules without simulated concepts',async()=>{
 vi.spyOn(api,'businessOntology').mockResolvedValue(fixture());render(<BusinessOntology canManage/>);
 expect(await screen.findByRole('heading',{name:'Connect the business foundation'})).toBeVisible();
 const modules=screen.getByRole('group',{name:'Business ontology modules'});
 expect(within(modules).getAllByRole('button')).toHaveLength(12);
 fireEvent.click(screen.getByRole('button',{name:'Foundational'}));
 expect(within(modules).getAllByRole('button')).toHaveLength(1);
 expect(within(screen.getByRole('article',{name:'Selected business module'})).getByRole('heading',{name:'Evidence and provenance'})).toBeVisible();
 expect(screen.getByText('No concepts have been generated for this module.')).toBeVisible();
 expect(screen.queryByRole('button',{name:/generate|approve|publish/i})).not.toBeInTheDocument();
});
it('requires distinct sources and saves the returned foundation',async()=>{
 const initial=fixture();vi.spyOn(api,'businessOntology').mockResolvedValue(initial);
 const saved={...initial,workspace:{ontology_id:'simpson' as const,title:'Simpson Business Ontology',namespace:'urn:test:',revision:1,status:'foundation' as const,created_at:'2026-10-31T12:00:00Z',sources:{service:'db1',quality:'db2'},source_revisions:{service:1,quality:1}},source_bindings:[{role:'service' as const,connection_id:'db1',name:'Simpson service db1',status:'connected' as const},{role:'quality' as const,connection_id:'db2',name:'Simpson quality db2',status:'connected' as const}]};
 const initialize=vi.spyOn(api,'initializeBusinessOntology').mockResolvedValue(saved);
 render(<BusinessOntology canManage/>);const create=await screen.findByRole('button',{name:'Create business ontology workspace'});
 expect(create).toBeDisabled();fireEvent.change(screen.getByLabelText('Service operations source'),{target:{value:'db1'}});fireEvent.change(screen.getByLabelText('Claims and quality source'),{target:{value:'db1'}});expect(create).toBeDisabled();
 fireEvent.change(screen.getByLabelText('Claims and quality source'),{target:{value:'db2'}});fireEvent.click(create);
 await waitFor(()=>expect(initialize).toHaveBeenCalledWith({service:'db1',quality:'db2'}));
 expect(await screen.findByRole('heading',{name:'Foundation ready'})).toBeVisible();expect(screen.getByText('Revision 1')).toBeVisible();
});
it('viewers can browse the catalogue without management controls',async()=>{
 vi.spyOn(api,'businessOntology').mockResolvedValue(fixture());render(<BusinessOntology canManage={false}/>);
 expect(await screen.findByText(/A workspace manager can connect/)).toBeVisible();
 expect(screen.queryByRole('button',{name:'Create business ontology workspace'})).not.toBeInTheDocument();
 expect(screen.queryByLabelText('Service operations source')).not.toBeInTheDocument();
});
it('shows load failure and supports retry',async()=>{
 const load=vi.spyOn(api,'businessOntology').mockRejectedValueOnce(new Error('Source unavailable')).mockResolvedValue(fixture());
 render(<BusinessOntology canManage/>);expect(await screen.findByRole('alert')).toBeVisible();
 fireEvent.click(screen.getByRole('button',{name:'Refresh business ontology'}));
 expect(await screen.findByRole('heading',{name:'Connect the business foundation'})).toBeVisible();expect(load).toHaveBeenCalledTimes(2);
});
it('does not initialize when the tab is opened',async()=>{
 vi.spyOn(api,'businessOntology').mockResolvedValue(fixture());const initialize=vi.spyOn(api,'initializeBusinessOntology');
 render(<BusinessOntology canManage/>);await screen.findByRole('heading',{name:'Connect the business foundation'});expect(initialize).not.toHaveBeenCalled();
});

beforeEach(()=>vi.spyOn(api,'businessPolicies').mockResolvedValue(policyLibrary()));
