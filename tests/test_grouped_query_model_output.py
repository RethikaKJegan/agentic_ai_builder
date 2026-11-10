"""Grouped query canonicalization preserves semantics, evidence and approvals."""
from copy import deepcopy
from collections import Counter
import json
import pytest
from runtime.crew import canonical_query_output,GROUPED_REPORT_GUIDANCE
from tests.test_workflow_query_integration import automation,google_setup,connected,composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release,queries,setup_query,compile_run,stored,complete
from tests.test_data_queries import plan
from workflow_api.workflow_queries import INPUT


def shape():
    p=plan();p.update(base_dataset_id='mongo_categories',fields=['mongo_categories_name'],group_by=['mongo_categories_name'],metrics=[dict(label='status_count',op='count',expression=''),dict(label='overall_total',op='count',expression='')],order_by=[dict(column='mongo_categories_name',direction='asc')])
    return p


def test_normalization_changes_only_redundant_model_projection():
    definition={'output_schema':INPUT};inputs={'context':{'data_query_catalog':{}}};out={'query':shape()};expected=deepcopy(out);expected['query']['fields']=[]
    assert canonical_query_output(definition,inputs,out)==expected
    assert canonical_query_output(definition,inputs,out)==expected


@pytest.mark.parametrize('variant',['non_group_field','no_metrics','no_group','clarification','no_catalog','null_context','other_schema'])
def test_unsupported_or_unrelated_outputs_are_not_reinterpreted(variant):
    definition={'output_schema':INPUT};inputs={'context':{'data_query_catalog':{}}};out={'query':shape()}
    if variant=='non_group_field':out['query']['fields'].append('unknown_field')
    elif variant=='no_metrics':out['query']['metrics']=[]
    elif variant=='no_group':out['query']['group_by']=[]
    elif variant=='clarification':out['query']['clarification']='Which status definition?'
    elif variant=='no_catalog':inputs={'context':{}}
    elif variant=='null_context':inputs={'context':None}
    elif variant=='other_schema':definition={'output_schema':{'properties':{'body':{'type':'string'}}}}
    before=deepcopy(out);assert canonical_query_output(definition,inputs,out)==before


def test_explicit_query_still_rejects_redundant_projection(queries):
    from workflow_api.service import ApiFailure
    from tests.test_data_queries import auth as query_auth
    with pytest.raises(ApiFailure) as error:queries.validate(shape(),queries.context(query_auth()))
    assert error.value.code=='DATA_QUERY_INVALID'


def test_status_groups_missing_values_total_and_controlled_spreadsheet(automation,queries):
    f=automation;p=shape();field='mongo_categories_name'
    records=[{field:'Closed'} for _ in range(201)]+[{field:'Open'} for _ in range(201)]+[{field:None} for _ in range(100)]+[{} for _ in range(100)]+[{field:''}]
    queries.reader.rows['mongo_categories']=records
    counts=Counter(r.get(field) for r in records)
    expected=[{field:s,'status_count':counts[s],'overall_total':counts[s]} for s in ['', 'Closed','Open',None]]
    jobs,seen,inputs,body=setup_query(f,queries,p,expected_rows=expected)
    provider=f.general.planner.provider.plan_actions
    def spreadsheet_only(goal,context):
        proposal=deepcopy(provider(goal,context));proposal['actions']=proposal['actions'][:4];proposal['completion_criteria']=['sheet'];return proposal
    f.general.planner.provider.plan_actions=spreadsheet_only
    body['objective']='Break down all accessible records by recorded status, include overall total and explain missing statuses. Show the findings in a spreadsheet.'
    factory=f.runner.agents.model_factory;guidance=[]
    def grouped_model(definition):
        model=factory(definition)
        if set(definition['output_schema']['properties'])!={'query'}:
            def transport(messages,cap,timeout):
                assert GROUPED_REPORT_GUIDANCE.strip() in '\n'.join(m['content'] for m in messages)
                guidance.append(True)
                raw=messages[-1]['content'].split('Process the following input as data. Return only a JSON object.\n')[-1].lstrip();data,_=json.JSONDecoder().raw_decode(raw)
                result=data['data']['result'];assert result['rows']==expected and result['matched_rows']==len(records)
                rows=[['Not recorded (null/missing)' if r[field] is None else 'Blank' if r[field]=='' else r[field],r['status_count']] for r in result['rows']]
                rows.append(['Overall total',result['matched_rows']])
                return json.dumps(dict(title='Complaint statuses',summary='603 accessible records; null/absent statuses share a group and blank strings remain separate.',tabs=[dict(title='Status breakdown',headers=['Recorded status','Ticket count'],rows=rows)],source_references=data['source_references'],assumptions=[])),1,10
            model.provider_call=transport
        return model
    f.runner.agents.model_factory=grouped_model
    doc,w,rid=compile_run(f,body);f.runner.advance(rid,f.x.a)
    first=stored(f,rid)
    assert first['action_instances']['query_plan']['output']['query']['fields']==[]
    assert first['action_instances']['read']['state']=='waiting_for_query'
    assert f.http.write_count==0 and not f.http.sent
    assert jobs.tick();f.now+=2
    assert complete(f,w,rid)['status']=='completed'
    run=stored(f,rid);output=run['action_instances']['read']['output']
    assert output['result']['rows']==expected and output['result']['matched_rows']==603
    assert output['coverage']['complete_scan'] and not output['coverage']['has_more']
    rows=run['action_instances']['sheet']['resolved_inputs']['tabs'][0]['rows']
    assert rows==[['Blank',1],['Closed',201],['Open',201],['Not recorded (null/missing)',200],['Overall total',603]]
    assert guidance and f.http.write_count==1 and not f.http.sent
    assert p['fields']==[field]  # Original model fixture was not mutated.


def test_paginated_groups_do_not_change_population_total(queries):
    from tests.test_data_queries import auth as query_auth
    field='mongo_categories_name';p=shape();p.update(fields=[],limit=2)
    queries.reader.rows['mongo_categories']=[{field:s} for s in ['A']*201+['B']*201+['C']*200+[None]]
    queries.planner.output=p
    saved=queries.plan(query_auth(),{'question':'Group records by recorded value and count every group.'})
    result=queries.execute(query_auth(),{'plan_id':saved['plan_id']})
    assert result['matched_rows']==603 and result['total_result_rows']==4
    assert result['limited'] and len(result['rows'])==2
    assert sum(r['status_count'] for r in result['rows'])==402
