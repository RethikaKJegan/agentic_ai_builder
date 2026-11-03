import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';
import {api} from '@/api/client';
import {businessSourcesSchema} from '@/api/business-sources';
import Panel from './BusinessSourcesPanel';
const fixture=()=>businessSourcesSchema.parse({api_version:1,sources:['service','quality'].map(role=>({role,connection_id:role,name:role==='service'?'Simpson db1':'Simpson db2',status:'current',metadata_revision:2,generation:1,baseline_revision:2,profile:null,refresh:null,datasets:[{dataset_id:role+'_tickets',name:role==='service'?'tickets':'claims',module_ids:['warranty'],mapping_basis:'supplied_source_inventory',sample_count:10,fields:[{field_id:'id',name:'_id',types:['string']}],field_count:1,profile_rows:null,statistics:{},can_browse:true}],changes:[],impacts:{modules:[],concepts:[],rules:[],workflows:[],workflows_limited:false}})),limits:{profile_rows_per_dataset:100,record_rows:25,record_fields:12,record_bytes:2000000},qualification:'Sampled metadata is not proof of absence.',model_calls:0});
afterEach(()=>vi.restoreAllMocks());
it('loads both databases without implicit profiling or company record reads',async()=>{
 vi.spyOn(api,'businessSources').mockResolvedValue(fixture());const profile=vi.spyOn(api,'profileBusinessSource'),records=vi.spyOn(api,'businessSourceRecords');render(<Panel canManage/>);
 expect(await screen.findByText('Simpson db1')).toBeVisible();expect(screen.getByText('Simpson db2')).toBeVisible();expect(profile).not.toHaveBeenCalled();expect(records).not.toHaveBeenCalled();
});
it('profiles only the clicked owned database and refreshes saved status',async()=>{
 const status=vi.spyOn(api,'businessSources').mockResolvedValue(fixture());const profile=vi.spyOn(api,'profileBusinessSource').mockResolvedValue({job_id:'job1',status:'queued',limits:{rows_per_dataset:100,seconds:60},basis:'bounded_sample'});render(<Panel canManage/>);
 fireEvent.click((await screen.findAllByRole('button',{name:'Profile database'}))[0]!);await waitFor(()=>expect(profile).toHaveBeenCalledWith('service'));await waitFor(()=>expect(status).toHaveBeenCalledTimes(2));expect(screen.getByText(/Profiling queued/)).toBeVisible();
});
it('browses revision-bound records only on demand and paginates',async()=>{
 vi.spyOn(api,'businessSources').mockResolvedValue(fixture());const read=vi.spyOn(api,'businessSourceRecords').mockResolvedValue({records:[{_id:'ticket1'}],fields:['_id'],offset:0,limit:10,has_more:true,next_offset:10,source:{connection_id:'service',dataset_id:'service_tickets',metadata_revision:2,generation:1,read_at:'2026-11-02T12:00:00Z'},qualification:'Reported evidence only.',model_calls:0});render(<Panel canManage={false}/>);
 const browse=await screen.findByRole('button',{name:'Browse tickets records'});fireEvent.click(screen.getByText(/tickets · 1 fields/));fireEvent.click(browse);
 expect(await screen.findByText('ticket1')).toBeVisible();expect(read).toHaveBeenCalledWith({connection_id:'service',dataset_id:'service_tickets',metadata_revision:2,generation:1,offset:0,limit:10});expect(screen.queryByRole('button',{name:'Profile database'})).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Next records'}));await waitFor(()=>expect(read).toHaveBeenLastCalledWith(expect.objectContaining({offset:10})));
});
it('shows metadata drift and referenced rules without rewriting definitions',async()=>{
 const value=fixture();value.sources[0]!.status='metadata_changed';value.sources[0]!.changes=[{dataset_id:'service_tickets',name:'tickets',state:'changed',added_fields:[],not_observed_fields:[],type_changes:[{field:'hours',previous_types:['string'],current_types:['number']}]}];value.sources[0]!.impacts.rules=[{id:'warranty',label:'Warranty eligibility',module_id:'warranty'}];vi.spyOn(api,'businessSources').mockResolvedValue(value);render(<Panel canManage/>);
 expect(await screen.findByText('hours: string → number')).toBeVisible();expect(screen.getByText(/Referenced rules: Warranty eligibility/)).toBeVisible();
});
