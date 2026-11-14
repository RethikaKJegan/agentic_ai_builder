import {describe,it,expect} from 'vitest';
import {render,screen,fireEvent} from '@testing-library/react';
import {compositionViewSchema,taskEdges} from '@/api/compositions';
import {CompositionInspector,CompositionReport,ToolReceipt} from './CompositionPanels';
import {parseOperationInputs,compositionActionInputs,emptyCompositionOptions,restoreCompositionOptions} from './CompositionOptions';
import {dynamicView} from '../../../e2e/fixtures/dynamic-investigation';

describe('dynamic business investigations',()=>{
 it('uses actual task dependencies for parallel reads and analysis',()=>{
  const view=compositionViewSchema.parse(dynamicView());const edges=taskEdges(view.tasks);
  expect(edges).toContainEqual({id:'task_1-task_3',source:'task_1',target:'task_3'});
  expect(edges.some(e=>e.source==='task_1'&&e.target==='task_2')).toBe(false);
 });
 it('keeps raw field paths and knowledge hashes behind technical details',()=>{
  render(<CompositionInspector view={compositionViewSchema.parse(dynamicView())} section="knowledge" onClose={()=>{}}/>);
  expect(screen.getByText('Engine')).toBeVisible();expect(screen.getByText(/saved_private_hash/)).not.toBeVisible();
  fireEvent.click(screen.getByText('Technical details'));expect(screen.getByText(/private_symptom_field/)).toBeVisible();
 });
 it('shows persisted source records and report results',()=>{
  render(<CompositionReport view={compositionViewSchema.parse(dynamicView('completed'))}/>);
  expect(screen.getByRole('heading',{name:'Investigation completed'})).toBeVisible();expect(screen.getByText(/Comparison completed using/)).toBeVisible();
  expect(screen.getByRole('heading',{name:'Supporting source records'})).toBeVisible();
 });
 it('does not equate completed execution with evidence readiness',()=>{
  const view=compositionViewSchema.parse(dynamicView('completed'));view.tasks[2]!.state='needs_input';view.tasks[2]!.result!.missing_information=['physical_identity'];
  render(<CompositionReport view={view}/>);expect(screen.getByRole('heading',{name:'Investigation completed — additional evidence required'})).toBeVisible();
 });
 it('isolates memory and recovery from business conclusions',()=>{
  render(<CompositionInspector view={compositionViewSchema.parse(dynamicView('completed'))} section="memory" onClose={()=>{}}/>);
  expect(screen.getByText(/does not supply business facts or permissions/)).toBeVisible();
  expect(screen.getByText(/completed_tasks/)).not.toBeVisible();fireEvent.click(screen.getByText('Scoped working memory'));expect(screen.getByText(/completed_tasks/)).toBeVisible();
 });
 it('rejects malformed task and run responses',()=>{expect(compositionViewSchema.safeParse({...dynamicView(),tasks:[{id:'fake',state:'completed'}]}).success).toBe(false);});
 it('requires explicit typed operation fields',()=>{
  const schema={type:'object',required:['to','event'],properties:{to:{type:'string'},event:{type:'object',required:['summary'],properties:{summary:{type:'string'},hours:{type:'integer'}}}}};
  expect(()=>parseOperationInputs(schema,{})).toThrow(/Provide To/);
  expect(parseOperationInputs(schema,{'to':'person@example.test','event.summary':'Inspection','event.hours':'2'})).toEqual({to:'person@example.test',event:{summary:'Inspection',hours:2}});
  expect(()=>parseOperationInputs(schema,{'to':'p','event.summary':'s','event.hours':'not a number'})).toThrow(/valid number/);
 });
 it('never infers a tool or resources when none are selected',()=>{
  expect(compositionActionInputs(emptyCompositionOptions,[])).toEqual({});
  expect(()=>compositionActionInputs({...emptyCompositionOptions,tool:'unregistered'},[])).toThrow(/no longer available/);
 });
});

 it('restores the pinned account and package instead of silently resetting details',()=>{
  expect(restoreCompositionOptions({google_connection_id:'account_owned',client_package_id:'retail',client_package_revision:3},[])).toMatchObject({google:'account_owned',packageId:'retail',packageRevision:3});
 });

it('exposes actual connected-read receipt counts for checking a tool invocation',()=>{
 const view=compositionViewSchema.parse(dynamicView('completed'));
 view.tasks[0]!.result!.tool_receipts=[{tool_id:'extension_mail_search',receipt:{returned_messages:1,messages_identifiers:[{id:'message_1'}]}}];
 render(<CompositionReport view={view}/>);
 fireEvent.click(screen.getByText('Tool response receipt'));
 expect(screen.getByText(/returned_messages/)).toBeVisible();
 expect(screen.getByText(/message_1/)).toBeVisible();
});

it('explains citation validation separately from agent identity and service failures',async()=>{
 const {compositionFailureMessage}=await import('@/api/compositions');
 expect(compositionFailureMessage('INVESTIGATION_AGENT_REFERENCE')).toBe('Execution stopped because the agent summary contained an unsupported or missing source citation.');
 expect(compositionFailureMessage('AGENT_REGISTRATION_REQUIRED')).toContain('agent registration required');
 expect(compositionFailureMessage('INVOCATION_FAILED')).toContain('internal service failure');
});


it('shows a database read and actual record count instead of an empty receipt',()=>{
 render(<ToolReceipt value={{tool_id:'business_retrieve_evidence',receipt:{returned_records:3,collections:['tickets','jointinspectionreports']}}}/>);
 expect(screen.getByText('Database read')).toBeVisible();
 expect(screen.getByText('3 record(s) retrieved.')).toBeVisible();
 expect(screen.getByText(/Source collections: tickets, jointinspectionreports/)).toBeVisible();
});
it('reports genuine zero matches without inventing records',()=>{
 render(<ToolReceipt value={{tool_id:'business_retrieve_evidence',receipt:{returned_records:0,collections:[]}}}/>);
 expect(screen.getByText('No matching records.')).toBeVisible();
 expect(screen.queryByText('3 record(s) retrieved.')).toBeNull();
});
it('uses the recorded task tool for legacy receipts without inventing receipt details',()=>{
 render(<ToolReceipt value={{tool_id:null,receipt:{}}} fallbackTool="business_retrieve_evidence"/>);
 expect(screen.getByText('Database read')).toBeVisible();
 expect(screen.getByText('No receipt details were recorded for this tool.')).toBeVisible();
 expect(screen.queryByText('Tool response receipt')).toBeNull();
});

it('shows pending tool state instead of rendering an empty provider receipt',()=>{
 const view=compositionViewSchema.parse(dynamicView('completed'));
 view.run!.actions=[{node_id:'pending_tool',label:'Pending database query',state:'pending',inputs:{},receipt:{}}];
 render(<CompositionReport view={view}/>);
 expect(screen.getByText('Tool has not returned a result yet.')).toBeVisible();
 expect(screen.queryByText('Provider receipt')).toBeNull();
});

it('distinguishes unattached individual records from aggregate query evidence',()=>{
 const view=compositionViewSchema.parse(dynamicView('completed'));
 view.tasks.forEach(task=>{if(task.result)task.result.records=[];});
 render(<CompositionReport view={view}/>);
 expect(screen.getByText('No individual records are attached to this report. Aggregate query results are shown separately.')).toBeVisible();
 expect(screen.queryByText('No mapped records have been retrieved.')).toBeNull();
});

it('explains the real goal and dependencies when the plan has no coordinator agent',()=>{
 const view=compositionViewSchema.parse(dynamicView());view.master=null;
 render(<CompositionInspector view={view} section="coordinator" onClose={()=>{}}/>);
 expect(screen.getByText(view.objective)).toBeVisible();expect(screen.getByText('Task dependencies')).toBeVisible();expect(screen.getByText(/This node represents the saved workflow plan/)).toBeVisible();expect(screen.queryByText('null')).toBeNull();
});
it('renders genuine web snippets and extracted text safely as separate evidence',()=>{
 render(<ToolReceipt value={{tool_id:'supplier_web_search',receipt:{web_sources:[{title:'Actual source',url:'https://example.com/path',snippet:'<script>not executable</script>'},{url:'https://example.com/page',text:'Actual extracted text'}]}}}/>);
 expect(screen.getByRole('link',{name:'https://example.com/path'})).toHaveAttribute('href','https://example.com/path');expect(screen.getByText('<script>not executable</script>')).toBeVisible();expect(document.querySelector('script')).toBeNull();expect(screen.getByText(/Search snippet only/)).toBeVisible();fireEvent.click(screen.getByText('Extracted page content'));expect(screen.getByText('Actual extracted text')).toBeVisible();
});


describe('backward compatible findings and independent status',()=>{
 it('renders plain text findings from existing connected workflows',()=>{
  const raw=dynamicView('completed');raw.tasks[2]!.result!.findings=['Plain saved finding'] as never;
  const view=compositionViewSchema.parse(raw);render(<CompositionReport view={view}/>);
  expect(screen.getByText('Plain saved finding')).toBeVisible();
  expect(view.tasks[2]!.result!.findings![0]!.references).toEqual([]);
 });
 it.each([undefined,[]])('accepts missing or empty optional findings: %s',findings=>{
  const raw=dynamicView('completed');raw.tasks[2]!.result!.findings=findings as never;
  expect(compositionViewSchema.parse(raw).run?.status).toBe('completed');
 });
 it('isolates malformed optional details and retains the terminal run status',()=>{
  const raw=dynamicView('completed');raw.tasks[2]!.result!.findings=[{statement:55}] as never;
  const view=compositionViewSchema.parse(raw);
  expect(view.run?.status).toBe('completed');expect(view.tasks[2]!.detail_error).toContain('unsupported format');
  expect(view.tasks[0]!.result).not.toBeNull();
  render(<CompositionInspector view={view} section={view.tasks[2]!.id} onClose={()=>{}}/>);
  expect(screen.getByRole('alert')).toHaveTextContent('saved execution status');
 });
 it('continues rejecting invalid task identities outside optional details',()=>{
  const raw=dynamicView('completed');raw.tasks[0]!.id=22 as never;
  expect(compositionViewSchema.safeParse(raw).success).toBe(false);
 });
});

it('never lets an older status response replace a newer revision of the same run',async()=>{
 const {newerComposition}=await import('@/api/compositions');
 const newest=compositionViewSchema.parse(dynamicView('completed'));newest.sequence=12;
 const older=structuredClone(newest);older.run!.status='running';older.sequence=11;
 expect(newerComposition(newest,older)).toBe(newest);
 older.run!.run_id='new_run';expect(newerComposition(newest,older)).toBe(older);
});
