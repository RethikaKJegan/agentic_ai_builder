"""Real compiler restoration over owned, pinned compositions; no model or external calls."""
from copy import deepcopy
import pytest
from tests.test_business_composition import (composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release,prepare)
from workflow_api.readiness import repair_draft
from workflow_api.business_composition import verify_composition
from workflow_api.service import ApiFailure

@pytest.mark.parametrize('field',['edges','nodes','tools','approval_gates'])
def test_restore_exact_owned_compilation_and_idempotence(composition,field):
 f=composition;doc=prepare(f);w=f.c.workflow(f.x.a,doc['composition_id']);expected=deepcopy(w)
 if not w[field]:return
 w[field]=[]
 with f.general.store.transaction() as db:
  repairs=repair_draft(f.general,w,f.x.a,db)
  verify_composition(db,f.x.a,w)
  assert w[field]==expected[field] and repairs[0]['applied']
  assert repair_draft(f.general,w,f.x.a,db)==[]
  assert len(w['metadata']['validation_repairs'])==1

@pytest.mark.parametrize('status',['approved','published','archived'])
def test_never_repair_approved_or_historical_workflow(composition,status):
 f=composition;doc=prepare(f);w=f.c.workflow(f.x.a,doc['composition_id']);w.update(status=status,edges=[]);before=deepcopy(w)
 with f.general.store.transaction() as db:assert repair_draft(f.general,w,f.x.a,db)==[]
 assert w==before


def test_no_cross_tenant_or_owner_repair(composition):
 f=composition;doc=prepare(f);w=f.c.workflow(f.x.a,doc['composition_id']);w['edges']=[];before=deepcopy(w)
 for key in ['workspace_id','subject_id']:
  a=deepcopy(f.x.a);a['subject'][key]='another'
  with f.general.store.transaction() as db:assert repair_draft(f.general,w,a,db)==[]
  assert w==before


def test_repair_refuses_changed_pins_and_business_meaning(composition):
 f=composition;doc=prepare(f);w=f.c.workflow(f.x.a,doc['composition_id']);w['edges']=[];w['execution_policy']['allow_external_writes']=True;before=deepcopy(w)
 with f.general.store.transaction() as db:
  with pytest.raises(ApiFailure):repair_draft(f.general,w,f.x.a,db)
 assert w==before

from tests.test_connected_action_plans import connected


def test_missing_protected_gate_restored_and_persisted_by_validate(connected):
 f=connected;f.x.a['permissions'].append('workflow.validate');doc=f.c.prepare_actions(f.x.a,f.request);w=f.c.workflow(f.x.a,doc['composition_id'])
 expected=deepcopy(w);assert w['approval_gates']
 w['approval_gates']=[];w['edges']=[e for e in w['edges'] if e.get('outcome')!='approved']
 with f.general.store.transaction() as db:f.general.store.put(db,'one',w)
 ref=dict(workflow_id=w['workflow_id'],workflow_version=w['version'])
 def validate(key):return f.general.handle(dict(request_id='req_repair',operation='validate_workflow',idempotency_key=key,payload=ref),f.x.a)
 r=validate('repair_validation_first');assert r['status']==200,r
 fixed=r['data']['workflow'];assert fixed['approval_gates']==expected['approval_gates'] and fixed['edges']==expected['edges']
 repairs=fixed['metadata']['validation_report']['repairs'];assert len(repairs)==2 and all(r['applied'] for r in repairs)
 again=validate('repair_validation_again');assert again['status']==200,again
 assert again['data']['workflow']['metadata']['validation_report']['repairs']==repairs
 assert f.http.posts==[] if hasattr(f.http,'posts') else True


def test_cycle_is_replaced_only_with_owned_canonical_dag(composition):
 f=composition;doc=prepare(f);w=f.c.workflow(f.x.a,doc['composition_id']);expected=deepcopy(w['edges'])
 w['edges'].append(dict(edge_id='bad_cycle',source=w['edges'][0]['target'],target=w['edges'][0]['source']))
 with f.general.store.transaction() as db:repair_draft(f.general,w,f.x.a,db)
 assert w['edges']==expected
 f.general.validate_document(w)


def test_blocking_readiness_cannot_be_submitted_for_review(connected):
 from workflow_api.review_actions import submit
 from workflow_api.readiness import fingerprint
 f=connected;f.x.a['permissions'].append('workflow.validate');doc=f.c.prepare_actions(f.x.a,f.request);w=f.c.workflow(f.x.a,doc['composition_id']);w['status']='validated'
 w['metadata']['validation_report']={'ready':False,'workflow_fingerprint':fingerprint(w),'issues':[{'blocking':True,'method':'model_assessment','category':'Missing relationship','problem':'Mandatory exact match unavailable'}]}
 with f.general.store.transaction() as db:f.general.store.put(db,'one',w)
 with pytest.raises(ApiFailure):submit(f.general,dict(request_id='req_submit_blocked',operation='submit_workflow_for_approval',idempotency_key='submit_blocked_001',payload=dict(workflow_id=w['workflow_id'],workflow_version=w['version'])),f.x.a)
 with f.general.store.transaction(write=False) as db:assert not f.general.store.get(db,'one',w['workflow_id'])['metadata'].get('approval_submission')


def test_repair_never_removes_an_added_requested_task(composition):
 f=composition;doc=prepare(f);w=f.c.workflow(f.x.a,doc['composition_id']);w['nodes'].append(dict(node_id='new_requested_task',kind='transform',label='Requested additional work'));before=deepcopy(w)
 with f.general.store.transaction() as db:assert repair_draft(f.general,w,f.x.a,db)==[]
 assert w==before


def test_running_workflow_cannot_be_repaired(connected):
 from tests.test_connected_action_plans import compile_run
 f=connected;doc,w,rid=compile_run(f);w['status']='draft';w['edges']=[];before=deepcopy(w)
 with f.general.store.transaction() as db:
  with pytest.raises(ApiFailure,match='active run'):repair_draft(f.general,w,f.x.a,db)
 assert w==before
