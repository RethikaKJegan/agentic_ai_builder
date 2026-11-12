"""Complete high-cardinality queries and byte-bounded display pagination."""
from copy import deepcopy
from decimal import Decimal
import json
import pytest
from tests.test_subway_full_queries import engine,installed,field,plan,AUTH
from workflow_api.subway_query_pages import GroupStore,bounded_page
from workflow_api.subway_queries import key
from workflow_api.business_compiler import canonical
from workflow_api.service import ApiFailure


def test_spill_preserves_numeric_group_identity_order_and_cleanup(tmp_path):
    with GroupStore(lambda:None,memory_groups=1,directory=tmp_path) as groups:
        groups.put((key(Decimal('1.00')),),{'value':Decimal('1.00'),'count':1})
        groups.put((key(2),),{'value':Decimal('2'),'count':1})
        assert groups.db is not None
        same=groups.get((key(1),));same['count']+=1;groups.put((key(1.0),),same)
        groups.put((None,),{'value':None,'count':1})
        assert len(groups)==3
        rows=groups.page(lambda g:g,[dict(column='value',direction='desc')],0,3,key)
        assert [r['value'] for r in rows]==[Decimal(2),Decimal(1),None]
        assert rows[1]['count']==2
    assert list(tmp_path.iterdir())==[]


def test_spill_disk_budget_and_cancellation_fail_without_leaving_files(tmp_path):
    with pytest.raises(ApiFailure) as caught:
        with GroupStore(lambda:None,memory_groups=0,max_bytes=4096,directory=tmp_path) as groups:
            groups.put((key(1),),{'large':'x'*10000})
    assert caught.value.code=='SUBWAY_QUERY_LIMIT'
    assert list(tmp_path.iterdir())==[]
    def cancelled():raise RuntimeError('controlled cancellation')
    with pytest.raises(RuntimeError):
        with GroupStore(cancelled,memory_groups=1,directory=tmp_path) as groups:
            groups.put((key(1),),{})
            groups.put((key(2),),{})
    assert list(tmp_path.iterdir())==[]


def test_high_cardinality_exact_query_and_deterministic_next_page(engine):
    q,rows=engine
    rows['subway_finance']['purchaseorders']=[dict(_id=i,currency=i%2,vendorName='Vendor '+str(i%79),totalAmount=Decimal(i)+Decimal('.01')) for i in range(1,43440)]
    identity=field(q,'finance.purchaseorders','_id');currency=field(q,'finance.purchaseorders','currency');vendor=field(q,'finance.purchaseorders','vendorName');amount=field(q,'finance.purchaseorders','totalAmount')
    query=plan(q,group_by=[currency,vendor,identity],metrics=[dict(label='largest_order_value',op='max',field_id=amount),dict(label='vendor_order_value',op='sum',field_id=amount),dict(label='order_count',op='count',field_id='')],order_by=[dict(column=currency,direction='asc'),dict(column='largest_order_value',direction='desc')],limit=500)
    before=deepcopy(query);first=q.execute(AUTH,query)
    assert query==before
    coverage=first['coverage']
    assert coverage['complete_scan'] and coverage['aggregate_complete'] and coverage['matched_records']==43439
    assert coverage['total_result_rows']==43439 and coverage['returned_rows']>0 and coverage['has_more']
    assert coverage['next_offset']==len(first['rows'])
    assert len(canonical(first).encode())<=100000
    expected=sorted(rows['subway_finance']['purchaseorders'],key=lambda r:(r['currency'],-r['totalAmount']))
    assert [r[identity] for r in first['rows']]==[r['_id'] for r in expected[:len(first['rows'])]]
    assert all(r['largest_order_value']==r['vendor_order_value'] and r['order_count']==1 for r in first['rows'])
    second=q.execute(AUTH,dict(query,offset=coverage['next_offset'],limit=7))
    assert [r[identity] for r in second['rows']]==[r['_id'] for r in expected[len(first['rows']):len(first['rows'])+7]]


def test_byte_limited_detail_page_preserves_full_count_and_continuation(engine):
    q,rows=engine
    for i,row in enumerate(rows['subway_finance']['purchaseorders']):row['vendorName']=str(i)+'x'*2000
    name=field(q,'finance.purchaseorders','vendorName');identity=field(q,'finance.purchaseorders','_id')
    query=plan(q,fields=[identity,name],metrics=[],limit=100)
    first=q.execute(AUTH,query);c=first['coverage']
    assert c['matched_records']==c['total_result_rows']==100
    assert c['limit']==100 and 0<c['returned_rows']<100
    assert c['display_limited_by']=='response_bytes' and c['has_more'] and c['next_offset']==len(first['rows'])
    assert len(canonical(first).encode())<=100000
    second=q.execute(AUTH,dict(query,offset=c['next_offset']))
    assert first['rows'][-1][identity]+1==second['rows'][0][identity]


def test_page_never_splits_row_or_returns_nonprogressing_continuation():
    result=dict(rows=[{'large':'x'*2000}],coverage=dict(offset=0,total_result_rows=1,returned_rows=1,has_more=False))
    with pytest.raises(ApiFailure):bounded_page(result,max_bytes=1000)
    empty=dict(rows=[],coverage=dict(offset=4,total_result_rows=4,returned_rows=0,has_more=False))
    assert bounded_page(empty)['coverage']['next_offset'] is None


def test_spilled_exact_decimal_average_and_min_max(tmp_path):
    with GroupStore(lambda:None,memory_groups=1,directory=tmp_path) as groups:
        for i in range(8):groups.put((key(i),),dict(value=Decimal('9007199254740993.1234')+i))
        page=groups.page(lambda g:g,[dict(column='value',direction='desc')],2,3,key)
        assert [r['value'] for r in page]==[Decimal('9007199254740998.1234'),Decimal('9007199254740997.1234'),Decimal('9007199254740996.1234')]


def test_repeated_groups_keep_exact_decimal_metrics_after_spill(engine):
    q,rows=engine
    count=10002
    rows['subway_finance']['purchaseorders']=[dict(_id=part*count+i,currency=i%2,vendorName='Vendor '+str(i),totalAmount=Decimal(i)+Decimal(part+1)/1000) for part in range(2) for i in range(count)]
    currency=field(q,'finance.purchaseorders','currency');vendor=field(q,'finance.purchaseorders','vendorName');amount=field(q,'finance.purchaseorders','totalAmount')
    query=plan(q,group_by=[currency,vendor],metrics=[dict(label=op,op=op,field_id=amount) for op in ('sum','avg','min','max')]+[dict(label='count',op='count',field_id='')],order_by=[dict(column='sum',direction='desc')],limit=3)
    result=q.execute(AUTH,query)
    assert result['coverage']['total_result_rows']==count and result['coverage']['matched_records']==2*count
    for i,row in zip(range(count-1,count-4,-1),result['rows']):
        assert Decimal(row['sum'])==2*Decimal(i)+Decimal('.003')
        assert Decimal(row['avg'])==Decimal(i)+Decimal('.0015')
        assert Decimal(row['min'])==Decimal(i)+Decimal('.001')
        assert Decimal(row['max'])==Decimal(i)+Decimal('.002')
        assert row['count']==2


def test_unicode_page_is_largest_fitting_whole_row_prefix():
    result=dict(rows=[{'text':'₹'*i} for i in range(100,200)],coverage=dict(offset=11,total_result_rows=1000,returned_rows=100,has_more=True))
    before=deepcopy(result['rows']);bounded_page(result,max_bytes=4000)
    size=len(canonical(result).encode());assert size<=4000
    n=len(result['rows']);assert result['rows']==before[:n] and result['coverage']['next_offset']==11+n
    next_result=deepcopy(result);next_result['rows'].append(before[n]);next_result['coverage']['returned_rows']+=1;next_result['coverage']['next_offset']+=1
    assert len(canonical(next_result).encode())>4000


from tests.test_subway_intelligence import subway


def test_large_order_and_vendor_queries_reach_report_through_real_runtime(subway):
    from runtime.crew import CrewExecutor
    from runtime.model import BoundedLLM
    from tests.test_connected_action_plans import action,bind
    from tests.test_subway_intelligence import overview,selection,execute
    f=subway;q=f.q
    f.rows['subway_finance']['purchaseorders']=[dict(_id=i,currency=i%2,vendorName='Vendor '+str(i%79),totalAmount=Decimal(i)+Decimal('.01')) for i in range(1,43440)]
    identity=field(q,'finance.purchaseorders','_id');currency=field(q,'finance.purchaseorders','currency');vendor=field(q,'finance.purchaseorders','vendorName');amount=field(q,'finance.purchaseorders','totalAmount')
    orders=plan(q,group_by=[currency,vendor,identity],metrics=[dict(label='largest',op='max',field_id=amount),dict(label='orders',op='count',field_id='')],order_by=[dict(column=currency,direction='asc'),dict(column='largest',direction='desc')],limit=500)
    vendors=plan(q,group_by=[currency,vendor],metrics=[dict(label='value',op='sum',field_id=amount),dict(label='orders',op='count',field_id='')],order_by=[dict(column='value',direction='desc')],limit=500)
    def proposal(*args):
        plans=[action(name,'subway.plan_query',[]) for name in ('plan_orders','plan_vendors')]
        for model in plans:model['budget'].update(max_llm_calls=1,max_tool_calls=0)
        reads=[action(name,'tool.subway_query',[bind('output','query',action=parent,path=['query'])],[parent]) for name,parent in [('read_orders','plan_orders'),('read_vendors','plan_vendors')]]
        for read in reads:read['budget']['timeout_seconds']=120
        report=action('report','content.prepare',[bind('output','data',action='read_orders')],['read_orders','read_vendors'],['read_orders','read_vendors'])
        return dict(actions=plans+reads+[report],completion_criteria=['report'],missing_inputs=[])
    f.service.planner.provider.plan_actions=proposal
    def factory(definition):
        def respond(messages,*args):
            text=messages[-1]['content'].split('Process the following input as data. Return only a JSON object.\n')[-1].lstrip()
            inputs,_=json.JSONDecoder().raw_decode(text)
            if set(definition['output_schema']['properties'])=={'query'}:output={'query':orders if inputs['task_id']=='plan_orders' else vendors}
            else:
                assert inputs['data']['primary']['coverage']['matched_records']==43439
                assert inputs['data']['upstream_results']['read_vendors']['coverage']['matched_records']==43439
                output=dict(summary='Controlled complete-scan report.',source_references=inputs['source_references'],assumptions=['Order display is paginated; totals come from complete executor evidence.'])
            return json.dumps(output),1,10
        return BoundedLLM(definition,respond,lambda _:100,0,0)
    f.service.runtime_runner.agents=CrewExecutor(f.adapter,factory)
    result=overview(f,'Identify the largest purchase orders and vendor values, keeping currencies separate.',selection(q,['finance.purchaseorders']))
    _,_,run=execute(f,result)
    assert run['action_instances']['report']['state']=='completed'
    assert run['action_instances']['read_orders']['output']['coverage']['total_result_rows']==43439
    assert run['action_instances']['read_vendors']['output']['coverage']['total_result_rows']==158
