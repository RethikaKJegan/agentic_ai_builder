import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {api,type Session,type RunRecord} from '@/api/client';
import {useBackend} from '@/api/state';
import {StopRun} from './StopRun';
const run:RunRecord={run_id:'run_control',workflow_id:'workflow',workflow_version:1,status:'running',approvals:[]};
beforeEach(()=>useBackend.setState({session:{auth:{decision:'allow',permissions:['workflow.execute']}} as Session}));
afterEach(()=>{cleanup();vi.restoreAllMocks();});
it('refreshes only after durable stop confirmation',async()=>{
  const refresh=vi.fn();let complete!:(value:RunRecord)=>void;
  vi.spyOn(api,'stopRun').mockImplementation(()=>new Promise(resolve=>{complete=resolve;}));
  render(<StopRun run={run} onStopped={refresh}/>);fireEvent.click(screen.getByRole('button',{name:'Stop run'}));
  expect(screen.getByRole('button',{name:'Stopping…'})).toBeDisabled();expect(refresh).not.toHaveBeenCalled();
  complete({...run,status:'cancelled'});await waitFor(()=>expect(refresh).toHaveBeenCalledOnce());
});
it('hides stop for terminal runs and viewers',()=>{
  render(<StopRun run={{...run,status:'completed'}} onStopped={()=>{}}/>);expect(screen.queryByRole('button')).toBeNull();cleanup();
  useBackend.setState({session:{auth:{decision:'allow',permissions:['runs.view']}} as Session});
  render(<StopRun run={run} onStopped={()=>{}}/>);expect(screen.queryByRole('button')).toBeNull();
});
