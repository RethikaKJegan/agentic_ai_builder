"""Infrastructure contention, grounded report views and scoped corrective feedback."""
from copy import deepcopy
import json
import sqlite3
import time
import pytest
from tests.test_business_composition import (composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release,prepare,approve,run,DiagnosticAgents)
from runtime import RuntimeService
from runtime.graph import GraphRunner
from runtime.delegation import DelegationSession
from runtime.recovery import classify
from runtime.service import RuntimeFailure
from workflow_api.composition_presentation import CompositionPresentation,result_view
from workflow_api.storage import WorkflowStore


def test_tool_discovery_works_while_another_connection_owns_writer_lock(composition):
 f=composition;d=prepare(f);w=approve(f,f.c.workflow(f.x.a,d['composition_id']));rt=RuntimeService(f.general);rt.store.busy_timeout_ms=25
 created=rt.create_run(dict(request_id='read_lock',idempotency_key='read_lock_001',payload=dict(workflow_id=w['workflow_id'],workflow_version=1,inputs={})),f.x.a)
 with rt.store.transaction() as db:
  current=rt.load(db,created['run_id'],f.x.a);current.update(status='running',worker='worker_test');rt.save(db,current)
 node=next(n for n in w['nodes'] if n['node_id']=='master_orchestrator');master=next(a for a in w['agents'] if a['agent_id']==node['agent_id'])
 session=DelegationSession(GraphRunner(rt,agents=DiagnosticAgents(),connectors=f.connectors),created['run_id'],f.x.a,'worker_test',w,node,master,{})
 child=next(a for a in session.children.values() if a['allowed_tool_ids'])
 with sqlite3.connect(rt.store.path) as writer:
  writer.execute('BEGIN IMMEDIATE');started=time.monotonic()
  tools=session.available_tools(child)
  assert tools and tools[0]['tool_id']=='business_retrieve_evidence'
  assert time.monotonic()-started<.5
  writer.rollback()


def test_storage_contention_survives_generic_failure_wrappers(tmp_path):
 store=WorkflowStore(tmp_path/'locked.sqlite3',busy_timeout_ms=10)
 with sqlite3.connect(store.path) as writer:
  writer.execute('BEGIN IMMEDIATE')
  with pytest.raises(sqlite3.OperationalError) as caught:
   with store.transaction():pass
  assert caught.value.code=='DATABASE_BUSY'
 assert classify(caught.value.code)['retry_eligible']
 assert classify(caught.value.code,external_write=True)['category']=='uncertain_external_write'
 assert classify('INVOCATION_FAILED')['recovery_strategy']=='inspect_service'


def test_source_record_counts_merge_partial_mapped_reads_without_cross_source_merge():
 def record(source,values):return dict(record_id='r1',collection='tickets',source_reference=source,read_at='2026-11-04',values=values)
 out=result_view(dict(source_evidence=[dict(records=[record('db_a',{'serial':'S1'})]),dict(records=[record('db_a',{'status':'CLOSED'}),record('db_b',{'serial':'S2'})])]))
 assert len(out['records'])==2
 assert out['records'][0]['values']=={'serial':'S1','status':'CLOSED'}


def test_new_run_gets_only_scoped_sanitized_previous_model_failure_feedback(composition):
 f=composition;d=prepare(f)
 class Invalid(DiagnosticAgents):
  def invoke_tool_decision(self,*args):raise RuntimeFailure('MODEL_OUTPUT_SCHEMA_INVALID','Rejected output must not be reused.')
 first,_,rt=run(f,d,Invalid());assert first['status']=='failed'
 w=f.c.workflow(f.x.a,d['composition_id'])
 created=rt.create_run(dict(request_id='new_attempt',idempotency_key='new_attempt_001',payload=dict(workflow_id=w['workflow_id'],workflow_version=1,inputs={})),f.x.a)
 with rt.store.transaction(write=False) as db:document=rt.load(db,created['run_id'],f.x.a)
 hints=document['previous_failure_feedback'];assert hints and all(set(h)=={'affected_task','code','hint'} for h in hints)
 assert 'Rejected output' not in json.dumps(hints)
 agents=DiagnosticAgents();result=GraphRunner(rt,agents=agents,connectors=f.connectors).advance(created['run_id'],f.x.a);assert result['status']=='completed'
 for context in agents.contexts:
  if 'context' in context:
   assert all(h['affected_task']==context['task_id'] for h in context['context']['previous_failure_feedback'])


def test_full_comparison_warranty_replacement_goal_finishes_with_evidence_qualifications(composition):
 f=composition;d=prepare(f,'Investigate complaint C123. Compare its linked inspection, review replacement evidence, check warranty readiness and prepare a source-backed report.')
 assert {'business.compare','business.assess_warranty','business.review_replacement'}<={t['capability_id'] for t in d['tasks']}
 result,events,rt=run(f,d);assert result['status']=='completed',events[-4:]
 f.general.runtime_runner=GraphRunner(rt,agents=DiagnosticAgents(),connectors=f.connectors)
 view=CompositionPresentation(f.c).view(f.x.a,d['composition_id'],result['run_id'])
 assert len(view['tasks'])==8 and all(t['state'] in ('completed','needs_input') for t in view['tasks'])
 assert view['request_context']['business_request']['inputs']['identifiers']['complaint_id']=='C123'


def test_read_tool_receipts_show_real_counts_without_mail_content_or_tokens():
 from workflow_api.composition_presentation import tool_receipt
 output=dict(messages=[dict(id='message_1',thread_id='thread_1',body='Private body')],next_page_token='opaque_cursor')
 receipt=tool_receipt(output)
 assert receipt['returned_messages']==1 and receipt['messages_identifiers']==[dict(id='message_1',thread_id='thread_1')]
 assert 'Private body' not in json.dumps(receipt) and 'opaque_cursor' not in json.dumps(receipt)
