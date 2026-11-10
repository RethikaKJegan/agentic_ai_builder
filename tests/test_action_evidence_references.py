"""Evidence references remain verified while generated graph edges are completed."""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from runtime.service import RuntimeFailure
from tests.test_goal_planning import automation,google_setup,connected,composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release
from tests.test_workflow_query_integration import setup_query
from tests.test_data_queries import queries


def generated(f,queries,change):
    jobs,seen,inputs,body=setup_query(f,queries)
    provider=f.general.planner.provider.plan_actions
    def select(goal,context):
        proposal=deepcopy(provider(goal,context));change(proposal,len(seen))
        return proposal
    f.general.planner.provider=SimpleNamespace(plan_actions=select)
    return jobs,seen,body


def test_known_ancestor_evidence_becomes_explicit_dependency(automation,queries):
    f=automation
    def change(p,call):next(a for a in p['actions'] if a['action_id']=='email')['evidence_references'].append('read')
    jobs,seen,body=generated(f,queries,change)
    doc=f.c.prepare_actions(f.x.a,body)
    email=next(a for a in doc['action_plan']['actions'] if a['action_id']=='email')
    assert 'read' in email['depends_on'] and 'read' in email['evidence_references']
    assert len(seen)==1 and not jobs.list(f.x.a)['items']
    assert not f.http.sent and f.http.write_count==0


def test_unknown_evidence_gets_precise_bounded_correction(automation,queries):
    f=automation
    def change(p,call):
        if call==1:next(a for a in p['actions'] if a['action_id']=='analysis')['evidence_references']=['fictional_source']
    jobs,seen,body=generated(f,queries,change)
    doc=f.c.prepare_actions(f.x.a,body)
    assert len(seen)==2
    feedback=seen[1]['validation_feedback'];issue=feedback['binding_issue']
    assert feedback['error_code']=='ACTION_CONTENT_UNVERIFIED'
    assert issue['action_id']=='analysis' and issue['invalid_references']==['fictional_source']
    assert 'read' in issue['allowed_references']
    assert doc['google_connection_id']==f.connection
    assert not jobs.list(f.x.a)['items'] and not f.http.sent and f.http.write_count==0


@pytest.mark.parametrize('bad_reference',['fictional_source','analysis'])
def test_repeated_unknown_or_self_reference_stops_after_one_correction(automation,queries,bad_reference):
    f=automation
    def change(p,call):next(a for a in p['actions'] if a['action_id']=='analysis')['evidence_references']=[bad_reference]
    jobs,seen,body=generated(f,queries,change)
    with pytest.raises(RuntimeFailure) as error:f.c.prepare_actions(f.x.a,body)
    assert error.value.code=='ACTION_CONTENT_UNVERIFIED' and len(seen)==2
    assert error.value.binding_issue['invalid_references']==[bad_reference]
    assert not jobs.list(f.x.a)['items'] and not f.http.sent and f.http.write_count==0


def test_explicit_unknown_reference_is_not_silently_removed(automation,queries):
    f=automation
    def change(p,call):next(a for a in p['actions'] if a['action_id']=='analysis')['evidence_references']=['fictional_source']
    jobs,seen,body=generated(f,queries,change)
    body['action_plan']=f.general.planner.provider.plan_actions(body['objective'],{})
    with pytest.raises(RuntimeFailure) as error:f.c.prepare_actions(f.x.a,body)
    assert error.value.code=='ACTION_CONTENT_UNVERIFIED' and len(seen)==1
    assert not jobs.list(f.x.a)['items'] and not f.http.sent and f.http.write_count==0


@pytest.mark.parametrize('variant',['cycle','conditional'])
def test_evidence_edges_cannot_bypass_graph_guards(automation,queries,variant):
    f=automation
    def change(p,call):
        read=next(a for a in p['actions'] if a['action_id']=='read')
        if variant=='cycle':read['evidence_references']=['analysis']
        else:
            read.update(optional=True,when={'binding':{'kind':'literal','key':'enabled','path':[],'target':['enabled']},'equals':True})
    jobs,seen,body=generated(f,queries,change)
    body['user_values']={'enabled':True}
    with pytest.raises(RuntimeFailure) as error:f.c.prepare_actions(f.x.a,body)
    assert error.value.code in ['ACTION_BINDING_INVALID','ACTION_DEPENDENCY_INVALID']
    assert not jobs.list(f.x.a)['items'] and not f.http.sent and f.http.write_count==0


def test_pinned_evidence_identity_is_not_reinterpreted_as_action():
    from workflow_api.goal_inputs import complete_binding_dependencies
    actions=[dict(action_id='pinned',depends_on=[],evidence_references=[],bindings=[]),dict(action_id='report',depends_on=[],evidence_references=['pinned','unknown'],bindings=[])]
    before=deepcopy(actions)
    complete_binding_dependencies(actions,pinned_evidence={'pinned'})
    assert actions==before


def test_completed_evidence_dependency_executes_through_real_runtime(automation,queries):
    from tests.test_connected_action_plans import compile_run,complete,stored
    f=automation
    def change(p,call):next(a for a in p['actions'] if a['action_id']=='email')['evidence_references'].append('read')
    jobs,seen,body=generated(f,queries,change)
    doc,w,rid=compile_run(f,body)
    assert f.runner.advance(rid,f.x.a)['status']=='running'
    assert stored(f,rid)['action_instances']['read']['state']=='waiting_for_query'
    assert not f.http.sent and f.http.write_count==0
    assert jobs.tick();f.now+=2
    assert complete(f,w,rid)['status']=='completed'
    assert len(queries.reader.calls)==1 and len(f.http.sent)==1 and f.http.write_count==1
