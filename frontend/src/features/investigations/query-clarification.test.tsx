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
it('shows an execution limitation without asking the saved question or inventing results',()=>{
 const {view}=data();render(<TaskResult task={view.tasks[0]!}/>);
 expect(screen.queryByText(question)).toBeNull();expect(screen.getByText('Evidence limitations')).toBeVisible();
 expect(screen.queryByText(/matching records|Connected tool results/)).not.toBeInTheDocument();
});
it('does not render an answer form or submit replacement work',()=>{
 const {doc,view}=data();const create=vi.spyOn(api,'createActionPlan');const execute=vi.spyOn(api,'request');
 render(<QueryClarification doc={doc} view={view}/>);
 expect(screen.getByRole('heading',{name:'Query blocked'})).toBeVisible();
 expect(screen.queryByRole('textbox')).toBeNull();expect(screen.queryByText(question)).toBeNull();
 expect(screen.queryByRole('button')).toBeNull();expect(create).not.toHaveBeenCalled();expect(execute).not.toHaveBeenCalled();
});
it('keeps the blocked status on remount without automatically submitting',()=>{
 const {doc,view}=data();const create=vi.spyOn(api,'createActionPlan');
 const first=render(<QueryClarification doc={doc} view={view}/>);first.unmount();
 render(<QueryClarification doc={doc} view={view}/>);
 expect(screen.getByRole('heading',{name:'Query blocked'})).toBeVisible();expect(create).not.toHaveBeenCalled();
});
