"""Generated query constraints and real offline CrewAI/runtime regressions."""
from copy import deepcopy
import json
import pytest
from jsonschema import Draft202012Validator
from runtime.crew import scoped_query_schema
from runtime.subway_query_model import GUIDANCE, canonical_projection
from runtime.action_plans import validate_content
from workflow_api.subway_queries import PLAN_OUTPUT, schema_identity_budget
from tests.test_subway_intelligence import engine, installed, subway, overview, selection, execute
from tests.test_subway_full_queries import field, plan


def catalog():
    return dict(sources=[dict(dataset_id='orders',fields=[dict(field_id='order_id'),dict(field_id='amount'),dict(field_id='currency')]),
                         dict(dataset_id='companies',fields=[dict(field_id='company_name')])],
                relationships=[dict(relationship_id='declared_company')])


def query(**changes):
    return dict(base_dataset_id='orders',fields=['order_id'],metrics=[],group_by=[],joins=[],filters=[],order_by=[],offset=0,limit=10,**changes) if not changes else {**query(),**changes}


def schema(c=None):
    return scoped_query_schema(dict(output_schema=deepcopy(PLAN_OUTPUT)),dict(context=dict(subway_query_catalog=c or catalog())))


def test_model_contract_excludes_mixed_detail_and_count_and_keeps_aggregate_modes():
    v=Draft202012Validator(schema())
    assert v.is_valid({'query':query()})
    assert v.is_valid({'query':query(fields=[],metrics=[dict(label='records',op='count',field_id='')])})
    assert v.is_valid({'query':query(fields=[],group_by=['currency'],metrics=[dict(label='value',op='sum',field_id='amount')])})
    assert not v.is_valid({'query':query(metrics=[dict(label='records',op='count',field_id='')])})
    assert not v.is_valid({'query':query(fields=[],metrics=[])})
    assert not v.is_valid({'query':query(group_by=['currency'])})
    assert 'coverage.matched_records' in GUIDANCE


@pytest.mark.parametrize('change',[dict(base_dataset_id='foreign'),dict(fields=['vendor label']),dict(group_by=['foreign']),
    dict(joins=['invented']),dict(filters=[dict(field_id='foreign',op='eq',value='private')]),
    dict(fields=[],metrics=[dict(label='total',op='sum',field_id='foreign')])])
def test_all_identifier_positions_are_catalog_scoped(change):
    assert not Draft202012Validator(schema()).is_valid({'query':query(**change)})


def test_supported_join_and_provider_budget_and_immutable_original():
    original=deepcopy(PLAN_OUTPUT);c=catalog();s=schema(c)
    assert Draft202012Validator(s).is_valid({'query':query(fields=['order_id','company_name'],joins=['declared_company'])})
    assert PLAN_OUTPUT==original
    assert min(schema_identity_budget(s))>=0
    c['relationships']=[]
    assert not Draft202012Validator(schema(c)).is_valid({'query':query(joins=['declared_company'])})
    c['sources'][0]['fields']=[dict(field_id='field_'+str(i)) for i in range(1400)]
    assert min(schema_identity_budget(schema(c)))>=0  # Falls back to bounded mode constraints.


def test_only_redundant_generated_group_projection_is_canonicalized():
    q=query(fields=['currency'],group_by=['currency'],metrics=[dict(label='total',op='sum',field_id='amount')])
    before=deepcopy(q);assert canonical_projection(q)['fields']==[];assert q==before
    assert canonical_projection(query(fields=['order_id'],group_by=['currency'],metrics=q['metrics']))['fields']==['order_id']
    assert canonical_projection(query())==query()


@pytest.mark.parametrize('mode',['detail','aggregate'])
def test_offline_model_transport_and_runtime_keep_complete_counts_and_currency(subway,mode):
    from runtime.crew import CrewExecutor
    from runtime.model import BoundedLLM
    f=subway;q=f.q
    amount=field(q,'finance.purchaseorders','totalAmount');currency=field(q,'finance.purchaseorders','currency');identifier=field(q,'finance.purchaseorders','poNumber')
    for i,row in enumerate(f.rows['subway_finance']['purchaseorders']):row['currency']=i%2
    f.query=plan(q,fields=[identifier,currency,amount],metrics=[],order_by=[dict(column=currency,direction='asc'),dict(column=amount,direction='desc')],limit=7) if mode=='detail' else plan(q,group_by=[currency],metrics=[dict(label='total',op='sum',field_id=amount)],limit=7)
    seen=[]
    def factory(definition):
        def respond(messages,cap,timeout):
            text=messages[-1]['content'].split('Process the following input as data. Return only a JSON object.\n')[-1].lstrip()
            inputs,_=json.JSONDecoder().raw_decode(text)
            if set(definition['output_schema']['properties'])=={'query'}:
                output={'query':deepcopy(f.query)}
                assert bridge.structured_format['name']=='scoped_read_query'
                assert Draft202012Validator(bridge.structured_format['schema']).is_valid(output)
                assert 'coverage.matched_records' in json.dumps(messages)
                seen.append(bridge.structured_format)
            else:output=dict(summary='Controlled complete-scan evidence report.',source_references=inputs['source_references'],assumptions=[])
            return json.dumps(output),1,10
        bridge=BoundedLLM(definition,respond,lambda _:100,0,0)
        return bridge
    f.service.runtime_runner.agents=CrewExecutor(f.adapter,factory)
    result=overview(f,'Rank purchase orders and vendor values; keep currencies separate and report complete matching counts.',selection(q,['finance.purchaseorders']))
    _,_,run=execute(f,result)
    receipt=run['action_instances']['read']['output']
    assert receipt['coverage']['complete_scan'] and receipt['coverage']['matched_records']==100
    assert seen and run['status']=='completed'
    if mode=='detail':assert len(receipt['rows'])==7 and receipt['coverage']['has_more']
    else:assert len(receipt['rows'])==2 and {r[currency] for r in receipt['rows']}=={0,1}


def test_strict_validator_keeps_unsupported_join_and_non_group_field_denied():
    from runtime.service import RuntimeFailure
    workflow={'metadata':{'connected_action_plan':{'actions':[{'action_id':'plan','capability_id':'subway.plan_query'}]}}}
    inputs=dict(context=dict(subway_query_catalog=catalog()))
    for change in (dict(joins=['invented']),dict(fields=['order_id'],group_by=['currency'],metrics=[dict(label='total',op='sum',field_id='amount')])):
        with pytest.raises(RuntimeFailure) as caught:validate_content(workflow,dict(node_id='plan'),{'query':query(**change)},inputs)
        assert caught.value.code=='AGENT_OUTPUT_INVALID' and caught.value.invalid_model_output


def test_rejected_model_query_records_safe_rule_without_running_source(subway):
    f=subway;q=f.q;identifier=field(q,'finance.purchaseorders','poNumber')
    f.query=plan(q,fields=[identifier])  # Intentionally mix detail fields and count.
    result=overview(f,'List orders and retain the complete matching count.',selection(q,['finance.purchaseorders']))
    c=f.service.business_composition;doc=c.get(f.auth,result['composition_id']);w=c.workflow(f.auth,doc['composition_id'])
    assert f.adapter.approve_pending(w,f.auth)['ready']
    grants=f.adapter.execution_assignments(w,f.auth)
    for a in w['agents']:a['allowed_tool_ids']=[g['tool_id'] for g in grants if g['agent_id']==a['agent_id']]
    w['status']='approved';w['metadata'].update(approved_by='controlled-test',validation_state='validated')
    with f.service.store.transaction() as db:f.service.store.put(db,'client-subway',w)
    runtime=f.service.runtime_runner.runtime
    run=runtime.create_run(dict(request_id='shape_negative',idempotency_key='shape_negative',payload=dict(workflow_id=w['workflow_id'],workflow_version=1,inputs={})),f.auth)
    failed=f.service.runtime_runner.advance(run['run_id'],f.auth)
    assert failed['status']=='failed'
    with f.service.store.transaction(write=False) as db:
        saved=runtime.load(db,run['run_id'],f.auth)
    assert saved['error_code']=='AGENT_OUTPUT_INVALID'
    assert saved['action_instances']['read']['state']=='pending'
    assert len(f.model_inputs)==1  # No increased retry allowance.
    events=runtime.events(run['run_id'],f.auth)['items']
    rejected=[e for e in events if e['event_type']=='agent.output_rejected']
    assert rejected and 'Use projected fields' in rejected[0]['details']['validation_rule']
    assert identifier not in json.dumps(rejected)
