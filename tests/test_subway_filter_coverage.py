"""Intent alternatives cannot disappear in a one-query planner proposal."""
from copy import deepcopy
import json
import pytest
from jsonschema import Draft202012Validator
from workflow_api.query_branches import expand,check,validate_branches
from workflow_api.service import ApiFailure
from tests.test_subway_intelligence import engine,installed,subway,overview,selection,execute
from tests.test_subway_full_queries import field,plan
from tests.test_connected_action_plans import action,bind


def templates():
    p=action('plan','subway.plan_query',[]);p['budget'].update(max_llm_calls=1,max_tool_calls=0)
    r=action('read','tool.subway_query',[bind('output','query',action='plan',path=['query'])],['plan']);r['budget']['timeout_seconds']=120
    report=action('report','content.prepare',[bind('output','data',action='read')],['read'],['read'])
    return [p,r,report]


def branches():
    return [dict(base_dataset_id='source',filters=[dict(field_id='amount',op=op,value=value),dict(field_id='status',op='eq',value='included')]) for op,value in [('lt',0),('is_null',None)]]


def test_expansion_preserves_every_category_and_leaves_input_untouched():
    a=templates();before=deepcopy(a);b=branches();original=deepcopy(b)
    actions,completion,pins=expand(a,['report'],b)
    assert a==before and b==original
    assert len(actions)==5 and completion==['report']
    report=next(x for x in actions if x['action_id']=='report')
    assert report['depends_on']==report['evidence_references']==['read','read_category_2']
    assert pins['plan']==pins['read']==b[0]
    assert pins['plan_category_2']==pins['read_category_2']==b[1]
    read=next(x for x in actions if x['action_id']=='read_category_2')
    assert read['depends_on']==['plan_category_2'] and read['bindings'][0]['action_id']=='plan_category_2'
    assert expand(a,['report'],[])==(a,['report'],{})


@pytest.mark.parametrize('change',['extra_pair','conditional','unlinked','unreported','collision','budget'])
def test_unsafe_templates_are_rejected_before_review(change):
    a=templates()
    if change=='extra_pair':a.append(dict(a[0],action_id='another'))
    elif change=='conditional':a[0]['optional']=True
    elif change=='unlinked':a[1]['bindings'][0]['action_id']='unknown'
    elif change=='unreported':a[2]['depends_on']=[]
    elif change=='collision':a.append(action('plan_category_2','content.prepare',[]))
    else:a.extend(action('other_'+str(i),'content.prepare',[]) for i in range(12))
    with pytest.raises(Exception):expand(a,['report'],branches())


@pytest.mark.parametrize('change',['omitted','additional','wrong_base','duplicated'])
def test_exact_predicate_pin_rejects_changed_query(change):
    b=branches()[1];q=deepcopy(b)
    if change=='omitted':q['filters']=q['filters'][:1]
    elif change=='additional':q['filters'].append(dict(field_id='x',op='eq',value=1))
    elif change=='wrong_base':q['base_dataset_id']='foreign'
    else:q['filters']=[q['filters'][0]]*2
    with pytest.raises(ApiFailure):check(q,b)
    check(dict(b,filters=list(reversed(b['filters']))),b)


def test_branch_authority_contradictions_and_unknown_fields(engine):
    q,_=engine;c=q.catalog(q.auth);did=next(iter(c['datasets']));fid=next(f for f in c['fields'] if c['fields'][f]['dataset_id']==did)
    good=[dict(base_dataset_id=did,filters=[dict(field_id=fid,op=op,value=None)]) for op in ('is_null','not_null')]
    validate_branches(good,c,{did})
    for bad in ([good[0]],good*2,[dict(good[0],base_dataset_id='foreign'),good[1]], [dict(good[0],filters=[dict(field_id='foreign',op='is_null',value=None)]),good[1]], [dict(good[0],filters=good[0]['filters']+good[1]['filters']),good[1]]):
        with pytest.raises(ApiFailure):validate_branches(bad,c,{did})


@pytest.mark.parametrize('missing_count',[0,2])
def test_real_runtime_expands_single_query_and_reports_both_complete_counts(subway,missing_count):
    from runtime.crew import CrewExecutor
    from runtime.model import BoundedLLM
    f=subway;q=f.q
    rows=[dict(_id=1,name='included',availableAmount=-5),dict(_id=2,name='included',availableAmount=-1),dict(_id=3,name='included',availableAmount=0),dict(_id=4,name='excluded',availableAmount=None)]
    if missing_count:rows.extend([dict(_id=5,name='included'),dict(_id=6,name='included',availableAmount=None)])
    f.rows['subway_finance']['lineitems']=rows
    fid=field(q,'finance.lineitems','availableAmount');name=field(q,'finance.lineitems','name')
    base=plan(q,'finance.lineitems')['base_dataset_id']
    b=[dict(base_dataset_id=base,filters=[dict(field_id=fid,op=op,value=value),dict(field_id=name,op='eq',value='included')]) for op,value in [('lt',0),('is_null',None)]]
    chosen=selection(q,['finance.lineitems']);chosen.update(metadata_mode='datasets',filter_branches=b)
    def proposal(goal,context):
        assert context['binding_context']['validated_context']['subway_query_catalog']['interpretation']['filter_branches']==b
        return dict(actions=templates(),completion_criteria=['report'],missing_inputs=[])
    f.service.planner.provider.plan_actions=proposal
    def factory(definition):
        def respond(messages,*args):
            raw=messages[-1]['content'].split('Process the following input as data. Return only a JSON object.\n')[-1].lstrip();inputs,_=json.JSONDecoder().raw_decode(raw)
            if set(definition['output_schema']['properties'])=={'query'}:
                pin=inputs['context']['subway_filter_branch']
                output={'query':plan(q,'finance.lineitems',filters=pin['filters'])}
            else:
                data=inputs['data']
                assert data['primary']['coverage']['matched_records']==2
                assert data['upstream_results']['read_category_2']['coverage']['matched_records']==missing_count
                output=dict(summary='Verified separate category counts supplied for both requested alternatives.',source_references=inputs['source_references'],assumptions=['Categories may overlap; no distinct union count.'])
            return json.dumps(output),1,10
        return BoundedLLM(definition,respond,lambda _:100,0,0)
    f.service.runtime_runner.agents=CrewExecutor(f.adapter,factory)
    # Exercise actual intent and action provider transports with no network/model calls.
    import httpx
    from openai import OpenAI
    from planner.provider import OpenAIStructuredOutputProvider
    from workflow_api.overview_automation import OverviewAutomation
    from tests.test_subway_intelligence import route
    chosen['percentage_basis']='none'
    chosen['business_resolution']=dict(status='ready',question='',notes='Separate requested categories.')
    calls=[]
    def transport(request):
        body=json.loads(request.content);name=body['text']['format']['name'];calls.append(name)
        if name=='overview_intent_v1':
            schema=body['text']['format']['schema']
            assert 'filter_branches' in schema['properties']['subway_selection']['required']
            assert 'EVERY category' in body['input'][0]['content']
            output=dict(route(chosen),event_selection=None,recipient_mode='none')
            assert Draft202012Validator(schema).is_valid(output)
        else:
            inputs=json.loads(body['input'][1]['content']);output=proposal(inputs['objective'],inputs)
        return httpx.Response(200,json=dict(id='offline',object='response',created_at=1,status='completed',model='offline',output=[dict(id='message',type='message',role='assistant',status='completed',content=[dict(type='output_text',text=json.dumps(output),annotations=[])])]))
    objectives=['Review line-item balances below zero or missing, restricted to the included category, and report both counts.', 'Find negative balances and separately list unrecorded balances for included line items.']
    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        f.service.planner.provider=OpenAIStructuredOutputProvider(client=OpenAI(api_key='offline-no-network',http_client=client,max_retries=0),model='offline')
        f.service.overview_automation=OverviewAutomation(f.service,f.env)
        result=f.service.overview_automation.handle(f.auth,dict(objective=objectives[bool(missing_count)],request_key='alternative_transport'))
        _,workflow,run=execute(f,result)
    assert calls==['overview_intent_v1','connected_action_proposal']
    for aid,expected in [('read',2),('read_category_2',missing_count)]:
        receipt=run['action_instances'][aid]['output']
        assert receipt['coverage']['complete_scan'] and receipt['coverage']['matched_records']==expected
        assert receipt['sources'][0]['scanned_records']==len(rows)
    assert run['action_instances']['report']['state']=='completed'
    # Tool dispatch independently refuses a changed query even if model checking is bypassed.
    from runtime.action_plans import params
    changed=deepcopy(run);changed['action_instances']['plan']['output']['query']['filters']=[]
    node=next(n for n in workflow['nodes'] if n['node_id']=='read')
    with pytest.raises(ApiFailure):params(workflow,node,changed)
    changed=deepcopy(run);changed['action_instances']['read_category_2']['state']='failed'
    node=next(n for n in workflow['nodes'] if n['node_id']=='report')
    with pytest.raises(Exception):params(workflow,node,changed)


def test_model_schema_requires_pinned_literals_and_count():
    from runtime.subway_query_model import response_schema
    from workflow_api.subway_queries import PLAN_OUTPUT
    pin=branches()[0]
    catalog=dict(sources=[dict(dataset_id='source',fields=[dict(field_id='amount'),dict(field_id='status')])],relationships=[])
    schema=response_schema(dict(output_schema=PLAN_OUTPUT),dict(context=dict(subway_query_catalog=catalog,subway_filter_branch=pin)))
    query=dict(base_dataset_id='source',joins=[],fields=['amount'],filters=pin['filters'],metrics=[],group_by=[],order_by=[],offset=0,limit=1)
    assert Draft202012Validator(schema).is_valid(dict(query=query))
    assert not Draft202012Validator(schema).is_valid(dict(query=dict(query,filters=[])))
    assert not Draft202012Validator(schema).is_valid(dict(query=dict(query,base_dataset_id='foreign')))
