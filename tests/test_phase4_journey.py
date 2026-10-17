"""Phase 4 read boundaries: no provider calls or production mutations."""
import json
from copy import deepcopy
import pytest
from tests import test_workflow_api as api_fixtures
from tests import test_runtime as runtime_fixtures
from workflow_api.release_read import read_release_state

@pytest.fixture
def context():
    fixture=api_fixtures.WorkflowApiTests('test_same_prompt_after_deletion_gets_stable_fresh_identity_and_agents');fixture.setUp()
    try: yield fixture
    finally:fixture.tearDown();fixture.doCleanups()

@pytest.fixture
def runtime_context():
    fixture=runtime_fixtures.RuntimeFixture();fixture.setUp()
    try:yield fixture
    finally:fixture.doCleanups()


def insert_release(context, workspace='local-workspace', version=1, state='active', active=True, generation=1):
    identity=f'rel_phase4_{workspace}_{generation}'
    document={'release_id':identity,'workspace_id':workspace,'revision':{'workflow_id':context.workflow['workflow_id'],'workflow_version':version},'state':state,'trigger_binding_ids':['binding_one']}
    with context.service.store.transaction() as db:
        db.execute('INSERT INTO lifecycle_releases VALUES (?,?,?,?,?,?,?)',(workspace,identity,context.workflow['workflow_id'],version,generation,state,json.dumps(document)))
        if active:db.execute('INSERT INTO lifecycle_active VALUES (?,?,?)',(workspace,context.workflow['workflow_id'],identity))
    return identity


def test_release_read_does_not_confuse_current_draft_with_active_revision(context):
    assert context.save().status_code==200
    identity=insert_release(context)
    draft=deepcopy(context.workflow);draft.update(version=2,status='draft',name='Newer edited design')
    assert context.save(draft,base=1,key='phase4_new_draft').status_code==200
    response=context.client.get(f'/workflows/{draft["workflow_id"]}/release-state',headers={'X-Request-ID':'req_phase4_release'})
    assert response.status_code==200,response.text
    assert response.headers['cache-control']=='no-store'
    assert response.json()['request_id']=='req_phase4_release'
    assert response.json()['data']['release']=={'release_id':identity,'workflow_version':1,'state':'active','trigger_binding_count':1}
    assert context.client.get(f'/workflows/{draft["workflow_id"]}').json()['data']['workflow']['version']==2


def test_release_read_workspace_isolation_and_no_release(context):
    insert_release(context,workspace='other-workspace')
    assert read_release_state(context.service.store,'local-workspace',context.workflow['workflow_id'])['release'] is None
    assert context.client.get(f'/workflows/{context.workflow["workflow_id"]}/release-state').json()['data']['release'] is None


def test_release_read_prefers_active_identity_over_newer_failed_preparation(context):
    identity=insert_release(context)
    insert_release(context,version=2,state='failed',active=False,generation=2)
    data=read_release_state(context.service.store,'local-workspace',context.workflow['workflow_id'])
    assert data['release']['release_id']==identity
    assert data['release']['workflow_version']==1


def test_release_read_reports_disabled_state_without_inventing_activation(context):
    insert_release(context,state='disabled',active=False)
    assert context.client.get(f'/workflows/{context.workflow["workflow_id"]}/release-state').json()['data']['release']['state']=='disabled'


def test_release_read_rejects_anonymous_and_unprivileged_requests(context):
    context.client.cookies.clear()
    assert context.client.get(f'/workflows/{context.workflow["workflow_id"]}/release-state').status_code==401
    client=context.session(['viewer'])
    client.app.state.workflow_auth['permissions']=[]
    try:assert client.get(f'/workflows/{context.workflow["workflow_id"]}/release-state').status_code==403
    finally:client.close()


def test_events_expose_database_sequence_without_rewriting_stored_evidence(runtime_context):
    f=runtime_context;run=f.runtime.create_run(f.request(),f.auth)
    with f.store.transaction() as db:
        first=json.loads(db.execute('SELECT document FROM runtime_events WHERE run_id=?',(run['run_id'],)).fetchone()[0])
        second={**first,'event_id':'evt_phase4_clock_skew','timestamp':'2000-01-01T00:00:00Z','event_type':'node.completed','details':{'node_id':'route'}}
        db.execute('INSERT INTO runtime_events(workspace,run_id,document) VALUES (?,?,?)',('local-workspace',run['run_id'],json.dumps(second)))
    events=f.runtime.events(run['run_id'],f.auth)['items']
    assert events[0]['event_id']==first['event_id']
    assert events[1]['event_id']==second['event_id']
    assert events[0]['details']['recorded_sequence']<events[1]['details']['recorded_sequence']
    with f.store.transaction(write=False) as db:
        assert all('recorded_sequence' not in json.loads(row[0]).get('details',{}) for row in db.execute('SELECT document FROM runtime_events WHERE run_id=?',(run['run_id'],)))
    foreign={**f.auth,'subject':{'subject_id':'foreign','workspace_id':'foreign'}}
    with pytest.raises(Exception):f.runtime.events(run['run_id'],foreign)
