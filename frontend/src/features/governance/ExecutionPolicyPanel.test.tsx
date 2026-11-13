import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {api,type Session} from '@/api/client';
import {useBackend} from '@/api/state';
import {ExecutionPolicyPanel} from './ExecutionPolicyPanel';
const value={revision:3,scope:'workspace',enforcement:'Intersection',cost_accounting:'Estimated costs only.',policy:{read_only:false,require_action_approval:false,restricted_tools:[],restricted_sources:[],limits:{},model_timeout_seconds:null,tool_timeout_seconds:null,delegation_timeout_seconds:null,step_timeout_seconds:null}};
beforeEach(()=>{useBackend.setState({status:'connected',session:{auth:{decision:'allow',subject:{workspace_id:'test',subject_id:'admin'},roles:['admin'],permissions:['workflow.edit','runs.view'],scopes:['workspace:write']}} as Session});vi.spyOn(api,'governancePolicy').mockResolvedValue(structuredClone(value));});
afterEach(()=>{cleanup();vi.restoreAllMocks();});
it('saves executable settings with the server revision and shows confirmed persistence',async()=>{
  vi.spyOn(api,'saveGovernancePolicy').mockImplementation(async body=>({...value,...body,revision:4}));
  render(<ExecutionPolicyPanel/>);
  fireEvent.click(await screen.findByRole('switch',{name:'Read-only execution'}));
  fireEvent.change(screen.getByLabelText('Run duration (seconds)'),{target:{value:'60'}});
  fireEvent.click(screen.getByRole('button',{name:'Save changes'}));
  await screen.findByText('Safety settings saved.');
  expect(api.saveGovernancePolicy).toHaveBeenCalledWith({revision:3,policy:expect.objectContaining({read_only:true,limits:{timeout_seconds:60}})});
  expect(screen.getByRole('button',{name:'Save changes'})).toBeDisabled();
});
it('does not grant server administration from a local role',async()=>{
  useBackend.setState({session:{...useBackend.getState().session!,auth:{...useBackend.getState().session!.auth,roles:['viewer'],permissions:['runs.view']}}});
  render(<ExecutionPolicyPanel/>);
  expect(await screen.findByRole('switch',{name:'Read-only execution'})).toBeDisabled();
  expect(screen.queryByRole('button',{name:'Save changes'})).toBeNull();
});
it('retains unsaved changes when a revision conflict rejects the save',async()=>{
  vi.spyOn(api,'saveGovernancePolicy').mockRejectedValue(new Error('Policy changed. Refresh before saving.'));
  render(<ExecutionPolicyPanel/>);fireEvent.click(await screen.findByRole('switch',{name:'Read-only execution'}));
  fireEvent.click(screen.getByRole('button',{name:'Save changes'}));
  await waitFor(()=>expect(screen.getByRole('alert')).toBeVisible());
  expect(screen.getByRole('switch',{name:'Read-only execution'})).toBeChecked();
  expect(screen.getByText('Unsaved changes')).toBeVisible();
});
