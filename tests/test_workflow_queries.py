"""Controlled complete-population workflow queries; no live model/provider calls."""
from copy import deepcopy
import json

import pytest
from jsonschema import Draft202012Validator

from tests.test_data_queries import queries, plan
from tests.test_data_relationships import auth
from workflow_api.data_query_jobs import DataQueryJobs
from workflow_api.workflow_queries import WorkflowQueries, QueryPending, INPUT, OUTPUT
from runtime.service import RuntimeFailure

@pytest.fixture
def capability(queries):
    a=auth()
    jobs=DataQueryJobs(queries,lambda w,o:a if (w,o)==('one','alice') else None)
    pin=queries.catalogue(a)['context_hash']
    root=WorkflowQueries(queries,jobs)
    workflow={'metadata':{'action_binding_context':{'validated_context':{'data_query_catalog':{'context_hash':pin}}}}}
    return root.bind_context(workflow,{},a,{}),workflow

def invoke(c,query=None,effect='run:query'):
    return c.invoke({'tool_id':'workflow_data_query'},{'query':query or plan()},effect)

def finish(c,query=None,effect='run:query'):
    with pytest.raises(QueryPending) as pending:invoke(c,query,effect)
    assert c.jobs.tick()
    return invoke(c,query,effect),pending.value.job

def test_complete_population_result_and_durable_reattachment(capability):
    c,w=capability
    result,job=finish(c)
    Draft202012Validator(OUTPUT).validate(result)
    assert result['result']['rows']==[{'sales':'33.360'}]
    assert result['result']['matched_rows']==3 and result['coverage']['complete_scan']
    restored=WorkflowQueries(c.queries,c.jobs).bind_context(w,{},auth(),{})
    assert invoke(restored)==result
    assert len(c.jobs.list(auth())['items'])==1
    assert len(c.queries.reader.calls)==1

@pytest.mark.parametrize('metric,expected',[('count',3),('min',2),('max',4),('avg','3')])
def test_inclusive_population_range_and_aggregates(capability,metric,expected):
    c,_=capability
    p=plan();p.update(filters=[dict(field_id='pg_lines_qty',op='gte',value=2),dict(field_id='pg_lines_qty',op='lte',value=4)],
        metrics=[dict(label='value',op=metric,expression='pg_lines_qty')],limit=1)
    result,_=finish(c,p)
    assert str(result['result']['rows'][0]['value'])==str(expected)
    assert result['result']['matched_rows']==3
    assert result['coverage']['aggregate_complete']

def test_detail_limit_is_not_population_denominator(capability):
    c,_=capability;p=plan();p.update(metrics=[],fields=['pg_lines_qty'],limit=1)
    r,_=finish(c,p)
    assert len(r['result']['rows'])==1 and r['result']['matched_rows']==3
    assert r['coverage']==dict(complete_scan=True,aggregate_complete=False,returned_rows=1,total_result_rows=3,has_more=True)

@pytest.mark.parametrize('change',['query','metadata','permission','foreign_account'])
def test_changed_scope_and_query_never_reuse_a_result(capability,change):
    c,w=capability;r,_=finish(c)
    if change=='query':
        p=plan();p['limit']=2
        with pytest.raises(RuntimeFailure) as exc:invoke(c,p)
        assert exc.value.code=='DATA_QUERY_CONFLICT'
    elif change=='metadata':
        with c.queries.store.transaction() as db:
            row=db.execute('SELECT document FROM data_source_connections WHERE connection_id=?',('pg',)).fetchone()
            doc=json.loads(row[0]);doc['generation']+=1
            db.execute('UPDATE data_source_connections SET document=? WHERE connection_id=?',(json.dumps(doc),'pg'))
        with pytest.raises(RuntimeFailure) as exc:invoke(c)
        assert exc.value.code=='DATA_QUERY_STALE'
    elif change=='permission':
        c.auth['permissions']=['tools.read']
        with pytest.raises(RuntimeFailure) as exc:invoke(c)
        assert exc.value.code=='OPERATION_NOT_AUTHORIZED'
    else:
        with pytest.raises(RuntimeFailure) as exc:WorkflowQueries(c.queries,c.jobs).bind_context(w,{},auth('bob'),{})
    assert len(c.queries.reader.calls)==1

def test_each_occurrence_gets_fresh_query_and_current_data(capability):
    c,_=capability;one,_=finish(c,effect='occurrence1:query')
    c.queries.reader.rows['pg_lines'][0]['pg_lines_qty']=10
    two,_=finish(c,effect='occurrence2:query')
    assert one['query_id']!=two['query_id']
    assert two['result']['rows']==[{'sales':'106.800'}]

def test_clarification_and_invalid_fields_do_not_read(capability):
    c,_=capability;p=plan();p['clarification']='Which date range?'
    with pytest.raises(RuntimeFailure) as exc:invoke(c,p)
    assert exc.value.code=='ACTION_INPUT_REQUIRED'
    p=plan();p['fields']=['foreign'];p['metrics']=[]
    with pytest.raises(RuntimeFailure):invoke(c,p)
    assert not c.queries.reader.calls


def test_strict_query_model_schema_matches_engine_contract():
    from runtime.model_protocol import closed_payload
    assert closed_payload(INPUT)
    Draft202012Validator(INPUT).validate({'query':plan()})


def test_sampled_result_cannot_become_population_evidence(capability,monkeypatch):
    c,_=capability
    with pytest.raises(QueryPending):invoke(c)
    assert c.jobs.tick()
    original=c.jobs.result
    def sample(auth,job):
        result=original(auth,job);result['execution']['strategy']='mongodb_evidence_sample'
        return result
    monkeypatch.setattr(c.jobs,'result',sample)
    with pytest.raises(RuntimeFailure) as error:invoke(c)
    assert error.value.code=='DATA_QUERY_INCOMPLETE'


def test_reviewed_objective_scope_cannot_expand_to_other_owned_sources(capability):
    c,w=capability
    catalog=w['metadata']['action_binding_context']['validated_context']['data_query_catalog']
    catalog['datasets']=[{'dataset_id':'mongo_categories'}]
    scoped=WorkflowQueries(c.queries,c.jobs).bind_context(w,{},auth(),{})
    with pytest.raises(RuntimeFailure) as error:invoke(scoped)
    assert error.value.code=='DATA_QUERY_SCOPE_DENIED'
    assert not c.queries.reader.calls
