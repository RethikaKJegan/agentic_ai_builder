"""Overview routing and temporal consent; no model/provider network transports."""
from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
import pytest
from workflow_api.overview_automation import OverviewAutomation, allowed_write
from workflow_api.temporal_queries import window, resolve, consent_schema, ANNOTATION
from workflow_api.service import ApiFailure


def intent(kind='recurring'):
    return dict(intent_type=kind, entity_scope='population', business_goal='Count accessible business records.', side_effects=[], missing_requirements=[],
        recurrence=dict(kind='daily' if kind=='recurring' else 'none', hour=18, minute=0, weekdays=[], timezone='Asia/Kolkata', date=None, month_day=None),
        temporal=dict(period='today', field_id='created', days=1))


def stamp(value): return datetime.fromisoformat(value).timestamp()


def query():
    return dict(base_dataset_id='tickets', fields=[], joins=[], group_by=[], metrics=[dict(label='count',op='count',expression='')],
        filters=[dict(field_id='status',op='eq',value='OPEN'), dict(field_id='created',op='gte',value='2026-11-09T18:30:00+00:00'),dict(field_id='created',op='lt',value='2026-11-10T18:30:00+00:00')],
        order_by=[],limit=1,explanation='Reviewed population.',clarification='')


def pin(): return dict(version='relative-query-v1',period='today',timezone='Asia/Kolkata',days=1,field_id='created',lower_index=1,upper_index=2)


@pytest.mark.parametrize('period,start,end',[
    ('today','2026-11-09T18:30:00+00:00','2026-11-10T18:30:00+00:00'),
    ('yesterday','2026-11-08T18:30:00+00:00','2026-11-09T18:30:00+00:00'),
    ('this_week','2026-11-08T18:30:00+00:00','2026-11-15T18:30:00+00:00'),
    ('previous_week','2026-11-01T18:30:00+00:00','2026-11-08T18:30:00+00:00'),
    ('current_month','2026-10-31T18:30:00+00:00','2026-11-30T18:30:00+00:00'),
    ('previous_month','2026-09-30T18:30:00+00:00','2026-10-31T18:30:00+00:00'),
    ('last_n_days','2026-11-07T18:30:00+00:00','2026-11-10T18:30:00+00:00')])
def test_business_calendar_windows(period,start,end):
    assert window(period,'Asia/Kolkata',stamp('2026-11-10T12:30:00+00:00'),3)==(start,end)


def test_dst_calendar_day_is_not_fixed_24_hours():
    a,b=window('today','America/New_York',stamp('2026-11-01T18:00:00+00:00'))
    assert stamp(b)-stamp(a)==25*3600


def test_only_two_reviewed_values_change_and_original_is_immutable():
    original=query(); due=stamp('2026-11-12T12:30:00+00:00')
    result=resolve(original,pin(),due)
    assert result['filters'][0]==original['filters'][0]
    result['filters'][1]['value']=original['filters'][1]['value'];result['filters'][2]['value']=original['filters'][2]['value']
    assert result==original
    schema=dict(type='object',required=['query'],properties={'query':{'const':original}},**{ANNOTATION:pin()})
    assert consent_schema(schema,due)['properties']['query']['const']==resolve(original,pin(),due)
    assert schema['properties']['query']['const']==original


@pytest.mark.parametrize('change',[{'days':91},{'lower_index':0},{'upper_index':1},{'version':'other'},{'timezone':'not/a/zone'}])
def test_invalid_semantic_parameter_is_rejected(change):
    p=pin();p.update(change)
    with pytest.raises(ApiFailure):resolve(query(),p,0)


@pytest.mark.parametrize('kind',['knowledge','investigation','population','one_time','recurring','event','unsupported','ambiguous'])
def test_structured_interpretation_preserves_routes_and_tenant_context(kind):
    seen=[];expected=intent(kind)
    router=OverviewAutomation(SimpleNamespace(),interpreter=lambda goal,ctx:seen.append(ctx) or expected)
    assert router.interpret('A short business request',{'workspace':{'workspace_id':'new_customer'}})==expected
    assert seen[0]['workspace']['workspace_id']=='new_customer'


def test_malformed_interpretation_and_read_route_writes_are_rejected():
    router=OverviewAutomation(SimpleNamespace(),interpreter=lambda *_:{'intent_type':'recurring'})
    with pytest.raises(ApiFailure):router.interpret('Report',{})
    r=intent('population');r['side_effects']=['email_send'];router.interpreter=lambda *_:r
    with pytest.raises(ApiFailure):router.interpret('No external writes',{})


def test_feature_requires_enable_and_exact_workspace_allowlist():
    r=OverviewAutomation(SimpleNamespace(),dict(BUILDER_OVERVIEW_ROUTING_ENABLED='1',BUILDER_OVERVIEW_ROUTING_WORKSPACES='simpson,subway'))
    assert r.enabled({'subject':{'workspace_id':'subway'}})
    assert not r.enabled({'subject':{'workspace_id':'other'}})
    assert OverviewAutomation(None).handle({'subject':{'workspace_id':'simpson'}},{})['state']=='legacy'


def test_schedule_conversion_reuses_existing_cron():
    from workflow_api.automation import DurableAutomation
    r=OverviewAutomation(SimpleNamespace(automation=SimpleNamespace(cron=DurableAutomation.cron)))
    due=stamp('2026-11-10T10:00:00+00:00')
    assert r.schedule(intent(),due)['next_due']==stamp('2026-11-10T12:30:00+00:00')
    weekly=intent();weekly['recurrence'].update(kind='weekly',weekdays=[1],hour=9)
    assert r.schedule(weekly,due)['cron']=='0 9 * * 1'
    weekly['recurrence'].update(kind='weekdays')
    assert r.schedule(weekly,due)['cron']=='0 9 * * 1-5'
    weekly['recurrence']['timezone']=None
    with pytest.raises(ApiFailure,match='timezone'):r.schedule(weekly,due)


def test_write_capability_cannot_be_added_to_read_only_route():
    assert allowed_write([],dict(kind='tool',side_effect='read',capability_id='tool.any_registered_read'))
    assert not allowed_write([],dict(kind='tool',side_effect='write',capability_id='tool.extension_mail_send'))
    assert not allowed_write(['email_send'],dict(kind='tool',side_effect='write',capability_id='tool.unknown_send'))


def test_router_transport_timeout_fails_closed_and_never_calls_an_executor():
    def unavailable(**kwargs): raise TimeoutError('controlled timeout')
    provider=SimpleNamespace(_client=SimpleNamespace(responses=SimpleNamespace(create=unavailable)),model='configured-model',timeout_seconds=45)
    r=OverviewAutomation(SimpleNamespace(planner=SimpleNamespace(provider=provider)))
    with pytest.raises(ApiFailure) as caught:r.interpret('Daily business report',{})
    assert caught.value.code=='OVERVIEW_ROUTER_UNAVAILABLE'


def test_exact_negative_delivery_instruction_does_not_forbid_requested_spreadsheet():
    route=intent('one_time');route['side_effects']=['sheet_create']
    r=OverviewAutomation(None,interpreter=lambda *_:route)
    assert r.interpret('Create a spreadsheet; do not send emails.',{})==route


def test_context_budget_is_checked_before_a_model_call():
    def forbidden(*_):raise AssertionError('Oversized context must not reach the model')
    r=OverviewAutomation(None,interpreter=forbidden)
    with pytest.raises(ApiFailure) as caught:r.interpret('Report',{'data':'x'*220001})
    assert caught.value.code=='OVERVIEW_CONTEXT_LIMIT'


def test_one_time_schedule_is_not_an_annual_recurrence():
    from workflow_api.automation import DurableAutomation
    r=OverviewAutomation(SimpleNamespace(automation=SimpleNamespace(cron=DurableAutomation.cron)))
    route=intent('one_time');route['recurrence'].update(kind='once',date='2026-11-11',hour=10)
    schedule=r.schedule(route,stamp('2026-11-10T10:00:00+00:00'))
    assert schedule['max_occurrences']==1 and schedule['cron']=='0 10 11 11 *'
    assert schedule['next_due']==stamp('2026-11-11T04:30:00+00:00')


@pytest.mark.parametrize('kind,schedule', [('one_time','daily'),('one_time','weekly'),('recurring','once')])
def test_route_cannot_change_one_time_into_recurring_or_drop_recurrence(kind,schedule):
    route=intent(kind);route['recurrence']['kind']=schedule
    router=OverviewAutomation(None,interpreter=lambda *_:route)
    with pytest.raises(ApiFailure):router.interpret('A reviewed business request',{})


def test_registered_sheet_updates_remain_subject_to_explicit_update_intent():
    for capability in ('tool.google_sheets_update_row','tool.google_sheets_upsert_record'):
        contract=dict(kind='tool',side_effect='write',capability_id=capability)
        assert allowed_write(['sheet_update'],contract)
        assert not allowed_write([],contract)
        assert not allowed_write(['sheet_create'],contract)


def test_configured_ai_transport_uses_bounded_structured_context_without_execution():
    import json
    calls=[];route=intent()
    def create(**kwargs):
        calls.append(deepcopy(kwargs))
        return SimpleNamespace(status='completed',output_text=json.dumps(route))
    provider=SimpleNamespace(_client=SimpleNamespace(responses=SimpleNamespace(create=create)),model='configured-model',timeout_seconds=180)
    router=OverviewAutomation(SimpleNamespace(planner=SimpleNamespace(provider=provider)))
    context={'workspace':{'workspace_id':'future_tenant'},'catalog':{'datasets':[]}}
    assert router.interpret('Daily mapped business report',context)==route
    assert len(calls)==1
    request=calls[0]
    assert request['model']=='configured-model' and request['store'] is False
    assert request['timeout']==45 and request['max_output_tokens']==3000
    assert request['text']['format']['strict'] is True
    assert json.loads(request['input'][1]['content'])['context']==context
    assert 'Never route requested public web research to knowledge' in request['input'][0]['content']


def test_monthly_first_day_uses_existing_scheduler_and_requires_a_day():
    from workflow_api.automation import DurableAutomation
    route=intent();route['recurrence'].update(kind='monthly',month_day=1,hour=9)
    router=OverviewAutomation(SimpleNamespace(automation=SimpleNamespace(cron=DurableAutomation.cron)),interpreter=lambda *_:route)
    assert router.interpret('On the first day of every month at 9 AM India time, report last month.',{})==route
    schedule=router.schedule(route,stamp('2026-11-10T10:00:00+00:00'))
    assert schedule['cron']=='0 9 1 * *'
    assert schedule['next_due']==stamp('2026-12-01T03:30:00+00:00')
    route['recurrence']['month_day']=None
    with pytest.raises(ApiFailure,match='day of the month'):router.schedule(route,stamp('2026-11-10T10:00:00+00:00'))
