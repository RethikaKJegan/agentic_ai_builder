"""Conjunction safety and alternative-condition workflows without source sampling."""
from copy import deepcopy
from decimal import Decimal
import json
import pytest
from workflow_api.query_predicates import validate_conjunction,FILTER_GUIDANCE
from workflow_api.service import ApiFailure
from tests.test_subway_intelligence import engine,installed,subway,overview,selection,execute
from tests.test_subway_full_queries import AUTH,field,plan


def predicate(op,value=None,fid='x'):return dict(field_id=fid,op=op,value=value)


@pytest.mark.parametrize('predicates',[
    [predicate('is_null'),predicate('lt',0)],
    [predicate('eq'),predicate('gte',0)],
    [predicate('is_null'),predicate('not_null')],
    [predicate('ne'),predicate('eq')],
    [predicate('eq',1),predicate('eq',2)],
    [predicate('eq',1),predicate('ne',1)],
    [predicate('gt',10),predicate('lte',10)],
    [predicate('gte',10),predicate('lt',10)],
    [predicate('gt',11),predicate('lt',10)],
    [predicate('eq',9),predicate('gte',10)],
    [predicate('eq',12),predicate('lte',10)],
    [predicate('lt',None)],
])
def test_provably_impossible_conjunction_is_rejected_without_rewriting(predicates):
    before=deepcopy(predicates)
    with pytest.raises(ApiFailure) as caught:validate_conjunction(predicates,{'x':{'types':['number']}})
    assert caught.value.code=='SUBWAY_QUERY_INVALID' and predicates==before


@pytest.mark.parametrize('predicates',[
    [predicate('lt',0)], [predicate('is_null')],
    [predicate('is_null'),predicate('ne',1)],
    [predicate('gte',-5),predicate('lt',10)],
    [predicate('gte',10),predicate('lte',10)],
    [predicate('eq',10),predicate('gte',10),predicate('lte',10)],
    [predicate('ne',1),predicate('ne',2)],
    [predicate('eq',1),predicate('eq',1)],
    [predicate('is_null'),predicate('lt',0,'y')],
])
def test_compatible_conjunctions_are_unchanged(predicates):
    before=deepcopy(predicates);validate_conjunction(predicates,{'x':{'types':['number']},'y':{'types':['number']}});assert predicates==before


def test_date_and_objectid_equality_follow_native_value_equivalence():
    validate_conjunction([predicate('eq','2026-01-01T00:00:00Z'),predicate('eq','2026-01-01T05:30:00+05:30')],{'x':{'types':['datetime']}})
    validate_conjunction([predicate('eq','abcdefabcdefabcdefabcdef'),predicate('eq','ABCDEFABCDEFABCDEFABCDEF')],{'x':{'types':['ObjectId']}})


def test_contradictory_filters_never_open_a_source_and_valid_empty_results_remain(engine,monkeypatch):
    q,rows=engine;amount=field(q,'finance.lineitems','availableAmount')
    query=plan(q,'finance.lineitems',filters=[predicate('lt',0,amount),predicate('is_null',None,amount)])
    with monkeypatch.context() as patch:
        patch.setattr(q.sources.manager.adapter,'connection',lambda *_:pytest.fail('Invalid query dispatched to source'))
        with pytest.raises(ApiFailure):q.execute(AUTH,query)
    rows['subway_finance']['lineitems']=[dict(_id=1,availableAmount=0),dict(_id=2,availableAmount=8)]
    empty=q.execute(AUTH,dict(query,filters=[predicate('lt',0,amount)]))
    assert empty['coverage']['matched_records']==0 and empty['coverage']['complete_scan']
    assert empty['rows']==[{'records':0}]


def test_real_runtime_keeps_alternative_branch_counts_and_common_constraints(subway):
    from runtime.crew import CrewExecutor
    from runtime.model import BoundedLLM
    from tests.test_connected_action_plans import action,bind
    f=subway;q=f.q
    f.rows['subway_finance']['lineitems']=[dict(_id=1,name='included',availableAmount=-5),dict(_id=2,name='included',availableAmount=Decimal('-.01')),dict(_id=3,name='included',availableAmount=0),dict(_id=4,name='included',availableAmount=7),dict(_id=5,name='included',availableAmount=None),dict(_id=6,name='included'),dict(_id=7,name='excluded',availableAmount=-100),dict(_id=8,name='excluded',availableAmount=None)]
    amount=field(q,'finance.lineitems','availableAmount');name=field(q,'finance.lineitems','name')
    shared=predicate('ne','excluded',name)
    queries={kind:plan(q,'finance.lineitems',filters=[deepcopy(shared),predicate(op,value,amount)]) for kind,op,value in [('negative','lt',0),('missing','is_null',None)]}
    def proposal(goal,context):
        assert FILTER_GUIDANCE in context['query_guidance']
        plans=[action('plan_'+kind,'subway.plan_query',[]) for kind in queries]
        for a in plans:a['budget'].update(max_llm_calls=1,max_tool_calls=0)
        reads=[action('read_'+kind,'tool.subway_query',[bind('output','query',action='plan_'+kind,path=['query'])],['plan_'+kind]) for kind in queries]
        for a in reads:a['budget']['timeout_seconds']=120
        report=action('report','content.prepare',[bind('output','data',action='read_negative')],['read_negative','read_missing'],['read_negative','read_missing'])
        return dict(actions=plans+reads+[report],completion_criteria=['report'],missing_inputs=[])
    f.service.planner.provider.plan_actions=proposal
    def factory(definition):
        def respond(messages,*args):
            raw=messages[-1]['content'].split('Process the following input as data. Return only a JSON object.\n')[-1].lstrip();inputs,_=json.JSONDecoder().raw_decode(raw)
            if set(definition['output_schema']['properties'])=={'query'}:
                assert FILTER_GUIDANCE in json.dumps(messages)
                output={'query':queries[inputs['task_id'].removeprefix('plan_')]}
            else:
                assert inputs['data']['primary']['coverage']['matched_records']==2
                assert inputs['data']['upstream_results']['read_missing']['coverage']['matched_records']==2
                output=dict(summary='Controlled evidence: 2 negative records and 2 missing/null records within the shared source scope.',source_references=inputs['source_references'],assumptions=['Separate complete branch counts; no inference of current production state or policy breach.'])
            return json.dumps(output),1,10
        return BoundedLLM(definition,respond,lambda _:100,0,0)
    f.service.runtime_runner.agents=CrewExecutor(f.adapter,factory)
    chosen=selection(q,['finance.lineitems']);chosen['metadata_mode']='datasets'
    result=overview(f,'Review recorded line-item values below zero or not recorded, excluding the named excluded category, and summarize each category.',chosen)
    _,_,run=execute(f,result)
    for kind in queries:
        receipt=run['action_instances']['read_'+kind]['output']
        assert receipt['rows']==[{'records':2}]
        assert receipt['coverage']['complete_scan'] and receipt['sources'][0]['scanned_records']==8
    assert run['action_instances']['report']['state']=='completed'
