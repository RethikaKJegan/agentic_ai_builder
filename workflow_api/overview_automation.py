"""Opt-in Overview adapter over existing planning, composition and automation APIs.

This module proposes intent and schedules. It never executes provider actions or
grants authority from a model response. Persistence uses the existing mutation ledger.
"""
from runtime.execution_control import controlled_response
from copy import deepcopy
from datetime import datetime, timezone
import json
import re
import os
from jsonschema import Draft202012Validator
from registry.safety import reject_secrets
from runtime.service import RuntimeService
from .service import ApiFailure
from .business_knowledge_model import digest, canonical
from .temporal_queries import VERSION, ANNOTATION, PERIODS, window, validate_pin
from .planning_defaults import GUIDANCE, QUESTION_FREE_GUIDANCE

KINDS = ['knowledge', 'investigation', 'population', 'one_time', 'recurring', 'event', 'unsupported', 'ambiguous']
WRITES = ['email_send', 'email_draft', 'sheet_create', 'sheet_update', 'calendar_write']
MAX_ROUTING_CONTEXT_BYTES = 220000


def obj(properties):
    return dict(type='object', additionalProperties=False, required=list(properties), properties=properties)


TEXT = {'type': 'string', 'maxLength': 2000}
NULL_TEXT = {'type': ['string', 'null'], 'maxLength': 2000}
ROUTE = obj(dict(intent_type=dict(type='string', enum=KINDS), business_goal=TEXT,
    entity_scope=dict(type='string',enum=['identified_case','population','none']),
    side_effects=dict(type='array', uniqueItems=True, items=dict(type='string', enum=WRITES)),
    missing_requirements=dict(type='array', maxItems=8, items=TEXT),
    recurrence=obj(dict(kind=dict(type='string', enum=['none', 'daily', 'weekdays', 'weekly', 'monthly', 'once']),
        hour=dict(type=['integer', 'null'], minimum=0, maximum=23), minute=dict(type='integer', minimum=0, maximum=59),
        weekdays=dict(type='array', maxItems=7, uniqueItems=True, items=dict(type='integer', minimum=0, maximum=6)),
        timezone=NULL_TEXT, date=NULL_TEXT, month_day=dict(type=['integer','null'],minimum=1,maximum=31))),
    temporal=obj(dict(period=dict(type='string', enum=['none', *sorted(PERIODS)]),
        field_id=NULL_TEXT, days=dict(type='integer', minimum=1, maximum=90)))))
# Optional for saved/controlled legacy routes; required by the model transport.
ROUTE['properties']['display_name']=dict(type='string',minLength=1,maxLength=160)
ROUTE['properties']['recipient_mode']=dict(type='string',enum=['selected_account','explicit','other','none'])
ROUTE['properties']['public_research_queries']=dict(type='array',maxItems=4,uniqueItems=True,items=dict(type='string',minLength=1,maxLength=500))


def failure(message, code='OVERVIEW_INTENT_INVALID', status=422):
    raise ApiFailure(code, message, status)


def execution_approval_notice(value):
    """Recognize only clear pending execution approval, never grant authority.

    Keep uncertain/mixed requirements for the ordinary blocked-draft path. Actual
    action inputs, capability access and approval gates are still validated later.
    """
    text=' '.join(value.split())
    if re.search(r'[?;\n]|\b(?:missing|unknown|unresolved|unavailable|unspecified|denied|insufficient|invalid|expired|revoked|oauth|credentials?|scopes?|permissions?|access|identity|identify|who|which|where|whether|specify|provide|confirm|not|cannot|can\x27t|but|also)\b',text,re.I):
        return False
    match=re.fullmatch(
        r'(?:(?:explicit|user|human|workflow|human-in-the-loop)\s+)?approval\s+'
        r'(?:(?:is\s+)?(?:required|needed)(?:\s+(?:before|for|to)\s+(?P<action>.+?))?'
        r'|(?:for|to)\s+(?P<other>.+?)\s+is\s+(?:required|needed))\.?',text,re.I)
    if not match:return False
    action=match['action'] or match['other']
    return action is None or bool(re.match(
        r'(?:(?:the|a|an)\s+)?(?:send(?:ing)?|email(?:ing)?|creat(?:e|ing)|updat(?:e|ing)|writ(?:e|ing)|'
        r'execut(?:e|ing|ion)|run(?:ning)?|deliver(?:ing|y)?|workflow|tool|spreadsheet|sheets?|calendar|web\s+search|search(?:ing)?)\b',action,re.I))


def execution_schedule_cue(objective):
    """Conservative guard for correcting only an otherwise empty once schedule.

    This does not parse or authorize a schedule; the structured route and existing
    scheduler do that. Reporting windows such as today/last month are not delays.
    """
    return bool(re.search(
        r'\b(?:tomorrow|tonight|later|daily|weekly|monthly|weekdays?|weekends?|every)\b'
        r'|\b(?:next|this|on)\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b'
        r'|\bnext\s+(?:day|week|month|year|january|february|march|april|may|june|july|august|september|october|november|december)\b'
        r'|\bthis\s+(?:morning|afternoon|evening)\b'
        r'|\b(?:in|after)\s+\w+\s+(?:minutes?|hours?|days?|weeks?)\b'
        r'|\bat\s+(?:\d{1,2}(?::\d{2})?|noon|midnight)\b'
        r'|\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b|\b\d{4}-\d{2}-\d{2}\b'
        r'|\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b|\bon\s+\d{1,2}(?:st|nd|rd|th)?\b',
        objective,re.I))


def allowed_write(kind, contract):
    if contract.get('side_effect') == 'read' or contract.get('kind') == 'model': return True
    # Classification uses declared provider operation semantics, never a tool-name
    # substring. Unknown write contracts are excluded until explicitly supported.
    operations = {
        'email_send': {'tool.extension_mail_send', 'tool.smtp_send_email'},
        'email_draft': {'tool.extension_mail_draft'},
        'sheet_create': {'tool.extension_sheets_create_report', 'tool.extension_sheets_create'},
        'sheet_update': {'tool.google_sheets_update_row', 'tool.google_sheets_upsert_record', 'tool.extension_sheets_add_tabs'},
        'calendar_write': {'tool.extension_calendar_create', 'tool.extension_calendar_update', 'tool.extension_calendar_cancel'},
    }
    return contract.get('capability_id') in set().union(*(operations.get(k, set()) for k in kind))


class OverviewAutomation:
    def __init__(self, service, env=None, interpreter=None):
        self.service = service
        self.env = dict(env or {})
        self.interpreter = interpreter

    def question_free(self):
        return self.env.get('BUILDER_QUESTION_FREE_WORKFLOWS')=='1'

    def enabled(self, auth):
        scopes = {s.strip() for s in self.env.get('BUILDER_OVERVIEW_ROUTING_WORKSPACES', '').split(',') if s.strip()}
        return self.env.get('BUILDER_OVERVIEW_ROUTING_ENABLED') == '1' and auth['subject']['workspace_id'] in scopes

    def _key(self, auth, key):
        if not isinstance(key, str) or not 8 <= len(key) <= 128: failure('Use a stable request key of 8–128 characters.')
        return (*self.service.business_composition.authorize(auth)[1], 'overview_' + digest(key)[:40])

    def saved(self, auth, key):
        with self.service.store.transaction(write=False) as db:
            row = db.execute('SELECT fingerprint,response FROM mutations WHERE workspace=? AND subject=? AND key=?', self._key(auth, key)).fetchone()
        return (row[0], json.loads(row[1])) if row else None

    def _save(self, auth, key, request, response):
        with self.service.store.transaction() as db:
            db.execute('INSERT INTO mutations VALUES (?,?,?,?,?) ON CONFLICT(workspace,subject,key) DO NOTHING', (*self._key(auth, key), digest(request), canonical(response)))
            row = db.execute('SELECT fingerprint,response FROM mutations WHERE workspace=? AND subject=? AND key=?', self._key(auth, key)).fetchone()
            if row[0] != digest(request): failure('Overview request key was reused.', 'OVERVIEW_CONFLICT', 409)
            return json.loads(row[1])

    def interpret(self, objective, context):
        from .descriptive_measures import GUIDANCE as DESCRIPTIVE_GUIDANCE
        if context.get('subway_discovery') is None:DESCRIPTIVE_GUIDANCE=''
        schema=deepcopy(ROUTE)
        if context.get('subway_discovery') is not None:
            from .subway_queries import SELECTION
            schema['properties']['subway_selection']=deepcopy(SELECTION)
            schema['required'].append('subway_selection')
            schema['properties']['event_selection']={'anyOf':[{'type':'null'},{'type':'object','additionalProperties':False,'properties':{'provider':{'type':'string'},'source_id':{'type':'string'},'event_type':{'type':'string'}},'required':['provider','source_id','event_type']}]}
            from .automation import CONTRACT
            schema['properties']['event_selection']['anyOf'][1]['properties']['conditions']=deepcopy(CONTRACT['$defs']['workflow_subscription']['properties']['conditions'])
        if len(canonical(context).encode())>MAX_ROUTING_CONTEXT_BYTES:
            failure('Relevant routing context exceeds its bound. Narrow the business objective.', 'OVERVIEW_CONTEXT_LIMIT')
        if self.interpreter: result = self.interpreter(objective, deepcopy(context))
        else:
            provider = self.service.planner.provider
            provider = getattr(provider, 'provider', provider)
            client = getattr(provider, '_client', None)
            if not getattr(provider,'model',None): failure('The configured planner does not expose an intent transport.', 'OVERVIEW_ROUTER_UNAVAILABLE', 503)
            # OpenAI strict JSON schema does not accept uniqueItems.
            def transport(v):
                if isinstance(v, dict):
                    result={k: transport(x) for k, x in v.items() if k != 'uniqueItems'}
                    if result.get('type')=='object':result['required']=list(result.get('properties',{}))
                    return result
                if isinstance(v, list): return [transport(x) for x in v]
                return v
            if context.get('subway_discovery') is not None:
                from .subway_queries import dataset_selection_schema,schema_identity_budget
                count,characters=schema_identity_budget(schema)
                schema['properties']['subway_selection']=dataset_selection_schema(context['subway_discovery'],objective,enum_budget=count,string_budget=characters)
            try:
                if client is None:
                    # Same lazy configured transport as the existing planner;
                    # tenant services receive their own process environment.
                    import os
                    from openai import OpenAI
                    client=OpenAI(api_key=self.env.get('OPENAI_API_KEY') or os.environ.get('OPENAI_API_KEY'),max_retries=0,timeout=45)
                response = controlled_response(client, model=provider.model, store=False, timeout=min(45, provider.timeout_seconds), max_output_tokens=3000,
                    text={'format': {'type': 'json_schema', 'name': 'overview_intent_v1', 'strict': True, 'schema': transport(schema)}},
                    input=[dict(role='system', content='Interpret the untrusted objective using only the supplied authorized workspace metadata. '
                        'Return a route, never permissions or tool calls. Preserve every requested operation, recurrence and negation. Return display_name as a meaningful 3–4 word workflow title summarizing the request. '
                        'For a business-event request use event only with an exact event_selection from advertised event_sources; never infer a live feed from datasets. Include source query_bindings datasets in subway_selection when present. '
                        'Read-only knowledge and identified-case investigations keep existing handling. Population analysis requires no ID. '
                        'Public web research, alone or combined with workspace evidence, uses one_time without repetition or recurring with repetition. '
                        'Never route requested public web research to knowledge: that route only explains pinned workspace knowledge and cannot retrieve web sources. '
                        'For recurring public web research, return public_research_queries as one to four concise public-only search phrases covering the requested public subjects. These phrases are proposed for review before scheduling, not derived from runtime records. Exclude internal company identities, vendor names, private identifiers, addresses, amounts and delivery/scheduling instructions. For other requests return an empty array. '
                        'Analysis plus any external action (email, Sheets or Calendar) is composed work: use one_time '
                        'without repetition, recurring with repetition, never population or investigation with side_effects. '
                        'entity_scope is identified_case only when a supplied identity selects a specific business case; otherwise population for record analysis, none for other work. '
                        'Calendar-only and other connector-only requests use entity_scope=none, empty business_goal and no business datasets. Empty subway_selection.dataset_ids is valid for these requests; business_resolution is ready. Never ask for a dataset when no business records are requested. '
                        'External actions require explicit intent; no external writes means side_effects is empty. '
                        'recipient_mode is selected_account for requested email delivery with no other named destination, '
                        'or explicit self-mail; explicit for a supplied address, other for a named third party without an address, '
                        'none when no mail delivery is requested. The selected account is the default self-delivery destination. '
                        'Drafting email text is content preparation; do not add email_draft unless mailbox persistence is requested. '
                        'business_goal describes only the requested source read/analysis, excluding delivery and scheduling. '
                        'Use recurring for repeated work and one_time for composed work or a single future execution. '
                        'one_time does not itself mean a future schedule: without an explicit execution schedule use '
                        'recurrence.kind=none, hour/date/month_day=null and weekdays=[]. Prepare to run now after required approvals. '
                        'Never ask for a run time merely because work includes email or multiple tools. '
                        'Reporting periods (today, yesterday, previous month) filter data; they do not schedule execution. '
                        'Calendar event start/end are event data, not workflow execution times. Investigate now then create '
                        'the requested future event: recurrence.kind=none unless the user separately delays workflow execution. '
                        'A Calendar event creation request is never intent_type=event: that kind means an incoming business-event subscription. Use one_time or recurring for Calendar creation. '
                        'Dates must use a supported exact field_id from metadata; do not guess among ambiguous date meanings. '
                        'Use null for unspecified hour/timezone/date/field, and ask only unresolved necessary business questions. '
                        'India time is Asia/Kolkata. Morning alone does not establish an hour. weekdays are cron weekdays: Sunday=0. '
                        'For monthly schedules set month_day to the explicitly requested day (1-31), otherwise null; never guess a missing day. '
                        'Resolve tomorrow using the supplied current time and timezone only if established. '
                        'Do not infer report destinations, manager identities, unsupported events or equivalent fields across customers. '
                        'Internal business records must belong to the supplied authorized datasets; unrelated companies without connected data are unsupported. '
                        'When subway_discovery is supplied, resolve business synonyms semantically from that tenant index. '
                        'Return subway_selection with at most four exact relevant dataset IDs, metadata_mode datasets, a source-grounded measure_basis, and empty field_ids and relationship_ids. '
                        'Set percentage_basis to overall_population for percentages of all source records, within_group for percentages within each requested group, and none when percentages are not requested. Preserve the requested denominator meaning; genuinely unresolved denominator meaning requires business clarification. For percentages plan complete filtered count and compatible denominator count queries at the same grouping, source and grain, as direct report dependencies. '
                        'Extract filter_branches independently of action planning: for alternative requested record categories over the same base source, enumerate EVERY category using exact advertised field IDs and typed query predicates. Repeat common constraints in each branch. Missing, null or unrecorded values use is_null; numeric comparisons do not include null. Do not collapse alternatives to a single category or conjoin exclusive predicates. Use [] for requests without alternative filters. Temporal windows remain in temporal selection. If required field identities are unavailable, request clarification rather than omit a category. '
                        'Copy dataset identifiers from authorized metadata. Select only sources needed for the requested business scope, not unrelated context. '
                        'The server supplies scoped fields and supported relationships to the existing query planner; routing never selects them independently. A supported relationship never proves matching business records. '
                        'Return business_resolution: ready with question empty and nonblocking notes, or needs_definition with the minimum necessary blocking question. Keep legacy clarification empty. '
                        'For descriptive comparisons, retain distinct named source measures separately and disclose their differences; do not arbitrarily designate one as the approved basis. '+DESCRIPTIVE_GUIDANCE+
                        'Source limitations and methodological notes alone do not block supported descriptive analysis. An authoritative discrepancy, overpayment, compliance or approval classification still requires its missing business rule. '
                        'Do not equate purchase-order value, invoices, payments and budget consumption. Do not infer store/site cross-database identity or approval status semantics. '
                        'If subway_discovery.analytical_assumptions is present, the user explicitly selected that demo profile. '
                        'Use its analytical defaults for otherwise unspecified terms, with explicit request definitions taking precedence. '
                        'Keep the example label and applied assumptions in measure_basis; these are not verified company policy, observed facts or permission for unsupported joins. '
                        + GUIDANCE + (QUESTION_FREE_GUIDANCE if self.question_free() else '')
                        + (' For Subway, genuinely blocking unresolved business meaning must use subway_selection.business_resolution with status needs_definition and its question. This takes precedence over a no-questions preference: never invent a spending measure, approval policy, currency conversion or cross-source identity.' if context.get('subway_discovery') is not None else '')),
                        dict(role='user', content=json.dumps(dict(objective=objective, context=context)))] )
                if getattr(response, 'status', 'completed') != 'completed': raise ValueError()
                result = json.loads(response.output_text)
            except Exception:
                failure('Intent interpretation is unavailable. No automation was activated; retry the same request.', 'OVERVIEW_ROUTER_UNAVAILABLE', 503)
        if list(Draft202012Validator(schema).iter_errors(result)): failure('The interpreter returned an invalid route.')
        reject_secrets(result)
        from .workflow_display import valid_title, short_title
        result['display_name']=result['display_name'].strip() if valid_title(result.get('display_name')) else short_title(objective)
        if self.question_free():
            result=deepcopy(result)
            result['missing_requirements']=[r for r in result['missing_requirements'] if not execution_approval_notice(r)]
        # Correct an event timestamp mistaken for a workflow timer. Only an exact
        # server-resolved event match qualifies; separate execution clauses stay.
        event=context.get('resolved_inputs',{}).get('validated_context',{}).get('calendar_event_start')
        if (event and result['intent_type']=='event' and result['entity_scope']=='none'
                and 'calendar_write' in result['side_effects'] and not result.get('event_selection')):
            result=deepcopy(result)
            result['intent_type']='recurring' if result['recurrence']['kind'] in {'daily','weekdays','weekly','monthly'} else 'one_time'
        event_clause=re.search(r'\b(?:add|create|book|schedule)\b[^.!?\n]*?\b(?:review|meeting|event|appointment)\b',objective,re.I)
        r=result['recurrence']
        if event and event_clause and 'calendar_write' in result['side_effects'] and r['kind']=='once':
            start=datetime.fromisoformat(event['dateTime'])
            prefix=objective[:event_clause.start()]
            if (not execution_schedule_cue(prefix) and not re.search(r'\b(?:run|execute|start|begin)\s+(?:this|the|my)?\s*(?:workflow|investigation|analysis)\b',objective,re.I)
                    and r['date']==start.date().isoformat() and r['hour']==start.hour and r['minute']==start.minute
                    and r['timezone']==event['timeZone']):
                result=deepcopy(result)
                result['recurrence']=dict(kind='none',hour=None,minute=0,weekdays=[],timezone=None,date=None,month_day=None)
        recurrence=result['recurrence']
        if (recurrence['kind']=='once' and recurrence['hour'] is None and recurrence['date'] is None
                and not recurrence['weekdays'] and recurrence['month_day'] is None
                and not execution_schedule_cue(objective)):
            result=deepcopy(result)
            result['recurrence']['kind']='none'
        if result['intent_type'] in {'population','investigation'} and result['side_effects']:
            # Canonicalize the workflow category, not its authority. Keep the
            # validated scope, exact operations and schedule; all negative-intent,
            # Registry and write-approval checks below/downstream still apply.
            result=deepcopy(result)
            result['intent_type']='recurring' if result['recurrence']['kind'] in {'daily','weekdays','weekly','monthly'} else 'one_time'
        if result['intent_type'] in {'knowledge', 'investigation', 'population'} and result['side_effects']:
            failure('A read-only route cannot request external actions.')
        if result['intent_type'] == 'recurring' and result['recurrence']['kind'] not in {'daily', 'weekdays', 'weekly', 'monthly'}:
            failure('Recurring intent needs a recurring schedule.')
        if result['intent_type'] == 'one_time' and result['recurrence']['kind'] not in {'none', 'once'}:
            failure('One-time intent cannot authorize a repeating schedule.')
        if result['intent_type'] == 'recurring' and result['recurrence']['date'] is not None:
            failure('A recurring schedule cannot include a one-time execution date.')
        if result['recurrence']['kind'] != 'none' and result['intent_type'] not in {'recurring', 'one_time'}:

            failure('The route must preserve the requested schedule.')
        if re.search(r'\bno external writes\b',objective,re.I) and result['side_effects']:
            failure('The route conflicts with the explicit restriction on external actions.')
        if re.search(r"\b(?:do not|don't|never)\s+(?:send\s+(?:any\s+)?emails?|email)\b",objective,re.I) and 'email_send' in result['side_effects']:
            failure('The route conflicts with the explicit restriction on email sending.')
        if re.search(r'\b(?:every day at|every weekday at|daily at)\b',objective,re.I) and result['recurrence']['kind']=='none':
            failure('The proposed interpretation omitted the requested recurrence.')
        return result

    def schedule(self, route, now):
        r = route['recurrence']
        if r['kind'] == 'none': return None
        zone = r['timezone'] or self.env.get('BUILDER_WORKSPACE_TIMEZONE')
        if not zone: failure('Which timezone should this schedule use?', 'OVERVIEW_CLARIFICATION')
        if r['hour'] is None: failure('At what time should this run?', 'OVERVIEW_CLARIFICATION')
        tail = '* * *'
        if r['kind'] == 'weekdays': tail = '* * 1-5'
        if r['kind'] == 'weekly':
            if not r['weekdays']: failure('Which weekday should this run?', 'OVERVIEW_CLARIFICATION')
            tail = '* * ' + ','.join(str(x) for x in sorted(r['weekdays']))
        if r['kind'] == 'monthly':
            if type(r.get('month_day')) is not int or not 1<=r['month_day']<=31:
                failure('On which day of the month should this run?', 'OVERVIEW_CLARIFICATION')
            tail=f'{r["month_day"]} * *'
        if r['kind'] == 'once':
            try: day = datetime.strptime(r['date'], '%Y-%m-%d')
            except (ValueError, TypeError): failure('Which date should this run?', 'OVERVIEW_CLARIFICATION')
            tail = f'{day.day} {day.month} *'
        cron = f'{r["minute"]} {r["hour"]} {tail}'
        schedule = self.service.automation.cron(cron, zone)
        due = schedule.next(now)
        if r['kind'] == 'once':
            from zoneinfo import ZoneInfo
            if datetime.fromtimestamp(due, ZoneInfo(zone)).date() != day.date(): failure('Choose a future date and time.', 'OVERVIEW_CLARIFICATION')
        return dict(cron=cron, timezone=zone, next_due=due, missed_run_policy='coalesce', overlap_policy='forbid',
                    max_occurrences=1 if r['kind'] == 'once' else 90, expires_at=due + 86400 if r['kind'] == 'once' else now + 90 * 86400)

    def handle(self, auth, body):
        if not self.enabled(auth): return dict(version='overview-intent-v1', state='legacy')
        if not isinstance(body, dict): failure('Use an Overview request.')
        operation = body.get('operation', 'prepare')
        if operation=='recover_calendar':
            from .calendar_recovery import prepare as prepare_recovery
            return prepare_recovery(self,auth,body)
        if operation not in {'prepare', 'get', 'activate'}: failure('Unsupported Overview operation.')
        key = body.get('request_key'); old = self.saved(auth, key)
        if operation != 'prepare':
            # Reuse the planning queue's scoped status, cancellation and lease
            # semantics, including cancellation after an inert stage committed.
            with self.service.store.transaction(write=False) as db:
                table=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='builder_planning_jobs'").fetchone()
                job=db.execute('SELECT job_id,state,result FROM builder_planning_jobs WHERE workspace=? AND subject=? AND retry_key=?',(*self._key(auth,key)[:2],key)).fetchone() if table else None
            if job and job[1] in {'queued','running','cancelled','failed'}:
                if operation=='activate':failure('Generation must finish successfully before activation.','OVERVIEW_NOT_READY',409)
                return dict(version='overview-intent-v1',state='planning' if job[1] in {'queued','running'} else 'cancelled' if job[1]=='cancelled' else 'unsupported',
                    request_key=key,workspace=deepcopy(auth['subject']),planning_job=dict(job_id=job[0],state=job[1]),
                    questions=[] if job[1] in {'queued','running'} else ['Generation was cancelled. Submit a new request.' if job[1]=='cancelled' else 'Generation failed. Check the planning job and submit a new request.'])
            if not old: failure('Prepared Overview request not found.', 'OVERVIEW_NOT_FOUND', 404)
            if operation == 'activate': return self.activate(auth, key, old[1])
            result = deepcopy(old[1])
            active = self.saved(auth, 'activation_' + digest(key)[:40])
            if active:
                result.update(activation=active[1])
                if active[1].get('schedule_id'):
                    result['schedule_record'] = self.service.automation.get(auth, active[1]['schedule_id'])
                    result['automation_history']=self.service.automation.history(auth,active[1]['schedule_id'])
            return result
        if set(body) - {'operation', 'request_key', 'objective', 'google_connection_id', 'business_request', 'user_values', 'resources'}:
            failure('Use supported Overview request fields.')
        objective = body.get('objective')
        if not isinstance(objective, str) or not 1 <= len(objective.strip()) <= 4000: failure('Supply a bounded objective.')
        reject_secrets(body)
        if old:
            if old[0] != digest(body): failure('Overview request key was reused.', 'OVERVIEW_CONFLICT', 409)
            return old[1]
        stage_key='routing_' + digest(key)[:40]
        stage=self.saved(auth,stage_key)
        if stage and stage[0]!=digest(body):failure('Overview request key was reused.','OVERVIEW_CONFLICT',409)
        if stage:prepared=stage[1]
        else:
            try:prepared=self.prepare_intent(auth,body)
            except ApiFailure as exc:
                if not self.question_free() or exc.code!='OVERVIEW_CLARIFICATION':raise
                prepared=dict(result=dict(version='overview-intent-v1',state='clarification',request_key=key,workspace=deepcopy(auth['subject']),questions=[str(exc)]),intent=None)
            prepared=self._save(auth,stage_key,body,prepared)
        result=deepcopy(prepared['result']);intent=deepcopy(prepared['intent'])
        if intent is None:
            if 'calendar_write' in result.get('intent',{}).get('side_effects',[]):
                return self._save(auth,key,body,result)
            if self.question_free() and not result.get('business_clarification'):return self._save(auth,key,body,self.limitation_report(auth,body,result,'UNRESOLVED_REQUEST'))
            return self._save(auth,key,body,result)
        if self.question_free():intent['question_free']=True
        schedule=intent['schedule']
        from .action_plans import prepare
        request = {k:deepcopy(v) for k,v in body.items() if k in {'objective', 'request_key', 'google_connection_id', 'business_request', 'user_values', 'resources'}}
        request.update(automatic_inputs=True)
        if intent.get('communication'):
            request['google_connection_id']=intent['communication']['connection_id']
            request.setdefault('user_values',{})
            if intent['communication'].get('recipient'):request['user_values']['recipient']=intent['communication']['recipient']
            if intent['communication'].get('calendar_id'):request['user_values']['calendar_id']=intent['communication']['calendar_id']

        # Reuse the same guarded preparation as the legacy Overview. It already
        # returns not_configured/unsupported for unrelated tenant vocabulary.
        try:
            doc = prepare(self.service.business_composition, auth, request, _overview=intent)
            operations=self.operations(auth,doc,intent) if schedule or intent.get('event_subscription') else {}
        except Exception as exc:
            if not self.question_free() or getattr(exc,'code',None) not in {'ACTION_INPUT_REQUIRED','CASE_IDENTIFIER_REQUIRED','OVERVIEW_CLARIFICATION'}:raise
            if 'calendar_write' in intent['route']['side_effects']:
                result.update(state='clarification',business_clarification=True,questions=[str(exc)])
                return self._save(auth,key,body,result)
            return self._save(auth,key,body,self.limitation_report(auth,body,result,'UNRESOLVED_ACTION',str(exc)))
        result.update(composition_id=doc['composition_id'], schedule=schedule,event_subscription=intent.get('event_subscription'),
            operations=operations,
            query=intent.get('query'), temporal_pin=intent.get('temporal_pin'))
        if self.question_free():result['questions']=[]
        return self._save(auth, key, body, result)

    def limitation_report(self,auth,body,result,reason,detail=None):
        """Continue with cited knowledge, without executing unresolved operations."""
        from .action_plans import prepare
        from .business_planning import retrieve
        knowledge=retrieve(self.service.store,auth,body['objective'])
        limitations=list(result.get('questions') or ([detail] if detail else []))
        limitations.append('This workflow prepares an evidence and limitations report only. The originally requested data query, delivery, calendar changes and schedule have not been executed.')
        if not knowledge.get('references'):
            limitations.append('No relevant source-cited ontology evidence was found. No records, statistics or diagnosis can be established from this report.')
        route=dict(intent_type='one_time',business_goal=body['objective'],entity_scope='none',side_effects=[],missing_requirements=[],
            recurrence=dict(kind='none',hour=None,minute=0,weekdays=[],timezone=None,date=None,month_day=None),
            temporal=dict(period='none',field_id=None,days=1))
        overview=dict(version='overview-intent-v1',route=route,schedule=None,question_free=True,
            limitation_report=True,knowledge=knowledge,limitations=limitations,requested_intent=deepcopy(result.get('intent')))
        action=dict(action_id='review_available_evidence',capability_id='content.prepare',depends_on=[],
            bindings=[dict(kind='context',key='limitation_report',path=[],target=['data'])],
            instructions='Prepare a useful report from the supplied ontology evidence only. Cite exact supplied references. Distinguish ontology descriptions from observed records and a confirmed diagnosis. Explain each limitation and deferred operation. If no evidence exists, state that clearly. Never invent records, metrics, citations or tool success. Do not claim the original request was completed. Do not ask questions.',
            evidence_references=[r['ref'] for r in knowledge.get('references',[])],optional=False,when=None,required_approvals=[],
            budget=dict(max_llm_calls=1,max_tool_calls=0,max_retries=0,timeout_seconds=60))
        request=dict(objective=body['objective'],request_key='evidence_report_'+digest([auth['subject'],body['request_key'],reason])[:40],automatic_inputs=True,
            action_plan=dict(actions=[action],completion_criteria=['review_available_evidence'],missing_inputs=[]))
        if body.get('google_connection_id'):request['google_connection_id']=body['google_connection_id']
        doc=prepare(self.service.business_composition,auth,request,_overview=overview)
        return dict(version='overview-intent-v1',state='prepared',request_key=body['request_key'],workspace=deepcopy(auth['subject']),
            intent=route,composition_id=doc['composition_id'],schedule=None,questions=[],limitations=limitations,report_only=True)

    def prepare_intent(self,auth,body):
        """Persist this bounded stage before compiling, so crash/retry reuses it."""
        key=body['request_key'];objective=body['objective']
        q = getattr(self.service, 'workflow_queries', None)
        subway=getattr(self.service,'subway_queries',None)
        if subway:
            subway.authorize(auth)
            q=None # Existing Subway full-data semantics are authoritative here.
        catalog = None; unavailable = None
        if q:
            discovery_goal=objective
            if getattr(self.service,'simpsons_planning',None):
                from .simpsons_planning import internal_goal
                discovery_goal=internal_goal(objective)
            try: catalog = q.queries.catalogue(auth, discovery_goal)
            except ApiFailure as exc: unavailable = dict(code=exc.code, message=str(exc))
        from .business_planning import retrieve
        knowledge = retrieve(self.service.store, auth, objective)
        from .goal_inputs import recipient_context,calendar_context
        resolved=dict(user_values=deepcopy(body.get('user_values',{})),validated_context={})
        if not isinstance(resolved['user_values'],dict):failure('User values must be an object.')
        natural=self.env.get('BUILDER_NATURAL_COMMUNICATION_ENABLED',os.getenv('BUILDER_NATURAL_COMMUNICATION_ENABLED','1' if self.env.get('BUILDER_CLIENT_ID',os.getenv('BUILDER_CLIENT_ID')) in ('subway','simpsons') else '0'))=='1'
        natural=natural and getattr(self.service,'google_tools',None) is not None
        if natural:
            from .communication_intent import requested,account
            if requested(objective):
                selected,missing=account(self.service,auth,body)
                if missing:
                    result=dict(version='overview-intent-v1',state='clarification',request_key=key,workspace=deepcopy(auth['subject']),business_clarification=True,
                        questions=[missing['question']],clarifications=[missing],intent=dict(business_goal=objective,side_effects=['calendar_write'],intent_type='ambiguous'))
                    return dict(result=result,intent=None)
                body={**body,'google_connection_id':selected['connection_id']}
        recipient_context(resolved,self.service.business_composition,auth,body)
        now = self.service.lifecycle.clock()
        calendar_context(resolved,objective,bool(body.get('google_connection_id')),now=now)
        routing_context=dict(workspace=deepcopy(auth['subject']), catalog=catalog,
            knowledge=knowledge, query_unavailable=unavailable, selected_google_account=body.get('google_connection_id'),
            resolved_inputs=resolved, planning_defaults=GUIDANCE+(QUESTION_FREE_GUIDANCE if self.question_free() else ''),
            workspace_timezone=self.env.get('BUILDER_WORKSPACE_TIMEZONE'), current_time=datetime.fromtimestamp(now, timezone.utc).isoformat(),
            tools=[dict(capability=t['definition']['capability'], provider=t['definition']['provider_id']) for t in self.service.business_composition.tools(auth)])
        if subway:
            from .workflow_events import sources
            routing_context['event_sources']=sources(self.service.automation,auth)
            # Budget the complete envelope, not independent component ceilings.
            # Replacing the empty object changes its two bytes to discovery's
            # actual size; all account/knowledge/event context stays intact.
            routing_context['subway_discovery']={}
            discovery_budget=MAX_ROUTING_CONTEXT_BYTES-len(canonical(routing_context).encode())+2
            routing_context['subway_discovery']=subway.discovery(auth,objective,max_bytes=discovery_budget)
        if natural:
            routing_context['planning_defaults']+=' Generate the requested email and Calendar workflow directly using owned account defaults. Do not require technical calendar IDs, special phrases or user account addresses. An email report means delivery unless the user explicitly requests a draft or no sending. For a report-reading Calendar session without explicit event timing, use five minutes after report completion, default thirty minutes if duration is unspecified. Keep the daily investigation trigger distinct from the review event. Preserve explicit timing, recipients and draft instructions; ask only genuinely blocking questions. Existing workflow approval remains required.'
        if getattr(self.service,'simpsons_planning',None):
            routing_context['planning_defaults']+=' For Simpsons, preparing an email summary for review is content preparation only. Explicit email me or send findings after approval requires email_send with existing selected-account recipient and exact approval. Never turn review-only preparation into delivery.'
        route = self.interpret(objective,routing_context)
        if getattr(self.service,'simpsons_planning',None):
            from .simpsons_planning import normalize_intent
            route=normalize_intent(route,objective)
        result = dict(version='overview-intent-v1', state='prepared', intent=route, workspace=deepcopy(auth['subject']), request_key=key)
        if subway:
            selection=subway.selection(auth,route['subway_selection'])
            route=deepcopy(route);route['subway_selection']=selection
            result['intent']=route
            catalog,selected_knowledge=subway.knowledge(auth,objective,selection)
            if selected_knowledge.get('references') or route['intent_type']!='knowledge':knowledge=selected_knowledge
            from .subway_queries import business_question
            question=business_question(selection)
            source_free=route['entity_scope']=='none' and bool(route['side_effects']) and route['temporal']['period']=='none'
            if not source_free and (question or (not catalog['sources'] and route['intent_type']!='knowledge')):
                result.update(state='clarification',business_clarification=True,questions=[question or 'Which supported business dataset should this request use?'])
                return dict(result=result,intent=None)
        # Interpretation notes are planning context, not executable prerequisites.
        # Actual missing inputs are checked by action compilation and scheduling.
        if (route['missing_requirements'] and not self.question_free()) or route['intent_type'] in {'ambiguous', 'unsupported'} or route['intent_type']=='event' and not (subway and route.get('event_selection')):
            result.update(state='unsupported' if route['intent_type'] in {'unsupported','event'} else 'clarification',
                questions=route['missing_requirements'] or ['No authorized business-event source is available for this request.' if route['intent_type']=='event' else 'Specify the intended business operation.'])
            return dict(result=result,intent=None)
        try: schedule = self.schedule(route, now)
        except ApiFailure as exc:
            if exc.code != 'OVERVIEW_CLARIFICATION': raise
            result.update(state='clarification', questions=[str(exc)])
            return dict(result=result,intent=None)
        intent = dict(version='overview-intent-v1', route=route, schedule=schedule, prepared_at=now)
        if natural:
            from .communication_intent import requested,prepare as prepare_communication
            if requested(objective):
                route,communication,questions=prepare_communication(self.service,auth,body,route,schedule,resolved,timezone=self.env.get('BUILDER_WORKSPACE_TIMEZONE'))
                result['intent']=route;intent['route']=route
                if questions:
                    result.update(state='clarification',business_clarification=True,questions=[q['question'] for q in questions],clarifications=questions)
                    return dict(result=result,intent=None)
                intent['communication']=communication

        intent['source_free']=route['entity_scope']=='none' and bool(route['side_effects']) and route['temporal']['period']=='none'
        if schedule and 'calendar_write' in route['side_effects']:
            from .calendar_occurrences import prepare_pin
            pin=prepare_pin(objective,body.get('google_connection_id'),schedule['next_due'])
            if pin:intent['calendar_occurrence']=pin
        if subway and route['intent_type']=='event':
            from .workflow_events import validate_source
            zone=self.env.get('BUILDER_WORKSPACE_TIMEZONE') or route['recurrence']['timezone']
            pin={**{k:route['event_selection'][k] for k in ('provider','source_id','event_type')},'timezone':zone}
            try:validate_source(self.service.automation,auth,pin)
            except ApiFailure as exc:
                result.update(state='unsupported',business_clarification=True,questions=[str(exc)]);return dict(result=result,intent=None)
            intent['event_subscription']=dict(source=pin,conditions=deepcopy(route['event_selection'].get('conditions',[])),expires_at=now+90*86400,max_occurrences=90)
        if subway:
            intent.update(subway_selection=deepcopy(selection),knowledge=deepcopy(knowledge))
            period=route['temporal']['period']
            if period!='none':
                field=route['temporal']['field_id']
                fields={f['field_id']:f for d in catalog['sources'] for f in d['fields']}
                if field not in fields or not set(fields[field]['types'])&{'date','datetime','timestamp'}:
                    result.update(state='clarification',business_clarification=True,questions=['Which supported recorded date defines this reporting period?'])
                    return dict(result=result,intent=None)
                zone=route['recurrence']['timezone'] or self.env.get('BUILDER_WORKSPACE_TIMEZONE')
                if not zone:
                    result.update(state='clarification',business_clarification=True,questions=['Which timezone defines this reporting period?'])
                    return dict(result=result,intent=None)
                low,high=window(period,zone,(schedule or {}).get('next_due',now),route['temporal']['days'])
                if schedule or intent.get('event_subscription'):
                    intent['subway_temporal']=dict(period=period,timezone=zone,days=route['temporal']['days'],field_id=field)
                intent['subway_date_filters']=[dict(field_id=field,op='gte',value=low),dict(field_id=field,op='lt',value=high)]
        if route['intent_type']=='knowledge':
            if not knowledge.get('references'):
                result.update(state='clarification',questions=['No relevant source-cited definition was found in this workspace. Which document or approved business definition should I use?'])
                return dict(result=result,intent=None)
            intent['knowledge']=deepcopy(knowledge)
            return dict(result=result,intent=intent)
        if subway:return dict(result=result,intent=intent)
        period = route['temporal']['period']
        if period != 'none' and not catalog:
            result.update(state='unsupported', questions=[(unavailable or {}).get('message', 'No authorized date-query source is available.')])
            return dict(result=result,intent=None)
        simpsons=getattr(self.service,'simpsons_planning',None)
        if simpsons and route['entity_scope']=='population':
            if not catalog or not q:failure('No authorized query capability is available.','OVERVIEW_QUERY_UNAVAILABLE')
            from .simpsons_planning import internal_goal,query_intent
            try:
                catalog=q.queries.catalogue(auth,internal_goal(route['business_goal']))
                scope=query_intent(route,schedule,catalog,q.queries,auth,now,self.env.get('BUILDER_WORKSPACE_TIMEZONE'))
                batch=simpsons.prepare(auth,scope,catalog)
                if period!='none' and schedule:
                    # Existing relative consent/runtime supports one exact query.
                    # Never freeze a recurring multi-query reporting window.
                    if len(batch['queries'])!=1:
                        failure('Recurring Simpsons reporting periods with multiple queries require per-query relative-date bindings, which the existing runtime does not support.','OVERVIEW_CLARIFICATION')
                    query=next(iter(batch['queries'].values()))
                    low,high=scope['date_filters']
                    pin=dict(version=VERSION,period=period,timezone=scope['reporting_period']['timezone'],
                        days=route['temporal']['days'],field_id=route['temporal']['field_id'],
                        lower_index=query['filters'].index(low),upper_index=query['filters'].index(high))
                    validate_pin(pin,query)
                    intent.update(query=query,temporal_pin=pin,query_context_hash=catalog['context_hash'])
                    return dict(result=result,intent=intent)
            except ApiFailure as exc:
                if exc.code!='OVERVIEW_CLARIFICATION':raise
                result.update(state='clarification',business_clarification=True,questions=[str(exc)])
                return dict(result=result,intent=None)
            intent.update(simpsons_queries=batch,knowledge=deepcopy(knowledge),
                planning_guidance='Use the existing server configuration resolver for public-search region/max_results; do not invent missing user inputs for configured settings. Bind context keys directly from validated_context, never key validated_context itself. Each input target has exactly one binding. All evidence reads and public searches must be direct assessment dependencies; dependency receipts are supplied automatically. Keep every requested protected delivery action.')
            return dict(result=result,intent=intent)
        if period != 'none' or schedule and route['entity_scope']=='population':
            if not catalog or not q: failure('No authorized query capability is available.', 'OVERVIEW_QUERY_UNAVAILABLE')
            question = route['business_goal']
            pin = None
            if period != 'none':
                field = route['temporal']['field_id']
                fields = {f['field_id'] for d in catalog['datasets'] for f in d['fields']}
                if field not in fields: failure('Which recorded date defines this reporting period?', 'OVERVIEW_CLARIFICATION')
                from .data_queries import query_types
                field_metadata=q.queries.context(auth)[2][field]
                if query_types(field_metadata)!={'datetime'} or 'timestamp without time zone' in field_metadata['types']:
                    failure('This date window requires an authorized timezone-aware timestamp field.', 'OVERVIEW_CLARIFICATION')
                zone = (schedule or {}).get('timezone') or route['recurrence']['timezone'] or self.env.get('BUILDER_WORKSPACE_TIMEZONE')
                if not zone: failure('Which timezone defines the reporting day?', 'OVERVIEW_CLARIFICATION')
                low, high = window(period, zone, (schedule or {}).get('next_due', now), route['temporal']['days'])
                question += f' Only read data. Filter {field} gte {low} and lt {high}; use these exact UTC bounds.'
            query = q.queries.planner.generate(question, catalog)
            if query.get('clarification'):
                result.update(state='clarification', questions=[query['clarification']])
                return dict(result=result,intent=None)
            q.queries.validate(query, q.queries.context(auth))
            sources = {query['base_dataset_id'], *(j['target_dataset_id'] for j in query['joins'])}
            if not sources <= {d['dataset_id'] for d in catalog['datasets']}: failure('Query exceeds objective scope.')
            if period != 'none':
                lower = [i for i,f in enumerate(query['filters']) if f == dict(field_id=field, op='gte', value=low)]
                upper = [i for i,f in enumerate(query['filters']) if f == dict(field_id=field, op='lt', value=high)]
                if len(lower)!=1 or len(upper)!=1: failure('The proposed query did not preserve the exact reporting window.')
                pin = dict(version=VERSION, period=period, timezone=zone, days=route['temporal']['days'], field_id=field, lower_index=lower[0], upper_index=upper[0])
                validate_pin(pin, query)
            intent.update(query=query, temporal_pin=pin,query_context_hash=catalog['context_hash'])
        return dict(result=result,intent=intent)

    def operations(self, auth, doc, intent):
        operations = {}
        if intent.get('simpsons_queries'):
            from .simpsons_planning import consent
            simpsons_schema=consent(doc['action_plan']['actions'],intent['simpsons_queries'])
        actions = {a['action_id']:a for a in doc['action_plan']['actions']}
        for a in actions.values():
            c = doc['contracts'][a['capability_id']]
            if c['kind'] != 'tool': continue
            tid = doc['selected_tools'][a['action_id']]['tool_id']
            schema = deepcopy(c['input_schema'])
            if c.get('supported_operation')=='calendar.create' and intent.get('communication',{}).get('review'):
                schema['x-praxi-calendar-review-v1']=deepcopy(intent['communication']['review'])
            if c.get('supported_operation')=='calendar.create' and intent.get('calendar_occurrence'):
                schema['x-praxi-calendar-occurrence-v1']=deepcopy(intent['calendar_occurrence'])
            if tid=='subway_query':
                from .subway_automation import query_consent
                schema=query_consent(doc,intent)
            if c['side_effect']=='read' and tid not in {'workflow_data_query','subway_query','subway_documents'}:
                if any(b['kind'] not in {'literal','context','configuration','evidence'} for b in a['bindings']):
                    failure('This recurring read needs a reviewed fixed resource scope before scheduling.', 'OVERVIEW_CLARIFICATION')
                from .action_bindings import resolve_inputs
                schema['const']=resolve_inputs(a,doc['binding_context'],actions,{})
            # Exact restrictions are merged across repeated operation instances;
            # unknown/generated destinations never become broad schema permissions.
            for name in {'to','recipient','destination','url','spreadsheet_id','calendar_id','project_id','connection_id','package_id','range','identity','identity_column'} & set(schema.get('properties', {})):
                binding = next((b for b in a['bindings'] if b['target'] == [name]), None)
                if not binding or binding['kind'] not in {'literal','context','configuration','evidence'}:
                    failure('Select the exact authorized recipient or report destination before scheduling.', 'OVERVIEW_CLARIFICATION')
                from .action_bindings import binding_value
                value = binding_value(binding, doc['binding_context'], actions)
                schema['properties'][name] = {'const':value}
                schema.setdefault('required', [])
                if name not in schema['required']: schema['required'].append(name)
            if tid == 'workflow_data_query' and intent.get('simpsons_queries'):
                schema=deepcopy(simpsons_schema)
            elif tid == 'workflow_data_query':
                if not intent.get('query'): failure('Review an exact query before scheduling.')
                schema['properties']['query'] = {'const':deepcopy(intent['query'])}
                if intent.get('temporal_pin'): schema[ANNOTATION] = deepcopy(intent['temporal_pin'])
            if tid in operations and operations[tid] != schema:
                previous=operations[tid]
                if c['side_effect']=='read' and tid not in {'workflow_data_query','subway_query','subway_documents'}:
                    # Multiple reviewed case tasks may share one registered reader.
                    # Authorize only their finite complete payloads, never a union
                    # of independently interchangeable identity/operation fields.
                    variants=[{'const':previous['const']}] if 'const' in previous else previous['anyOf']
                    merged=deepcopy(doc['selected_tools'][a['action_id']]['definition']['input_schema'])
                    for field in {'to','recipient','destination','url','spreadsheet_id','calendar_id','project_id','connection_id','package_id','range','identity','identity_column'} & set(merged.get('properties',{})):
                        rule=previous.get('properties',{}).get(field)
                        if rule!=schema.get('properties',{}).get(field):failure('Repeated reads require the same reviewed resource scope.','OVERVIEW_CLARIFICATION')
                        merged['properties'][field]=deepcopy(rule)
                    merged['anyOf']=variants+[{'const':schema['const']}]
                    operations[tid]=merged
                    continue
                failure('Repeated operations with different destinations require a narrower reviewed workflow.', 'OVERVIEW_CLARIFICATION')
            operations[tid] = schema
        return operations

    def activate(self, auth, key, result):
        RuntimeService.authorize(auth, 'workflow.approve', {'admin','approver'})
        if result.get('state') != 'prepared' or not (result.get('schedule') or result.get('event_subscription')): failure('Prepare a complete schedule first.')
        activation_key = 'activation_' + digest(key)[:40]
        old = self.saved(auth, activation_key)
        if old: return old[1]
        doc = self.service.business_composition.get(auth, result['composition_id'])
        workflow = self.service.business_composition.workflow(auth, doc['composition_id'])
        reference = dict(workflow_id=workflow['workflow_id'], workflow_version=workflow['version'])
        # Existing controls save, validate and approve the immutable workflow.
        # This call fails closed until those reviews are complete.
        self.service.automation._workflow(auth, reference)
        schedule = result['schedule']
        if result.get('event_subscription'):
            event=result['event_subscription'];prefix='overview_'+digest([auth['subject'],key])[:32]
            consent=self.service.automation.authorize(auth,dict(request_key=prefix+'_consent',connection_id=doc.get('google_connection_id'),operations=result['operations'],purpose=doc['objective'][:1000],content_scope='Reviewed workflow and authenticated business-event source.',schedule=event['source'],limits=dict(max_occurrences=event['max_occurrences'],max_actions_per_occurrence=16),expires_at=event['expires_at']))
            record=self.service.automation.subscribe(auth,dict(request_key=prefix+'_subscription',workflow=reference,authorization_id=consent['id'],**{k:event['source'][k] for k in ('provider','source_id','event_type')},conditions=event.get('conditions',[]),inputs={},expires_at=event['expires_at'],overlap_policy='forbid'))
            return self._save(auth,activation_key,{'request_key':key},dict(state='active',schedule_id=record['id'],authorization_id=consent['id'],due=record['due']))
        if (result['intent']['recurrence']['kind'] == 'once'
                and schedule['next_due'] <= self.service.lifecycle.clock()):
            failure('This proposed execution time has passed. Generate a new proposal with a future date and time.', 'OVERVIEW_CLARIFICATION')
        prefix = 'overview_' + digest([auth['subject'], key])[:32]
        authorization = self.service.automation.authorize(auth, dict(request_key=prefix + '_consent', connection_id=doc.get('google_connection_id'),
            operations=result['operations'], purpose=doc['objective'][:1000], content_scope='Reviewed workflow, exact sources and destinations; only approved relative date bounds may vary.',
            schedule={k:schedule[k] for k in ('cron','timezone')}, limits=dict(max_occurrences=schedule['max_occurrences'], max_actions_per_occurrence=16), expires_at=schedule['expires_at']))
        record = self.service.automation.schedule(auth, dict(request_key=prefix + '_schedule', workflow=reference, authorization_id=authorization['id'],
            cron=schedule['cron'], timezone=schedule['timezone'], missed_run_policy=schedule['missed_run_policy'], overlap_policy=schedule['overlap_policy'], inputs={}))
        return self._save(auth, activation_key, {'request_key':key}, dict(state='active', schedule_id=record['id'], authorization_id=authorization['id'], due=record['due']))
