import {beforeEach,afterEach,expect,it,vi} from 'vitest';
import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
import {webcrypto} from 'node:crypto';
import {api} from '@/api/client';
import {useBackend} from '@/api/state';
import {actionDocumentSchema} from '@/api/orchestration';
import {compositionViewSchema} from '@/api/compositions';
import fixture from '@/test/fixtures/orchestration.json';
import {dynamicView} from '../../../e2e/fixtures/dynamic-investigation';
import {QueryClarification} from './QueryClarification';
import {TaskResult} from './CompositionPanels';
const navigate=vi.hoisted(()=>vi.fn());
vi.mock('@/lib/navigation',()=>({useNavigate:()=>navigate}));
const question='Which complaint hours field and unit should be used?';
function data(){
 const doc=actionDocumentSchema.parse(fixture.document);const view=compositionViewSchema.parse(dynamicView('completed'));
 view.tasks[0]!.state='needs_input';view.tasks[0]!.result={classification:'query_clarification',state:'needs_input',summary:'This query needs a business definition before it can run.',missing_information:[question],records:[],rule_results:[],tool_receipts:[]};
 view.recovery={eligible:false,can_clarify:true,reason:question};return {doc,view};
}
beforeEach(()=>{
 vi.restoreAllMocks();navigate.mockReset();sessionStorage.clear();Object.defineProperty(globalThis,'crypto',{value:webcrypto,configurable:true});
 useBackend.setState({session:{auth:{subject:{workspace_id:'one',subject_id:'alice'},roles:['admin'],permissions:['workflow.plan'],scopes:['workspace:read'],decision:'allow'}}} as never);
});
afterEach(cleanup);
it('shows the saved definition question without invented statistics or receipts',()=>{
 const {view}=data();render(<TaskResult task={view.tasks[0]!}/>);
 expect(screen.getByText(question)).toBeVisible();expect(screen.getByText('Definition needed before querying')).toBeVisible();expect(screen.queryByText(/matching records|Connected tool results/)).not.toBeInTheDocument();
});
it('generates a new reviewed plan only after an explicit answer and preserves selected account',async()=>{
 const {doc,view}=data();const next={...doc,composition_id:'composition_clarified'};
 const create=vi.spyOn(api,'createActionPlan').mockResolvedValue(next);const execute=vi.spyOn(api,'request');
 render(<QueryClarification doc={doc} view={view}/>);
 const button=screen.getByRole('button',{name:'Generate clarified workflow'});expect(button).toBeDisabled();expect(create).not.toHaveBeenCalled();
 fireEvent.change(screen.getByLabelText('Business definition'),{target:{value:'Use tickets.hmr as the entered hour-meter reading in hours.'}});fireEvent.click(button);fireEvent.click(button);
 await waitFor(()=>expect(create).toHaveBeenCalledTimes(1));expect(create.mock.calls[0]![0]).toMatchObject({google_connection_id:doc.google_connection_id,automatic_inputs:true,client_id:doc.action_plan.scope.client_id});expect(create.mock.calls[0]![0]['objective']).toContain('Business definition supplied by the user: Use tickets.hmr');
 await waitFor(()=>expect(navigate).toHaveBeenCalledWith({to:'/app/workflows/investigate',search:{connected:'1',composition:'composition_clarified'}}));expect(execute).not.toHaveBeenCalled();
});
it('retains the persisted question on remount without automatically submitting',()=>{
 const {doc,view}=data();const create=vi.spyOn(api,'createActionPlan');const first=render(<QueryClarification doc={doc} view={view}/>);expect(screen.getByText(question)).toBeVisible();first.unmount();render(<QueryClarification doc={doc} view={view}/>);expect(screen.getByText(question)).toBeVisible();expect(create).not.toHaveBeenCalled();
});
