import {act,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {useState} from 'react';
import {api} from '@/api/client';
import {businessOntologySchema,businessVersionSchema,type BusinessOntologyState} from '@/api/business-ontology';
import {moduleCoverage} from '@/test/fixtures/business-intelligence';
import {graphPlan} from '@/test/fixtures/business-graph';
import {ruleCatalogue} from '@/test/fixtures/business-rules';
import catalog from '@/test/fixtures/business-ontology.json';
import BusinessGenerationPanel from './BusinessGenerationPanel';
import BusinessDraftDefinitions from './BusinessDraftDefinitions';
const document={source_id:'doc1',title:'Warranty process',kind:'process',module_ids:['warranty'],text:'Missing coverage information requires review.',sha256:'abc123',origin:'owner_supplied'};
function state(){return businessOntologySchema.parse({...catalog,workspace:{ontology_id:'simpson',title:'Simpson',namespace:'urn:test:',revision:1,status:'foundation',created_at:'2026-10-31',sources:{service:'db1',quality:'db2'},source_revisions:{service:1,quality:1}},documents:[document],current_version_id:'v1',versions:[{version_id:'v1',revision:1,created_at:'2026-10-31',kind:'foundation'}]});}
const base={id:'warranty:review',label:'Requires review',definition:'Missing coverage information requires review.',layer:'business',module_id:'warranty',status:'draft',evidence:[{source_id:'doc1',quote:document.text}],confidence:.8,unknowns:['Exclusions are not supplied.']};
const snapshot=()=>businessVersionSchema.parse({version_id:'v2',revision:2,kind:'draft',created_at:'2026-10-31',concepts:[{...base,id:'warranty:engine',label:'Engine',parent_id:null,properties:[]}],relationships:[],rules:[{...base,inputs:['warranty:engine'],conditions:['Coverage information is missing'],outcome:'Requires review',basis:'proposed_logic',executable:false}],questions:{warranty:['Which exclusions apply?']},sources:[document],extraction:{module_id:'warranty',model:'configured-model',input_tokens:500,output_tokens:200}});
beforeEach(()=>{vi.spyOn(api,'businessModuleCoverage').mockResolvedValue(moduleCoverage());vi.spyOn(api,'businessGraphPlan').mockResolvedValue(graphPlan());vi.spyOn(api,'businessRuleCatalogue').mockResolvedValue(ruleCatalogue());vi.spyOn(api,'businessCompilation').mockResolvedValue({compilation:null});});
afterEach(()=>{vi.restoreAllMocks();vi.useRealTimers();});
it('submits one explicit module job with current revision and a stable retry key',async()=>{
 vi.spyOn(api,'businessGenerationJobs').mockResolvedValue({items:[],configured:true});
 const submit=vi.spyOn(api,'generateBusinessModule').mockResolvedValue({job_id:'j1',module_id:'warranty',state:'queued',created_at:'2026-10-31',version_id:null,error:null,usage:null});
 render(<BusinessGenerationPanel data={state()} canManage moduleId="warranty" onModule={()=>{}} onData={()=>{}}/>);
 const generate=await screen.findByRole('button',{name:'Generate module draft'});await waitFor(()=>expect(generate).toBeEnabled());
 fireEvent.click(generate);await waitFor(()=>expect(submit).toHaveBeenCalledTimes(1));
 expect(submit.mock.calls[0]?.[0]).toMatchObject({module_id:'warranty',expected_revision:1,request_key:expect.any(String)});
});
it('polls completion and refreshes real draft state without invoking another generation',async()=>{
 vi.useFakeTimers();let complete=false;
 const job={job_id:'j1',module_id:'warranty',state:'running' as const,created_at:'2026-10-31',version_id:null,error:null,usage:null};
 vi.spyOn(api,'businessGenerationJobs').mockImplementation(async()=>({items:[complete?{...job,state:'succeeded' as const,version_id:'v2'}:job],configured:true}));
 const next={...state(),current_version_id:'v2',generation_status:'draft_available' as const};vi.spyOn(api,'businessOntology').mockResolvedValue(next);
 const generate=vi.spyOn(api,'generateBusinessModule');const update=vi.fn();
 render(<BusinessGenerationPanel data={state()} canManage moduleId="warranty" onModule={()=>{}} onData={update}/>);
 await act(async()=>{});expect(screen.getByRole('button',{name:'Generate module draft'})).toBeDisabled();
 complete=true;await act(async()=>{await vi.advanceTimersByTimeAsync(2000);});expect(update).toHaveBeenCalledWith(next);expect(generate).not.toHaveBeenCalled();
});
it('viewers can inspect source documents but cannot start generation',async()=>{
 vi.spyOn(api,'businessGenerationJobs').mockResolvedValue({items:[],configured:true});vi.spyOn(api,'businessSource').mockResolvedValue(document);
 render(<BusinessGenerationPanel data={state()} canManage={false} moduleId="warranty" onModule={()=>{}} onData={()=>{}}/>);
 expect(screen.queryByRole('button',{name:'Generate module draft'})).not.toBeInTheDocument();
 fireEvent.click(screen.getByText('Inspect source documents'));fireEvent.click(screen.getByRole('button',{name:'Warranty process · process'}));
 expect(await screen.findByText(document.text)).toBeVisible();
});
it('inspects non-executable rules, quotations, unknowns and immutable older versions',async()=>{
 const current=snapshot();const old={...current,version_id:'v1',revision:1,kind:'foundation' as const,concepts:[],rules:[]};
 const load=vi.spyOn(api,'businessVersion').mockImplementation(async id=>id==='v1'?old:current);
 const data={...state(),current_version_id:'v2',versions:[...state().versions,{version_id:'v2',revision:2,kind:'draft' as const,created_at:'2026-10-31'}]};
 render(<BusinessDraftDefinitions data={data} moduleId="warranty"/>);
 fireEvent.click(await screen.findByRole('button',{name:/Requires review/}));
 const detail=screen.getByRole('article',{name:'Business definition detail'});
 expect(within(detail).getByText(/Execution availability is shown in the rule catalogue/)).toBeVisible();expect(within(detail).getByRole('blockquote')).toHaveTextContent(document.text);
 expect(within(detail).getByText('Exclusions are not supplied.')).toBeVisible();
 fireEvent.change(screen.getByLabelText('Definition version'),{target:{value:'v1'}});
 expect(await screen.findByText('No generated definitions for this module in this version.')).toBeVisible();expect(load).toHaveBeenCalledWith('v1');
});

it('keeps one compiler and one catalogue when an explicit compile refreshes readiness',async()=>{
 const current=snapshot();vi.spyOn(api,'businessVersion').mockResolvedValue(current);
 vi.spyOn(api,'businessRuleCatalogue').mockResolvedValue(ruleCatalogue(current));
 vi.spyOn(api,'compileBusinessVersion').mockResolvedValue({compilation:null});
 render(<BusinessDraftDefinitions data={{...state(),current_version_id:'v2'}} moduleId="warranty" canManage/>);
 const compile=await screen.findByRole('button',{name:'Compile & validate version'});await waitFor(()=>expect(compile).toBeEnabled());
 fireEvent.click(compile);await waitFor(()=>expect(api.compileBusinessVersion).toHaveBeenCalledExactlyOnceWith('v2'));
 await waitFor(()=>expect(api.businessRuleCatalogue).toHaveBeenCalledTimes(2));
 expect(screen.getAllByRole('region',{name:'Ontology compilation'})).toHaveLength(1);
 expect(screen.getAllByRole('region',{name:'Business rules and competency questions'})).toHaveLength(1);
});

it('separates selected-module success from old failures and opens the exact saved draft',async()=>{
 const done={job_id:'done',module_id:'warranty',state:'succeeded' as const,created_at:'2026-11-01',version_id:'v2',error:null,usage:null};
 vi.spyOn(api,'businessGenerationJobs').mockResolvedValue({configured:true,items:[done,{...done,job_id:'old',module_id:'organization',state:'failed',version_id:null,error:{code:'BUSINESS_EXTRACTION_INVALID',message:'Earlier generation did not pass checks.'}}]});
 vi.spyOn(api,'businessOntology').mockResolvedValue({...state(),current_version_id:'v2'});const open=vi.fn();
 render(<BusinessGenerationPanel data={{...state(),current_version_id:'v2',versions:[{version_id:'v2',revision:2,created_at:'2026-11-01',kind:'draft'}]}} canManage moduleId="warranty" onModule={()=>{}} onData={()=>{}} onOpenDraft={open}/>);
 const result=await screen.findByRole('region',{name:'Selected module generation'});expect(await within(result).findByText('Draft generated successfully · Revision 2.')).toBeVisible();expect(within(result).queryByText(/Earlier generation/)).not.toBeInTheDocument();
 fireEvent.click(within(result).getByRole('button',{name:'View generated draft'}));expect(open).toHaveBeenCalledWith('warranty','v2');
 fireEvent.click(screen.getByText('Generation history (2)'));fireEvent.click(screen.getByText('Earlier failure details'));expect(screen.getByText(/BUSINESS_EXTRACTION_INVALID/)).toBeVisible();
});

it('refreshes status without replay and does not repeatedly fetch a synchronized success',async()=>{
 vi.useFakeTimers();const job={job_id:'done',module_id:'warranty',state:'succeeded' as const,created_at:'2026-11-01',version_id:'v2',error:null,usage:null};
 const jobs=vi.spyOn(api,'businessGenerationJobs').mockResolvedValue({configured:true,items:[job]});const load=vi.spyOn(api,'businessOntology').mockResolvedValue({...state(),current_version_id:'v2'});const submit=vi.spyOn(api,'generateBusinessModule');
 render(<BusinessGenerationPanel data={state()} canManage moduleId="warranty" onModule={()=>{}} onData={()=>{}}/>);await act(async()=>{});await act(async()=>{await vi.advanceTimersByTimeAsync(6000);});expect(load).toHaveBeenCalledTimes(1);fireEvent.click(screen.getByRole('button',{name:'Refresh generation status'}));await act(async()=>{});expect(jobs.mock.calls.length).toBeGreaterThan(3);expect(submit).not.toHaveBeenCalled();
});

it('imports and saves sources with visible confirmation and retries a failed selected module explicitly',async()=>{
 const job={job_id:'old',module_id:'warranty',state:'failed' as const,created_at:'2026-11-01',version_id:null,error:{code:'BUSINESS_EXTRACTION_INVALID',message:'A generated quotation could not be matched to its source.'},usage:null};
 vi.spyOn(api,'businessGenerationJobs').mockResolvedValue({configured:true,items:[job]});vi.spyOn(api,'importBusinessReference').mockResolvedValue(state());vi.spyOn(api,'businessOntology').mockResolvedValue(state());const save=vi.spyOn(api,'addBusinessSource').mockResolvedValue(document);const submit=vi.spyOn(api,'generateBusinessModule').mockResolvedValue({...job,job_id:'new',state:'queued',error:null});
 render(<BusinessGenerationPanel data={state()} canManage moduleId="warranty" onModule={()=>{}} onData={()=>{}}/>);await screen.findByRole('button',{name:'Retry selected module'});expect(submit).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('button',{name:'Import supplied Simpson reference'}));expect(await screen.findByText(/Reference sources ready/)).toBeVisible();
 fireEvent.click(screen.getByRole('button',{name:'Add source document'}));fireEvent.change(screen.getByLabelText('Source title'),{target:{value:'New source'}});fireEvent.change(screen.getByLabelText('Source text'),{target:{value:document.text}});fireEvent.click(screen.getByRole('button',{name:'Save source document'}));expect(await screen.findByText(/Source document saved for/)).toBeVisible();expect(save).toHaveBeenCalledWith({title:'New source',kind:'process',module_ids:['warranty'],text:document.text});
 fireEvent.click(screen.getByRole('button',{name:'Retry selected module'}));await waitFor(()=>expect(submit).toHaveBeenCalledTimes(1));
});

it('shows a successful first-attempt source correction without calling it policy authority',async()=>{
 const adjustments=[{rule_id:'warranty:review',original_basis:'policy_statement' as const,basis:'proposed_logic' as const,reason:'cited_source_kind_does_not_support_authority' as const}];
 vi.spyOn(api,'businessGenerationJobs').mockResolvedValue({configured:true,items:[{job_id:'done',module_id:'warranty',state:'succeeded',created_at:'2026-11-01',version_id:'v2',error:null,usage:{classification_adjustments:adjustments}}]});
 render(<BusinessGenerationPanel data={{...state(),current_version_id:'v2'}} canManage moduleId="warranty" onModule={()=>{}} onData={()=>{}}/>);
 expect(await screen.findByText(/Source checks completed. Unsupported policy\/code labels were kept as proposed logic/)).toBeVisible();expect(screen.queryByRole('button',{name:'Retry selected module'})).not.toBeInTheDocument();
});
