import { render,screen,fireEvent,waitFor } from '@testing-library/react';
import { describe,it,expect,vi,beforeEach } from 'vitest';
import { AgentBehaviourPanel } from './AgentBehaviourPanel';
const api=vi.hoisted(()=>({executionPreferences:vi.fn(),saveExecutionPreferences:vi.fn()}));
vi.mock('@/api/client',()=>({api}));
vi.mock('@/api/state',()=>({useBackend:(selector:(s:unknown)=>unknown)=>selector({status:'connected',session:{auth:{subject:{workspace_id:'tenant',subject_id:'owner'}}}})}));
vi.mock('@/features/workflows/ApiFeedback',()=>({ApiFeedback:()=>null}));
const saved={settings:{revision:0,behaviours:{formalTone:false,conciseResponses:false,clarifyUncertainty:false,requireSupportingEvidence:false}}};
beforeEach(()=>{vi.clearAllMocks();api.executionPreferences.mockResolvedValue(structuredClone(saved));api.saveExecutionPreferences.mockImplementation(async value=>({settings:{revision:1,behaviours:value.behaviours}}));});
describe('Persisted execution behavior',()=>{
 it('shows only supported controls and ignores obsolete browser preferences',async()=>{localStorage.setItem('mesh-local-drafts-v1',JSON.stringify({agentBehaviourPreferences:{preferredLanguage:true,strictOutputFormat:true,screenAbusiveLanguage:true}}));render(<AgentBehaviourPanel policies={[]} onViewLimits={()=>{}}/>);await waitFor(()=>expect(screen.getByRole('switch',{name:'Formal tone'})).not.toBeDisabled());expect(screen.getAllByRole('switch')).toHaveLength(4);expect(screen.queryByRole('switch',{name:'Preferred language'})).toBeNull();expect(screen.queryByText('Strict output format')).toBeNull();expect(screen.queryByRole('switch',{name:'Screen abusive language'})).toBeNull();});
 it('saves actual effective values to the authenticated backend',async()=>{render(<AgentBehaviourPanel policies={[]} onViewLimits={()=>{}}/>);await waitFor(()=>expect(screen.getByRole('switch',{name:'Formal tone'})).not.toBeDisabled());fireEvent.click(screen.getByRole('switch',{name:'Formal tone'}));fireEvent.click(screen.getByRole('button',{name:'Apply preferences'}));await waitFor(()=>expect(api.saveExecutionPreferences).toHaveBeenCalledWith({expected_revision:0,behaviours:{...saved.settings.behaviours,formalTone:true}}));expect(await screen.findByText('Execution preferences saved on the server.')).toBeInTheDocument();});
});
