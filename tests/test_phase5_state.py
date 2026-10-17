"""Authoritative concurrency/permission/release invariants used by Phase 5 UI."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import pytest
from tests import test_workflow_api as fixtures
from tests import test_phase4_journey as phase4

@pytest.fixture
def context():
    fixture=fixtures.WorkflowApiTests('test_same_prompt_after_deletion_gets_stable_fresh_identity_and_agents');fixture.setUp()
    try:yield fixture
    finally:fixture.tearDown();fixture.doCleanups()

def test_two_editors_cannot_lose_updates_or_advance_an_unconfirmed_base(context):
    assert context.save().status_code==200
    candidates=[]
    for name in ['Editor A','Editor B']:
        d=deepcopy(context.workflow);d.update(version=2,name=name);candidates.append(d)
    def save(item):return context.save(item,base=1,key='phase5_editor_'+item['name'].replace(' ','_'))
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(save,candidates))
    assert sorted(r.status_code for r in results)==[200,409]
    loser=next(r for r in results if r.status_code==409)
    assert loser.json()['data']['error']['error_code']=='REVISION_CONFLICT'
    winner=next(r.json()['data']['workflow'] for r in results if r.status_code==200)
    assert context.client.get('/workflows/'+context.workflow['workflow_id']).json()['data']['workflow']==winner
    original=context.client.get('/workflows/'+context.workflow['workflow_id']+'?version=1').json()['data']['workflow']
    assert original['name']==context.workflow['name']

def test_new_draft_preserves_layout_metadata_branches_and_the_active_release(context):
    assert context.save().status_code==200
    identity=phase4.insert_release(context)
    candidate=deepcopy(context.workflow);candidate.update(version=2,name='Editable newer draft');candidate['nodes'][0]['layout']={'x':123,'y':456};candidate['metadata']['retained']={'purpose':'review'}
    response=context.save(candidate,base=1,key='phase5_layout_revision');assert response.status_code==200,response.text
    saved=response.json()['data']['workflow'];assert saved['nodes'][0]['layout']=={'x':123,'y':456};assert saved['metadata']['retained']=={'purpose':'review'}
    assert saved['conditions']==candidate['conditions'];assert saved['approval_gates']==candidate['approval_gates']
    release=context.client.get('/workflows/'+candidate['workflow_id']+'/release-state').json()['data']['release']
    assert release['release_id']==identity and release['workflow_version']==1

def test_client_draft_cannot_supply_executable_assignments_or_old_approval(context):
    assert context.save().status_code==200
    candidate=deepcopy(context.workflow);candidate.update(version=2,status='draft')
    agent=json.loads((Path(__file__).resolve().parents[1]/'shared/contracts/examples/agents/valid-classifier.json').read_text())
    for key in ['name','retry_policy','guardrails']:agent.pop(key,None)
    agent['allowed_tool_ids']=['unreviewed_tool'];candidate['agents']=[agent]
    response=context.save(candidate,base=1,key='phase5_unreviewed_grant');assert response.status_code==403,response.text
    assert response.json()['data']['error']['error_code']=='UNTRUSTED_ASSIGNMENT'
    candidate['agents']=[];candidate['metadata'].update(approved_by='browser_claim',approval_submission={'submitted_by':'browser_claim'},validation_state='validated')
    response=context.save(candidate,base=1,key='phase5_clear_approval');assert response.status_code==200,response.text
    saved=response.json()['data']['workflow'];assert saved['status']=='draft'
    assert 'approved_by' not in saved['metadata'] and 'approval_submission' not in saved['metadata']
    assert saved['metadata']['validation_state']=='not_validated'
