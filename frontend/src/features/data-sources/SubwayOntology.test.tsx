import {render,screen} from '@testing-library/react';
import {expect,it,vi} from 'vitest';
import {api} from '@/api/client';
import {businessOntologySchema} from '@/api/business-ontology';
import {businessSourcesSchema} from '@/api/business-sources';
import SimpsonBusinessOntology from './SimpsonBusinessOntology';
import snapshot from '../../../../ontology/subway/business-ontology-v1.json';

it('renders Subway source bindings and business modules without the Simpsons reference import',async()=>{
 const state=businessOntologySchema.parse({api_version:1,workspace:snapshot.workspace,layers:snapshot.layers,modules:snapshot.modules.map(m=>({...m,concept_count:1})),available_sources:[],source_bindings:[{role:'central',connection_id:'central',name:'Subway Central',status:'connected'},{role:'finance',connection_id:'finance',name:'Subway Finance',status:'connected'}],versions:[{version_id:snapshot.version_id,revision:1,created_at:snapshot.created_at,kind:'draft'}],counts:{concepts:54,relationships:11,rules:0},generation_status:'draft_available',definitions:{concepts:snapshot.concepts,relationships:snapshot.relationships,rules:[]},documents:[],questions:snapshot.questions,current_version_id:snapshot.version_id});
 vi.spyOn(api,'businessOntology').mockResolvedValue(state);
 vi.spyOn(api,'businessGenerationJobs').mockResolvedValue({items:[],configured:false});
 render(<SimpsonBusinessOntology canManage={false}/>);
 expect(await screen.findByRole('heading',{name:'Subway Business Ontology'})).toBeVisible();
 expect(screen.getByText('Subway Central')).toBeVisible();
 expect(screen.getByText('Finance and procurement')).toBeVisible();
 expect(screen.getAllByText('Procurement and catalogue').at(-1)).toBeVisible();
 expect(screen.queryByText('Import supplied Simpson reference')).not.toBeInTheDocument();
});

it('accepts both client source roles in the existing source browser contract',()=>{
 const data=businessSourcesSchema.parse({api_version:1,sources:['central','finance'].map(role=>({role,connection_id:role,name:role,status:'current',metadata_revision:1,generation:1,baseline_revision:1,profile:null,refresh:null,datasets:[],changes:[],impacts:{modules:[],concepts:[],rules:[],workflows:[],workflows_limited:false}})),limits:{profile_rows_per_dataset:100,record_rows:25,record_fields:12,record_bytes:2000000},qualification:'Bounded snapshot.',model_calls:0});
 expect(data.sources.map(s=>s.role)).toEqual(['central','finance']);
});
