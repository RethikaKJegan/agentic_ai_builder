"""Shared presentation changes verified with isolated actual persistence and Registry."""
from copy import deepcopy
import json
import pytest
from tests.test_connected_action_plans import (connected, composition, investigation, retrieval, knowledge, reference, generation, foundation, auth, release)
from tests.test_business_composition import prepare
from tests.test_business_investigations import plan
from workflow_api.composition_presentation import CompositionPresentation
from workflow_api.workflow_duplicates import composition_copy, investigation_copy
from workflow_api.workflow_display import display_title, title_before_planning
from workflow_api.automation import DurableAutomation


def test_titles_are_short_preserve_manual_names_and_do_not_change_objective():
    class Provider:
        def workflow_title(self, objective):
            assert objective == 'Summarize purchase orders by vendor and currency.'
            return 'Purchase Order Vendor Summary'
    objective='Summarize purchase orders by vendor and currency.'
    assert title_before_planning(objective,Provider())=='Purchase Order Vendor Summary'
    assert len(title_before_planning(objective).split()) in (3,4)
    assert len(title_before_planning('x'*4000))<=160
    assert len(title_before_planning('Report').split())==3
    assert display_title(dict(objective=objective,display_name='My chosen title with five words'))=='My chosen title with five words'


@pytest.mark.parametrize('actions',[False,True])
def test_duplicate_is_independent_idempotent_and_has_no_run_or_release(connected,actions):
    f=connected;ui=CompositionPresentation(f.c)
    original=f.c.prepare_actions(f.x.a,f.request) if actions else prepare(f)
    ui.rename(f.x.a,original['composition_id'],{'display_name':'Original workflow title'})
    body={'request_key':'duplicate_test_request'}
    result=composition_copy(ui,f.x.a,original['composition_id'],body)
    assert composition_copy(ui,f.x.a,original['composition_id'],body)==result
    copied=f.c.get(f.x.a,result['composition_id'])
    assert copied['composition_id']!=original['composition_id']
    assert copied['objective']==original['objective']
    assert copied['tasks']==original['tasks']
    assert {c['definition']['agent_id'] for c in copied['configurations']}.isdisjoint(c['definition']['agent_id'] for c in original['configurations'])
    assert ui.view(f.x.a,result['composition_id'])['run'] is None
    assert ui.view(f.x.a,result['composition_id'])['workflow_status'] is None
    ui.rename(f.x.a,result['composition_id'],{'display_name':'Independent copy title'})
    assert ui.view(f.x.a,original['composition_id'])['display_name']=='Original workflow title'
    assert f.c.get(f.x.a,original['composition_id'])==original
    # Compile the copied plan through current source/tool/Registry checks.
    assert f.c.workflow(f.x.a,result['composition_id'])['status']=='draft'
    denied=deepcopy(f.x.a);denied['permissions'].remove('workflow.edit')
    with pytest.raises(Exception):composition_copy(ui,denied,original['composition_id'],{'request_key':'duplicate_denied_request'})


def test_duplicate_legacy_investigation_has_new_identity_and_no_runs(investigation):
    x=investigation;x.a['permissions'].append('workflow.edit');x.current['permissions'].append('workflow.edit');p=plan(x)
    result=investigation_copy(x.service,x.a,p['workflow_id'],{'request_key':'duplicate_legacy_test'})
    copied=x.service.get_plan(x.a,result['workflow_id'])
    assert copied['workflow_id']!=p['workflow_id']
    assert copied['objective']==p['objective'] and copied['graph']==p['graph']
    assert investigation_copy(x.service,x.a,p['workflow_id'],{'request_key':'duplicate_legacy_test'})==result
    assert x.service.get_plan(x.a,p['workflow_id'])==p


def test_background_filters_before_paging_and_keeps_related_records(connected):
    f=connected;auto=DurableAutomation(f.general)
    # Minimal isolated saved records exercise selection independently of provider setup.
    docs=[
        dict(id='z_other',kind='schedule',state='active',request={'workflow':{'workflow_id':'other'}}),
        dict(id='a_schedule',kind='schedule',state='active',request={'workflow':{'workflow_id':'wanted'},'authorization_id':'a_auth'}),
        dict(id='a_occurrence',kind='occurrence',state='completed',schedule_id='a_schedule'),
        dict(id='a_auth',kind='authorization',state='active',request={}),
        dict(id='z_foreign',kind='schedule',state='active',request={'workflow':{'workflow_id':'wanted'}}),
    ]
    with f.general.store.transaction() as db:
        for doc in docs:
            db.execute('INSERT INTO automation_records VALUES (?,?,?,?,?,?,?)',('one','someone_else' if doc['id']=='z_foreign' else 'alice',doc['kind'],doc['id'],doc['state'],None,json.dumps(doc)))
    first=auto.listing(f.x.a,limit=1,workflow_id='wanted')
    assert first['items'][0]['id']=='a_schedule' and first['has_more']
    second=auto.listing(f.x.a,before=first['next_cursor'],limit=10,workflow_id='wanted')
    assert {d['id'] for d in second['items']}=={'a_occurrence','a_auth'}
    assert first['metrics']['occurrence_states']=={'completed':1}
    assert auto.listing(f.x.a,workflow_id='absent')['items']==[]
