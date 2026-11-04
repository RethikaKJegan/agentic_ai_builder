import {beforeEach,describe,it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
import {webcrypto} from 'node:crypto';
import {compositionViewSchema} from '@/api/compositions';
import {dynamicView} from '../../../e2e/fixtures/dynamic-investigation';
import {api,ApiError} from '@/api/client';
import {useBackend} from '@/api/state';
import {caseSchema,processDefinitionSchema,fieldInputs,userFields} from '@/api/business-lifecycle';
import fixture from '@/test/fixtures/business-lifecycle.json';
import BusinessLifecycle from './BusinessLifecycle';
import {LifecycleStages,LifecycleEvidence,SavedDetails} from './LifecyclePanels';

const saved=()=>caseSchema.parse(structuredClone(fixture.simpson));
beforeEach(()=>{cleanup();vi.restoreAllMocks();sessionStorage.clear();Object.defineProperty(globalThis,'crypto',{configurable:true,value:webcrypto});
 useBackend.setState({status:'connected',session:{mode:'local-development',planning_available:true,runtime_available:true,approval_service_available:true,auth:{subject:{workspace_id:'one',subject_id:'alice'},roles:['admin','approver'],permissions:['workflow.view','workflow.edit','workflow.plan','workflow.execute','workflow.validate','workflow.approve','events.ingest','runs.view'],scopes:['workspace:read','workspace:write'],decision:'allow'}}});
 vi.spyOn(api,'businessCases').mockResolvedValue({items:[],next_cursor:null});vi.spyOn(api,'businessProcesses').mockResolvedValue({items:[]});vi.spyOn(api,'simpsonProcess').mockResolvedValue(saved().process_definition);vi.spyOn(api,'clientPackages').mockResolvedValue({items:[]});vi.spyOn(api,'businessCase').mockImplementation(async()=>saved());
 vi.spyOn(api,'businessCaseSection').mockImplementation(async(id,section)=>section==='report'?{qualification:'Analytical result only; shipment remains unverified.',stages:[],pending_real_world_waits:[]}:{items:[]});
});
describe('persistent lifecycle presentation',()=>{
 it('renders the pinned twelve stages and a different eight-stage retail process',()=>{
  const {unmount}=render(<LifecycleStages value={saved()}/>);expect(screen.getAllByTestId('lifecycle-stage')).toHaveLength(12);expect(screen.getByText('OEM complaint initiation')).toBeVisible();unmount();
  render(<LifecycleStages value={caseSchema.parse(fixture.retail)}/>);expect(screen.getAllByTestId('lifecycle-stage')).toHaveLength(8);expect(screen.getByText('Order identification')).toBeVisible();
 });
 it('renders skipped branches independently from physical completion',()=>{
  const c=saved();c.stages['replacement_logistics']!.business_outcome_status='SKIPPED';render(<LifecycleStages value={c}/>);expect(screen.getAllByText('SKIPPED')).not.toHaveLength(0);expect(screen.getAllByText(/UNVERIFIED/).length).toBeGreaterThan(0);
 });
 it('shows actual, derived, inferred and synthetic evidence with source limitations',()=>{
  render(<LifecycleEvidence value={saved()}/>);expect(screen.getAllByText('ACTUAL').length).toBeGreaterThan(0);expect(screen.getAllByText('SYNTHETIC').length).toBeGreaterThan(0);expect(screen.getAllByText('DERIVED').length).toBeGreaterThan(0);expect(screen.getAllByText('INFERRED').length).toBeGreaterThan(0);expect(screen.getByText('Conflicts and stale conclusions')).toBeVisible();
 });
 it('withholds credential-shaped content',()=>{render(<SavedDetails value={{access_token:'private-value'}}/>);expect(screen.queryByText(/private-value/)).not.toBeInTheDocument();expect(screen.getByText('Sensitive data withheld.')).toBeInTheDocument();});
 it('uses process-declared inputs without generating user authority from defaults',()=>{
  const p=processDefinitionSchema.parse(fixture.simpson.process_definition);expect(fieldInputs(p,{})).toEqual({});expect(userFields(p).some(f=>f.path==='complaint_id')).toBe(true);expect(fieldInputs(p,{complaint_id:'C123',capa_required:'false'})).toEqual({complaint_id:'C123',capa_required:false});
 });
 it('reopens server state and retrieves the qualified report',async()=>{
  render(<BusinessLifecycle initialCaseId={saved().case_id}/>);await screen.findByText(/Revision 48/);expect(screen.getByText(/Analytical completion does not confirm/)).toBeVisible();fireEvent.click(screen.getByRole('button',{name:'Inspect report'}));await screen.findByRole('heading',{name:'Analytical lifecycle report'});expect(api.businessCaseSection).toHaveBeenCalledWith(saved().case_id,'report');
 });
 it('creates a case from dynamic process inputs',async()=>{
  vi.spyOn(api,'createBusinessCase').mockResolvedValue(saved());render(<BusinessLifecycle/>);await waitFor(()=>expect(screen.getByRole('button',{name:'Create case'})).toBeEnabled());
  fireEvent.change(screen.getByLabelText('Lifecycle investigation goal'),{target:{value:'Review complaint C123'}});fireEvent.change(screen.getByLabelText('complaint id'),{target:{value:'C123'}});fireEvent.click(screen.getByRole('button',{name:'Create case'}));
  await waitFor(()=>expect(api.createBusinessCase).toHaveBeenCalledTimes(1));expect(vi.mocked(api.createBusinessCase).mock.calls[0]![0]).toMatchObject({original_user_goal:'Review complaint C123',inputs:{complaint_id:'C123'},request_key:expect.any(String)});
 });
 it('does not retry an uncertain drive automatically and explicitly reuses its exact key',async()=>{
  const c=saved();c.case_status='READY';vi.mocked(api.businessCase).mockResolvedValue(c);
  const post=vi.spyOn(api,'businessCaseCommand').mockRejectedValueOnce(new ApiError({error_code:'API_UNAVAILABLE',message:'Unavailable',request_id:'req_test',retryable:true},undefined,{outcome:'unknown'})).mockResolvedValueOnce({case_id:c.case_id,stop_reason:'external_or_input_wait',commands_used:1});
  render(<BusinessLifecycle initialCaseId={c.case_id}/>);const drive=await screen.findByRole('button',{name:'Drive / continue'});await waitFor(()=>expect(drive).toBeEnabled());fireEvent.click(drive);await screen.findByRole('button',{name:'Retry same command'});expect(post).toHaveBeenCalledTimes(1);fireEvent.click(screen.getByRole('button',{name:'Retry same command'}));await waitFor(()=>expect(post).toHaveBeenCalledTimes(2));expect(post.mock.calls[0]).toEqual(post.mock.calls[1]);
 });
 it('handles revision conflicts with fresh server state and no automatic command replay',async()=>{
  const c=saved();c.case_status='READY';vi.mocked(api.businessCase).mockResolvedValue(c);const post=vi.spyOn(api,'businessCaseCommand').mockRejectedValue(new ApiError({error_code:'CASE_CONFLICT',message:'Reload revision',request_id:'req_conflict',retryable:false},undefined,{outcome:'rejected',httpStatus:409}));
  render(<BusinessLifecycle initialCaseId={c.case_id}/>);const start=await screen.findByRole('button',{name:'Start'});fireEvent.click(start);await waitFor(()=>expect(post).toHaveBeenCalledOnce());await screen.findByText('Reload revision');expect(post.mock.calls[0]![2]['expected_revision']).toBe(c.revision);expect(screen.queryByRole('button',{name:'Retry same command'})).not.toBeInTheDocument();
 });
 it('hides unauthorized event ingestion while showing pending source information',async()=>{
  useBackend.setState(s=>({session:{...s.session!,auth:{...s.session!.auth,permissions:['workflow.view']}}}));render(<BusinessLifecycle initialCaseId={saved().case_id}/>);await screen.findByRole('button',{name:'Pending activities'});fireEvent.click(screen.getByRole('button',{name:'Pending activities'}));expect(screen.getByText('inspection findings')).toBeVisible();expect(screen.queryByText('Submit authenticated source event')).not.toBeInTheDocument();expect(screen.queryByRole('button',{name:'Approve action'})).not.toBeInTheDocument();
 });
 it('clears case content when the authenticated owner changes',async()=>{
  render(<BusinessLifecycle initialCaseId={saved().case_id}/>);await screen.findByText(/Revision 48/);useBackend.setState(s=>({session:{...s.session!,auth:{...s.session!.auth,subject:{workspace_id:'other',subject_id:'someone'}}}}));await waitFor(()=>expect(screen.queryByText(/Revision 48/)).not.toBeInTheDocument());
 });
});

it('retains the selected capability stage after validating its workflow',async()=>{
 const c=saved();vi.mocked(api.businessCase).mockImplementation(async()=>structuredClone(c));
 let status='draft';vi.spyOn(api,'compositionView').mockImplementation(async(id)=>compositionViewSchema.parse({...dynamicView(),composition_id:id,workflow_status:status}));
 vi.spyOn(api,'request').mockImplementation(async()=>{status='validated';return {} as never});
 render(<BusinessLifecycle initialCaseId={c.case_id}/>);fireEvent.click(await screen.findByRole('button',{name:'Agents & tools'}));
 fireEvent.change(screen.getByLabelText('Agent stage'),{target:{value:'warranty_assessment'}});
 fireEvent.click(await screen.findByRole('button',{name:'Validate workflow'}));
 await screen.findByRole('button',{name:'Approve workflow'});expect(screen.getByLabelText('Agent stage')).toHaveValue('warranty_assessment');
});
it('submits reviewed late evidence with the saved event and expected revision',async()=>{
 const c=saved();c.conflicts=[{reason:'late_event_requires_downstream_reassessment',stage:'field_diagnosis',event:{event_id:'late_inspection',source:'simpson.field_service',payload:{diagnosis:'Reported finding'}}}];
 vi.mocked(api.businessCase).mockResolvedValue(c);const post=vi.spyOn(api,'businessCaseCommand').mockResolvedValue(c);
 render(<BusinessLifecycle initialCaseId={c.case_id}/>);fireEvent.click(await screen.findByRole('button',{name:'Memory & recovery'}));
 fireEvent.click(screen.getByText('Review late evidence for field_diagnosis'));fireEvent.change(screen.getByLabelText('Reviewed input bindings'),{target:{value:'{"reported_diagnosis":"diagnosis"}'}});fireEvent.click(screen.getByRole('button',{name:'Create reviewed reassessment'}));
 await waitFor(()=>expect(post).toHaveBeenCalledOnce());expect(post.mock.calls[0]).toEqual([c.case_id,'reassess',{event_id:'late_inspection',source:'simpson.field_service',input_bindings:{reported_diagnosis:'diagnosis'},expected_revision:c.revision,request_key:expect.any(String)}]);
});

it('allows cancelling an unprepared case without starting business work',async()=>{
 const c=saved();c.case_status='CREATED';c.prepared_at=null;vi.mocked(api.businessCase).mockImplementation(async()=>structuredClone(c));
 vi.spyOn(window,'confirm').mockReturnValue(true);const post=vi.spyOn(api,'businessCaseCommand').mockResolvedValue(c);
 render(<BusinessLifecycle initialCaseId={c.case_id}/>);const cancel=await screen.findByRole('button',{name:'Cancel'});expect(cancel).toBeEnabled();fireEvent.click(cancel);
 await waitFor(()=>expect(post).toHaveBeenCalledOnce());expect(post.mock.calls[0]).toEqual([c.case_id,'cancel',{expected_revision:c.revision,request_key:expect.any(String)}]);
});
