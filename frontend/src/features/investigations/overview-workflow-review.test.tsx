import {render,screen,waitFor} from '@testing-library/react';
import {beforeEach,it,expect,vi} from 'vitest';
import {OverviewWorkflowReview} from './OverviewWorkflowReview';

const calls=vi.hoisted(()=>({read:vi.fn(),subject:{workspace_id:'one',subject_id:'alice'}}));
vi.mock('@/api/client',async original=>({...await original<typeof import('@/api/client')>(),api:{overviewIntent:calls.read}}));
vi.mock('@/api/state',()=>({useBackend:()=>({session:{auth:{subject:calls.subject}}})}));
vi.mock('./OverviewAutomationReview',()=>({OverviewAutomationReview:({value,initialRunId,onRun}:{value:{composition_id:string};initialRunId?:string;onRun:(id:string)=>void})=><button onClick={()=>onRun('run_next')}>Review {value.composition_id} {initialRunId}</button>}));

const saved=()=>({version:'overview-intent-v1',state:'prepared',request_key:'request_saved',composition_id:'composition_saved',workspace:{workspace_id:'one',subject_id:'alice'}});
beforeEach(()=>{vi.clearAllMocks();calls.subject={workspace_id:'one',subject_id:'alice'};});

it('restores the saved review and selected run without preparing or executing work',async()=>{
  calls.read.mockResolvedValue(saved());const onRun=vi.fn();
  render(<OverviewWorkflowReview requestKey="request_saved" compositionId="composition_saved" runId="run_saved" onRun={onRun}/>);
  await screen.findByRole('button',{name:'Review composition_saved run_saved'});
  expect(calls.read).toHaveBeenCalledExactlyOnceWith({operation:'get',request_key:'request_saved'});
  screen.getByRole('button').click();expect(onRun).toHaveBeenCalledWith('run_next');
});

it.each([{composition_id:'other'}, {request_key:'other'}, {workspace:{workspace_id:'other',subject_id:'alice'}}, {workspace:{workspace_id:'one',subject_id:'bob'}}])('rejects a mismatched saved review %j',async change=>{
  calls.read.mockResolvedValue({...saved(),...change});
  render(<OverviewWorkflowReview requestKey="request_saved" compositionId="composition_saved" onRun={vi.fn()}/>);
  await screen.findByText(/does not match the workflow/);
  expect(screen.queryByText(/Review composition_saved/)).toBeNull();
});

it('discards a stale response when another request opens',async()=>{
  let finish!:(value:ReturnType<typeof saved>)=>void;
  calls.read.mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve;})).mockResolvedValue({...saved(),request_key:'request_new',composition_id:'composition_new'});
  const {rerender}=render(<OverviewWorkflowReview requestKey="request_saved" compositionId="composition_saved" onRun={vi.fn()}/>);
  rerender(<OverviewWorkflowReview requestKey="request_new" compositionId="composition_new" onRun={vi.fn()}/>);
  await screen.findByRole('button',{name:'Review composition_new'});
  finish(saved());
  await waitFor(()=>expect(screen.queryByText(/Review composition_saved/)).toBeNull());
});
