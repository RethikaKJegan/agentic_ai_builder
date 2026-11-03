import {render,screen} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';
import {api} from '@/api/client';
import DataIntelligence from './DataIntelligence';
vi.mock('@/api/state',()=>({useBackend:()=>({status:'connected',can:()=>true})}));
afterEach(()=>vi.restoreAllMocks());
it('shows one Business Ontology tab and no legacy Ontology tab',async()=>{
 vi.spyOn(api,'dataSources').mockResolvedValue({configured:true,shared_demo_identity:true,items:[]});
 render(<DataIntelligence/>);
 expect(await screen.findByRole('tab',{name:'Business Ontology'})).toBeVisible();
 expect(screen.queryByRole('tab',{name:/^Ontology$/})).not.toBeInTheDocument();
});
