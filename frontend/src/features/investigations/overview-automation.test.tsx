import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {beforeEach,describe,it,expect,vi} from 'vitest';
import {OverviewAutomationReview} from './OverviewAutomationReview';
import {overviewResultSchema,overviewStorageKey} from '@/api/overview-automation';
import {InputError} from '@/api/feedback';

const calls=vi.hoisted(()=>({activate:vi.fn(),read:vi.fn(),control:vi.fn()}));
vi.mock('next/navigation',()=>({usePathname:()=>'/app'}));
vi.mock('@/api/client',async importOriginal=>({...await importOriginal<typeof import('@/api/client')>(),api:{activateOverview:calls.activate,overviewIntent:calls.read,controlAutomation:calls.control}}));
vi.mock('@/api/state',()=>({useBackend:()=>({session:{auth:{subject:{workspace_id:'one',subject_id:'alice'}}},can:()=>true})}));
vi.mock('./ConnectedPlan',()=>({ConnectedPlan:({scheduled}:{scheduled:boolean})=><div>Existing workflow review {scheduled?'scheduled':'one time'}</div>,actionButton:'button'}));

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
