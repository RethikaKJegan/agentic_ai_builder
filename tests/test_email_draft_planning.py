"""Planning concerns are context; compiler contracts decide executable inputs."""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from tests.test_question_free_workflows import (automation,google_setup,connected,composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release,queries,setup_query,empty_once,router)
from tests.test_connected_action_plans import action,bind

@pytest.mark.parametrize('goal',[
 'My engine is leaking oil. Review similar inspection reports and send an email explaining likely causes.',
 'Review similar purchase-order delays and send an email with the findings.',
 'Compare support incidents and email a summary.',
])
def test_scoped_selected_account_delivery_and_advisory_notes_prepare(automation,queries,goal):
 f=automation;_,_,_,body=setup_query(f,queries);r=empty_once();r.update(recipient_mode='selected_account',side_effects=['email_send'],missing_requirements=['No destination was typed. Evidence is preliminary; sources cannot be joined.'])
 def propose(objective,context):
  assert context['binding_context']['user_values']['recipient']=='owner@example.com'
  assert context['overview_intent']['route']['missing_requirements']
  planning=action('query','data.plan_query',[]);planning['budget'].update(max_llm_calls=1,max_tool_calls=0)
  read=action('read','tool.workflow_data_query',[bind('output','query',action='query',path=['query'])],['query'])
  content=action('summary','content.prepare',[bind('output','data',action='read')],['read'],['read'])
  send=action('send','tool.extension_mail_send',[bind('literal','to','recipient'),bind('generated','subject',action='summary',path=['subject']),bind('generated','body',action='summary',path=['body'])],['summary'])
  return dict(actions=[planning,read,content,send],completion_criteria=['send'],missing_inputs=[])
 f.general.planner.provider=SimpleNamespace(plan_actions=propose)
 body.update(objective=goal,request_key='generic_email_'+str(len(goal)));body.pop('automatic_inputs')
 result=router(f,r).handle(f.x.a,body);assert not result.get('blocked') and result['questions']==[]
 doc=f.c.get(f.x.a,result['composition_id']);assert doc['state']=='ready'
 assert f.c.workflow(f.x.a,result['composition_id'])['approval_gates']
 assert not f.http.sent and not f.http.write_count


def test_draft_content_needs_no_recipient_or_mailbox_write(automation,queries):
 f=automation;_,_,_,body=setup_query(f,queries);r=empty_once();r.update(recipient_mode='none',side_effects=[],missing_requirements=['No recipient supplied; an unsent draft can omit it.','No unique engine ID; this is preliminary population evidence.'])
 def propose(goal,context):
  assert 'recipient' not in context['binding_context']['user_values']
  assert 'tool.extension_mail_send' not in context['capabilities']
  return dict(actions=[action('draft_content','content.prepare',[bind('literal','data','draft_input')])],completion_criteria=['draft_content'],missing_inputs=[])
 f.general.planner.provider=SimpleNamespace(plan_actions=propose)
 body.update(objective='Review similar inspection reports and draft an email.',request_key='plain_draft_content',user_values={'draft_input':{'limitations':['Preliminary evidence only.']}});body.pop('automatic_inputs')
 result=router(f,r).handle(f.x.a,body);doc=f.c.get(f.x.a,result['composition_id'])
 assert doc['state']=='ready' and not doc['selected_tools'] and not result['questions']
 assert not f.http.sent and not f.http.write_count


def test_named_third_party_is_not_replaced_with_selected_account(automation,queries):
 f=automation;_,_,_,body=setup_query(f,queries);r=empty_once();r.update(recipient_mode='other',side_effects=['email_send'],missing_requirements=['Unknown manager address.'])
 def propose(goal,context):
  assert 'recipient' not in context['binding_context']['user_values']
  from runtime.service import RuntimeFailure
  raise RuntimeFailure('ACTION_INPUT_REQUIRED','Manager address unavailable.',422)
 f.general.planner.provider=SimpleNamespace(plan_actions=propose)
 body.update(objective='Email my manager the findings.',request_key='unknown_named_recipient');body.pop('automatic_inputs')
 result=router(f,r).handle(f.x.a,body);assert result['report_only'] and not result['questions'] and not f.http.sent


def test_explicit_recipient_overrides_selected_account_default(automation,queries):
 f=automation;_,_,_,body=setup_query(f,queries);r=empty_once();r.update(recipient_mode='selected_account',side_effects=['email_send'])
 def propose(goal,context):
  assert context['binding_context']['user_values']['recipient']=='engineer@example.com'
  return dict(actions=[action('content','content.prepare',[bind('literal','data','draft_input')])],completion_criteria=['content'],missing_inputs=[])
 f.general.planner.provider=SimpleNamespace(plan_actions=propose)
 body.update(objective='Send the findings to engineer@example.com.',request_key='explicit_destination',user_values={'draft_input':{'limitations':['Test only.']}});body.pop('automatic_inputs')
 assert router(f,r).handle(f.x.a,body)['state']=='prepared'


def test_new_model_transport_requires_structured_recipient_mode():
 import json
 from unittest.mock import Mock
 from workflow_api.overview_automation import OverviewAutomation
 route=empty_once();route['recipient_mode']='selected_account'
 client=Mock();client.responses.create.return_value=SimpleNamespace(status='completed',output_text=json.dumps(route))
 service=SimpleNamespace(planner=SimpleNamespace(provider=SimpleNamespace(model='controlled',timeout_seconds=5,_client=client)))
 r=OverviewAutomation(service,{'BUILDER_QUESTION_FREE_WORKFLOWS':'1'})
 assert r.interpret('Prepare an account-scoped summary.',{})['recipient_mode']=='selected_account'
 schema=client.responses.create.call_args.kwargs['text']['format']['schema']
 assert 'recipient_mode' in schema['required']
 assert set(schema['properties']['recipient_mode']['enum'])=={'selected_account','explicit','other','none'}
