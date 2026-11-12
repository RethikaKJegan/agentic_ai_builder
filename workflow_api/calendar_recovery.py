"""Prepare a separately reviewed Calendar-only continuation after a proven non-write."""
from copy import deepcopy
from datetime import datetime
from .business_knowledge_model import digest
from .communication_timing import preview_values
from .service import ApiFailure


def prepare(router,auth,body):
    if set(body)!={'operation','request_key','composition_id','run_id'}:raise ApiFailure('OVERVIEW_CLARIFICATION','Choose the reading session to reschedule.',422)
    from runtime.service import RuntimeService
    RuntimeService.authorize(auth,'workflow.plan',{'admin','builder'})
    RuntimeService.authorize(auth,'workflow.execute',{'admin','builder'})
    old=router.saved(auth,body['request_key'])
    if old:
        if old[0]!=digest(body):raise ApiFailure('OVERVIEW_CONFLICT','This review request has changed.',409)
        return old[1]
    service=router.service;doc=service.business_composition.get(auth,body['composition_id'])
    rt=service.runtime_runner.runtime
    with service.store.transaction(write=False) as db:
        run=rt.load(db,body['run_id'],auth)
    if run['workflow_id']!='cw_'+body['composition_id'].removeprefix('composition_'):
        raise ApiFailure('OVERVIEW_NOT_FOUND','The reading session does not belong to this workflow.',404)
    info=doc.get('overview_intent',{}).get('communication')
    if not info or not (run.get('error_code')=='CALENDAR_REVIEW_TIME_PASSED' or run['status']=='paused_for_approval'):
        raise ApiFailure('CALENDAR_RECONCILIATION_REQUIRED','Confirm the Calendar outcome before retrying. The email will not be resent.',409)
    events=[a for a in doc['action_plan']['actions'] if doc['contracts'][a['capability_id']].get('supported_operation')=='calendar.create']
    if len(events)!=1 or run.get('node_invocations',{}).get(events[0]['action_id']):
        raise ApiFailure('CALENDAR_RECONCILIATION_REQUIRED','The Calendar request may have reached Google. Confirm its outcome before creating another event.',409)
    event=events[0];old_values=run.get('communication_calendar_times',{}).get(event['action_id'],{}).get('values')
    if not old_values or datetime.fromisoformat(old_values['calendar_event_start']['dateTime']).timestamp()>rt.clock():
        raise ApiFailure('CALENDAR_RECONCILIATION_REQUIRED','This reading-session time has not expired.',409)
    if run['status']=='paused_for_approval':
        if run.get('approval_context',{}).get('node_id')!='approve_'+event['action_id']:
            raise ApiFailure('CALENDAR_RECONCILIATION_REQUIRED','Finish the current action review before rescheduling.',409)
        with service.store.transaction() as db:
            current=rt.load(db,body['run_id'],auth)
            if current['status']!='paused_for_approval' or current.get('node_invocations',{}).get(event['action_id']):
                raise ApiFailure('CALENDAR_RECONCILIATION_REQUIRED','The Calendar state changed. Refresh before continuing.',409)
            current['current_node_id']=event['action_id'];current['node_states'][event['action_id']]='failed'
            current.setdefault('action_instances',{}).setdefault(event['action_id'],{}).update(state='failed',external_effect_status='not_performed')
            service.runtime_runner.fail(db,current,'CALENDAR_REVIEW_TIME_PASSED')
    # Exact cached content from the already completed report; no new model, source read or email.
    content={}
    for binding in event['bindings']:
        if binding.get('target') not in (['event','summary'],['event','description']):continue
        if binding.get('kind') not in ('generated','output'):raise ApiFailure('CALENDAR_RECONCILIATION_REQUIRED','Review the original event content before continuing.',409)
        parent=run.get('action_instances',{}).get(binding['action_id'],{})
        if parent.get('state')!='completed':raise ApiFailure('CALENDAR_RECONCILIATION_REQUIRED','The report must finish first.',409)
        value=parent['output']
        for part in binding['path']:value=value[part]
        content[binding['target'][-1]]=deepcopy(value)
    if not content.get('summary'):raise ApiFailure('CALENDAR_RECONCILIATION_REQUIRED','Review the event title before continuing.',409)
    from .communication_intent import account,review_lines
    selected,missing=account(service,auth,dict(google_connection_id=info['connection_id'],user_values={}))
    if missing:raise ApiFailure('GOOGLE_RECONNECT_REQUIRED',missing['question'],409)
    timing=preview_values(dict(mode='after_ready',timezone=info['review']['timezone'],duration_minutes=info['review']['duration_minutes'],lead_minutes=5),rt.clock())
    start=datetime.fromisoformat(timing['calendar_event_start']['dateTime'])
    policy=dict(mode='fixed',timezone=info['review']['timezone'],duration_minutes=info['review']['duration_minutes'],hour=start.hour,minute=start.minute,on_date=start.date().isoformat())
    communication={**selected,'calendar_id':info['calendar_id'],'recipient':None,'review':policy,'recovery_of':dict(composition_id=body['composition_id'],run_id=body['run_id'],action_id=event['action_id'])}
    values=dict(calendar_id=info['calendar_id'],summary=content['summary'],description=content.get('description',''))
    def binding(field):return dict(kind='literal',key=field,path=[],target=['event',field] if field!='calendar_id' else ['calendar_id'])
    timeout=doc['selected_tools'][event['action_id']]['definition']['timeout_seconds']
    action=dict(action_id='reschedule_review',capability_id=event['capability_id'],depends_on=[],bindings=[binding(k) for k in values],instructions='Create only the separately reviewed reading session using the completed report. No email.',evidence_references=[],required_approvals=['exact_payload'],budget=dict(max_llm_calls=0,max_tool_calls=1,max_retries=0,timeout_seconds=timeout),optional=False,when=None)
    overview=dict(version='overview-intent-v1',request_key=body['request_key'],route=dict(intent_type='one_time',business_goal='Reschedule the reading session using the completed report.',entity_scope='none',side_effects=['calendar_write']),schedule=None,source_free=True,communication=communication)
    request=dict(objective=overview['route']['business_goal'],request_key='calendar_recovery_'+digest(body)[:32],google_connection_id=selected['connection_id'],automatic_inputs=True,user_values=values,action_plan=dict(actions=[action],completion_criteria=['reschedule_review'],missing_inputs=[]))
    from .action_plans import prepare as compile_review
    recovery=compile_review(service.business_composition,auth,request,_overview=overview)
    result=dict(version='overview-intent-v1',request_key=body['request_key'],state='prepared',workspace=deepcopy(auth['subject']),intent=overview['route'],composition_id=recovery['composition_id'],schedule=None,questions=[],communication_review=review_lines(communication)+['Calendar-only recovery. The confirmed email will not be resent.'])
    return router._save(auth,body['request_key'],body,result)
