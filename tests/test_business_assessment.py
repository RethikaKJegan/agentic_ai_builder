"""Three-outcome truth table and explicit, source-qualified draft arithmetic."""
from copy import deepcopy
import json
from unittest.mock import patch
import pytest
from tests.test_business_graph import graph,build
from tests.test_business_compiler import compiled_draft
from tests.test_business_generation import generation
from tests.test_business_ontology import foundation,auth
from tests.test_business_policies import policies,body,request
from workflow_api.business_assessment import decide,period
from workflow_api.business_policies import digest
from workflow_api.service import ApiFailure


@pytest.mark.parametrize('states,verified,expected',[
 (['passed','passed'],True,'Warranty Eligible'),(['passed','failed'],True,'Warranty Not Eligible'),
 (['failed','unknown'],True,'Requires Review'),(['passed','unknown'],True,'Requires Review'),
 (['failed','failed'],False,'Requires Review'),([],True,'Requires Review'),(['unexpected'],True,'Requires Review'),
])
def test_three_outcome_unknown_precedence(states,verified,expected):
    assert decide([dict(status=s) for s in states],policy_verified=verified,identity_verified=verified,applicability_verified=verified)==expected


@pytest.mark.parametrize('missing',['policy_verified','identity_verified','applicability_verified'])
def test_each_verification_prerequisite_is_mandatory(missing):
    flags=dict(policy_verified=True,identity_verified=True,applicability_verified=True);flags[missing]=False
    assert decide([dict(status='passed')],**flags)=='Requires Review'


@pytest.mark.parametrize('start,end,months,method,boundary,state,deadline',[
 ('2026-01-31','2026-02-28',1,'calendar_month_anniversary_clamped','inclusive','passed','2026-02-28'),
 ('2026-01-31','2026-02-28',1,'calendar_month_anniversary_clamped','exclusive','failed','2026-02-28'),
 ('2024-02-29','2025-02-28',12,'calendar_month_anniversary_clamped','inclusive','passed','2025-02-28'),
 ('2026-01-31','2026-02-01',1,'calendar_month_difference','exclusive','failed',None),
 ('2026-01-31','2026-02-01',1,'calendar_month_anniversary_clamped','exclusive','passed','2026-02-28'),
 ('2026-06-02','2026-06-01',1,'calendar_month_difference','inclusive','unknown',None),
 ('2026-01-01','2026-01-01',0,'calendar_month_anniversary_clamped','inclusive','passed','2026-01-01'),
 ('2026-01-01','2026-01-01',0,'calendar_month_anniversary_clamped','exclusive','failed','2026-01-01'),
 ('9999-12-31','9999-12-31',1200,'calendar_month_anniversary_clamped','inclusive','unknown',None),
 ('bad','2026-01-01',1,'calendar_month_anniversary_clamped','inclusive','unknown',None),
 ('2026-01-01','2026-01-02',True,'calendar_month_anniversary_clamped','inclusive','unknown',None),
 ('2026-01-01','2026-01-02',1,'guessed_method','inclusive','unknown',None),
])
def test_period_conventions(start,end,months,method,boundary,state,deadline):
    result=period(start,end,months,method,boundary);assert result['status']==state and result['deadline']==deadline


def setup_case(policies,hours='0',exclusion_mode='none_declared'):
    x,service,source=policies;x.reader.rows['tickets'][0]['complaintRecord.dateOfSale']='2026-01-01';x.reader.rows['tickets'][0]['complaintRecord.hmr']=hours
    b=body(source);b['policy']['clauses']['exclusion_mode']['value']=exclusion_mode
    if exclusion_mode=='none_declared':b['policy']['clauses']['exclusion_checks']=dict(value=None,quote=None)
    p=service.save(auth(),b);g=build(x);return x,service,p,g


def test_complete_looking_draft_calculations_do_not_approve_case(policies):
    x,service,p,g=setup_case(policies);calls=len(x.reader.calls)
    with patch('socket.create_connection',side_effect=AssertionError('No external calls')):
        result=service.assess(auth(write=False),x.snapshot['version_id'],g['graph_id'],request(p,g))
    assert all(c['status']=='passed' for c in result['checks']) and result['draft_calculation']=='within_declared_limits'
    assert result['classification']=='Requires Review' and result['eligibility_final'] is False and result['business_policy_verified'] is False
    assert {'POLICY_AUTHORITY_UNVERIFIED','PHYSICAL_IDENTITY_UNRESOLVED'}<={b['code'] for b in result['blockers']}
    assert next(c for c in result['checks'] if c['check_id']=='operating_hours')['observed']=='0'
    assert result['company_queries']==result['model_calls']==0 and len(x.reader.calls)==calls
    assert service.assess(auth(),x.snapshot['version_id'],g['graph_id'],request(p,g))['report_sha256']==result['report_sha256']


@pytest.mark.parametrize('hours,boundary,state',[('1000','inclusive','passed'),('1000','exclusive','failed'),('1000.01','inclusive','failed'),('-1','inclusive','unknown')])
def test_hours_equality_failure_and_invalid_input(policies,hours,boundary,state):
    x,service,source=policies;x.reader.rows['tickets'][0]['complaintRecord.hmr']=hours;x.reader.rows['tickets'][0]['complaintRecord.dateOfSale']='2026-01-01'
    b=body(source);b['policy']['clauses']['hours_boundary']['value']=boundary;p=service.save(auth(),b);g=build(x)
    result=service.assess(auth(),x.snapshot['version_id'],g['graph_id'],request(p,g))
    assert next(c for c in result['checks'] if c['check_id']=='operating_hours')['status']==state
    assert result['classification']=='Requires Review' # exclusion findings and authority are not established


def test_required_exclusion_findings_never_come_from_flags(policies):
    x,service,p,g=setup_case(policies,exclusion_mode='checks_required')
    result=service.assess(auth(),x.snapshot['version_id'],g['graph_id'],request(p,g))
    exclusion=next(c for c in result['checks'] if c['check_id']=='exclusion:misuse_check')
    assert exclusion['status']=='unknown' and result['draft_calculation']=='incomplete_evidence'


def test_legacy_policy_has_no_new_calculation_defaults(policies):
    x,service,p,g=setup_case(policies)
    legacy=deepcopy(p)
    for key in ['coverage_mode','coverage_date_basis','period_method','period_boundary','hours_boundary','exclusion_mode','exclusion_checks']:legacy['clauses'].pop(key)
    legacy['schema_version']='simpson-policy-draft-v1';legacy['sha256']=digest({k:v for k,v in legacy.items() if k!='sha256'})
    with x.f.store.transaction() as db:db.execute('UPDATE business_policy_versions SET document=? WHERE policy_id=?',(json.dumps(legacy),p['policy_id']))
    result=service.assess(auth(),x.snapshot['version_id'],g['graph_id'],request(p,g))
    assert result['draft_calculation']=='incomplete_evidence' and next(c for c in result['checks'] if c['check_id']=='coverage_profile')['status']=='unknown'
    assert service.get(auth(),p['policy_id'])==legacy


def test_invoice_profile_requires_explicit_selected_invoice_and_date(policies):
    x,service,source=policies;b=body(source);b['policy']['clauses']['coverage_mode']['value']='invoice_and_hours';p=service.save(auth(),b);g=build(x)
    result=service.assess(auth(),x.snapshot['version_id'],g['graph_id'],request(p,g))
    assert next(c for c in result['checks'] if c['check_id']=='invoice_period')['status']=='unknown'
    assert not any(c['check_id']=='sale_period' for c in result['checks'])


@pytest.mark.parametrize('change',[{'policy_verified':True},{'identity_verified':True},{'exclusions':[]},{'hours':0},{'assessment_at':'2026-01-01'},{'ticket_node_id':'foreign'}])
def test_client_cannot_override_verification_or_observations(policies,change):
    x,service,p,g=setup_case(policies)
    with pytest.raises(ApiFailure):service.assess(auth(),x.snapshot['version_id'],g['graph_id'],{**request(p,g),**change})


def test_assessment_scope_disconnect_and_no_mutation(policies):
    x,service,p,g=setup_case(policies)
    for foreign in [auth(owner='bob'),auth(workspace='two')]:
        with pytest.raises(ApiFailure):service.assess(foreign,x.snapshot['version_id'],g['graph_id'],request(p,g))
    with x.f.store.transaction() as db:db.execute("UPDATE data_source_connections SET document=? WHERE connection_id='quality'",(json.dumps(dict(connection_status='disconnected',metadata_revision=10)),))
    with x.f.store.transaction(write=False) as db:before={name:db.execute('SELECT * FROM '+name).fetchall() for name in ['business_policy_versions','business_ontology_versions','business_ontology_graphs','business_ontology_events','data_source_connections']}
    assert service.assess(auth(write=False),x.snapshot['version_id'],g['graph_id'],request(p,g))['classification']=='Requires Review'
    with x.f.store.transaction(write=False) as db:assert all(db.execute('SELECT * FROM '+name).fetchall()==rows for name,rows in before.items())


def test_new_profile_validation_and_exclusion_contradictions(policies):
    x,service,source=policies
    for key,value in [('period_method','guess'),('hours_boundary','truthy'),('coverage_date_basis','today'),('exclusion_checks',['bad-code'])]:
        b=body(source);b['policy']['clauses'][key]['value']=value
        with pytest.raises(ApiFailure):service.save(auth(),b)
    b=body(source);b['policy']['clauses']['exclusion_mode']['value']='none_declared'
    with pytest.raises(ApiFailure):service.save(auth(),b)
    assert service.list(auth())['items']==[]


def test_real_http_assessment_and_no_public_verification_override(tmp_path,policies):
    from fastapi.testclient import TestClient
    from workflow_api.main import create_app
    from tests.test_business_policies import TEXT
    x,_,_=policies;x.reader.rows['tickets'][0]['complaintRecord.hmr']='0';x.reader.rows['tickets'][0]['complaintRecord.dateOfSale']='2026-01-01';g=build(x)
    app=create_app(database=tmp_path/'assessment.sqlite',dev_auth=True,start_workers=False,planning_worker_enabled=False)
    client=TestClient(app);root='/business-ontology/v1'
    assert client.post(root+'/versions/x/graphs/x/warranty-assessment',json={}).status_code==401
    client.get('/session');client.cookies.set('builder_dev_session',client.cookies.get('builder_dev_session'),path='/')
    with app.state.workflow_service.store.transaction() as db:
        for cid in ('service','quality'):
            doc=dict(connection_id=cid,name=cid,engine='mongodb',connection_status='connected',metadata_revision=1)
            db.execute('INSERT INTO data_source_connections VALUES (?,?,?,?,?)',(cid,'local-workspace','local-builder',None,json.dumps(doc)))
    version=client.post(root+'/initialize',json={'sources':{'service':'service','quality':'quality'}}).json()['data']['current_version_id']
    source=client.post(root+'/documents',json=dict(title='Synthetic HTTP policy',kind='policy',module_ids=['warranty'],text=TEXT)).json()['data']
    saved=client.post(root+'/warranty-policies',json=body(source)).json()['data'];g['version_id']=version
    with app.state.workflow_service.store.transaction() as db:db.execute('INSERT INTO business_ontology_graphs VALUES (?,?,?,?,?,?,?)',('local-workspace','local-builder',version,g['graph_id'],'assessment_http_graph','fixture',json.dumps(g)))
    endpoint=root+'/versions/'+version+'/graphs/'+g['graph_id']+'/warranty-assessment';req=request(saved,g)
    with app.state.workflow_service.store.transaction(write=False) as db:before={name:db.execute('SELECT * FROM '+name).fetchall() for name in ['business_policy_versions','business_ontology_versions','business_ontology_graphs','business_ontology_events','data_source_connections']}
    with patch('socket.create_connection',side_effect=AssertionError('No network')):response=client.post(endpoint,json=req)
    assert response.status_code==200 and response.headers['cache-control']=='no-store'
    assert response.json()['data']['classification']=='Requires Review' and response.json()['data']['draft_calculation']=='incomplete_evidence'
    absent=client.post(endpoint,json={**req,'policy_id':None})
    assert absent.status_code==200 and absent.headers['cache-control']=='no-store'
    assert absent.json()['data']['policy_id'] is None and absent.json()['data']['blockers'][0]['code']=='POLICY_MISSING'
    assert client.post(endpoint,json={**req,'policy_verified':True}).status_code==422
    assert client.post(endpoint,json=req,headers={'origin':'https://untrusted.example'}).status_code==403
    assert client.post(endpoint,content='bad-json').status_code==422
    with app.state.workflow_service.store.transaction(write=False) as db:assert all(db.execute('SELECT * FROM '+name).fetchall()==rows for name,rows in before.items())
    app.state.workflow_auth['subject']['subject_id']='other'
    assert client.post(endpoint,json=req).status_code==404


def test_absent_policy_returns_review_without_inventing_a_policy(policies):
    x,service,source=policies;g=build(x);req=dict(policy_id=None,ticket_node_id=next(r['node_id'] for r in g['records'] if r['collection']=='tickets'),assessment_at='2026-06-01T12:00:00Z',invoice_node_id=None)
    result=service.assess(auth(write=False),x.snapshot['version_id'],g['graph_id'],req)
    assert result['classification']=='Requires Review' and result['policy_id'] is result['policy_source'] is None and result['policy_clauses']=={}
    assert result['blockers'][0]['code']=='POLICY_MISSING' and result['coverage_calculations_performed'] is False
    assert service.list(auth())['items']==[]
    with pytest.raises(ApiFailure):service.assess(auth(),x.snapshot['version_id'],g['graph_id'],{**req,'policy_verified':True})
