"use client";
import { useState } from 'react';
import { api } from '@/api/client';
import { useBackend } from '@/api/state';
import { useMesh } from '@/domain/store';
import { useNavigate } from '@/lib/navigation';
import { GoogleAccountSelect } from './GoogleWorkflowConnection';
import { ApiFeedback } from './ApiFeedback';
const samples:Record<string,unknown>={
  google_sheets_read_rows:{spreadsheet_id:'PASTE_SPREADSHEET_ID',range:'Sheet1!A1:D10'},
  google_sheets_upsert_record:{spreadsheet_id:'PASTE_SPREADSHEET_ID',range:'Sheet1!A1:D100',identity:'test-record-1',fields:{status:'Checked'}},
  extension_sheets_discover:{spreadsheet_id:'PASTE_SPREADSHEET_ID'},
  extension_sheets_create:{project_id:'google_demo',creation_key:'test_sheet_1',title:'Google connection test',tabs:[{title:'Checks',headers:['id','status']}]},
  extension_sheets_add_tabs:{project_id:'google_demo',creation_key:'test_tab_1',spreadsheet_id:'PASTE_SPREADSHEET_ID',tabs:[{title:'Checks',headers:['id','status']}]},
  extension_mail_search:{query:'in:inbox',limit:5},
  extension_mail_message:{message_id:'PASTE_GMAIL_MESSAGE_ID'},
  extension_mail_thread:{thread_id:'PASTE_GMAIL_THREAD_ID'},
  extension_mail_draft:{to:'ENTER_TEST_RECIPIENT',subject:'Google connection test',body:'This is a test draft.'},
  extension_mail_send:{to:'ENTER_TEST_RECIPIENT',subject:'Google connection test',body:'This is a test message.'},
  extension_mail_reply:{message_id:'PASTE_GMAIL_MESSAGE_ID',body:'This is a test reply.'},
  extension_calendar_list:{calendar_id:'primary',limit:5},
  extension_calendar_create:{calendar_id:'primary',event:{summary:'Google connection test',start:{dateTime:'2026-11-01T10:00:00+05:30',timeZone:'Asia/Kolkata'},end:{dateTime:'2026-11-01T10:15:00+05:30',timeZone:'Asia/Kolkata'}}},
  extension_calendar_update:{calendar_id:'primary',event_id:'PASTE_TEST_EVENT_ID',event:{summary:'Updated Google connection test',start:{dateTime:'2026-11-01T11:00:00+05:30',timeZone:'Asia/Kolkata'},end:{dateTime:'2026-11-01T11:15:00+05:30',timeZone:'Asia/Kolkata'}}},
  extension_calendar_cancel:{calendar_id:'primary',event_id:'PASTE_TEST_EVENT_ID'},
};
export function GoogleToolChecks(){
  const backend=useBackend();const navigate=useNavigate();
  const [connection,setConnection]=useState('');const [tool,setTool]=useState('');const [input,setInput]=useState('{}');const [targets,setTargets]=useState('[]');const [busy,setBusy]=useState(false);const [error,setError]=useState<Error>();
  const tools=backend.tools.filter(item=>item.definition.availability==='enabled'&&Object.hasOwn(samples,item.tool_id));
  const create=async()=>{if(busy)return;setBusy(true);setError(undefined);try{const result=await api.googleToolCheckDraft(connection,tool,JSON.parse(input),JSON.parse(targets));useMesh.getState().acceptWorkflow(result.workflow);navigate({to:'/app/workflows/$id',params:{id:result.workflow.workflow_id}});}catch(e){setError(e instanceof Error?e:new Error('The test draft could not be created.'));}finally{setBusy(false);}};
  return <details className="mt-5 rounded-xl border p-4"><summary className="cursor-pointer text-sm font-semibold">Test Google tools with a workflow</summary><div className="mt-4 space-y-4"><p className="text-xs text-muted-foreground">Create a draft only. Review its exact inputs, then validate, approve, publish and run it using the existing workflow controls. Write steps retain their approval gate.</p><GoogleAccountSelect value={connection} onChange={setConnection} disabled={busy}/><label className="block text-xs font-medium">Registered operation<select aria-label="Google test operation" value={tool} onChange={e=>{setTool(e.target.value);setInput(JSON.stringify(samples[e.target.value]??{},null,2));}} className="mt-1 w-full rounded-lg border bg-background p-2"><option value="">Choose an operation</option>{tools.map(t=><option key={t.tool_id} value={t.tool_id}>{t.definition.capability} · {t.tool_id}</option>)}</select></label>{tool&&<><label className="block text-xs font-medium">Exact operation inputs<textarea aria-label="Google test inputs" rows={10} value={input} onChange={e=>setInput(e.target.value)} className="mt-1 w-full rounded-lg border p-3 font-mono text-xs"/></label><details className="text-xs"><summary className="cursor-pointer">Accepted input schema</summary><pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap">{JSON.stringify(tools.find(t=>t.tool_id===tool)?.definition.input_schema,null,2)}</pre></details></>}{tool==='google_sheets_upsert_record'&&<label className="block text-xs">Reviewed Sheet write targets (JSON)<textarea aria-label="Google test sheet targets" rows={5} value={targets} onChange={e=>setTargets(e.target.value)} className="mt-1 w-full rounded-lg border p-2 font-mono"/></label>}<button disabled={busy||!connection||!tool||!backend.can('workflow.edit')} onClick={()=>void create()} className="rounded-lg bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-40">{busy?'Creating draft…':'Create tool-check draft'}</button><ApiFeedback error={error}/></div></details>;
}
