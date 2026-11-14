from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from workflow_api.readiness import assess,enforce,fingerprint
from workflow_api.storage import WorkflowStore
from workflow_api.service import ApiFailure

@pytest.fixture(params=['client-simpsons','client-subway'])
def context(tmp_path,request):
    store=WorkflowStore(tmp_path/'readiness.sqlite3')
    service=SimpleNamespace(store=store,registry_adapter=SimpleNamespace(review=lambda *_:{'ready':True,'items':[]}),planner=SimpleNamespace(provider=SimpleNamespace()))
    workflow=json.loads((Path(__file__).parents[1]/'shared/contracts/examples/workflows/support-triage.json').read_text())
    workflow['metadata']={'workspace_id':request.param,'original_objective':'Read supported records; produce count and average; no email.'}
    auth={'subject':{'workspace_id':request.param,'subject_id':'owner'}}
    return service,workflow,auth

def test_unresolved_rule_blocks_but_missing_evidence_is_a_warning(context):
    s,w,a=context;w['metadata']['unresolved_requirements']=['No executable rule handler for requested policy.'];w['metadata']['report_limitations']=['A historical source is incomplete.']
    with s.store.transaction(write=False) as db:result=assess(s,w,a,db)
    assert not result['ready'];assert any(i['category']=='Unsupported requirement' and i['blocking'] for i in result['issues'])
    assert any(i['category']=='Evidence limitation' and not i['blocking'] for i in result['issues'])
    assert result['execution_outcomes_verified'] is False

def test_model_coverage_is_labeled_and_not_factual_verification(context):
    s,w,a=context
    s.planner.provider.review_requirements=lambda objective,ctx:dict(covered_requirements=[],issues=[dict(category='Unsupported requirement',task='report',requirement='Average hours',problem='Average metric missing',resource='hours',blocking=True,correction='Add an authorized average query metric.')])
    with s.store.transaction(write=False) as db:result=assess(s,w,a,db,semantic=True)
    assert not result['ready'];assert result['issues'][-1]['method']=='model_assessment'
    assert result['original_objective']==w['metadata']['original_objective']

def test_cross_tenant_and_source_drift_rejected(context):
    s,w,a=context;w['metadata']['workspace_id']='foreign'
    with s.store.transaction(write=False) as db:
        with pytest.raises(ApiFailure,match='readiness'):enforce(s,w,a,db)

def test_execution_rechecks_saved_report_and_current_permissions(context):
    s,w,a=context
    with s.store.transaction(write=False) as db:report=assess(s,w,a,db)
    w['metadata']['validation_report']=report
    with s.store.transaction(write=False) as db:assert enforce(s,w,a,db)['ready']
    w['nodes'][0]['label']='Changed requirement'
    with s.store.transaction(write=False) as db:
        with pytest.raises(ApiFailure,match='changed workflow'):enforce(s,w,a,db)

def test_unavailable_relationship_and_field_are_precise(context):
    s,w,a=context
    def invalid(query,current):raise ApiFailure('DATA_QUERY_INVALID','Plan references an unavailable relationship.',422)
    s.workflow_queries=SimpleNamespace(queries=SimpleNamespace(context=lambda *_:(),validate=invalid))
    w['metadata']['action_binding_context']={'validated_context':{'reviewed_query':{'base_dataset_id':'missing'}}}
    with s.store.transaction(write=False) as db:result=assess(s,w,a,db)
    assert any(i['category']=='Missing relationship' for i in result['issues']);assert not result['ready']


def model_issue(phase,category='Evidence limitation',blocking=True):
    return dict(category=category,task='report',requirement='Report evidence',problem='Controlled finding',resource='',blocking=blocking,correction='Check at the appropriate boundary.',phase=phase)

@pytest.mark.parametrize('phase,category,blocked',[
 ('runtime_evidence','Evidence limitation',False),('review_decision','Permission/approval required',False),
 ('configuration','Missing relationship',True),('configuration','Missing source mapping',True),('configuration','Unsupported requirement',True)])
def test_explicit_phases_preserve_mandatory_constraints(context,phase,category,blocked):
    s,w,a=context;s.planner.provider.review_requirements=lambda *_:dict(covered_requirements=[],issues=[model_issue(phase,category)])
    with s.store.transaction(write=False) as db:r=assess(s,w,a,db,semantic=True)
    assert r['ready'] is not blocked
    assert r['readiness_state']==(category if blocked else 'Ready for review')


def test_review_decision_without_boundary_remains_blocked(context):
    s,w,a=context;w['execution_policy']['requires_review_before_execution']=False
    s.planner.provider.review_requirements=lambda *_:dict(covered_requirements=[],issues=[model_issue('review_decision','Permission/approval required')])
    with s.store.transaction(write=False) as db:r=assess(s,w,a,db,semantic=True)
    assert not r['ready']


def test_semantic_review_reused_but_changed_request_is_reviewed(context):
    s,w,a=context;calls=[]
    def evaluate(*args):calls.append(args);return dict(covered_requirements=['Report'],issues=[])
    s.planner.provider.review_requirements=evaluate
    with s.store.transaction(write=False) as db:w['metadata']['validation_report']=assess(s,w,a,db,semantic=True)
    with s.store.transaction(write=False) as db:r=assess(s,w,a,db,semantic=True)
    assert len(calls)==1 and r['ready']
    w['metadata']['original_objective']='A changed mandatory comparison'
    with s.store.transaction(write=False) as db:assess(s,w,a,db,semantic=True)
    assert len(calls)==2


def test_repeat_review_always_checks_current_authorization(context):
    s,w,a=context;s.planner.provider.review_requirements=lambda *_:dict(covered_requirements=[],issues=[])
    with s.store.transaction(write=False) as db:w['metadata']['validation_report']=assess(s,w,a,db,semantic=True)
    s.registry_adapter.review=lambda *_:dict(items=[dict(authorization_state='denied',reason_codes=['FORBIDDEN'])])
    with s.store.transaction(write=False) as db:r=assess(s,w,a,db,semantic=True)
    assert not r['ready']


def test_projection_discloses_resolved_binding_without_private_value(context):
    from workflow_api.readiness import review_projection
    s,w,a=context;secret='private-account@example.test'
    action=dict(action_id='send',capability_id='tool.extension_mail_send',depends_on=[],bindings=[dict(kind='literal',key='communication_recipient',path=[],target=['to'])])
    w['metadata']['action_binding_context']={'user_values':{'communication_recipient':secret},'evidence':{'private':'stored source observation'}}
    p=review_projection(w,[action],{}, {},{})
    assert secret not in json.dumps(p) and 'stored source observation' not in json.dumps(p)
    assert p['actions'][0]['binding_availability'][0]['state']=='available'


def test_future_output_contract_validated_without_receipts(context):
    s,w,a=context
    actions=[dict(action_id='read',capability_id='tool.query',depends_on=[],bindings=[],expected_output_schema={'type':'object','properties':{'rows':{'type':'array'}}}),
             dict(action_id='report',capability_id='content.prepare',depends_on=['read'],bindings=[dict(kind='output',action_id='read',path=['rows'],target=['data'])])]
    w['metadata']['connected_action_plan']={'actions':actions}
    with s.store.transaction(write=False) as db:r=assess(s,w,a,db)
    assert r['ready'] and not r['execution_outcomes_verified']
    actions[1]['depends_on']=[]
    with s.store.transaction(write=False) as db:r=assess(s,w,a,db)
    assert not r['ready']


def test_missing_recipient_gets_specific_input_request(context):
    s,w,a=context;w['metadata']['connected_action_plan']={'actions':[dict(action_id='send',capability_id='tool.extension_mail_send',depends_on=[],bindings=[dict(kind='literal',key='communication_recipient',path=[],target=['to'])])]}
    with s.store.transaction(write=False) as db:r=assess(s,w,a,db)
    assert r['readiness_state']=='Needs input'
    assert any(i['problem']=='Which authorized email address should receive this report?' for i in r['issues'])


def test_configured_approval_pending_is_ready_for_review(context):
    s,w,a=context;s.registry_adapter.review=lambda *_:dict(items=[dict(authorization_state='pending_approval',reason_codes=['APPROVAL_REQUIRED'])])
    with s.store.transaction(write=False) as db:r=assess(s,w,a,db)
    assert r['ready'] and r['readiness_state']=='Ready for review'


def test_static_literal_queries_use_existing_engine_validation(context):
    s,w,a=context;calls=[]
    def invalid(query,current):calls.append(query);raise ApiFailure('DATA_QUERY_INVALID','Unknown field in the authorized source.',422)
    s.workflow_queries=SimpleNamespace(queries=SimpleNamespace(context=lambda *_:(),validate=invalid))
    query={'base_dataset_id':'authorized_source','fields':['unknown']}
    w['metadata']['action_binding_context']={'user_values':{'query':query}}
    w['metadata']['connected_action_plan']={'actions':[dict(action_id='read',capability_id='tool.workflow_data_query',depends_on=[],bindings=[dict(kind='literal',key='query',path=[],target=['query'])])]}
    with s.store.transaction(write=False) as db:r=assess(s,w,a,db)
    assert calls==[query] and not r['ready']
    assert any(i['category']=='Missing source mapping' for i in r['issues'])
