import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen} from '@testing-library/react';
import {AutomationProgress} from './AutomationProgress';
import {compositionViewSchema} from '@/api/compositions';
import {dynamicView} from '../../../e2e/fixtures/dynamic-investigation';
afterEach(cleanup);
function run() {
 const result=compositionViewSchema.parse(dynamicView('completed')).run!;
 result.status='blocked';result.error_code='ADAPTIVE_FALSE_COMPLETION';
 result.action_instances={mail:{state:'completed',verified_receipt:true,output:{message_id:'synthetic-message'}}};
 return result;
}
it('shows delivered mail and unfinished processing without raw codes or false success',()=>{
 const details=vi.fn();render(<AutomationProgress run={run()} onUpdated={vi.fn()} onDetails={details}/>);
 expect(screen.getByRole('status')).toHaveTextContent('Email sent. This run needs attention.');
 expect(screen.queryByText(/ADAPTIVE_FALSE_COMPLETION|Investigation blocked|Plan revision|Objective satisfied/)).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'View execution details'}));expect(details).toHaveBeenCalledOnce();
});
it('only confirms delivered email from a completed verified receipt',()=>{
 const current=run();current.action_instances!['mail']!.verified_receipt=false;
 render(<AutomationProgress run={current} onUpdated={vi.fn()} onDetails={vi.fn()}/>);
 expect(screen.getByRole('status')).not.toHaveTextContent('Email sent');
});
it('shows success only when the saved execution completed',()=>{
 const current=run();current.status='completed';current.error_code=null;
 render(<AutomationProgress run={current} onUpdated={vi.fn()} onDetails={vi.fn()}/>);
 expect(screen.getByRole('status')).toHaveTextContent('Email sent. This run is complete.');
});
it('keeps required business input actionable without verbose diagnostic panels',()=>{
 const current=run();current.status='running';current.adaptive={objective:'Synthetic recurring report',status:'waiting_for_input',revision:1,turns:1,assessment:null,pending_wait:{wait_id:'synthetic',requests:[{key:'threshold',reason:'Choose the review threshold',schema:{type:'number'}}]},decisions:[],revisions:[],blocker:'PRIVATE_DIAGNOSTIC'};
 render(<AutomationProgress run={current} onUpdated={vi.fn()} onDetails={vi.fn()}/>);
 expect(screen.getByLabelText('Choose the review threshold')).toBeVisible();
 expect(screen.getByRole('button',{name:'Save input and resume'})).toBeVisible();
 expect(screen.queryByText('PRIVATE_DIAGNOSTIC')).not.toBeInTheDocument();
});
