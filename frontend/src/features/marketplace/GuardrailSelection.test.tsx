import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
import {afterEach,it,expect,vi} from 'vitest';
import {api} from '@/api/client';
import {useBackend} from '@/api/state';
import {GuardrailSelection} from './GuardrailSelection';
afterEach(()=>{cleanup();vi.restoreAllMocks();});
it('selects a workflow without showing revisions and saves the server-resolved current pin',async()=>{
 useBackend.setState({session:{auth:{subject:{workspace_id:'client-subway',subject_id:'owner'}}} as never});
 const pages=vi.spyOn(api,'workflowsPage').mockResolvedValueOnce({items:[],next_cursor:'page1',has_more:true} as never).mockResolvedValueOnce({items:[{workflow_id:'later_draft',version:3,name:'Later draft',agents:[],status:'draft'}],next_cursor:null,has_more:false} as never);
 const pack={id:'mk_gr_injection',version:1,controls:['instruction_override_screening'],limitations:['Known patterns only']};
 const data={settings:{revision:0,packs:[]},packs:[pack],scope:{workflow_version:3}};
 const read=vi.spyOn(api,'executionPreferences').mockResolvedValue(data as never);
 const save=vi.spyOn(api,'saveExecutionPreferences').mockResolvedValue({...data,settings:{revision:1,packs:[{...pack,status:'Applied'}]}} as never);
 render(<GuardrailSelection packId="mk_gr_injection"/>);fireEvent.click(await screen.findByRole('button',{name:'Load more workflows'}));await screen.findByRole('option',{name:'Later draft'});
 expect(screen.queryByText(/v3/)).toBeNull();fireEvent.change(screen.getByLabelText('Guardrail workflow'),{target:{value:'later_draft'}});
 fireEvent.click(await screen.findByRole('button',{name:'Apply protections'}));
 await waitFor(()=>expect(save).toHaveBeenCalledWith({workflow_id:'later_draft',workflow_version:3,current_revision:true,expected_revision:0,packs:[{id:pack.id,version:1,controls:pack.controls}]}));
 expect(read).toHaveBeenCalledWith('later_draft',undefined,undefined);expect(pages).toHaveBeenLastCalledWith('page1');expect(await screen.findByText(/Protections saved to the current/)).toBeVisible();
});
it('gives an actionable issue for an approved workflow without saving protections',async()=>{
 vi.spyOn(api,'workflowsPage').mockResolvedValue({items:[{workflow_id:'approved',version:9,name:'Historical workflow',agents:[],status:'approved'}]} as never);const save=vi.spyOn(api,'saveExecutionPreferences');render(<GuardrailSelection packId="mk_gr_pii"/>);await screen.findByRole('option',{name:/Historical workflow/});fireEvent.change(screen.getByLabelText('Guardrail workflow'),{target:{value:'approved'}});expect(await screen.findByText(/Create a new editable/)).toBeVisible();expect(save).not.toHaveBeenCalled();
});
