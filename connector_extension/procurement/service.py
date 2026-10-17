"""Durable first-slice coordinator; all Google operations use canonical workflows."""
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
import threading
import os
from workflow_api.auxiliary_database import connection as database_connection
from uuid import uuid4
from jsonschema import Draft202012Validator
from runtime.connectors import google_spreadsheet_id
from connector_extension.examples import connector_workflow
from connector_extension.sheets import read_location
from .layout import tracking_workflow, TABLE_HEADERS
from .runtime_tools import ingestion_workflow
from .store import ProcurementStore, ProcurementError, require, encoded, scope_digest, SCHEMA

ITEM_FIELDS=('section','description','quantity','unit','specifications','delivery_location','delivery_deadline')
CONTEXT_FIELDS=('description','delivery_location','delivery_deadline','quote_deadline','time_zone','comparison_currency')


def stable(value):return hashlib.sha256(encoded(value).encode()).hexdigest()


class ProcurementService:
    def __init__(self, workflows, state, currency_precision, auth_supplier):
        self.workflows,self.auth_supplier=workflows,auth_supplier
        self.store=ProcurementStore(state,currency_precision=currency_precision,authority_check=self.source_authority,database_url=getattr(workflows,'auxiliary_database_url',None))
        self.lock=threading.RLock()
        self.restored=set()
        self.cursor=0
        with self.store.connection() as db:
            db.execute('CREATE TABLE IF NOT EXISTS procurement_jobs(workspace TEXT,project TEXT,body TEXT NOT NULL, '
                       'PRIMARY KEY(workspace,project))')
            db.execute('CREATE TABLE IF NOT EXISTS procurement_snapshots(workspace TEXT,project TEXT,kind TEXT, '
                       'hash TEXT,body TEXT,PRIMARY KEY(workspace,project,kind))')
            db.execute('CREATE TABLE IF NOT EXISTS procurement_source_proofs(workspace TEXT,project TEXT,id TEXT, '
                       'body TEXT,PRIMARY KEY(workspace,project,id))')

    def job(self, workspace, project):
        self.store.scope(workspace,project)
        with self.store.connection(write=False) as db:
            row=db.execute('SELECT body FROM procurement_jobs WHERE workspace=? AND project=?',(workspace,project)).fetchone()
        require(row is not None,'PROCUREMENT_PROJECT_NOT_FOUND');return json.loads(row[0])

    def save_job(self, workspace, job):
        with self.store.connection() as db:
            db.execute('UPDATE procurement_jobs SET body=? WHERE workspace=? AND project=?',
                       (encoded(job),workspace,job['plan']['project_id']))

    def source_authority(self, evidence, role):
        # Source accessibility attests only the selected input table, never buyer,
        # supplier, compliance or canonical human approval.
        if role!='OPERATOR' or evidence['data']['provider']!='google_sheets':return False
        with self.store.connection(write=False) as db:
            row=db.execute('SELECT body FROM procurement_source_proofs WHERE workspace=? AND project=? AND id=?',
                           (evidence['workspace_id'],evidence['project_id'],evidence['record_id'])).fetchone()
        return bool(row and json.loads(row[0])==evidence)

    @staticmethod
    def authorize(auth, mutate=False):
        from runtime.service import RuntimeService
        RuntimeService.authorize(auth,'workflow.edit' if mutate else 'workflow.view',
                                 {'admin','builder'} if mutate else {'admin','builder','viewer','approver'})
        if mutate:
            for permission in ('workflow.validate','workflow.approve','workflow.publish','workflow.execute'):
                RuntimeService.authorize(auth,permission,{'admin','builder','approver'})
        return auth['subject']['workspace_id']

    def setup(self, plan, auth, *, owner_workflow=None):
        workspace=self.authorize(auth,True);plan=deepcopy(plan)
        require(isinstance(plan,dict) and set(plan)=={'project_id','name','simulation','context','requirements','vendors'},'PROCUREMENT_SETUP_INVALID')
        self.store.scope(workspace,plan['project_id'])
        require(isinstance(plan['name'],str) and 1<=len(plan['name'])<=160 and type(plan['simulation']) is bool,'PROCUREMENT_SETUP_INVALID')
        require(isinstance(plan['context'],dict) and not set(plan['context'])-set(CONTEXT_FIELDS),'PROCUREMENT_CONTEXT_INVALID')
        plan['context']={k:plan['context'].get(k) for k in CONTEXT_FIELDS}
        context_schema=SCHEMA['$defs']['project']['properties']['data']['properties']['context']
        require(not list(Draft202012Validator(context_schema).iter_errors(plan['context'])),'PROCUREMENT_CONTEXT_INVALID')
        for kind,required,allowed in (('requirements',{'item_id'},set(ITEM_FIELDS)|{'item_id'}),
                                      ('vendors',{'vendor_id','name','email','item_categories'},{'vendor_id','name','email','item_categories'})):
            source=plan[kind]
            require(isinstance(source,dict) and set(source)=={'spreadsheet_url','range','columns'} and
                    isinstance(source['columns'],dict) and required<=set(source['columns'])<=allowed and
                    all(isinstance(v,str) and v.strip()==v and v for v in source['columns'].values()),'PROCUREMENT_SOURCE_INVALID')
            google_spreadsheet_id(source['spreadsheet_url']);location=read_location(source['range'])
            require(location[4]-location[2]+1<=101 and location[3]-location[1]+1<=100,'PROCUREMENT_SOURCE_BOUNDS')
        fp=stable(plan)
        with self.lock,self.store.connection() as db:
            row=db.execute('SELECT body FROM procurement_jobs WHERE workspace=? AND project=?',(workspace,plan['project_id'])).fetchone()
            if row:
                job=json.loads(row[0]);require(job['fingerprint']==fp,'PROCUREMENT_PLAN_MISMATCH')
                if owner_workflow is not None:
                    require(job.get('owner_workflow')==owner_workflow,'PROCUREMENT_PROJECT_BOUND')
                return self.status(workspace,plan['project_id'])
            require(self.store.get(workspace,plan['project_id'],plan['project_id']) is None,'PROCUREMENT_PROJECT_EXISTS')
            prefix='procure_'+stable([workspace,plan['project_id']])[:20]
            job={'plan':plan,'fingerprint':fp,'started_at':datetime.now(timezone.utc).isoformat(),
                 'ingestion_workflow_id':prefix+'_ingest','prefix':prefix,'phase':'INGESTING','actions':{},'issues':[]}
            if owner_workflow is not None:job['owner_workflow']=deepcopy(owner_workflow)
            db.execute('INSERT INTO procurement_jobs VALUES (?,?,?)',(workspace,plan['project_id'],encoded(job)))
        return self.advance(plan['project_id'],auth)

    def status(self, workspace, project):
        job=self.job(workspace,project)
        records=self.store.list_records(workspace,project)
        return {'project_id':project,'phase':job['phase'],'issues':job['issues'],
                'recovery_history':job.get('recovery_history',[]),
                'actions':job['actions'],'record_counts':{kind:sum(r['record_type']==kind for r in records)
                for kind in ('project','boq_item','vendor','rfq')},'records':records,
                'resources':self.store.resources(workspace,project),'sync_intents':self.store.pending_sync(workspace,project)}

    @staticmethod
    def table(rows, columns):
        require(isinstance(rows,list) and 2<=len(rows)<=101,'PROCUREMENT_EMPTY_SOURCE')
        headers=rows[0];require(all(isinstance(h,str) and h and h==h.strip() for h in headers) and
            len(set(headers))==len(headers) and set(columns.values())<=set(headers),'PROCUREMENT_HEADERS_INVALID')
        require(all(isinstance(row,list) and len(row)<=len(headers) for row in rows[1:]),'PROCUREMENT_ROWS_INVALID')
        result=[]
        for offset,row in enumerate(rows[1:],1):
            if all(v in ('',None) for v in row):continue
            values={field:row[headers.index(header)] if headers.index(header)<len(row) else None for field,header in columns.items()}
            result.append((offset,values,row))
        require(result,'PROCUREMENT_EMPTY_SOURCE');return result

    def ingest(self, workspace, project, requirements_rows, vendor_rows):
        with self.lock:
            job=self.job(workspace,project);plan=job['plan']
            fingerprints={kind:stable(rows) for kind,rows in (('requirements',requirements_rows),('vendors',vendor_rows))}
            with self.store.connection() as db:
                for kind,rows in (('requirements',requirements_rows),('vendors',vendor_rows)):
                    old=db.execute('SELECT hash FROM procurement_snapshots WHERE workspace=? AND project=? AND kind=?',(workspace,project,kind)).fetchone()
                    require(not old or old[0]==fingerprints[kind],'PROCUREMENT_SOURCE_CHANGED')
                    db.execute('INSERT OR IGNORE INTO procurement_snapshots VALUES (?,?,?,?,?)',(workspace,project,kind,fingerprints[kind],encoded(rows)))
            if job.get('ingested'):return {'project_id':project,'ready':not job['issues'],'issues':job['issues']}
            req=self.table(requirements_rows,plan['requirements']['columns']);vendors=self.table(vendor_rows,plan['vendors']['columns'])
            now=job['started_at'];issues=[];records=[];item_ids=[];vendor_ids=[]
            def record(kind,identifier,data,evidence=()):
                return {'schema_version':'procurement-v1','record_type':kind,'record_id':identifier,
                    'workspace_id':workspace,'project_id':project,'revision':1,'created_at':now,'updated_at':now,
                    'evidence_ids':list(evidence),'data':data}
            def text(v):return str(v).strip() if v is not None and str(v).strip() else None
            def evidence(kind,offset,values,raw):
                source=plan[kind];identifier='source_'+stable([kind,offset])[:24]
                r=record('evidence',identifier,{'source_kind':'SHEET_ROW','provider':'google_sheets',
                    'source_id':google_spreadsheet_id(source['spreadsheet_url']),
                    'locator':source['range']+'#row_offset='+str(offset),'content_sha256':stable(raw),'captured_at':now,
                    'authority_state':'VERIFIED_SOURCE','asserted_actor_role':'OPERATOR',
                    'verified_subject_id':None,'artifact_reference':None})
                r = self.source_evidence(job, kind, offset, raw, r)
                records.append(r)
                with self.store.connection() as db:db.execute('INSERT OR IGNORE INTO procurement_source_proofs VALUES (?,?,?,?)',(workspace,project,identifier,encoded(r)))
                return identifier
            for offset,values,raw in req:
                identifier=text(values.get('item_id'));require(identifier and re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{1,127}',identifier),'PROCUREMENT_ITEM_ID_INVALID')
                require(identifier not in item_ids and identifier!=project,'PROCUREMENT_DUPLICATE_ID');item_ids.append(identifier)
                data={k:text(values.get(k)) for k in ITEM_FIELDS}
                for field in ('delivery_location','delivery_deadline'):data[field]=data[field] or plan['context'][field]
                try:
                    n=Decimal(data['quantity']);quantity=format(n,'f')
                    require(n>0 and re.fullmatch(r'(?:0|[1-9][0-9]{0,17})(?:\.[0-9]{1,6})?',quantity),'PROCUREMENT_QUANTITY_INVALID')
                    data['quantity']=quantity
                except (InvalidOperation,TypeError,ProcurementError):data['quantity']=None
                missing=[k for k in ITEM_FIELDS if data[k] is None]
                issues.extend(identifier+':missing_'+k for k in missing)
                source=evidence('requirements',offset,values,raw)
                data.update(status='EXTRACTED',source_evidence_ids=[source],group_id=None,
                            unresolved_issue_ids=['missing_'+k for k in missing])
                records.append(record('boq_item',identifier,data,[source]))
            for offset,values,raw in vendors:
                source=evidence('vendors',offset,values,raw);identifier=text(values.get('vendor_id'))
                require(identifier and re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{1,127}',identifier) and
                        identifier not in vendor_ids+item_ids and identifier!=project,'PROCUREMENT_VENDOR_ID_INVALID')
                vendor_ids.append(identifier)
                from connector_extension.mail import address
                try:email=address(text(values.get('email')) or '')
                except Exception:issues.append(identifier+':invalid_email');continue
                categories=[s.strip() for s in str(values.get('item_categories') or '').split(',') if s.strip()]
                if not categories or not text(values.get('name')):issues.append(identifier+':missing_contact_fields');continue
                records.append(record('vendor',identifier,{'status':'NEEDS_REVIEW','name':text(values['name']),
                    'email':email,'item_categories':categories,'contact_evidence_ids':[source]},[source]))
            context=deepcopy(plan['context'])
            for field in ('delivery_location','delivery_deadline'):
                unique={r['data'][field] for r in records if r['record_type']=='boq_item' and r['data'][field]}
                if context[field] is None and len(unique)==1:context[field]=next(iter(unique))
            issues.extend('project:missing_'+k for k,v in context.items() if v is None)
            if context['comparison_currency'] and context['comparison_currency'] not in self.store.precision:issues.append('project:unsupported_currency')
            items=[r for r in records if r['record_type']=='boq_item'];contacts=[r for r in records if r['record_type']=='vendor']
            for item in items:
                if not any((item['data']['section'] or '').casefold() in [c.casefold() for c in v['data']['item_categories']] for v in contacts):
                    issues.append(item['record_id']+':no_matching_vendor')
            p=record('project',project,{'name':plan['name'],'status':'DRAFT','simulation':plan['simulation'],'context':context,
                'required_item_ids':item_ids,'resolved_item_ids':[],'excluded_item_ids':[],'scope_change_approval_ids':[],
                'unresolved_issue_ids':['issue_'+stable(i)[:20] for i in issues],
                'owned_spreadsheet_ids':[],'owned_calendar_event_ids':[],'cleanup_state':'NOT_REQUESTED'})
            records.insert(0,p)
            self.store.commit(workspace,project,'ingest_initial',[{'record':r,'expected_revision':0} for r in records])
            self.update(workspace,project,'project_validate',[self.changed(p,status='VALIDATING')])
            changed=[]
            for item in items:changed.append(self.changed(item,status='NEEDS_CLARIFICATION' if item['data']['unresolved_issue_ids'] else 'READY'))
            for vendor in contacts:changed.append(self.changed(vendor,status='ACTIVE'))
            validated=self.changed(p,status='VALIDATING')
            changed.append(self.changed(validated,status='NEEDS_CLARIFICATION' if issues else 'ACTIVE'))
            self.update(workspace,project,'ingest_ready',changed)
            if not issues:
                rfqs=[]
                current_items=[self.store.get(workspace,project,i) for i in item_ids]
                for vendor in contacts:
                    sections=sorted({i['data']['section'] for i in current_items if i['data']['section'].casefold() in
                                    [c.casefold() for c in vendor['data']['item_categories']]})
                    for section in sections:
                        scope=[i for i in current_items if i['data']['section']==section]
                        identifier='rfq_'+stable([vendor['record_id'],section])[:24]
                        rfqs.append(record('rfq',identifier,{'status':'DRAFT','scope_item_ids':[i['record_id'] for i in scope],
                            'scope_digest':scope_digest(scope),'vendor_id':vendor['record_id'],'recipient':vendor['data']['email'],
                            'quote_deadline':context['quote_deadline'],'comparison_currency':context['comparison_currency'],
                            'subject_reference':identifier,'gmail_message_id':None,'gmail_thread_ids':[],'send_action_id':None},vendor['evidence_ids']))
                self.update(workspace,project,'rfqs_initial',rfqs)
                self.update(workspace,project,'rfqs_ready',[self.changed(r,status='READY') for r in rfqs])
            job['ingested']=True;job['issues']=issues;self.save_job(workspace,job)
            return {'project_id':project,'ready':not issues,'issues':issues}

    @staticmethod
    def changed(record,**data):
        result=deepcopy(record);result['revision']+=1;result['data'].update(data);return result

    def update(self, workspace, project, key, records, **kwargs):
        return self.store.commit(workspace,project,key,[{'record':r,'expected_revision':r['revision']-1} for r in records],**kwargs)

    def call(self, operation, payload, auth, key):
        result=self.workflows.handle({'request_id':'req_'+uuid4().hex,'operation':operation,
            'idempotency_key':'procurement_'+key,'payload':payload},auth)
        require(result['status']==200,result.get('data',{}).get('error',{}).get('error_code','PROCUREMENT_RUNTIME_FAILED'))
        return result['data']

    def run_action(self, workspace, job, name, workflow, auth):
        action=job['actions'].get(name)
        if not action:
            action={'workflow_id':workflow['workflow_id'],'workflow_version':1,'state':'PREPARING'}
            job['actions'][name]=action;self.save_job(workspace,job)
        ref={'workflow_id':action['workflow_id'],'workflow_version':1};identity=action['workflow_id']
        if action.get('run_id') and identity not in self.restored:
            persisted=self.call('get_workflow',ref,auth,identity+'_restore_read')['workflow']
            require(persisted['status']=='published' and persisted['metadata'].get('validation_state')=='validated' and
                    persisted['metadata'].get('approved_by')==auth['subject']['subject_id'] and
                    persisted['metadata'].get('procurement_project_id')==job['plan']['project_id'], 'PROCUREMENT_APPROVAL_RESTORE_DENIED')
            # Restore only this coordinator's previously published exact revision.
            # This is Registry publication evidence, not a runtime action decision.
            self.workflows.registry_adapter.resolve_draft(persisted,auth)
            self.workflows.registry_adapter.approve_pending(persisted,auth)
            self.restored.add(identity)
        if not action.get('run_id'):
            steps=(('save_workflow_version',{**ref,'base_version':0,'workflow':workflow}),('validate_workflow',ref),
                   ('approve_workflow',{**ref,'action':'approve'}),('approve_workflow',{**ref,'action':'publish'}))
            for op,payload in steps:self.call(op,payload,auth,identity+'_'+op+'_'+payload.get('action',''))
            run=self.call('execute_workflow',{**ref,'inputs':{}},auth,identity+'_execute')['run']
            latest=self.job(workspace,job['plan']['project_id'])
            for field in ('ingested','issues'):
                if field in latest:job[field]=latest[field]
            action['run_id']=run['run_id'];self.save_job(workspace,job)
            self.restored.add(identity)
        run=self.workflows.runtime_runner.runtime.get_run(action['run_id'],auth)
        action['state']=run['status'];action['approvals']=run['approvals'];self.save_job(workspace,job)
        if run['status'] in ('failed','blocked','rejected','cancelled'):
            job['phase']='STOPPED';job['issues']=list(dict.fromkeys(job['issues']+['runtime:'+run['status']]))
            if name.startswith('sync_'):
                with self.store.connection() as db:
                    db.execute('UPDATE sync_intents SET status=? WHERE workspace=? AND project=? AND key=?',
                        ('REJECTED' if run['status']=='rejected' else 'NEEDS_RECONCILIATION',workspace,
                         job['plan']['project_id'],name.removeprefix('sync_')))
            self.save_job(workspace,job)
        if run['status']!='completed':return None
        events=self.workflows.runtime_runner.runtime.events(action['run_id'],auth)['items']
        outputs={e['details']['node_id']:e['details']['output'] for e in events if e['event_type']=='node.completed' and
                 'output' in e['details'] and 'node_id' in e['details']}
        return outputs

    def gated_workflow(self, tool, inputs, identity, project, targets=None):
        w=connector_workflow(tool,inputs,identity,sheet_targets=targets)
        w['name']=('RFQ draft for '+inputs['to'][:100]) if tool=='extension_mail_draft' else 'Procurement tracking row '+inputs['identity']
        w['metadata']['procurement_project_id']=project
        w['approval_gates'][0]['timeout_seconds']=86400
        w['execution_policy']['limits']['timeout_seconds']=90000
        return w

    def retry_tracking(self, project, expected_run_id, absence_confirmed, auth):
        workspace=self.authorize(auth,True)
        from runtime.service import RuntimeService
        RuntimeService.authorize(auth,'workflow.approve',{'admin','approver'})
        require(type(absence_confirmed) is bool,'OPERATOR_ABSENCE_CONFIRMATION_REQUIRED')
        with self.lock:
            job=self.job(workspace,project)
            if any(h['previous_run_id']==expected_run_id for h in job.get('recovery_history',[])):
                return self.status(workspace,project)
            failed=job['actions'].get('tracking')
            require(job['phase']=='STOPPED' and failed and failed['run_id']==expected_run_id and
                    failed['state'] in ('blocked','failed') and not job.get('tracking'), 'TRACKING_RETRY_NOT_ALLOWED')
            require(len(job.get('recovery_history',[]))<2,'TRACKING_RETRY_LIMIT')
            path=self.store.path.parent/'sheet-resources.sqlite3'
            if path.exists() or self.store.database_url or os.getenv('BUILDER_AUXILIARY_DATABASE_URL'):
                with database_connection(path,write=False,database_url=self.store.database_url) as db:
                    found=db.execute('SELECT 1 FROM observations WHERE workspace=? AND project=?',(workspace,project)).fetchone()
                require(not found,'TRACKING_RESOURCE_RECONCILIATION_REQUIRED')
            known_rejection=False
            if not absence_confirmed:
                from runtime.service import digest as effect_digest
                from connector_extension.sheet_creation import setup_inputs
                ref={'workflow_id':failed['workflow_id'],'workflow_version':1}
                published=self.call('get_workflow',ref,auth,failed['workflow_id']+'_recovery_read')['workflow']
                inputs=setup_inputs(next(n['configuration']['input'] for n in published['nodes'] if n.get('tool_id')=='extension_sheets_create'))
                effect='sheet_setup_'+effect_digest([workspace,project,inputs['creation_key']])
                with database_connection(self.store.path.parent/'effects.sqlite3',write=False,database_url=self.store.database_url) as db:
                    prior=db.execute('SELECT fingerprint,state,result FROM effects WHERE key=?',
                                     (effect_digest(['extension_sheets_create',effect]),)).fetchone()
                known_rejection=bool(prior and prior[0]==effect_digest(inputs) and prior[1]=='started' and prior[2] and
                                     json.loads(prior[2]).get('failure_category')=='PROVIDER_HTTP_400')
                require(known_rejection,'OPERATOR_ABSENCE_CONFIRMATION_REQUIRED')
            count=len(job.get('recovery_history',[]))+1
            job.setdefault('recovery_history',[]).append({'previous_run_id':expected_run_id,'action':deepcopy(failed),
                'operator_subject':auth['subject']['subject_id'],'absence_reported':absence_confirmed,
                'retry_basis':'CONFIRMED_HTTP_400_REJECTION' if known_rejection else 'OPERATOR_REPORTED_ABSENT',
                'reported_at':datetime.now(timezone.utc).isoformat(),'previous_issues':job['issues']})
            del job['actions']['tracking'];job['phase']='TRACKING';job['issues']=[]
            job['tracking_workflow_id']=job['prefix']+'_tracking_retry_'+str(count)
            job['tracking_creation_key']='tracking_book_retry_'+str(count)
            self.save_job(workspace,job)
        return self.advance(project,auth)

    def ingestion_workflow(self, plan, workflow_id, workspace=None):
        return ingestion_workflow(plan, workflow_id)

    def source_evidence(self, job, kind, offset, raw, evidence):
        return evidence

    def advance(self, project, auth):
        workspace=self.authorize(auth,True)
        with self.lock:
            job=self.job(workspace,project);plan=job['plan']
            if job['phase'] in ('DRAFTS_READY','NEEDS_CLARIFICATION','STOPPED'):return self.status(workspace,project)
            try:
                if job['phase']=='INGESTING':
                    out=self.run_action(workspace,job,'ingestion',self.ingestion_workflow(plan,job['ingestion_workflow_id'],workspace),auth)
                    if out is None:return self.status(workspace,project)
                    job=self.job(workspace,project)
                    job['phase']='NEEDS_CLARIFICATION' if job['issues'] else 'TRACKING';self.save_job(workspace,job)
                    if job['issues']:return self.status(workspace,project)
                if job['phase']=='TRACKING':
                    w=tracking_workflow(project,plan['name']+' tracking',
                        creation_key=job.get('tracking_creation_key','tracking_book_v1'),
                        workflow_id=job.get('tracking_workflow_id',job['prefix']+'_tracking'))
                    w['approval_gates'][0]['timeout_seconds']=86400;w['execution_policy']['limits']['timeout_seconds']=90000
                    out=self.run_action(workspace,job,'tracking',w,auth)
                    if out is None:return self.status(workspace,project)
                    receipt=out['action'];targets=receipt['proposed_write_targets']
                    require(len(targets)==6 and [t['title'] for t in receipt['tabs']]==list(TABLE_HEADERS),'PROCUREMENT_TRACKING_INVALID')
                    job['tracking']=receipt
                    self.prepare_projections(workspace,project,job)
                    job['phase']='PROJECTIONS';self.save_job(workspace,job)
                if job['phase']=='PROJECTIONS':
                    for intent in self.store.pending_sync(workspace,project):
                        if intent['status']=='CONFIRMED':continue
                        payload=intent['payload'];identity=job['prefix']+'_s_'+stable(intent['key'])[:12]
                        w=self.gated_workflow('google_sheets_upsert_record',payload['inputs'],identity,project,[payload['target']])
                        out=self.run_action(workspace,job,'sync_'+intent['key'],w,auth)
                        if out is None:return self.status(workspace,project)
                        self.acknowledge_sync(workspace,project,intent['key'],out['action'])
                    job['phase']='DRAFTS';self.save_job(workspace,job)
                if job['phase']=='DRAFTS':
                    for rfq in self.store.list_records(workspace,project,'rfq'):
                        identifier=rfq['record_id'];identity=job['prefix']+'_d_'+stable(identifier)[:12]
                        if any(link['record_id']==identifier and 'draft_id' in link['metadata']
                               for link in self.store.resources(workspace,project)):continue
                        mail=self.rfq_mail(workspace,project,rfq)
                        out=self.run_action(workspace,job,'draft_'+identifier,
                            self.gated_workflow('extension_mail_draft',mail,identity,project),auth)
                        if out is None:return self.status(workspace,project)
                        result=out['action'];link={'record_id':identifier,'provider':'gmail','resource_type':'message',
                            'resource_id':result['message_id'],'metadata':{'draft_id':result['draft_id'],'thread_id':result['thread_id'],
                            'workflow_id':identity,'run_id':job['actions']['draft_'+identifier]['run_id'],'sent':False}}
                        # RFQ stays READY: draft creation is not evidence of sending.
                        initial=self.store.get(workspace,project,identifier,2)
                        self.update(workspace,project,'draft_confirm_'+identifier,[self.changed(initial)],resources=[link])
                    job['phase']='DRAFTS_READY';self.save_job(workspace,job)
            except ProcurementError as exc:
                job=self.job(workspace,project);job['issues']=list(dict.fromkeys(job['issues']+[exc.code]))
                job['phase']='STOPPED';self.save_job(workspace,job)
            # Terminal runtime failures are frozen, not replaced with another run.
            if self.failed_actions(job):
                job['phase']='STOPPED';self.save_job(workspace,job)
            return self.status(workspace,project)

    def failed_actions(self,job):
        return [a for a in job['actions'].values() if a['state'] in ('failed','blocked','rejected','cancelled')]

    def rfq_mail(self, workspace, project, rfq):
        d=rfq['data'];p=self.store.get(workspace,project,project)
        lines=[]
        for identifier in d['scope_item_ids']:
            item=self.store.get(workspace,project,identifier);v=item['data']
            require(v['status']=='READY' and scope_digest([self.store.get(workspace,project,i) for i in d['scope_item_ids']])==d['scope_digest'],'STALE_REQUIREMENTS')
            lines.append(f"{identifier}: {v['description']} — {v['quantity']} {v['unit']}; specifications: {v['specifications']}; deliver to {v['delivery_location']} by {v['delivery_deadline']}")
        vendor=self.store.get(workspace,project,d['vendor_id'])
        require(vendor['data']['status']=='ACTIVE' and vendor['data']['email']==d['recipient'],'CONTACT_MISMATCH')
        prefix='[SIMULATION] ' if p['data']['simulation'] else ''
        return {'to':d['recipient'],'subject':prefix+'RFQ '+rfq['record_id'],
                'body':prefix+'Request for quotation: '+rfq['record_id']+'\n'+ '\n'.join(lines)+
                '\nPlease provide itemized prices, discounts, taxes, shipping and total delivered cost in '+d['comparison_currency']+
                ', compliance evidence, delivery date and quote validity. Quote deadline: '+d['quote_deadline']+'.'}

    def prepare_projections(self, workspace, project, job):
        receipt=job['tracking'];targets=dict(zip(TABLE_HEADERS,receipt['proposed_write_targets']))
        records=self.store.list_records(workspace,project);intents=[]
        for r in records:
            kind=r['record_type'];d=r['data'];table={'boq_item':'BOQ','vendor':'Vendors','rfq':'RFQs'}.get(kind)
            if not table:continue
            if kind=='boq_item':fields={k:d[k] for k in ITEM_FIELDS};fields.update(status=d['status'],source_reference=','.join(d['source_evidence_ids']),project_id=project,revision=r['revision'])
            elif kind=='vendor':fields={'vendor_name':d['name'],'email':d['email'],'item_categories':','.join(d['item_categories']),
                'status':d['status'],'contact_evidence':','.join(d['contact_evidence_ids'])}
            else:fields={'vendor_id':d['vendor_id'],'item_ids':','.join(d['scope_item_ids']),'scope_digest':d['scope_digest'],
                'quote_deadline':d['quote_deadline'],'currency':d['comparison_currency'],'status':d['status'],
                'gmail_message_id':None,'gmail_thread_ids':'','revision':r['revision']}
            t=targets[table];inputs={'spreadsheet_id':t['spreadsheet_id'],'range':t['range'],
                                    'identity_column':t['identity_column'],'identity':r['record_id'],'fields':fields}
            intents.append({'key':'initial_'+r['record_id'],'record_id':r['record_id'],'record_revision':r['revision'],
                            'target':'sheets','payload':{'inputs':inputs,'target':t}})
        p=self.store.get(workspace,project,project,3);updated=self.changed(p,owned_spreadsheet_ids=[receipt['spreadsheet_id']])
        link={'record_id':project,'provider':'google_sheets','resource_type':'spreadsheet','resource_id':receipt['spreadsheet_id'],
              'metadata':{'ownership_receipt':receipt,'workflow_id':job['actions']['tracking']['workflow_id']}}
        self.update(workspace,project,'tracking_projection_intents',[updated],resources=[link],sync_intents=intents)

    def acknowledge_sync(self, workspace, project, key, result):
        with self.store.connection() as db:
            row=db.execute('SELECT payload FROM sync_intents WHERE workspace=? AND project=? AND key=?',(workspace,project,key)).fetchone()
            require(row and result.get('identity')==json.loads(row[0])['inputs']['identity'],'SYNC_RESULT_MISMATCH')
            db.execute("UPDATE sync_intents SET status='CONFIRMED' WHERE workspace=? AND project=? AND key=?",(workspace,project,key))

    def tick(self):
        with self.store.connection(write=False) as db:jobs=db.execute("SELECT rowid,workspace,project,body FROM procurement_jobs WHERE rowid>? AND "
            "json_extract(body,'$.phase') NOT IN ('DRAFTS_READY','NEEDS_CLARIFICATION','STOPPED') ORDER BY rowid LIMIT 5",(self.cursor,)).fetchall()
        if not jobs:self.cursor=0
        for rowid,workspace,project,body in jobs:
            self.cursor=rowid
            if json.loads(body)['phase'] in ('DRAFTS_READY','NEEDS_CLARIFICATION','STOPPED'):continue
            auth=self.auth_supplier(workspace)
            if auth is not None:
                try:self.advance(project,auth)
                except Exception:
                    import logging
                    logging.getLogger(__name__).warning('Procurement advancement failed; inspect project status before retrying.')
