"""Durable automation records over the existing lifecycle queue and executor.

Only server adapters deliver evidence. Consent, source evidence, queued intents
and run receipts remain separate; no stored document is executable authority.
"""
from copy import deepcopy
from datetime import datetime, timezone
from email.utils import parseaddr
import json
import time
from pathlib import Path
from jsonschema import Draft202012Validator
from registry.safety import reject_secrets
from runtime.service import RuntimeService, RuntimeFailure
from .business_cases import fail, TERMINAL
from .business_knowledge_model import canonical, digest
from .lifecycle import now_iso
from .scheduler import CronSchedule


CONTRACT=json.loads((Path(__file__).resolve().parents[1]/'shared/contracts/durable-automation-v1.json').read_text())


class DurableAutomation:
    def __init__(self, service, clock=None, providers=None):
        self.service, self.store = service, service.store
        self.clock = clock or service.lifecycle.clock
        self.providers = dict(providers or {})
        self.providers.setdefault('gmail', GmailReplyProvider(service))
        self.health = dict(state='ready', last_success=None, last_error=None)
        with self.store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS automation_migrations (name TEXT PRIMARY KEY, version INTEGER NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS automation_records (workspace TEXT NOT NULL, owner TEXT NOT NULL, kind TEXT NOT NULL, id TEXT PRIMARY KEY, state TEXT NOT NULL, due REAL, document TEXT NOT NULL, UNIQUE(workspace,owner,kind,id))')
            db.execute('CREATE TABLE IF NOT EXISTS automation_deliveries (workspace TEXT NOT NULL, owner TEXT NOT NULL, subscription TEXT NOT NULL, event_id TEXT NOT NULL, document TEXT NOT NULL, PRIMARY KEY(workspace,owner,subscription,event_id))')
            db.execute('CREATE INDEX IF NOT EXISTS automation_delivery_event ON automation_deliveries(workspace,owner,event_id)')
            db.execute('INSERT INTO automation_migrations(name,version) VALUES (?,?) ON CONFLICT DO NOTHING', ('durable_automation',1))
        service.automation = self

    @staticmethod
    def scope(auth, write=False):
        RuntimeService.authorize(auth, 'workflow.execute' if write else 'workflow.view', {'admin','builder','viewer','approver'})
        return auth['subject']['workspace_id'], auth['subject']['subject_id']

    @staticmethod
    def request(kind,body):
        schema={'$defs':CONTRACT['$defs'],'$ref':'#/$defs/'+kind}
        if list(Draft202012Validator(schema).iter_errors(body)):fail('Automation request violates durable-automation-v1.','AUTOMATION_REQUEST_INVALID',422)

    @staticmethod
    def cron(expression,zone):
        from .lifecycle import LifecycleFailure
        try:return CronSchedule(expression,zone)
        except LifecycleFailure as exc:fail(str(exc),exc.code,exc.status)

    @staticmethod
    def schema(value):
        from .adaptive_orchestration import AdaptiveOrchestration
        AdaptiveOrchestration._local_schema(value)

    def _get(self, db, scope, identifier, kind=None):
        row=db.execute('SELECT kind,document FROM automation_records WHERE workspace=? AND owner=? AND id=?',(*scope,identifier)).fetchone()
        if not row or kind and row[0]!=kind:fail('Automation record not found.','AUTOMATION_NOT_FOUND',404)
        return json.loads(row[1])

    def _save(self, db, doc):
        doc.setdefault('schema_version','durable-automation-v1')
        if list(Draft202012Validator(CONTRACT['$defs']['record']).iter_errors(doc)):fail('Automation persistence contract violation.')
        reject_secrets(doc)
        if len(canonical(doc).encode())>1000000:fail('Automation record exceeds its bound.')
        db.execute('INSERT INTO automation_records(workspace,owner,kind,id,state,due,document) VALUES (?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET state=excluded.state,due=excluded.due,document=excluded.document',
            (doc['workspace_id'],doc['owner_id'],doc['kind'],doc['id'],doc['state'],doc.get('poll_after',doc.get('due')),canonical(doc)))

    def get(self, auth, identifier):
        with self.store.transaction(write=False) as db:return self._get(db,self.scope(auth),identifier)

    def listing(self, auth, kind=None, before=None, limit=100, workflow_id=None):
        scope=self.scope(auth)
        if type(limit) is not int or not 1<=limit<=100:fail('Use a bounded automation page size.')
        if kind is not None and kind not in CONTRACT['$defs']['record']['properties']['kind']['enum']:fail('Unknown automation record kind.')
        if workflow_id is not None:
            return self.workflow_listing(auth,workflow_id,kind,before,limit)
        query='SELECT kind,id,document FROM automation_records WHERE workspace=? AND owner=?';args=list(scope)
        if kind is not None:query+=' AND kind=?';args.append(kind)
        if before is not None:query+=' AND id<?';args.append(before)
        query+=' ORDER BY id DESC LIMIT ?';args.append(limit+1)
        with self.store.transaction(write=False) as db:
            rows=db.execute(query,tuple(args)).fetchall()
            jobs=[json.loads(r[0]) for r in db.execute("SELECT document FROM lifecycle_jobs WHERE workspace=? AND json_extract(document,'$.owner_id')=? ORDER BY rowid DESC LIMIT 100",scope).fetchall()]
        with self.store.transaction(write=False) as db:
            counts={state:count for state,count in db.execute("SELECT state,COUNT(*) FROM automation_records WHERE workspace=? AND owner=? AND kind='occurrence' GROUP BY state",scope).fetchall()}
            totals=db.execute("SELECT COALESCE(SUM(CAST(json_extract(document,'$.duplicate_count') AS INTEGER)),0),COALESCE(SUM(CAST(json_extract(document,'$.rejected_count') AS INTEGER)),0) FROM automation_records WHERE workspace=? AND owner=? AND kind='subscription'",scope).fetchone()
        terminal=counts.get('completed',0)+sum(counts.get(s,0) for s in ('failed','dead_letter','requires_reconciliation'))
        metrics=dict(occurrence_states=counts,terminal_success_rate=counts.get('completed',0)/terminal if terminal else None,duplicate_events=totals[0],rejected_events=totals[1])
        return dict(items=[json.loads(r[2]) for r in rows[:limit]],has_more=len(rows)>limit,next_cursor=rows[limit-1][1] if len(rows)>limit else None,jobs=[j for j in jobs if j.get('automation_kind')],health=deepcopy(self.health),metrics=metrics)

    def workflow_listing(self, auth, workflow_id, kind, before, limit):
        """Filter before pagination; include related consent and occurrence records."""
        scope=self.scope(auth)
        if not isinstance(workflow_id,str) or not 1<=len(workflow_id)<=128:fail('Supply a workflow identifier.')
        with self.store.transaction(write=False) as db:
            docs=[json.loads(r[0]) for r in db.execute('SELECT document FROM automation_records WHERE workspace=? AND owner=? ORDER BY id DESC',scope).fetchall()]
            jobs=[json.loads(r[0]) for r in db.execute("SELECT document FROM lifecycle_jobs WHERE workspace=? AND json_extract(document,'$.owner_id')=? ORDER BY rowid DESC",scope).fetchall()]
        def matches(doc):
            request=doc.get('request',{})
            return any(isinstance(ref,dict) and ref.get('workflow_id')==workflow_id for ref in (request.get('workflow'),request.get('poll_workflow'),doc.get('result'))) or doc.get('workflow_id')==workflow_id
        ids={d['id'] for d in docs if matches(d)}
        cases={d.get('request',{}).get('case_id') for d in docs if d['id'] in ids}-{None}
        # Follow only explicit relationships, never workspace-wide membership.
        for _ in range(3):
            for d in docs:
                request=d.get('request',{})
                if d['id'] in ids:
                    ids.update(x for x in (request.get('authorization_id'),d.get('schedule_id'),request.get('target_id')) if isinstance(x,str))
                elif d.get('schedule_id') in ids or request.get('target_id') in ids or (request.get('case_id') is not None and request.get('case_id') in cases):
                    ids.add(d['id'])
        scoped=[d for d in docs if d['id'] in ids]
        visible=[d for d in scoped if (kind is None or d['kind']==kind) and (before is None or d['id']<before)]
        counts={}
        for d in scoped:
            if d['kind']=='occurrence':counts[d['state']]=counts.get(d['state'],0)+1
        terminal=counts.get('completed',0)+sum(counts.get(s,0) for s in ('failed','dead_letter','requires_reconciliation'))
        metrics=dict(occurrence_states=counts,terminal_success_rate=counts.get('completed',0)/terminal if terminal else None,
            duplicate_events=sum(d.get('duplicate_count',0) for d in scoped if d['kind']=='subscription'),
            rejected_events=sum(d.get('rejected_count',0) for d in scoped if d['kind']=='subscription'))
        return dict(items=visible[:limit],has_more=len(visible)>limit,next_cursor=visible[limit-1]['id'] if len(visible)>limit else None,
            jobs=[j for j in jobs if j.get('automation_kind') and (j.get('target_id') in ids or j.get('schedule_id') in ids or j.get('target_id') in cases or j.get('workflow_id')==workflow_id)],health=deepcopy(self.health),metrics=metrics)

    def _document(self, auth, kind, body):
        if kind!='control':self.request(kind,body)
        scope=self.scope(auth,True);reject_secrets(body)
        if not isinstance(body,dict) or not isinstance(body.get('request_key'),str) or not 8<=len(body['request_key'])<=128 or len(canonical(body))>100000:fail('Supply a bounded idempotent automation request.')
        return dict(id='auto_'+digest([scope,kind,body['request_key']])[:32],kind=kind,workspace_id=scope[0],owner_id=scope[1],state='active',created_at=self.clock(),request=deepcopy(body),fingerprint=digest(body),errors=[],attempts=0)

    def _existing(self, doc):
        with self.store.transaction(write=False) as db:
            row=db.execute('SELECT document FROM automation_records WHERE id=?',(doc['id'],)).fetchone()
        if not row:return None
        old=json.loads(row[0])
        if old['fingerprint']!=doc['fingerprint']:fail('Automation request key reused.','AUTOMATION_CONFLICT',409)
        return old

    def _put(self, doc):
        with self.store.transaction() as db:
            row=db.execute('SELECT document FROM automation_records WHERE id=?',(doc['id'],)).fetchone()
            if row:
                old=json.loads(row[0])
                if old['fingerprint']!=doc['fingerprint']:fail('Concurrent automation request conflict.','AUTOMATION_CONFLICT',409)
                return old
            self._save(db,doc)
        return doc

    def _workflow(self, auth, reference):
        if not isinstance(reference,dict) or set(reference)!={'workflow_id','workflow_version'}:fail('Supply an exact workflow revision.')
        with self.store.transaction(write=False) as db:
            workflow,_=self.service.runtime_runner.runtime.revision(db,reference['workflow_id'],reference['workflow_version'],auth,True)
        control=workflow.get('metadata',{}).get('adaptive_control')
        if control and control.get('kind')!='workflow-investigation':fail('A recurring occurrence requires an independent approved workflow, not a case-owned adaptive revision.')
        return workflow

    def authorize(self, auth, body):
        doc=self._document(auth,'authorization',body)
        RuntimeService.authorize(auth,'workflow.approve',{'admin','approver'})
        required={'request_key','connection_id','operations','purpose','content_scope','schedule','limits','expires_at'}
        if set(body)!=required:fail('Supply the full recurring business authorization.')
        old=self._existing(doc)
        if old:return old
        if body['connection_id'] is None:
            if not getattr(self.service,'subway_queries',None) or not set(body['operations']) <= {'subway_query','subway_documents','subway_assess'}:
                fail('Native recurring consent requires owned read-only Subway operations.','AUTOMATION_SCOPE_DENIED',403)
            self.service.subway_queries.authorize(auth)
        else:self._connection(auth,body['connection_id'])
        if not isinstance(body['purpose'],str) or not 1<=len(body['purpose'])<=1000:fail('Supply the business purpose.')
        if not isinstance(body['content_scope'],str) or not 1<=len(body['content_scope'])<=2000:fail('Describe the authorized content scope.')
        if set(body['schedule'])=={'cron','timezone'}:
            self.cron(body['schedule']['cron'],body['schedule']['timezone'])
        else:
            from .workflow_events import validate_source
            validate_source(self,auth,body['schedule'])
        if not self.clock()<body['expires_at']<=self.clock()+366*86400:fail('Consent must expire within one year.')
        limits=body['limits']
        if set(limits)!={'max_occurrences','max_actions_per_occurrence'} or any(type(v) is not int or not 1<=v<=10000 for v in limits.values()) or limits['max_actions_per_occurrence']>16:fail('Supply bounded recurring execution limits.')
        if not isinstance(body['operations'],dict) or not 1<=len(body['operations'])<=16:fail('Specify permitted registered operations.')
        tools={t['tool_id']:t for t in self.service.business_composition.tools(auth)}
        for tid,schema in body['operations'].items():
            if tid not in tools:fail('Authorization names an unavailable registered operation.')
            self.schema(schema)
            if 'x-praxi-calendar-occurrence-v1' in schema:
                from .calendar_occurrences import values
                pin=schema['x-praxi-calendar-occurrence-v1']
                if tid!='extension_calendar_create' or not isinstance(pin,dict) or pin.get('timezone')!=body['schedule']['timezone']:
                    fail('Recurring Calendar time must match the reviewed schedule timezone.','AUTOMATION_SCOPE_DENIED',403)
                if set(pin)!={'timezone','hour','minute','duration_minutes'} or any(type(pin[k]) is not int for k in ('hour','minute','duration_minutes')) or not (0<=pin['hour']<24 and 0<=pin['minute']<60 and 1<=pin['duration_minutes']<=999):
                    fail('Invalid recurring Calendar interval.','AUTOMATION_SCOPE_DENIED',403)
                values(pin,self.clock())
            if tid=='subway_assess':
                from .subway_assessments import INPUT as assessment_input
                from jsonschema import Draft202012Validator
                exact=schema.get('const')
                from .subway_automation import DEMO_ASSESSMENT,validate_assessment_consent
                if DEMO_ASSESSMENT in schema:
                    validate_assessment_consent(schema,body['schedule']['timezone'])
                elif not isinstance(exact,dict) or list(Draft202012Validator(assessment_input).iter_errors(exact)):
                    fail('Recurring assessments require exact reviewed input consent.','AUTOMATION_SCOPE_DENIED',403)
            if tid=='subway_query':
                from .subway_automation import validate_consent
                validate_consent(schema,body['schedule']['timezone'])
            # Bound authority fields explicitly; OAuth is not business consent.
            if tid=='workflow_data_query':
                # A fresh executable plan may be prepared each day, but the model
                # cannot expand the reviewed query meaning under recurring consent.
                query_scope=schema.get('properties',{}).get('query',{})
                if 'query' not in schema.get('required',[]) or not isinstance(query_scope.get('const'),dict):
                    fail('Recurring queries require the exact reviewed query in the operation schema properties.query.const.','AUTOMATION_QUERY_SCOPE_REQUIRED',403)
                from .data_queries import CHECKER
                if list(CHECKER.iter_errors(query_scope['const'])) or query_scope['const'].get('clarification'):
                    fail('Resolve and validate the recurring query before authorizing it.','AUTOMATION_QUERY_SCOPE_REQUIRED',403)
                from .temporal_queries import ANNOTATION,validate_pin
                if ANNOTATION in schema:
                    validate_pin(schema[ANNOTATION],query_scope['const'])
                    if schema[ANNOTATION]['timezone']!=body['schedule']['timezone']:
                        fail('Relative-query timezone must match the authorized schedule.','AUTOMATION_QUERY_SCOPE_REQUIRED',403)
            fields=['to'] if tid in ('extension_mail_send','smtp_send_email') else ['message_id'] if tid=='extension_mail_reply' else ['project_id'] if tid=='extension_sheets_create_report' else ['calendar_id'] if tid.startswith('extension_calendar_') else []
            fields=list(set(fields)|({k for k in tools[tid]['definition']['input_schema'].get('properties',{}) if k in {'to','recipient','destination','url','spreadsheet_id','calendar_id','project_id','connection_id','package_id'}}))
            for field in fields:
                rule=schema.get('properties',{}).get(field,{})
                if field not in schema.get('required',[]) or not ('const' in rule or rule.get('enum')):fail('Recurring identity/destination fields require explicit constant restrictions.')
        doc.update(approved_by=deepcopy(auth['subject']),approved_at=self.clock(),used_occurrences=0)
        return self._put(doc)

    def _connection(self, auth, identifier):
        from .google_tools import OwnedToken
        google=getattr(self.service,'google_tools',None)
        if google is None:fail('Selected-account Google integration is required.','GOOGLE_TOOL_UNSUPPORTED',403)
        return OwnedToken(google.manager,auth,identifier).record()

    def schedule(self, auth, body):
        doc=self._document(auth,'schedule',body)
        if set(body)!={'request_key','workflow','authorization_id','cron','timezone','missed_run_policy','overlap_policy','inputs'}:fail('Supply the complete recurring schedule.')
        old=self._existing(doc)
        if old:return old
        if body['missed_run_policy'] not in ('skip','coalesce','catch_up') or body['overlap_policy'] not in ('forbid','allow') or not isinstance(body['inputs'],dict):fail('Unsupported occurrence policy.')
        workflow=self._workflow(auth,body['workflow']);policy=self.get(auth,body['authorization_id'])
        if policy['kind']!='authorization' or policy['state']!='active' or policy['request']['expires_at']<=self.clock():fail('Current recurring consent is required.','AUTOMATION_AUTH_EXPIRED',403)
        if policy['request']['schedule']!={'cron':body['cron'],'timezone':body['timezone']}:fail('Schedule differs from approved consent.')
        if workflow.get('metadata',{}).get('google_connection_id')!=policy['request']['connection_id']:fail('Schedule and authorization must pin the same selected account.')
        doc.update(name=policy['request']['purpose'],due=self.cron(body['cron'],body['timezone']).next(self.clock()),workflow_sha256=digest(workflow),occurrences=0)
        return self._put(doc)

    def subscribe(self, auth, body):
        if isinstance(body,dict) and 'workflow' in body:
            from .workflow_events import subscribe
            return subscribe(self,auth,body)
        doc=self._document(auth,'subscription',body)
        required={'request_key','case_id','wait_id','stage_id','provider','connection_id','correlation','participants','expected_information','payload_mapping','deadline','poll_workflow'}
        if set(body)!=required:fail('Supply a complete event subscription.')
        old=self._existing(doc)
        if old:return old
        RuntimeService.authorize(auth,'events.ingest',{'admin','builder'})
        case=self.service.business_cases.get(auth,body['case_id'])
        if case['case_status'] in TERMINAL:fail('Cannot subscribe a terminal case.')
        wait=case.get('adaptive',{}).get('pending_wait') or case['waits'].get(body['wait_id'])
        if not wait or wait['wait_id']!=body['wait_id'] or body['stage_id'] not in case['stages']:fail('Select the saved waiting stage/action.')
        if wait.get('kind','event')!='event' or body['stage_id']!=case.get('adaptive',{}).get('stage_instance_id',wait.get('stage_instance_id')):fail('Subscription differs from the saved event wait.')
        if not isinstance(body['deadline'],(int,float)) or not self.clock()<body['deadline']<=self.clock()+90*86400:fail('Subscription deadline must be within 90 days.')
        if body['provider'] not in self.providers:fail('Install an authorized provider adapter.')
        if not isinstance(body['participants'],list) or not 1<=len(body['participants'])<=16 or any(not isinstance(x,str) or parseaddr(x)[1]!=x for x in body['participants']):fail('Specify explicit expected participant addresses.')
        if not isinstance(body['correlation'],dict) or not isinstance(body['payload_mapping'],dict) or not 1<=len(body['payload_mapping'])<=16:fail('Supply bounded correlation identifiers and payload paths.')
        if not isinstance(body['expected_information'],str) or not 1<=len(body['expected_information'])<=2000:fail('Describe expected information.')
        binding=self.providers[body['provider']].validate(body,auth,case) or {}
        doc['not_before']=binding.get('not_before',self.clock())
        doc.update(event_type=wait['event_type'],expected_source=wait['expected_source'],cursor=None,processed_count=0,due=self.clock())
        with self.store.transaction() as db:
            current=self.service.business_cases._load(db,self.scope(auth),case['case_id'])
            if current['revision']!=case['revision']:fail('Case changed while subscribing.','CASE_CONFLICT',409)
            if case.get('adaptive'):
                pending=current['adaptive']['pending_wait']
                pending['deadline']=body['deadline'];pending['automation_subscription_id']=doc['id']
                current['adaptive']['suspended_at']=self.clock()
                self.service.business_cases._save(db,self.scope(auth),current)
            timer_body=dict(request_key='deadline_'+doc['id'],case_id=case['case_id'],wait_id=body['wait_id'],stage_id=body['stage_id'],due=body['deadline'],purpose='reply_deadline')
            timer=self._document(auth,'timer',timer_body);timer.update(due=body['deadline'],subscription_id=doc['id']);self._save(db,timer)
            doc['timer_id']=timer['id'];self._save(db,doc)
        return doc

    def _approval_wait(self,db,auth,case,body,expired=False):
        stage=case['stages'][body['stage_id']];rid=stage.get('run_id')
        if not rid:return None
        run=self.service.runtime_runner.runtime.load(db,rid,auth)
        approval=next((x for x in run['approvals'] if x['approval_id']==body['wait_id'] and x['status'] in (('pending','timed_out') if expired else ('pending',))),None)
        if not approval or run['status']!='paused_for_approval' and not (expired and approval['status']=='timed_out'):return None
        return dict(wait_id=approval['approval_id'],kind='approval',status='PENDING' if approval['status']=='pending' else 'TIMED_OUT',run_id=rid)

    def timer(self, auth, body):
        doc=self._document(auth,'timer',body)
        required={'request_key','case_id','wait_id','stage_id','due','purpose'}
        if set(body)!=required or body['purpose'] not in ('follow_up','reply_deadline','approval_deadline','escalation','delayed_continuation','retry_after'):fail('Supply a typed durable timer.')
        if type(body['due']) not in (int,float) or not self.clock()<=body['due']<=self.clock()+90*86400:fail('Timer due time is outside its bound.')
        case=self.service.business_cases.get(auth,body['case_id'])
        if case['case_status'] in TERMINAL or body['stage_id'] not in case['stages']:fail('Select an active case stage.')
        wait=case.get('adaptive',{}).get('pending_wait') or case['waits'].get(body['wait_id'])
        if body['purpose']=='approval_deadline':
            with self.store.transaction(write=False) as db:wait=self._approval_wait(db,auth,case,body)
            if wait:doc['approval_id']=wait['wait_id']
        if not wait or wait['wait_id']!=body['wait_id']:fail('Timer must reference a current wait.')
        doc['due']=body['due']
        old=self._existing(doc)
        if old:return old
        with self.store.transaction() as db:
            current=self.service.business_cases._load(db,self.scope(auth),case['case_id'])
            if current['revision']!=case['revision']:fail('Case changed while registering timer.','CASE_CONFLICT',409)
            if current.get('adaptive'):
                current['adaptive'].setdefault('suspended_at',self.clock())
                self.service.business_cases._save(db,self.scope(auth),current)
            self._save(db,doc)
        return doc

    def control(self, auth, identifier, body):
        scope=self.scope(auth,True);self.request('control',body)
        if body['action']=='retry':return self.retry(auth,identifier,body)
        command=self._document(auth,'control',{**body,'target_id':identifier})
        with self.store.transaction() as db:
            old=db.execute('SELECT document FROM automation_records WHERE id=?',(command['id'],)).fetchone()
            if old:
                if json.loads(old[0])['fingerprint']!=command['fingerprint']:fail('Control request key reused.','AUTOMATION_CONFLICT',409)
                return self._get(db,scope,identifier)
            doc=self._get(db,scope,identifier)
            if doc['kind'] in ('occurrence','control'):fail('Control the parent schedule instead of an occurrence or command.')
            if doc['kind']=='authorization':RuntimeService.authorize(auth,'workflow.approve',{'admin','approver'})
            if doc['state'] in ('cancelled','revoked','completed'):return doc
            action=body['action']
            if action=='replace':
                RuntimeService.authorize(auth,'workflow.approve',{'admin','approver'})
                replacement=self._get(db,scope,body['replacement_id'])
                if doc['kind'] not in ('schedule','subscription') or replacement['kind']!=doc['kind'] or replacement['state'] not in ('active','paused') or replacement['id']==doc['id']:fail('Select a separately reviewed active replacement automation.')
                policy=self._get(db,scope,replacement['request']['authorization_id'],'authorization')
                if policy['state']!='active' or policy['request']['expires_at']<=self.clock():fail('Replacement authority has expired.')
                doc['replaced_by']=replacement['id'];replacement['replaces']=doc['id'];replacement['state']='active';self._save(db,replacement)
            doc['state']={'pause':'paused','resume':'active','cancel':'cancelled','revoke':'revoked','replace':'cancelled'}[action]
            doc['updated_at']=self.clock();self._save(db,doc)
            if doc['kind']=='subscription' and doc.get('timer_id'):
                timer=self._get(db,scope,doc['timer_id']);timer['state']=doc['state'];self._save(db,timer)
            command['state']='completed';self._save(db,command)
        return doc

    def retry(self,auth,identifier,body):
        scope=self.scope(auth,True);self._fresh(auth)
        command=self._document(auth,'control',{**body,'target_id':identifier})
        with self.store.transaction() as db:
            prior=db.execute('SELECT document FROM automation_records WHERE id=?',(command['id'],)).fetchone()
            if prior:
                if json.loads(prior[0])['fingerprint']!=command['fingerprint']:fail('Retry key reused.','AUTOMATION_CONFLICT',409)
                return self._get(db,scope,identifier)
            occurrence=self._get(db,scope,identifier,'occurrence')
            if occurrence['state'] not in ('failed','dead_letter') or occurrence.get('retry_count',0)>=3:fail('Occurrence is not eligible for bounded retry.','AUTOMATION_RETRY_INELIGIBLE',409)
            parent=self._get(db,scope,occurrence['schedule_id']);policy=self._get(db,scope,parent['request']['authorization_id'],'authorization')
            if parent['state']!='active' or policy['state']!='active' or policy['request']['expires_at']<=self.clock():fail('Renew current automation authority before retrying.','AUTOMATION_AUTH_REVOKED',403)
            if occurrence.get('run_id'):
                run=self.service.runtime_runner.runtime.load(db,occurrence['run_id'],auth)
                if run['status'] not in ('queued','running') or any(x.get('external_effect_status')=='requires_reconciliation' for x in run.get('action_instances',{}).values()):fail('Terminal or uncertain runs require review; completed effects cannot be replayed.','AUTOMATION_RETRY_INELIGIBLE',409)
            elif occurrence.get('last_error_code') not in ('AUTOMATION_AUTH_REVOKED','QUEUE_CAPACITY_EXCEEDED','GOOGLE_TOOL_UNSUPPORTED','GOOGLE_CONNECTION_REQUIRED','DATABASE_UNAVAILABLE'):
                fail('Uncertain dispatch requires review.','AUTOMATION_RETRY_INELIGIBLE',409)
            row=db.execute('SELECT document FROM lifecycle_jobs WHERE job_id=?',(occurrence['job_id'],)).fetchone();job=json.loads(row[0])
            if job['state']=='leased':fail('A worker still owns this job.','AUTOMATION_RETRY_INELIGIBLE',409)
            job.update(state='queued',lease_until=None,available_at=now_iso(self.clock));db.execute('DELETE FROM lifecycle_job_claims WHERE job_id=?',(job['job_id'],))
            db.execute("UPDATE lifecycle_jobs SET state='queued',lease_until=NULL,available_at=?,document=? WHERE job_id=?",(job['available_at'],canonical(job),job['job_id']))
            occurrence.update(state='queued',retry_count=occurrence.get('retry_count',0)+1);self._save(db,occurrence)
            command['state']='completed';self._save(db,command)
        return occurrence

    def suspended(self,db,auth,run):
        if not run.get('automation_reference'):return False
        self._fresh(auth);scope=self.scope(auth,True)
        occurrence=self._get(db,scope,run['automation_reference']['occurrence_id'],'occurrence')
        parent=self._get(db,scope,occurrence['schedule_id']);policy=self._get(db,scope,parent['request']['authorization_id'],'authorization')
        if parent['state']=='paused' or policy['state']=='paused':
            run.update(lease_until=0,available_at=self.clock()+15);self.service.runtime_runner.runtime.save(db,run);return True
        return False

    def history(self,auth,identifier):
        scope=self.scope(auth);self.get(auth,identifier)
        with self.store.transaction(write=False) as db:
            items=[json.loads(row[0]) for row in db.execute("SELECT document FROM automation_records WHERE workspace=? AND owner=? AND kind='occurrence' AND json_extract(document,'$.schedule_id')=? ORDER BY due DESC LIMIT 50",(*scope,identifier)).fetchall()]
        return [dict({k:deepcopy(o[k]) for k in ('id','state','due','created_at','run_id','result','last_error_code','retry_count','metrics') if k in o},retry_eligible=o['state'] in ('failed','dead_letter') and not o.get('run_id') and o.get('retry_count',0)<3 and o.get('last_error_code') in ('AUTOMATION_AUTH_REVOKED','QUEUE_CAPACITY_EXCEEDED','GOOGLE_TOOL_UNSUPPORTED','GOOGLE_CONNECTION_REQUIRED','DATABASE_UNAVAILABLE')) for o in items]

    def _enqueue(self, db, scope, target, key, kind, **fields):
        job_id='automation_job_'+digest([scope,key])[:32]
        now=now_iso(self.clock)
        job=dict(job_id=job_id,workspace_id=scope[0],owner_id=scope[1],automation_kind=kind,target_id=target,serialization_key='case:'+target if kind=='case' else fields.get('serialization_key'),state='queued',attempt=0,lease_until=None,available_at=now,deduplication_key=job_id,**{k:v for k,v in fields.items() if k!='serialization_key'})
        db.execute('INSERT INTO lifecycle_jobs(workspace,job_id,release_id,workflow_id,state,available_at,lease_until,attempt,document) VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(job_id) DO NOTHING', (scope[0],job_id,'automation',target,'queued',now,None,0,canonical(job)))
        return job_id

    def _unsuspend(self, db, auth, case):
        a=case.get('adaptive')
        if not a or a.get('suspended_at') is None:return
        elapsed=max(0,self.clock()-a.pop('suspended_at'))
        a['status']='active'
        a['deadline']+=elapsed;a['waited_seconds']=a.get('waited_seconds',0)+elapsed
        rid=a.get('run_id')
        if rid:
            rt=self.service.runtime_runner.runtime;run=rt.load(db,rid,auth)
            if run.get('lease_until',0)>self.clock() or any(v=='executing' for v in run['node_states'].values()):fail('Cannot resume an in-flight invocation.','AUTOMATION_CASE_BUSY',409)
            run['created_at']+=elapsed;run.setdefault('automation_pauses',[]).append(dict(seconds=elapsed,resumed_at=self.clock()));rt.save(db,run)

    def accept(self, auth, subscription_id, event):
        subscription=self.get(auth,subscription_id)
        if 'workflow' in subscription.get('request',{}):
            from .workflow_events import accept
            return accept(self,auth,subscription,event)
        sub=self.get(auth,subscription_id);body=deepcopy(sub['request']);body['sent_at']=sub.get('not_before',0);scope=self.scope(auth,True)
        RuntimeService.authorize(auth,'events.ingest',{'admin','builder'})
        identity=event['event_id']
        with self.store.transaction(write=False) as db:
            old=db.execute('SELECT document FROM automation_deliveries WHERE workspace=? AND owner=? AND subscription=? AND event_id=?',(*scope,sub['id'],identity)).fetchone()
        if old:return dict(duplicate=True,accepted=False)
        with self.store.transaction(write=False) as db:
            seen=db.execute("SELECT 1 FROM automation_deliveries d JOIN automation_records r ON r.id=d.subscription WHERE d.workspace=? AND d.owner=? AND d.event_id=? AND json_extract(r.document,'$.request.case_id')=? AND json_extract(r.document,'$.request.provider')=? AND json_extract(r.document,'$.request.connection_id')=?",(*scope,identity,body['case_id'],body['provider'],body['connection_id'])).fetchone()
        if seen:return dict(duplicate=True,accepted=False)
        if sub['state']!='active' or self.clock()>body['deadline']:return dict(accepted=False)
        case=self.service.business_cases.get(auth,body['case_id'])
        if case['case_status'] in TERMINAL:return dict(accepted=False)
        self.providers[body['provider']].validate(body,auth,case)
        if not self.providers[body['provider']].matches(body,event):return dict(accepted=False)
        payload={k:self.service.lifecycle._lookup(event['payload'],path) for k,path in body['payload_mapping'].items()}
        key='event_'+digest([sub['id'],identity])[:48]
        def commit(db,current):
            latest=self._get(db,scope,sub['id'],'subscription')
            if latest['state']!='active':fail('Subscription was paused or revoked.','AUTOMATION_CANCELLED',409)
            self._unsuspend(db,auth,current)
            current.setdefault('automation_evidence',[]).append(dict(event_id=identity,subscription_id=sub['id'],provider=body['provider'],connection_id=body['connection_id'],payload=deepcopy(event['payload']),provenance_type='ACTUAL',qualification='Provider-reported event; not business authority.'))
            self.service.business_cases._save(db,scope,current)
            job=self._enqueue(db,scope,current['case_id'],key,'case')
            db.execute('INSERT INTO automation_deliveries(workspace,owner,subscription,event_id,document) VALUES (?,?,?,?,?)',(*scope,sub['id'],identity,canonical(dict(event=event,job_id=job))))
            latest.update(state='completed',cursor=event.get('cursor',identity),processed_count=latest['processed_count']+1,completed_at=self.clock());self._save(db,latest)
        if case.get('adaptive'):
            from .adaptive_orchestration import AdaptiveOrchestration
            wait=case['adaptive']['pending_wait']
            if not wait or wait['wait_id']!=body['wait_id']:return dict(accepted=False)
            AdaptiveOrchestration(self.service.business_cases).supply(auth,case['case_id'],dict(request_key=key,expected_revision=case['revision'],wait_id=body['wait_id'],event=dict(source=sub['expected_source'],event_type=sub['event_type'],payload=payload)),on_accept=commit)
        else:
            wait=case['waits'][body['wait_id']]
            self.service.business_cases.event(auth,case['case_id'],dict(request_key=key,event_id=identity,event_type=sub['event_type'],source=sub['expected_source'],correlation_keys=wait['correlation_keys'],payload=payload),on_accept=commit)
        return dict(accepted=True,duplicate=False)

    def _due_schedule(self, auth, saved):
        scope=self.scope(auth,True)
        with self.store.transaction() as db:
            doc=self._get(db,scope,saved['id'],'schedule');body=doc['request'];now=self.clock()
            if doc['state']!='active' or doc['due']>now:return
            policy=self._get(db,scope,body['authorization_id'],'authorization')
            if policy['state']!='active' or policy['request']['expires_at']<=now:
                doc.update(state='paused',last_error_code='AUTOMATION_AUTH_EXPIRED');self._save(db,doc);return
            cron=self.cron(body['cron'],body['timezone']);due=doc['due'];count=0
            # Bounded catch-up. Each due time is a stable occurrence identity.
            scanned=0
            while due<=now and count<10 and scanned<1000:
                scanned+=1
                following=cron.next(due)
                if body['missed_run_policy']=='skip' and now-due>=60:
                    doc['skipped_count']=doc.get('skipped_count',0)+1;due=cron.next(now);break
                if body['missed_run_policy']=='coalesce' and following<=now:
                    due=following;continue
                active=[json.loads(r[0]) for r in db.execute("SELECT document FROM automation_records WHERE workspace=? AND owner=? AND kind='occurrence'",scope).fetchall()]
                if body['overlap_policy']=='forbid' and any(o['schedule_id']==doc['id'] and o['state'] in ('queued','running','waiting','requires_reconciliation') for o in active):
                    doc['poll_after']=now+15;self._save(db,doc);return
                if policy['used_occurrences']>=policy['request']['limits']['max_occurrences']:
                    doc.update(state='paused',last_error_code='AUTOMATION_OCCURRENCE_LIMIT');break
                identifier='occ_'+digest([scope,doc['id'],due])[:32]
                old=db.execute('SELECT 1 FROM automation_records WHERE id=?',(identifier,)).fetchone()
                if not old:
                    occurrence=dict(id=identifier,kind='occurrence',workspace_id=scope[0],owner_id=scope[1],schedule_id=doc['id'],state='queued',due=due,created_at=now,errors=[],attempts=0,run_id=None)
                    job=self._enqueue(db,scope,identifier,identifier,'occurrence',schedule_id=doc['id'],serialization_key='schedule:'+doc['id'] if body['overlap_policy']=='forbid' else None)
                    occurrence['job_id']=job;self._save(db,occurrence);policy['used_occurrences']+=1;doc['occurrences']+=1
                due=following;count+=1
            doc.pop('poll_after',None);doc['due']=due;self._save(db,policy);self._save(db,doc)

    def _fire_timer(self, auth, saved):
        scope=self.scope(auth,True);cases=self.service.business_cases
        with self.store.transaction() as db:
            doc=self._get(db,scope,saved['id'],'timer');body=doc['request']
            if doc['state']!='active' or doc['due']>self.clock():return
            case=cases._load(db,scope,body['case_id'])
            if case['case_status'] in TERMINAL:doc['state']='cancelled';self._save(db,doc);return
            a=case.get('adaptive');wait=(a or {}).get('pending_wait') or case['waits'].get(body['wait_id'])
            if doc.get('approval_id'):wait=self._approval_wait(db,auth,case,body,expired=True)
            if not wait or wait['wait_id']!=body['wait_id']:doc['state']='cancelled';self._save(db,doc);return
            observation=dict(observation_id='timer:'+doc['id'],kind='timer_expired',provenance_type='ACTUAL',value=dict(timer_id=doc['id'],purpose=body['purpose'],due=doc['due'],observed_at=self.clock(),reply_observed=False))
            if doc.get('approval_id'):
                self._unsuspend(db,auth,case)
                run=self.service.runtime_runner.runtime.load(db,wait['run_id'],auth)
                if wait['status']=='PENDING':self.service.runtime_runner.expire(db,run)
            if a:
                self._unsuspend(db,auth,case);wait.update(status='TIMED_OUT');a.setdefault('wait_history',[]).append(deepcopy(wait));a['pending_wait']=None;a.setdefault('input_observations',[]).append(observation);a['status']='active'
                from .adaptive_orchestration import AdaptiveOrchestration
                adaptive=AdaptiveOrchestration(cases);adaptive._status(case,'READY');adaptive._phase(case,'EVALUATE')
            else:
                wait['current_status']='TIMED_OUT';cases.refresh(case,scope)
            cases.record(case,'automation.timer_expired',timer_id=doc['id']);cases._save(db,scope,case)
            self._enqueue(db,scope,case['case_id'],doc['id'],'case');doc.update(state='completed',fired_at=self.clock());self._save(db,doc)
            if doc.get('subscription_id'):
                sub=self._get(db,scope,doc['subscription_id']);sub['state']='expired';self._save(db,sub)

    def tick(self, authenticate):
        with self.store.transaction(write=False) as db:
            records=[json.loads(r[0]) for r in db.execute("SELECT document FROM automation_records WHERE state='active' AND kind IN ('schedule','timer','subscription') AND (due IS NULL OR due<=?) ORDER BY id LIMIT 200",(self.clock(),)).fetchall()]
        for doc in records:
            if doc.get('poll_after',doc.get('due',0))>self.clock():continue
            auth=authenticate(doc['workspace_id'],doc['owner_id'])
            if not auth:continue
            try:
                self.scope(auth,True)
                if doc['kind']=='schedule':self._due_schedule(auth,doc)
                elif doc['kind']=='timer':self._fire_timer(auth,doc)
                elif doc['kind']=='subscription':
                    if 'workflow' in doc['request']:
                        from .workflow_events import poll
                        poll(self,auth,doc)
                        continue
                    case=self.service.business_cases.get(auth,doc['request']['case_id'])
                    if case['case_status'] in TERMINAL:
                        with self.store.transaction() as db:
                            current=self._get(db,self.scope(auth),doc['id']);current['state']='cancelled';self._save(db,current)
                        continue
                    if doc['request']['deadline']<self.clock():continue
                    events,cursor=self.providers[doc['request']['provider']].poll(doc,auth,case)
                    for event in events:
                        if self.accept(auth,doc['id'],event).get('accepted'):break
                    with self.store.transaction() as db:
                        current=self._get(db,self.scope(auth),doc['id']);current['cursor']=cursor;current['last_polled_at']=self.clock();current['poll_after']=self.clock()+15;self._save(db,current)
            except Exception as exc:
                with self.store.transaction() as db:
                    current=self._get(db,(doc['workspace_id'],doc['owner_id']),doc['id']);current['attempts']+=1;current['poll_after']=self.clock()+min(3600,2**min(current['attempts'],10));current['last_error_code']=getattr(exc,'code','AUTOMATION_PROVIDER_FAILED');current['errors']=(current['errors']+[dict(code=current['last_error_code'],at=self.clock())])[-16:];self._save(db,current)
        self._resume_jobs(authenticate)
        failures=sum(1 for d in records if d.get('last_error_code'))
        self.health.update(state='degraded' if failures else 'ready',last_success=self.clock(),last_error='AUTOMATION_RECORDS_REQUIRE_ATTENTION' if failures else None)

    def _resume_jobs(self,authenticate):
        with self.store.transaction(write=False) as db:
            jobs=[json.loads(r[0]) for r in db.execute("SELECT document FROM lifecycle_jobs WHERE state='waiting' ORDER BY rowid LIMIT 100").fetchall()]
        for job in jobs:
            if not job.get('automation_kind'):continue
            scope=(job['workspace_id'],job['owner_id']);auth=authenticate(*scope)
            if not auth:continue
            try:
                with self.store.transaction() as db:
                    row=db.execute('SELECT document FROM lifecycle_jobs WHERE job_id=?',(job['job_id'],)).fetchone();current=json.loads(row[0])
                    if current['state']!='waiting':continue
                    if job['automation_kind']=='occurrence':
                        occurrence=self._get(db,scope,job['target_id']);rid=occurrence.get('run_id')
                    else:
                        case=self.service.business_cases._load(db,scope,job['target_id']);rid=case.get('adaptive',{}).get('run_id')
                    if not rid:
                        if job['automation_kind']=='occurrence':
                            parent=self._get(db,scope,occurrence['schedule_id'])
                            if parent['state']=='active':
                                current.update(state='queued',lease_until=None)
                                db.execute("UPDATE lifecycle_jobs SET state='queued',lease_until=NULL,document=? WHERE job_id=?",(canonical(current),current['job_id']))
                        if job['automation_kind']=='case':
                            stage=case['stages'][case['adaptive']['stage_instance_id']];reference=stage.get('workflow',{})
                            workflow=self.store.get(db,scope[0],reference.get('workflow_id'),reference.get('version',1))
                            if workflow and workflow['status'] in ('approved','published'):
                                self._enqueue(db,scope,job['target_id'],'reviewed:'+job['job_id']+':'+digest(workflow),'case')
                                self.service.lifecycle._finish_job(db,current,'completed',None)
                        continue
                    run=self.service.runtime_runner.runtime.load(db,rid,auth)
                    if run['status'] in ('completed','failed','blocked','cancelled') and job['automation_kind']=='occurrence':
                        state='completed' if run['status']=='completed' else 'dead_letter'
                        occurrence.update(state=state,result={k:deepcopy(run[k]) for k in ('run_id','workflow_id','workflow_version','status','error_code','trace_reference') if k in run});self._save(db,occurrence)
                        self.service.lifecycle._finish_job(db,current,state,run.get('error_code'))
                    elif run['status'] in ('running','queued'):
                        if job['automation_kind']=='case':
                            self._enqueue(db,scope,job['target_id'],'resume:'+job['job_id']+':'+digest(run.get('approval_decisions',{})),'case')
                            self.service.lifecycle._finish_job(db,current,'completed',None)
                        else:
                            current.update(state='queued',lease_until=None)
                            db.execute("UPDATE lifecycle_jobs SET state='queued',lease_until=NULL,document=? WHERE job_id=?",(canonical(current),current['job_id']))
            except Exception:continue

    def _fresh(self,auth):
        resolver=getattr(self.service,'worker_authenticate',None)
        if not resolver:fail('Configure current worker authentication.','AUTOMATION_AUTH_REVOKED',403)
        current=resolver(auth['subject']['workspace_id'],auth['subject']['subject_id'])
        if not current or current.get('subject')!=auth['subject']:fail('Execution identity was revoked.','AUTOMATION_AUTH_REVOKED',403)
        self.scope(current,True)
        return current

    def guard_run(self,db,auth,run,workflow):
        try:
            policy,schedule,occurrence=self._policy(db,auth,run)
            if not self._pinned(db,run,workflow,schedule):fail('Pinned recurring definition changed.','AUTOMATION_SCOPE_DENIED',403)
            return policy
        except Exception as exc:
            raise RuntimeFailure(getattr(exc,'code','AUTOMATION_AUTH_REVOKED'),'Recurring execution authority must be renewed.',403) from None

    def _policy(self, db, auth, run):
        auth=self._fresh(auth);scope=self.scope(auth,True);ref=run.get('automation_reference')
        if not ref:return None
        occurrence=self._get(db,scope,ref['occurrence_id'],'occurrence');schedule=self._get(db,scope,occurrence['schedule_id']);policy=self._get(db,scope,schedule['request']['authorization_id'],'authorization')
        if 'scheduled_due' in ref and ref['scheduled_due']!=occurrence['due']:fail('Logical occurrence time changed.','AUTOMATION_SCOPE_DENIED',403)
        if schedule['state']!='active' or policy['state']!='active' or policy['request']['expires_at']<=self.clock():fail('Recurring business authority is inactive.','AUTOMATION_AUTH_REVOKED',403)
        if run['workflow_id']!=schedule['request']['workflow']['workflow_id'] or run['workflow_version']!=schedule['request']['workflow']['workflow_version']:fail('Recurring workflow pin differs.','AUTOMATION_SCOPE_DENIED',403)
        return policy,schedule,occurrence

    def _pinned(self,db,run,workflow,schedule):
        root=self.store.get(db,run['workspace_id'],run['workflow_id'],run['workflow_version'])
        if not root or digest(root)!=schedule['workflow_sha256']:return False
        from .workflow_adaptive import effective
        return digest(effective(run,root))==digest(workflow)

    def check_action(self, db, auth, run, workflow, node, inputs):
        if not run.get('automation_reference'):return
        policy,schedule,occurrence=self._policy(db,auth,run)
        self.service.registry_adapter.execution_assignments(workflow,self._fresh(auth))
        if not self._pinned(db,run,workflow,schedule) or workflow.get('metadata',{}).get('google_connection_id')!=policy['request']['connection_id']:fail('Recurring workflow/account changed.','AUTOMATION_SCOPE_DENIED',403)
        schema=policy['request']['operations'].get(node['tool_id'])
        if schema and 'x-praxi-calendar-occurrence-v1' in schema:
            from .calendar_occurrences import values
            pin=workflow.get('metadata',{}).get('overview_intent',{}).get('calendar_occurrence')
            if node['tool_id']!='extension_calendar_create' or pin!=schema['x-praxi-calendar-occurrence-v1']:
                fail('Calendar interval differs from the reviewed workflow.','AUTOMATION_SCOPE_DENIED',403)
            expected=values(pin,occurrence['due'])
            if any(inputs.get('event',{}).get(field)!=expected['calendar_event_'+field] for field in ('start','end')):
                fail('Calendar event must preserve its reviewed occurrence time.','AUTOMATION_SCOPE_DENIED',403)
        if node['tool_id']=='subway_assess' and schema and 'x-praxi-subway-demo-assessment-v1' in schema:
            from .subway_automation import check_assessment
            check_assessment(schema,inputs,workflow,run,self.service.subway_queries,auth)
        if node['tool_id']=='subway_query':
            from .subway_automation import check_query
            check_query(schema,inputs,workflow,run,self.service.subway_queries,auth)
        from .temporal_queries import ANNOTATION,consent_schema
        if schema and ANNOTATION in schema:
            overview=workflow.get('metadata',{}).get('overview_intent',{})
            if (node['tool_id']!='workflow_data_query' or schema[ANNOTATION]!=overview.get('temporal_pin')
                    or schema.get('properties',{}).get('query',{}).get('const')!=overview.get('query')):
                fail('Relative query differs from the approved workflow.','AUTOMATION_SCOPE_DENIED',403)
            schema=consent_schema(schema,occurrence['due'])
        if schema is None or list(Draft202012Validator(schema).iter_errors(inputs)):fail('Action exceeds recurring business consent.','AUTOMATION_APPROVAL_REQUIRED',403)
        if len(run.get('automation_approvals',{}))>policy['request']['limits']['max_actions_per_occurrence']:fail('Recurring action limit exceeded.','AUTOMATION_ACTION_LIMIT',403)

    def _approve(self, auth, run):
        auth=self._fresh(auth)
        rid=run['run_id'];runtime=self.service.runtime_runner.runtime
        with self.store.transaction(write=False) as db:
            saved=runtime.load(db,rid,auth);workflow=self.store.get(db,saved['workspace_id'],saved['workflow_id'],saved['workflow_version'])
            approval=saved['approvals'][-1];gate=saved['approval_context']['node_id'];edge=next(e for e in workflow['edges'] if e['source']==gate and e.get('outcome')=='approved');node=next(n for n in workflow['nodes'] if n['node_id']==edge['target'])
            from .workflow_adaptive import effective
            try:self.check_action(db,auth,saved,effective(saved,workflow),node,approval['resolved_payload'])
            except Exception:return False
            if len(saved.get('automation_approvals',{}))>=self._policy(db,auth,saved)[0]['request']['limits']['max_actions_per_occurrence']:return False
        self._connection(auth,workflow['metadata']['google_connection_id'])
        self.service.runtime_runner.decide(dict(request_id='recurring_'+approval['approval_id'],idempotency_key='recurring_'+approval['approval_id'],payload=dict(approval_id=approval['approval_id'],workflow_id=run['workflow_id'],workflow_version=run['workflow_version'],decision='approved')),auth)
        with self.store.transaction() as db:
            saved=runtime.load(db,rid,auth);saved.setdefault('automation_approvals',{})[approval['approval_id']]=dict(policy_id=self._policy(db,auth,saved)[0]['id'],payload_sha256=digest(approval['resolved_payload']),at=self.clock());runtime.save(db,saved)
        return True

    def execute_job(self, job, claim, runner):
        lifecycle=self.service.lifecycle;scope=(job['workspace_id'],job['owner_id'])
        resolver=getattr(self.service,'worker_authenticate',None);auth=resolver(*scope) if resolver else None
        result=None;error=None;state='dead_letter'
        try:
            if auth is None or auth.get('subject')!={'workspace_id':scope[0],'subject_id':scope[1]}:fail('Fresh worker authority is required.','AUTOMATION_AUTH_REVOKED',403)
            self.scope(auth,True)
            if job['automation_kind']=='case':
                from .lifecycle_driver import LifecycleDriver
                case=self.service.business_cases.get(auth,job['target_id'])
                if case['case_status']=='CANCELLED':state='cancelled'
                else:
                    result=LifecycleDriver(self.service.business_cases).drive(auth,job['target_id'],dict(request_key=job['job_id'],max_commands=16,max_seconds=120))
                    state='queued' if result['stop_reason']=='driver_in_progress' else 'completed' if result['stop_reason'] in ('terminal','external_or_input_wait','budget_exhausted') else 'waiting' if result['stop_reason'] in ('approval_wait','execution_in_progress') else 'dead_letter'
            else:
                with self.store.transaction(write=False) as db:
                    occurrence=self._get(db,scope,job['target_id'],'occurrence');schedule=self._get(db,scope,occurrence['schedule_id']);policy=self._get(db,scope,schedule['request']['authorization_id'],'authorization')
                if schedule['state']=='paused' or policy['state']=='paused':
                    with self.store.transaction() as db:
                        current=self._get(db,scope,occurrence['id']);current['state']='waiting';self._save(db,current)
                        return lifecycle._finish_job(db,job,'waiting',None,claim)
                if occurrence['state']=='completed':state='completed'
                else:
                    if policy['request']['connection_id'] is not None:self._connection(auth,policy['request']['connection_id'])
                    workflow=self._workflow(auth,schedule['request']['workflow'])
                    if digest(workflow)!=schedule['workflow_sha256'] or schedule['state']!='active' or policy['state']!='active' or policy['request']['expires_at']<=self.clock():fail('Schedule or consent revoked.','AUTOMATION_AUTH_REVOKED',403)
                    if len(workflow.get('metadata',{}).get('connected_action_plan',{}).get('actions',workflow['nodes']))>policy['request']['limits']['max_actions_per_occurrence']:fail('Occurrence exceeds consent execution limits.','AUTOMATION_ACTION_LIMIT',403)
                    def attach(db,created):
                        current=self._get(db,scope,occurrence['id'])
                        if current.get('run_id'):
                            if current['run_id']!=created['run_id']:fail('Occurrence run identity changed.','AUTOMATION_CONFLICT',409)
                            return
                        current.update(state='running',run_id=created['run_id']);self._save(db,current)
                        run=runner.runtime.load(db,created['run_id'],auth);run['automation_reference']=dict(occurrence_id=current['id'],scheduled_due=current['due'],trigger=deepcopy(current.get('trigger',{'kind':'schedule','automation_id':schedule['id']}))); runner.runtime.save(db,run)
                    created=runner.runtime.create_automation_run(dict(request_id='occurrence_'+occurrence['id'],idempotency_key=occurrence['id'],payload={**schedule['request']['workflow'],'inputs':schedule['request']['inputs']}),auth,on_created=attach)
                    for _ in range(17):
                        result=runner.advance(created['run_id'],auth)
                        if result['status']=='paused_for_approval' and self._approve(auth,result):continue
                        break
                    state='completed' if result['status']=='completed' else 'waiting' if result['status'] in ('paused_for_approval','running','queued') else 'dead_letter'
                    if state=='dead_letter':
                        with self.store.transaction(write=False) as db:failed=runner.runtime.load(db,created['run_id'],auth)
                        error=failed.get('error_code') or 'AUTOMATION_RUNTIME_FAILED'
        except Exception as exc:
            error=getattr(exc,'code','AUTOMATION_DISPATCH_UNCERTAIN')
            from .postgres import DatabaseFailure
            import sqlite3
            transient=(isinstance(exc,DatabaseFailure) and exc.retryable or isinstance(exc,sqlite3.OperationalError) and getattr(exc,'sqlite_errorcode',0)&255 in (sqlite3.SQLITE_BUSY,sqlite3.SQLITE_LOCKED) or error=='QUEUE_CAPACITY_EXCEEDED')
            if transient and job['attempt']<3:
                state='queued';job['available_at']=datetime.fromtimestamp(self.clock()+min(2**job['attempt'],60),timezone.utc).isoformat()

        with self.store.transaction() as db:
            token=db.execute('SELECT token FROM lifecycle_job_claims WHERE job_id=?',(job['job_id'],)).fetchone()
            if not token or token[0]!=claim:return job
            if job['automation_kind']=='occurrence':
                occurrence=self._get(db,scope,job['target_id']);occurrence.update(state='completed' if state=='completed' else 'waiting' if state=='waiting' else 'queued' if state=='queued' else 'failed',last_error_code=error,result={k:deepcopy(result[k]) for k in ('run_id','workflow_id','workflow_version','status','error_code','trace_reference') if result and k in result})
                if occurrence.get('run_id'):
                    saved_run=db.execute('SELECT document FROM runtime_runs WHERE workspace=? AND run_id=?',(scope[0],occurrence['run_id'])).fetchone()
                    run=json.loads(saved_run[0]) if saved_run else {}
                    if run.get('subject_id')!=scope[1]:fail('Occurrence run ownership differs.','AUTOMATION_SCOPE_DENIED',403)
                    if any(x.get('external_effect_status')=='requires_reconciliation' for x in run.get('action_instances',{}).values()):occurrence['state']='requires_reconciliation'
                    occurrence['metrics']=dict(scheduler_delay_seconds=max(0,occurrence['created_at']-occurrence['due']),workflow_latency_seconds=max(0,runner.runtime.clock()-run['created_at']),usage=deepcopy(run.get('usage',{}).get('workflow',{})),replans=max(0,run.get('adaptive',{}).get('revision',1)-1),worker_recoveries=max(0,job['attempt']-1),freshness_failures=sum(1 for l in run.get('adaptive',{}).get('deterministic_limitations',[]) if l['code']=='SOURCE_FRESHNESS_UNVERIFIED'))
                self._save(db,occurrence)
                if state=='completed':
                    parent=self._get(db,scope,occurrence['schedule_id']);consent=self._get(db,scope,parent['request']['authorization_id'],'authorization')
                    outstanding=db.execute("SELECT 1 FROM automation_records WHERE workspace=? AND owner=? AND kind='occurrence' AND json_extract(document,'$.schedule_id')=? AND state IN ('queued','running','waiting','requires_reconciliation')",(*scope,parent['id'])).fetchone()
                    if parent['state']=='active' and consent['used_occurrences']>=consent['request']['limits']['max_occurrences'] and not outstanding:
                        parent.update(state='completed',due=None,completed_at=self.clock());parent.pop('poll_after',None);self._save(db,parent)
            if state=='dead_letter' and error is None:error=(result or {}).get('error_code') or 'AUTOMATION_CONTINUATION_FAILED'
            if result:job['result']={k:deepcopy(result[k]) for k in ('case_id','revision','stop_reason','commands_used','run_id','workflow_id','workflow_version','status','error_code','trace_reference') if k in result}
            if state=='completed' and job['automation_kind']=='case' and result and result['stop_reason']=='budget_exhausted' and result.get('adaptive',{}).get('deadline',self.clock()+1)>self.clock() and job.get('turn',0)<64:
                turn=job.get('turn',0)+1;root=job.get('chain_id',job['job_id']);self._enqueue(db,scope,job['target_id'],root+':'+str(turn),'case',turn=turn,chain_id=root)
            if error and job.get('result') is not None:job['result']['error_code']=error
            if state=='queued':db.execute('UPDATE lifecycle_jobs SET available_at=? WHERE job_id=?',(job['available_at'],job['job_id']))
            return lifecycle._finish_job(db,job,state,error,claim)


class GmailReplyProvider:
    """Selected-account, Registry-assigned Gmail thread polling; no IMAP fallback."""
    def __init__(self,service):self.service=service

    def _binding(self,body,auth):
        reference=body['poll_workflow']
        with self.service.store.transaction(write=False) as db:
            workflow,_=self.service.runtime_runner.runtime.revision(db,reference['workflow_id'],reference['workflow_version'],auth,True)
        if workflow.get('metadata',{}).get('google_connection_id')!=body['connection_id']:fail('Reply monitor account differs from the approved workflow.')
        grants=self.service.registry_adapter.execution_assignments(workflow,auth)
        grant=next((g for g in grants if g['tool_id']=='extension_mail_thread'),None)
        if grant is None:fail('Reply polling requires the registered Gmail thread-read assignment.','AUTOMATION_POLL_ASSIGNMENT_REQUIRED',403)
        connector=self.service.runtime_runner.connectors.get(grant['tool_id'])
        if connector is None:fail('The Gmail thread connector is unavailable.')
        bound=connector.bind_workflow(workflow)
        return workflow,grant,self.service.bind_google_connector(bound,workflow,{},auth,grant)

    def validate(self,body,auth,case):
        if body['connection_id']!=case.get('google_connection_id'):fail('Subscription must use the case selected provider account.')
        if set(body['correlation'])!={'thread_id','sent_message_id','rfc_message_id'} or any(not isinstance(v,str) or not 1<=len(v)<=300 for v in body['correlation'].values()):fail('Pin actual Gmail thread/message receipt identifiers.')
        rid=case.get('adaptive',{}).get('run_id')
        if not rid:rid=case['stages'][body['stage_id']].get('run_id')
        with self.service.store.transaction(write=False) as db:run=self.service.runtime_runner.runtime.load(db,rid,auth)
        receipts=[x for x in run.get('action_instances',{}).values() if x.get('state')=='completed' and x.get('verified_receipt')]
        c=body['correlation']
        sent=next((x for x in receipts if x.get('output',{}).get('message_id')==c['sent_message_id'] and x['output'].get('thread_id')==c['thread_id'] and x['output'].get('rfc_message_id')==c['rfc_message_id']),None)
        if not sent:fail('Reply correlation requires a completed verified Gmail send receipt.')
        if sorted(x.casefold() for x in body['participants'])!=[sent['resolved_inputs']['to'].casefold()]:fail('Expected participant must match the actually authorized recipient.')
        self._binding(body,auth)
        return dict(not_before=int(run.get('created_at',0)*1000)/1000)

    def poll(self,sub,auth,case):
        body=sub['request'];self.validate(body,auth,case);workflow,grant,connector=self._binding(body,auth)
        out=connector.invoke(grant,{'thread_id':body['correlation']['thread_id']},'reply_poll:'+sub['id'])
        events=[]
        for message in out['messages']:
            events.append(dict(event_id=message['message_id'],payload=message,cursor=message['message_id']))
        return events,(events[-1]['event_id'] if events else sub.get('cursor'))

    def matches(self,body,event):
        p=event['payload'];c=body['correlation']
        if p.get('message_id')!=event['event_id'] or p.get('message_id')==c['sent_message_id'] or p.get('thread_id')!=c['thread_id']:return False
        if parseaddr(p.get('from',''))[1].casefold() not in {x.casefold() for x in body['participants']}:return False
        if p.get('reply_to') and parseaddr(p['reply_to'])[1].casefold()!=parseaddr(p.get('from',''))[1].casefold():return False
        if p.get('auto_submitted','no').casefold()!='no' or p.get('precedence','').casefold() in ('bulk','list','junk'):return False
        references=(p.get('in_reply_to','')+' '+p.get('references','')).split()
        if c['rfc_message_id'] not in references:return False
        try:received=datetime.fromisoformat(p['received_at']).timestamp()
        except (KeyError,ValueError,TypeError):return False
        return received>=body.get('sent_at',0) and received<=body['deadline'] and isinstance(p.get('text'),str)
