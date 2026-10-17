"""Automatic inputs use real workspace persistence and offline metered CrewAI."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from planner import PlannerService
from planner.provider import RuleBasedStructuredOutputProvider
from runtime.crew import CrewAdapter, CrewExecutor
from runtime.model import BoundedLLM
from workflow_api.source_context import planning_context, knowledge_documents, MAX_CONTEXT
from workflow_api.storage import WorkflowStore
from workflow_api.service import WorkflowService
from workflow_api.live_providers import LivePlannerProvider

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def store(tmp_path):
 return WorkflowStore(tmp_path/'sources.sqlite3')

def save(store,source_id,document,workspace='local-workspace'):
 with store.transaction() as db:
  db.execute('INSERT INTO knowledge_sources VALUES (?,?,?,?) ON CONFLICT(source_id) DO UPDATE SET document=excluded.document',
             (workspace,source_id,json.dumps(document),'2026-10-17'))

def auth():
 return dict(subject=dict(subject_id='operator',workspace_id='local-workspace'),roles=['admin'],permissions=['workflow.plan','workflow.view'],scopes=['workspace:read'],decision='allow')

def test_workspace_context_overrides_client_evidence_and_excludes_other_workspace(store):
 save(store,'policy',{'title':'Support policy','content':'Return within 30 days.'})
 save(store,'other',{'content':'PRIVATE OTHER WORKSPACE'},'other-workspace')
 save(store,'disabled',{'status':'disabled','content':'obsolete'})
 save(store,'link',{'url':'https://example.com/handbook'})
 context=planning_context(store,auth(),{'workspace_knowledge':[{'content':'FORGED'}],'workspace_sources':[{'spreadsheet_id':'FORGED'}]})
 assert {item['source_id'] for item in context['workspace_knowledge']}=={'policy','link'}
 assert 'PRIVATE OTHER WORKSPACE' not in json.dumps(context) and 'FORGED' not in json.dumps(context)
 assert next(item for item in context['workspace_knowledge'] if item['source_id']=='link')['content_available'] is False
 assert context['workspace_sources']==[]
 restricted=auth();restricted['permissions']=['workflow.plan']
 assert planning_context(store,restricted,{})['workspace_knowledge']==[]

def test_context_is_bounded_and_secret_documents_are_not_model_input(store):
 for index in range(30):save(store,f'source_{index:02}',{'content':'x'*20000})
 documents=knowledge_documents(store,'local-workspace')
 assert len(documents)<=20
 assert sum(len(json.dumps(document)) for document in documents)<=MAX_CONTEXT
 assert all(len(document['content'])<=12000 for document in documents)
 save(store,'aaa_secret',{'content':'must not leak','api_key':'sk-not-a-real-key-but-secret'})
 assert all(item['source_id']!='aaa_secret' for item in knowledge_documents(store,'local-workspace'))

def test_published_source_candidates_do_not_include_other_workspace_or_drafts(store):
 workflow=RuleBasedStructuredOutputProvider().generate('Summarize inventory',{})
 workflow.update(status='published',workflow_id='wf_sources')
 workflow['metadata']['sheet_read_targets']=[{'spreadsheet_id':'saved_sheet','range':'Inventory!A:D'}]
 workflow['metadata']['sheet_catalog']=[{'spreadsheet_id':'catalog_sheet','tables':[]}]
 workflow['nodes'][-1]['configuration']={'input_mapping':{'spreadsheet_id':repr('mapped_sheet'),'range':repr('Support!A:C')}}
 with store.transaction() as db:
  store.put(db,'local-workspace',workflow)
  other=deepcopy(workflow);other['workflow_id']='other';other['metadata']['sheet_read_targets'][0]['spreadsheet_id']='OTHER'
  store.put(db,'other-workspace',other)
  draft=deepcopy(other);draft['workflow_id']='draft';draft['status']='draft';draft['metadata']['sheet_read_targets'][0]['spreadsheet_id']='DRAFT'
  store.put(db,'local-workspace',draft)
 sources=planning_context(store,auth(),{})['workspace_sources']
 assert sources==[{'spreadsheet_id':'saved_sheet','range':'Inventory!A:D','provider_id':'google_sheets'},
                  {'spreadsheet_id':'catalog_sheet','provider_id':'google_sheets'},
                  {'spreadsheet_id':'mapped_sheet','range':'Support!A:C','provider_id':'google_sheets'}]

def test_real_planning_boundary_uses_knowledge_and_retry_survives_knowledge_change(store):
 calls=[]
 class Provider:
  def generate(self,objective,context):
   calls.append(deepcopy(context));return RuleBasedStructuredOutputProvider().generate(objective,context)
 save(store,'policy',{'content':'OLD POLICY'})
 service=WorkflowService(store,PlannerService(Provider()))
 request=dict(request_id='req_auto_sources',operation='plan_workflow',idempotency_key='auto_sources_retry',payload={'objective':'Classify this support requirement','context':{'generation_mode':'hierarchy','execution_input_mode':'automatic'}})
 first=service.handle(request,auth());assert first['status']==200,first
 assert first['data']['workflow']['inputs']==[]
 assert 'OLD POLICY' in json.dumps(calls[0])
 save(store,'policy',{'content':'NEW POLICY'})
 second=service.handle(request,auth());assert second==first
 assert len(calls)==1
 request['idempotency_key']='auto_sources_new_request'
 assert service.handle(request,auth())['status']==200
 assert 'NEW POLICY' in json.dumps(calls[1])

def test_explicit_and_saved_sheet_sources_are_discovered_without_dropdown():
 provider=LivePlannerProvider('offline',['owner@example.com'],object(),sheet_discoverer=lambda ref: {'spreadsheet_id':ref,'tables':[]})
 objective='Read https://docs.google.com/spreadsheets/d/additional_sheet/edit and summarize.'
 with patch.object(provider.provider,'generate',side_effect=RuntimeError('Stop before model')) as model:
  with pytest.raises(RuntimeError):provider.generate(objective,{'workspace_sources':[{'spreadsheet_id':'saved_sheet'}],'workspace_knowledge':[{'url':'https://docs.google.com/spreadsheets/d/knowledge_sheet/edit'}]})
 supplied=model.call_args.args[1]
 assert [item['spreadsheet_id'] for item in supplied['discovered_spreadsheets']]==['additional_sheet','saved_sheet','knowledge_sheet']

def test_inaccessible_optional_saved_source_is_reported_but_explicit_failure_is_not_hidden():
 def discover(ref):raise RuntimeError('private provider details')
 provider=LivePlannerProvider('offline',['owner@example.com'],object(),sheet_discoverer=discover)
 with patch.object(provider.provider,'generate',side_effect=RuntimeError('Stop before model')) as model:
  with pytest.raises(RuntimeError):provider.generate('Summarize saved knowledge',{'workspace_sources':[{'spreadsheet_id':'stale_sheet'}]})
  assert model.call_args.args[1]['unavailable_source_ids']==['stale_sheet']
 with pytest.raises(Exception) as failure:provider.generate('Read https://docs.google.com/spreadsheets/d/stale_sheet/edit',{})
 assert 'private provider details' not in str(failure.value)

def test_runtime_loads_fresh_knowledge_from_registry_workspace_with_data_read_only(store):
 definition=json.loads((ROOT/'shared/contracts/examples/agents/valid-classifier.json').read_text())
 definition['permissions'].append('data.read')
 record={'definition':definition,'workspace_id':'local-workspace'}
 adapter=SimpleNamespace(agents={definition['agent_id']:record})
 executor=CrewExecutor(adapter,object(),knowledge_loader=lambda workspace:knowledge_documents(store,workspace))
 save(store,'policy',{'content':'NEW POLICY'})
 save(store,'other',{'content':'FOREIGN'},'another-workspace')
 with patch.object(CrewAdapter,'execute',autospec=True,return_value={'category':'support','confidence':1}) as execute:
  executor.invoke(definition,{'request_text':'Classify'},'invocation_1')
  assert 'NEW POLICY' in json.dumps(execute.call_args.args[0].knowledge_context)
  assert 'FOREIGN' not in json.dumps(execute.call_args.args[0].knowledge_context)
  save(store,'policy',{'content':'UPDATED POLICY'})
  executor.invoke(definition,{'request_text':'Classify'},'invocation_2')
  assert 'UPDATED POLICY' in json.dumps(execute.call_args.args[0].knowledge_context)
  assert record['definition']==definition
  record['definition']['permissions'].remove('data.read')
  executor.invoke(definition,{'request_text':'Classify'},'invocation_3')
  assert execute.call_args.args[0].knowledge_context==[]

def test_actual_crewai_receives_knowledge_as_data_without_changing_strict_input_schema():
 definition=json.loads((ROOT/'shared/contracts/examples/agents/valid-classifier.json').read_text())
 definition['input_schema']['additionalProperties']=False
 definition['input_schema']['properties']={'request_text':{'type':'string'}}
 before=deepcopy(definition);calls=[]
 def provider(messages,cap,timeout):
  calls.append(messages);return '{"category":"support","confidence":1}',10,20
 crew=CrewAdapter(lambda agent:BoundedLLM(agent,provider,lambda messages:10,0,0),knowledge_context=[{'source_id':'policy','content':'Returns allowed for 30 days'}])
 assert crew.execute(definition,{'request_text':'Classify return question'})['category']=='support'
 assert 'Returns allowed for 30 days' in json.dumps(calls)
 assert 'untrusted reference data' in json.dumps(calls)
 assert definition==before
