import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {beforeEach,describe,it,expect,vi} from 'vitest';
import {OverviewAutomationReview} from './OverviewAutomationReview';
import {overviewResultSchema,overviewStorageKey} from '@/api/overview-automation';
import {InputError} from '@/api/feedback';

const calls=vi.hoisted(()=>({activate:vi.fn(),read:vi.fn(),control:vi.fn(),list:vi.fn()}));
vi.mock('next/navigation',()=>({usePathname:()=>'/app'}));
vi.mock('@/api/client',async importOriginal=>({...await importOriginal<typeof import('@/api/client')>(),api:{activateOverview:calls.activate,overviewIntent:calls.read,controlAutomation:calls.control,automationRecords:calls.list}}));
vi.mock('@/api/state',()=>({useBackend:()=>({session:{auth:{subject:{workspace_id:'one',subject_id:'alice'}}},can:()=>true})}));
vi.mock('./ConnectedPlan',()=>({ConnectedPlan:({scheduled}:{scheduled:boolean})=><div>Existing workflow review {scheduled?'scheduled':'one time'}</div>,actionButton:'button'}));

beforeEach(()=>vi.clearAllMocks());

const prepared=()=>overviewResultSchema.parse({version:'overview-intent-v1',state:'prepared',request_key:'overview_test_001',workspace:{workspace_id:'one',subject_id:'alice'},intent:{intent_type:'recurring',business_goal:'Daily source report',side_effects:['email_send']},composition_id:'composition_review',schedule:{cron:'0 18 * * *',timezone:'Asia/Kolkata',next_due:1794313800,expires_at:1800000000,max_occurrences:90,missed_run_policy:'coalesce',overlap_policy:'forbid'},operations:{extension_mail_send:{properties:{to:{const:'owner@example.com'}}}}});

describe('Existing Overview automation review',()=>{
  beforeEach(()=>vi.clearAllMocks());
  it('requires explicit consent and reuses the workflow review without automatically activating',async()=>{
    const value=prepared();calls.activate.mockResolvedValue({});calls.read.mockResolvedValue(value);
    const changed=vi.fn();render(<OverviewAutomationReview value={value} onChange={changed}/>);
    const button=screen.getByRole('button',{name:'Authorize and start schedule'});
    expect(button).toBeDisabled();expect(calls.activate).not.toHaveBeenCalled();
    expect(screen.getByText('Existing workflow review scheduled')).toBeVisible();
    fireEvent.click(screen.getByRole('checkbox'));fireEvent.click(button);
    await waitFor(()=>expect(changed).toHaveBeenCalledWith(value));
    expect(calls.activate).toHaveBeenCalledExactlyOnceWith('overview_test_001');
  });
  it('shows a precise clarification and uses the existing prompt for corrections',()=>{
    const value=prepared();value.state='clarification';value.questions=['Which report should be updated?'];delete value.composition_id;delete value.schedule;
    render(<OverviewAutomationReview value={value} onChange={vi.fn()}/>);
    expect(screen.queryByText('Which report should be updated?')).toBeNull();expect(screen.getByText(/no additional answer is requested here/)).toBeVisible();
    expect(screen.queryByRole('textbox')).toBeNull();
    expect(screen.queryByText('Authorize and start schedule')).toBeNull();
  });
  it('shows a source-meaning clarification for Subway without adding input bindings',()=>{
    const value=prepared();value.state='clarification';value.questions=['Should spending mean purchase-order value or paid invoices?'];value['business_clarification']=true;delete value.composition_id;delete value.schedule;
    render(<OverviewAutomationReview value={value} onChange={vi.fn()}/>);
    expect(screen.getByText(value.questions[0]!)).toBeVisible();
    expect(screen.getByText(/Update the request with the intended business meaning/)).toBeVisible();
    expect(screen.queryByRole('textbox')).toBeNull();
  });
  it('keeps Overview compact with a workflow link and no graph or authorization controls',()=>{
    render(<OverviewAutomationReview value={prepared()} onChange={vi.fn()} compact/>);
    expect(screen.getByRole('link',{name:'Open workflow'})).toHaveAttribute('href',expect.stringContaining('overview=overview_test_001'));
    expect(screen.queryByText('Existing workflow review scheduled')).toBeNull();
    expect(screen.queryByRole('checkbox')).toBeNull();
    expect(calls.activate).not.toHaveBeenCalled();
  });
  it('does not render another tenant review and scopes refresh keys by owner',()=>{
    const value=prepared();value.workspace!.workspace_id='another';
    render(<OverviewAutomationReview value={value} onChange={vi.fn()}/>);
    expect(screen.queryByRole('region')).toBeNull();
    expect(overviewStorageKey('one','alice')).not.toBe(overviewStorageKey('one','bob'));
  });
  it('retains failed activation as an error without claiming an active schedule',async()=>{
    calls.activate.mockRejectedValue(new InputError('Approve the workflow first.'));
    render(<OverviewAutomationReview value={prepared()} onChange={vi.fn()}/>);
    fireEvent.click(screen.getByRole('checkbox'));fireEvent.click(screen.getByText('Authorize and start schedule'));
    await waitFor(()=>expect(screen.getByText('Approve the workflow first.')).toBeVisible());
    expect(calls.read).not.toHaveBeenCalled();
  });
  it('requires a fresh acknowledgement for a new proposal',()=>{
    const value=prepared();const {rerender}=render(<OverviewAutomationReview value={value} onChange={vi.fn()}/>);
    fireEvent.click(screen.getByRole('checkbox'));
    expect(screen.getByRole('button',{name:'Authorize and start schedule'})).toBeEnabled();
    rerender(<OverviewAutomationReview value={{...value,request_key:'another_proposal'}} onChange={vi.fn()}/>);
    expect(screen.getByRole('checkbox')).not.toBeChecked();
    expect(screen.getByRole('button',{name:'Authorize and start schedule'})).toBeDisabled();
  });
  it('resumes a paused schedule through the existing control API',async()=>{
    const value=prepared();value.activation={state:'active',schedule_id:'auto_saved',authorization_id:'auto_consent',due:123};value.schedule_record={id:'auto_saved',state:'paused',due:123};
    calls.control.mockResolvedValue({});calls.read.mockResolvedValue(value);
    render(<OverviewAutomationReview value={value} onChange={vi.fn()}/>);
    expect(screen.queryByText('Pause schedule')).toBeNull();
    fireEvent.click(screen.getByRole('button',{name:'Resume schedule'}));
    await waitFor(()=>expect(calls.control).toHaveBeenCalledWith('auto_saved',expect.objectContaining({action:'resume',request_key:expect.any(String)})));
  });
});

describe('Subway event review and execution history',()=>{
  beforeEach(()=>vi.clearAllMocks());
  it('requires consent for a configured event and prevents manual execution',()=>{
    const value=prepared();value.schedule=null;value.event_subscription={source:{provider:'fixture',source_id:'synthetic-finance',event_type:'invoice.created',timezone:'UTC'},expires_at:1800000000,max_occurrences:10};
    render(<OverviewAutomationReview value={value} onChange={vi.fn()}/>);
    expect(screen.getByText(/Business event: invoice.created/)).toBeVisible();
    expect(screen.getByText('Existing workflow review scheduled')).toBeVisible();
    const start=screen.getByRole('button',{name:'Authorize and start event subscription'});
    expect(start).toBeDisabled();fireEvent.click(screen.getByRole('checkbox'));expect(start).toBeEnabled();
    expect(calls.activate).not.toHaveBeenCalled();
  });
  it('shows blocked executions and opens their saved run',()=>{
    const value=prepared();value.activation={state:'active',schedule_id:'saved',authorization_id:'approved',due:123};value.automation_history=[{id:'occ_1',state:'failed',due:123,run_id:'run_verified',last_error_code:'SOURCE_FRESHNESS_UNVERIFIED'}];
    const onRun=vi.fn();render(<OverviewAutomationReview value={value} onChange={vi.fn()} onRun={onRun}/>);
    expect(screen.getByText(/failed · SOURCE_FRESHNESS_UNVERIFIED/)).toBeVisible();
    fireEvent.click(screen.getByRole('button',{name:'Inspect execution'}));expect(onRun).toHaveBeenCalledWith('run_verified');
  });
});

it('retries only an eligible saved occurrence with an idempotent control',async()=>{
  const value=prepared();value.activation={state:'active',schedule_id:'parent',authorization_id:'consent',due:123};value.automation_history=[{id:'occ_retry',state:'failed',due:123,run_id:null,retry_eligible:true,last_error_code:'AUTOMATION_AUTH_REVOKED'}];
  calls.control.mockResolvedValue({});calls.read.mockResolvedValue(value);
  render(<OverviewAutomationReview value={value} onChange={vi.fn()}/>);
  fireEvent.click(screen.getByRole('button',{name:'Retry eligible execution'}));
  await waitFor(()=>expect(calls.control).toHaveBeenCalledWith('occ_retry',expect.objectContaining({action:'retry',request_key:expect.any(String)})));
});

it('replaces a definition only with a selected reviewed automation',async()=>{
  const value=prepared();value.activation={state:'active',schedule_id:'original',authorization_id:'consent',due:123};
  calls.list.mockResolvedValue({items:[{id:'replacement',kind:'schedule',state:'paused',name:'Edited purchasing report',request:{}}]});
  calls.control.mockResolvedValue({});calls.read.mockResolvedValue({...value,schedule_record:{id:'original',state:'cancelled'}});
  render(<OverviewAutomationReview value={value} onChange={vi.fn()}/>);
  fireEvent.click(screen.getByRole('button',{name:'Edit automation'}));
  await screen.findByRole('option',{name:'Edited purchasing report'});
  expect(calls.control).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText('Reviewed replacement'),{target:{value:'replacement'}});
  fireEvent.click(screen.getByRole('button',{name:'Replace reviewed definition'}));
  await waitFor(()=>expect(calls.control).toHaveBeenCalledWith('original',expect.objectContaining({action:'replace',replacement_id:'replacement',request_key:expect.any(String)})));
});

it('asks communication choices without technical instructions or automatic activation',()=>{
 const value=overviewResultSchema.parse({...prepared(),state:'clarification',composition_id:undefined,schedule:undefined,clarifications:[{field:'email_delivery',question:'Should I email the report or prepare a draft?',options:[{value:'send',label:'Email it to me'},{value:'draft',label:'Prepare a draft'}]},{field:'review_timing',question:'When would you like the reading session?',options:[{value:'after_ready',label:'After the report is ready'},{value:'fixed',label:'At a fixed time'}]}]});
 const answer=vi.fn();render(<OverviewAutomationReview value={value} onChange={vi.fn()} onAnswer={answer} compact/>);
 fireEvent.change(screen.getByLabelText('Should I email the report or prepare a draft?'),{target:{value:'send'}});
 fireEvent.change(screen.getByLabelText('When would you like the reading session?'),{target:{value:'fixed'}});
 fireEvent.change(screen.getByLabelText('Review start time'),{target:{value:'22:50'}});
 fireEvent.click(screen.getByRole('button',{name:'Continue to review'}));
 expect(answer).toHaveBeenCalledWith({email_delivery:'send',review_timing:'fixed',review_time:'22:50'});
 expect(calls.activate).not.toHaveBeenCalled();expect(screen.queryByText(/Calendar identity must be explicit/)).not.toBeInTheDocument();
});

it('shows recipient calendar and timing policy before recurring authorization',()=>{
 const value=overviewResultSchema.parse({...prepared(),communication_review:['Connected account: owner@example.com','Report recipient: owner@example.com','Review calendar: Primary calendar','Reading session: 30 minutes, starting 5 minutes after the report is ready.']});
 render(<OverviewAutomationReview value={value} onChange={vi.fn()}/>);
 expect(screen.getByLabelText('Email and Calendar review')).toHaveTextContent('owner@example.com');
 expect(screen.getByLabelText('Email and Calendar review')).toHaveTextContent('5 minutes after the report is ready');
 expect(screen.getByRole('button',{name:'Authorize and start schedule'})).toBeDisabled();expect(calls.activate).not.toHaveBeenCalled();
});
