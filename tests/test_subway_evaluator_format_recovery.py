"""Real strict decoder, normal Overview/Registry/runtime, controlled provider only."""
from copy import deepcopy
from types import SimpleNamespace
import json
import pytest
from planner.evaluator_protocol import encode,decode,transport_schema
from workflow_api.workflow_adaptive import CONTRACT
from tests.test_subway_autonomy import subway,engine,installed,start,decision,drain,load

@pytest.mark.parametrize('repeat',[False,True])
def test_invalid_encoded_value_after_query_is_bounded_and_preserves_receipt(subway,repeat):
 f=subway;calls=[];receipt=[]
 def evaluate(ctx,**_):
  calls.append(deepcopy(ctx))
  result=decision(ctx)
  if 'read' in ctx['completed_actions']:
   if not receipt:
    receipt.append(deepcopy(load(f,rid)['action_instances']['read']))
   if repeat or not any(c.get('decision_feedback',{} ) and c['decision_feedback'].get('validation_stage')=='encoded_value' for c in calls):
    wire=encode(result,CONTRACT);wire['proposal']='invalid private provider value'
    return decode(SimpleNamespace(status='completed',output_text=json.dumps(wire)),CONTRACT,transport_schema(CONTRACT))
  return result
 rid,_,_=start(f,evaluate)
 run=drain(f,rid)
 assert run['action_instances']['read']==receipt[0]
 assert run['adaptive_reasoning_usage']['llm_calls']==len(calls)
 with f.service.store.transaction(write=False) as db:
  events=[json.loads(row[0]) for row in db.execute('SELECT document FROM runtime_events WHERE run_id=?',(rid,))]
 assert len([e for e in events if e['event_type']=='adaptive.format_correction_scheduled'])==1
 assert 'invalid private provider value' not in json.dumps(events)
 if repeat:
  assert run['status']=='blocked' and run['error_code']=='ADAPTIVE_DECISION_INVALID'
  assert len([c for c in calls if 'read' in c['completed_actions']])==2
 else:
  assert run['status']=='completed' and run['adaptive']['assessment']['completion_eligible']
  assert len(calls)==5

@pytest.mark.parametrize('scope',[
 {'client_id':'simpsons','workspace_id':'client-subway'},
 {'client_id':'subway','workspace_id':'foreign'},
 {}])
def test_non_subway_or_foreign_scope_does_not_enable_correction(scope):
 from planner.errors import PlannerFailure
 from workflow_api.workflow_adaptive import format_correction_checkpoint
 exc=PlannerFailure('ADAPTIVE_DECISION_INVALID','private',details={'validation_stage':'encoded_value'})
 workflow={'metadata':{'connected_action_plan':{'scope':scope}}}
 run={'workspace_id':'client-subway','adaptive':{'revision':1}}
 assert format_correction_checkpoint(exc,workflow,run) is None
