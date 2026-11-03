import {act,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';
import {api} from '@/api/client';
import {intelligenceCatalogue,intelligenceReport,moduleCoverage} from '@/test/fixtures/business-intelligence';
import {businessOntologySchema} from '@/api/business-ontology';
import catalog from '@/test/fixtures/business-ontology.json';
import BusinessIntelligencePanel from './BusinessIntelligencePanel';
import BusinessModuleCoveragePanel from './BusinessModuleCoveragePanel';
afterEach(()=>vi.restoreAllMocks());
it('runs only explicit fixed reports, paginates, and inspects record provenance',async()=>{
 vi.spyOn(api,'businessIntelligenceCatalogue').mockResolvedValue(intelligenceCatalogue());
 const run=vi.spyOn(api,'runBusinessIntelligence').mockImplementation(async(_v,_g,body)=>intelligenceReport(body.question_id,body.offset));const inspect=vi.fn();
 render(<BusinessIntelligencePanel versionId="v2" graphId="g1" onInspect={inspect}/>);
 const button=await screen.findByRole('button',{name:'Run snapshot report'});expect(run).not.toHaveBeenCalled();fireEvent.click(button);
 expect(await screen.findByText('tickets · hmr')).toBeVisible();expect(run).toHaveBeenCalledExactlyOnceWith('v2','g1',{question_id:'service_path',limit:20,offset:0});
 fireEvent.click(screen.getByRole('button',{name:'Inspect source record'}));expect(inspect).toHaveBeenCalledWith('node1');
 fireEvent.click(screen.getByRole('button',{name:'Next observations'}));await waitFor(()=>expect(run).toHaveBeenLastCalledWith('v2','g1',{question_id:'service_path',limit:20,offset:20}));
 expect(screen.getByText(/warranty eligibility: not evaluated/)).toBeVisible();
 fireEvent.change(screen.getByLabelText('Snapshot question'),{target:{value:'claim_fields'}});expect(screen.queryByText('tickets · hmr')).not.toBeInTheDocument();expect(run).toHaveBeenCalledTimes(2);
});
it('discards late report responses when the graph changes',async()=>{
 vi.spyOn(api,'businessIntelligenceCatalogue').mockImplementation(async(v,g)=>intelligenceCatalogue(v,g));
 let finish:(value:ReturnType<typeof intelligenceReport>)=>void=()=>{};vi.spyOn(api,'runBusinessIntelligence').mockImplementation(()=>new Promise(resolve=>{finish=resolve;}));
 const view=render(<BusinessIntelligencePanel versionId="v2" graphId="g1" onInspect={()=>{}}/>);fireEvent.click(await screen.findByRole('button',{name:'Run snapshot report'}));
 view.rerender(<BusinessIntelligencePanel versionId="v3" graphId="g2" onInspect={()=>{}}/>);await act(async()=>finish(intelligenceReport()));expect(screen.queryByText('tickets · hmr')).not.toBeInTheDocument();
});
it('shows empty evidence without implying database-wide absence and exposes retry on failure',async()=>{
 vi.spyOn(api,'businessIntelligenceCatalogue').mockResolvedValue(intelligenceCatalogue());const run=vi.spyOn(api,'runBusinessIntelligence').mockResolvedValue({...intelligenceReport(),rows:[],total_rows:0,has_more:false,next_offset:null,result_state:'no_matching_observations'});
 render(<BusinessIntelligencePanel versionId="v2" graphId="g1" onInspect={()=>{}}/>);fireEvent.click(await screen.findByRole('button',{name:'Run snapshot report'}));expect(await screen.findByText(/This does not establish absence/)).toBeVisible();
 run.mockRejectedValueOnce(new Error('Unavailable'));fireEvent.click(screen.getByRole('button',{name:'Run snapshot report'}));expect(await screen.findByRole('button',{name:'Retry read'})).toBeVisible();expect(screen.queryByText(/This does not establish absence/)).not.toBeInTheDocument();
});
it('adds missing reference drafts explicitly with the revision and a stable retry key',async()=>{
 vi.spyOn(api,'businessModuleCoverage').mockResolvedValue(moduleCoverage());const next=businessOntologySchema.parse(catalog),onData=vi.fn();const add=vi.spyOn(api,'addBusinessReferenceModules').mockRejectedValueOnce(new Error('Unknown outcome')).mockResolvedValue({version_id:'v3',state:next});
 render(<BusinessModuleCoveragePanel versionId="v2" canManage onData={onData}/>);const button=await screen.findByRole('button',{name:'Add missing reference drafts'});expect(add).not.toHaveBeenCalled();
 fireEvent.click(button);await screen.findByRole('button',{name:'Retry read'});fireEvent.click(button);await waitFor(()=>expect(onData).toHaveBeenCalledWith(next));
 expect(add.mock.calls[0]?.[0]).toEqual({expected_revision:2,request_key:expect.any(String)});expect(add.mock.calls[1]?.[0]).toEqual(add.mock.calls[0]?.[0]);
});
it('does not offer reference import to viewers or historical versions',async()=>{
 vi.spyOn(api,'businessModuleCoverage').mockResolvedValue({...moduleCoverage(),import_available:false,unavailable_reason:'Choose the latest saved version.'});const add=vi.spyOn(api,'addBusinessReferenceModules');
 const view=render(<BusinessModuleCoveragePanel versionId="v1" canManage={false} onData={()=>{}}/>);expect(await screen.findByText('1 of 2 modules contain drafts.')).toBeVisible();expect(screen.queryByRole('button',{name:'Add missing reference drafts'})).not.toBeInTheDocument();
 view.rerender(<BusinessModuleCoveragePanel versionId="v1" canManage onData={()=>{}}/>);expect(screen.getByRole('button',{name:'Add missing reference drafts'})).toBeDisabled();expect(add).not.toHaveBeenCalled();
});
