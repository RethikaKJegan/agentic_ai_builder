import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {AdaptiveProgress} from './AdaptiveProgress';
import {api,type RunRecord} from '@/api/client';
afterEach(()=>{cleanup();vi.restoreAllMocks();});
function run():RunRecord {
  return {run_id:'run_subway',workflow_id:'subway',workflow_version:1,status:'running',approvals:[],
    adaptive:{objective:'Investigate purchasing exceptions',status:'waiting_for_input',revision:2,turns:4,assessment:null,
      pending_wait:{wait_id:'business_wait',requests:[{key:'threshold',reason:'What analytical threshold should be used?',schema:{type:'number',minimum:0}}]},
      decisions:[{decision:'request_input',rationale:'No authoritative company threshold exists.',revision:2}],revisions:[]}};
}
it('shows the objective and persists typed input for the exact run and wait',async()=>{
  const current=run();const update=vi.fn();
  const request=vi.spyOn(api,'adaptiveInput').mockResolvedValue({run:current});
  render(<AdaptiveProgress run={current} onUpdated={update}/>);
  expect(screen.getByRole('status')).toHaveTextContent('Waiting for business input · Plan revision 2');
  fireEvent.change(screen.getByLabelText('What analytical threshold should be used?'),{target:{value:'125'}});
  fireEvent.click(screen.getByRole('button',{name:'Save input and resume'}));
  await waitFor(()=>expect(update).toHaveBeenCalledOnce());
  expect(request).toHaveBeenCalledExactlyOnceWith('run_subway','business_wait',{threshold:125});
});
it('keeps blocked evidence gaps visible without claiming a satisfied objective',()=>{
  const current=run();current.status='blocked';current.adaptive!.status='blocked';current.adaptive!.pending_wait=null;
  current.adaptive!.blocker='ADAPTIVE_OBJECTIVE_BLOCKED';
  current.adaptive!.assessment={objective:current.adaptive!.objective,requirements:[{id:'cause',description:'Establish a supported cause',status:'unsatisfied',evidence_ids:[]}],
    findings:[],gaps:[{id:'unknown-cause',description:'Purchasing correlation does not establish causality.',blocking:true}],
    source_limitations:['No authoritative budget policy was supplied.'],invalid_assumptions:[],recoverable_failures:[],rule_evaluations:[],completion_eligible:false};
  render(<AdaptiveProgress run={current} onUpdated={vi.fn()}/>);
  expect(screen.getByRole('status')).toHaveTextContent('Investigation blocked');
  expect(screen.getByText('Blocking gap: Purchasing correlation does not establish causality.')).toBeVisible();
  expect(screen.queryByRole('button',{name:'Save input and resume'})).not.toBeInTheDocument();
});
