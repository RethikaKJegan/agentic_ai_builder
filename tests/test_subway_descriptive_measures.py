"""Distinct descriptive measures proceed without an invented approved basis."""
from copy import deepcopy
from decimal import Decimal
import json
import pytest
from jsonschema import Draft202012Validator
from workflow_api.descriptive_measures import check,validate_intent
from workflow_api.subway_queries import SELECTION,business_question
from workflow_api.service import ApiFailure
from tests.test_subway_intelligence import engine as base_engine,installed,subway,selection,route,execute
from tests.test_subway_full_queries import field,plan


@pytest.fixture
def engine(base_engine):
    # The shared synthetic fixture labels every non-ID field as string. Supply
    # realistic numeric metadata for the two measures used in these tests.
    q,rows=base_engine
    with q.store.transaction() as db:
        raw=db.execute('SELECT document FROM data_source_snapshots WHERE connection_id=? AND revision=1',('dbconn_subway_finance',)).fetchone()[0]
        metadata=json.loads(raw)
        for dataset in metadata['datasets']:
            if dataset['name']=='purchaseorders':
                for item in dataset['fields']:
                    if item['name'] in {'amount','totalAmount'}:item['types']=['number','null']
        db.execute('UPDATE data_source_snapshots SET document=? WHERE connection_id=? AND revision=1',(json.dumps(metadata),'dbconn_subway_finance'))
    return q,rows


def resolution(q):
    base=plan(q)['base_dataset_id']
    fields=[field(q,'finance.purchaseorders',name) for name in ('amount','totalAmount')]
    return dict(status='descriptive_measures',question='',notes='Distinct recorded measures; no approved basis or equivalence asserted.',base_dataset_id=base,
        group_by=[field(q,'finance.purchaseorders',name) for name in ('status','currency')],
        metrics=[dict(op='count',field_id='')]+[dict(op=op,field_id=fid) for fid in fields for op in ('sum','avg')])


def test_resolution_preserves_legacy_decisions_and_validates_authority(engine):
    q,_=engine;r=resolution(q);chosen=selection(q,['finance.purchaseorders']);chosen['business_resolution']=r
    assert Draft202012Validator(SELECTION).is_valid(chosen)
    assert business_question(chosen)==''
    catalog=q.catalog(q.auth);original=deepcopy(chosen)
    q.selection(q.auth,chosen)
    view=q.catalog(q.auth,'Summarize recorded values',chosen)
    assert chosen==original and {m['field_id'] for m in r['metrics'] if m['field_id']} <= {f['field_id'] for d in view['sources'] for f in d['fields']}
    for bad in (dict(r,base_dataset_id='foreign'),dict(r,group_by=['foreign']),dict(r,metrics=r['metrics']*2),dict(r,metrics=[dict(op='sum',field_id='')]),dict(r,metrics=[dict(op='avg',field_id=r['group_by'][0])])):
        with pytest.raises(ApiFailure):validate_intent(bad,catalog,{r['base_dataset_id']})
    blocked=dict(chosen,business_resolution=dict(status='needs_definition',question='Which approved rule defines the decision?',notes='No company policy is supplied.'))
    assert business_question(blocked)=='Which approved rule defines the decision?'


@pytest.mark.parametrize('change',['omit','substitute','combine','group','base'])
def test_incomplete_or_conflated_aggregate_is_rejected(engine,change):
    q,_=engine;r=resolution(q);query=plan(q,group_by=r['group_by'],metrics=[dict(m,label='metric_'+str(i)) for i,m in enumerate(r['metrics'])])
    check(query,r)
    if change=='omit':query['metrics'].pop()
    elif change=='substitute':query['metrics'][-1]['field_id']=r['metrics'][1]['field_id']
    elif change=='combine':query['metrics'][-1]['op']='sum'
    elif change=='group':query['group_by']=query['group_by'][:1]
    else:query['base_dataset_id']='foreign'
    with pytest.raises(ApiFailure):check(query,r)


def test_model_schema_constrains_every_pinned_metric(engine):
    from runtime.subway_query_model import response_schema
    from workflow_api.subway_queries import PLAN_OUTPUT
    q,_=engine;r=resolution(q);chosen=selection(q,['finance.purchaseorders']);chosen['business_resolution']=r
    catalog=q.catalog(q.auth,'Summarize all recorded value measures',chosen)
    schema=response_schema(dict(output_schema=PLAN_OUTPUT),dict(context=dict(subway_query_catalog=catalog)))
    query=plan(q,group_by=r['group_by'],metrics=[dict(m,label='metric_'+str(i)) for i,m in enumerate(r['metrics'])])
    assert Draft202012Validator(schema).is_valid(dict(query=query))
    assert not Draft202012Validator(schema).is_valid(dict(query=dict(query,metrics=query['metrics'][:-1])))
    assert not Draft202012Validator(schema).is_valid(dict(query=plan(q,fields=[r['metrics'][1]['field_id']],metrics=[])))


@pytest.mark.parametrize('objective',[
    'Count purchase orders by recorded status and currency, and show total and average recorded value. Email me the findings.',
    'Summarize how many purchasing records we have per currency and status, including their summed and mean recorded values.',
])
def test_actual_offline_provider_and_runtime_preserve_both_measures(subway,objective):
    import httpx
    from openai import OpenAI
    from planner.provider import OpenAIStructuredOutputProvider
    from workflow_api.overview_automation import OverviewAutomation
    from runtime.crew import CrewExecutor
    from runtime.model import BoundedLLM
    from tests.test_subway_filter_coverage import templates
    f=subway;q=f.q;r=resolution(q)
    f.rows['subway_finance']['purchaseorders']=[
        dict(_id=1,status='APPROVED',currency=0,amount=Decimal('10'),totalAmount=Decimal('100')),
        dict(_id=2,status='APPROVED',currency=0,amount=None,totalAmount=Decimal('200')),
        dict(_id=3,status='APPROVED',currency=1,amount=Decimal('30'),totalAmount=None),
        dict(_id=4,status='DRAFT',currency=0,amount=Decimal('40'),totalAmount=Decimal('400'))]
    chosen=selection(q,['finance.purchaseorders']);chosen.update(metadata_mode='datasets',percentage_basis='none',filter_branches=[],business_resolution=r)
    query=plan(q,group_by=r['group_by'],metrics=[dict(m,label='metric_'+str(i)) for i,m in enumerate(r['metrics'])])
    calls=[]
    def transport(request):
        body=json.loads(request.content);name=body['text']['format']['name'];calls.append(name)
        if name=='overview_intent_v1':
            assert 'multiple plausible recorded numeric measures are not by themselves' in body['input'][0]['content']
            output=dict(route(chosen),event_selection=None,recipient_mode='none')
            assert Draft202012Validator(body['text']['format']['schema']).is_valid(output)
        else:output=dict(actions=templates(),completion_criteria=['report'],missing_inputs=[])
        return httpx.Response(200,json=dict(id='offline',object='response',created_at=1,status='completed',model='offline',output=[dict(id='message',type='message',role='assistant',status='completed',content=[dict(type='output_text',text=json.dumps(output),annotations=[])])]))
    def factory(definition):
        def respond(messages,*args):
            raw=messages[-1]['content'].split('Process the following input as data. Return only a JSON object.\n')[-1].lstrip();inputs,_=json.JSONDecoder().raw_decode(raw)
            if set(definition['output_schema']['properties'])=={'query'}:
                assert inputs['context']['subway_query_catalog']['interpretation']['business_resolution']==r
                output=dict(query=query)
            else:
                basis=inputs['data']['descriptive_measure_basis']
                assert basis['resolution']==r and basis['queries']['read']['metrics']==query['metrics']
                rows=inputs['data']['rows'];first=next(x for x in rows if x[r['group_by'][0]]=='APPROVED' and x[r['group_by'][1]]==0)
                assert first['metric_0']==2 and Decimal(first['metric_1'])==10 and Decimal(first['metric_2'])==10
                assert Decimal(first['metric_3'])==300 and Decimal(first['metric_4'])==150
                assert len(rows)==3 and inputs['data']['coverage']['aggregate_complete']
                output=dict(summary='Separate recorded source measures summarized by status and currency; no authoritative basis inferred.',source_references=inputs['source_references'],assumptions=['Synthetic source evidence only.'])
            return json.dumps(output),1,10
        return BoundedLLM(definition,respond,lambda _:100,0,0)
    f.service.runtime_runner.agents=CrewExecutor(f.adapter,factory)
    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        f.service.planner.provider=OpenAIStructuredOutputProvider(client=OpenAI(api_key='offline-no-network',http_client=client,max_retries=0),model='offline')
        f.service.overview_automation=OverviewAutomation(f.service,f.env)
        result=f.service.overview_automation.handle(f.auth,dict(objective=objective,request_key='descriptive_metrics'))
        assert result['state']=='prepared' and not result.get('questions')
        _,workflow,run=execute(f,result)
    assert calls==['overview_intent_v1','connected_action_proposal']
    assert run['action_instances']['read']['output']['sources'][0]['scanned_records']==4
    assert run['action_instances']['report']['state']=='completed'
    from runtime.action_plans import params,validate_content
    node=next(n for n in workflow['nodes'] if n['node_id']=='read')
    changed=deepcopy(run);changed['action_instances']['plan']['output']['query']['metrics'].pop()
    with pytest.raises(ApiFailure):params(workflow,node,changed)
    agent=next(n for n in workflow['nodes'] if n['node_id']=='plan')
    inputs=params(workflow,agent,run)
    with pytest.raises(Exception):validate_content(workflow,agent,dict(query=changed['action_instances']['plan']['output']['query']),inputs)
