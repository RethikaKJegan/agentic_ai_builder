"""Durable one-module extraction jobs; uncertain model calls are never replayed."""
from copy import deepcopy
from hashlib import sha256
import json
import re
import secrets
from threading import Event, Lock, Thread
import time

from .business_ontology import identity, MODULES, LAYERS
from .business_documents import context_documents, source_stamp
from .business_extraction import OpenAIExtraction, prepare_result, VALIDATION_HINTS
from .google_connections import now
from .service import ApiFailure


class BusinessGeneration:
    def __init__(self, ontology, authenticate, provider=None, env=None, clock=time.time):
        self.ontology=ontology;self.store=ontology.store;self.authenticate=authenticate
        self.provider=provider or OpenAIExtraction(env or {});self.clock=clock
        self.stop_event=Event();self.wake=Event();self.guard=Lock();self.thread=None
        with self.store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS business_ontology_jobs (job_id TEXT PRIMARY KEY, workspace TEXT NOT NULL, owner TEXT NOT NULL, request_key TEXT NOT NULL, fingerprint TEXT NOT NULL, state TEXT NOT NULL, document TEXT NOT NULL, claim TEXT, deadline REAL, created REAL NOT NULL, UNIQUE(workspace,owner,request_key))')
            db.execute("CREATE UNIQUE INDEX IF NOT EXISTS business_ontology_active_job ON business_ontology_jobs(workspace,owner) WHERE state IN ('queued','running')")

    @staticmethod
    def public(row):
        doc=json.loads(row[2])
        return dict(job_id=row[0],state=row[1],module_id=doc['module_id'],created_at=doc['created_at'],
                    version_id=doc.get('version_id'),error=doc.get('error'),usage=doc.get('usage'))

    def get(self,auth,job_id):
        scope=identity(auth)
        with self.store.transaction(write=False) as db:
            row=db.execute('SELECT job_id,state,document FROM business_ontology_jobs WHERE job_id=? AND workspace=? AND owner=?',(job_id,*scope)).fetchone()
        if not row:raise ApiFailure('BUSINESS_JOB_NOT_FOUND','Generation job not found.',404)
        return self.public(row)

    def list(self,auth):
        scope=identity(auth)
        with self.store.transaction(write=False) as db:
            rows=db.execute('SELECT job_id,state,document FROM business_ontology_jobs WHERE workspace=? AND owner=? ORDER BY created DESC LIMIT 20',scope).fetchall()
        return dict(items=[self.public(r) for r in rows],configured=bool(self.provider.configured))

    def submit(self,auth,body):
        scope=identity(auth,True)
        if (not isinstance(body,dict) or set(body)!={'module_id','expected_revision','request_key'}
            or not isinstance(body['module_id'],str) or body['module_id'] not in {m[0] for m in MODULES}
            or type(body['expected_revision']) is not int or body['expected_revision']<1
            or not isinstance(body['request_key'],str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,100}',body['request_key'])):
            raise ApiFailure('BUSINESS_GENERATION_INVALID','Choose a module, current revision and request key.',422)
        fingerprint=sha256(json.dumps({k:body[k] for k in ('module_id','expected_revision')},sort_keys=True).encode()).hexdigest()
        with self.store.transaction() as db:
            old=db.execute('SELECT job_id,fingerprint FROM business_ontology_jobs WHERE workspace=? AND owner=? AND request_key=?',(*scope,body['request_key'])).fetchone()
            if old:
                if old[1]!=fingerprint:raise ApiFailure('IDEMPOTENCY_KEY_REUSED','This request key belongs to a different generation.',409)
                job_id=old[0]
            else:
                if not self.provider.configured:raise ApiFailure('BUSINESS_MODEL_UNAVAILABLE','The existing OpenAI integration is not configured.',503)
                workspace=self.ontology.document(db,scope)
                if not workspace:raise ApiFailure('BUSINESS_FOUNDATION_REQUIRED','Create the business foundation first.',409)
                if workspace['revision']!=body['expected_revision']:raise ApiFailure('BUSINESS_REVISION_CONFLICT','Refresh the business ontology before generating.',409)
                stamp=source_stamp(self.ontology,db,scope,workspace)
                active=db.execute("SELECT job_id FROM business_ontology_jobs WHERE workspace=? AND owner=? AND state IN ('queued','running')",scope).fetchone()
                if active:raise ApiFailure('BUSINESS_GENERATION_ACTIVE','A generation is already queued or running.',409)
                documents=context_documents(self.ontology,db,scope,workspace,body['module_id'])
                current=self.ontology.view(db,scope)['definitions']
                retained={kind:[x for x in items if x['module_id']!=body['module_id']] for kind,items in current.items()}
                required={c['parent_id'] for c in retained['concepts'] if c['parent_id']}
                required.update(v for edge in retained['relationships'] for v in (edge['source'],edge['target']))
                required.update(v for rule in retained['rules'] for v in rule['inputs'])
                latest=self.ontology.version(auth,self.ontology.view(db,scope)['current_version_id'])
                required.update(latest.get('knowledge',{}).get('manifest',{}).get('protected',{}).get('concepts',[]))
                required_concepts=[{k:c[k] for k in ('id','label','definition','layer','parent_id','properties','evidence')} for c in current['concepts'] if c['id'] in required and c['module_id']==body['module_id']]
                protected=latest.get('knowledge',{}).get('manifest',{}).get('protected',{})
                protected_definitions={group:[x for x in latest[group] if x['id'] in protected.get(group,[]) and x['module_id']==body['module_id']] for group in ('concepts','relationships','rules')}
                needed_sources={e['source_id'] for items in protected_definitions.values() for x in items for e in x['evidence']}
                available_sources={d['source_id'] for d in documents}
                documents += [d for d in latest.get('sources',[]) if d['source_id'] in needed_sources-available_sources]
                payload=dict(required_concepts=required_concepts,module_id=body['module_id'],module_description=next(m[2] for m in MODULES if m[0]==body['module_id']),
                    documents=documents,retained_concepts=[{k:c[k] for k in ('id','label','layer')} for c in retained['concepts']])
                if protected:payload['protected_definitions']=protected_definitions
                if len(json.dumps(payload))>100000:raise ApiFailure('BUSINESS_EVIDENCE_LIMIT','Selected evidence exceeds the input limit.',422)
                doc=dict(module_id=body['module_id'],created_at=now(),base_revision=workspace['revision'],stamp=stamp,payload=payload,retained=retained)
                job_id='boj_'+secrets.token_hex(16)
                db.execute('INSERT INTO business_ontology_jobs VALUES (?,?,?,?,?,?,?,?,?,?)',(job_id,*scope,body['request_key'],fingerprint,'queued',json.dumps(doc),None,None,self.clock()))
        self.wake.set()
        return self.get(auth,job_id)

    def cancel(self,auth,job_id):
        scope=identity(auth,True);self.get(auth,job_id)
        with self.store.transaction() as db:
            row=db.execute('SELECT document FROM business_ontology_jobs WHERE job_id=? AND workspace=? AND owner=?',(job_id,*scope)).fetchone()
            doc=json.loads(row[0]);doc.pop('payload',None);doc.pop('retained',None)
            db.execute("UPDATE business_ontology_jobs SET state='cancelled',document=?,claim=NULL,deadline=NULL WHERE job_id=? AND workspace=? AND owner=? AND state IN ('queued','running')",(json.dumps(doc),job_id,*scope))
        return self.get(auth,job_id)

    def authority(self,scope):
        auth=self.authenticate(*scope)
        if auth is None:raise ApiFailure('OPERATION_NOT_AUTHORIZED','Generation authority is no longer available.',403)
        identity(auth,True)
        return auth

    def check(self,db,scope,doc):
        workspace=self.ontology.document(db,scope)
        if not workspace or workspace['revision']!=doc['base_revision']:
            raise ApiFailure('BUSINESS_REVISION_CONFLICT','A newer draft exists; this generation was not applied.',409)
        if source_stamp(self.ontology,db,scope,workspace)!=doc['stamp']:
            raise ApiFailure('BUSINESS_SOURCE_CHANGED','Source metadata or connection generation changed; this result was not applied.',409)
        return workspace

    def finish_failure(self,job_id,claim,code,detail=None):
        with self.store.transaction() as db:
            row=db.execute("SELECT document FROM business_ontology_jobs WHERE job_id=? AND state='running' AND claim=?",(job_id,claim)).fetchone()
            if not row:return
            doc=json.loads(row[0]);doc.pop('payload',None);doc.pop('retained',None)
            message='Generation was not applied. Inspect source information and current state before starting a new request.'
            if code=='BUSINESS_EXTRACTION_INVALID' and detail in VALIDATION_HINTS:message='Generation was not applied. '+detail+' Your saved definitions have not changed.'
            doc['error']=dict(code=code,message=message)
            db.execute("UPDATE business_ontology_jobs SET state='failed',document=?,claim=NULL,deadline=NULL WHERE job_id=? AND state='running' AND claim=?",(json.dumps(doc),job_id,claim))

    def tick(self):
        claim=secrets.token_hex(16)
        with self.store.transaction() as db:
            expired=db.execute("SELECT job_id,claim FROM business_ontology_jobs WHERE state='running' AND deadline<?",(self.clock(),)).fetchall()
        for job_id,old_claim in expired:self.finish_failure(job_id,old_claim,'BUSINESS_GENERATION_INTERRUPTED')
        with self.store.transaction() as db:
            row=db.execute("SELECT job_id,workspace,owner,document FROM business_ontology_jobs WHERE state='queued' ORDER BY created LIMIT 1").fetchone()
            if not row:return False
            job_id,workspace_id,owner,raw=row;scope=(workspace_id,owner);doc=json.loads(raw)
            changed=db.execute("UPDATE business_ontology_jobs SET state='running',claim=?,deadline=? WHERE job_id=? AND state='queued'",(claim,self.clock()+240,job_id)).rowcount
            if not changed:return True
        try:
            self.authority(scope)
            with self.store.transaction(write=False) as db:self.check(db,scope,doc)
            result,usage=self.provider.generate(deepcopy(doc['payload']))
            output,adjustments=prepare_result(result,doc['module_id'],doc['payload']['documents'],doc['retained'])
            usage={**usage,'classification_adjustments':adjustments}
            self.authority(scope)
            with self.store.transaction() as db:
                current=db.execute('SELECT state,claim,deadline FROM business_ontology_jobs WHERE job_id=?',(job_id,)).fetchone()
                if current[0]!='running' or current[1]!=claim:return True
                if current[2]<self.clock():raise ApiFailure('BUSINESS_GENERATION_INTERRUPTED','The job deadline expired.',409)
                workspace=self.check(db,scope,doc)
                # Expected-revision CAS also serializes concurrent PostgreSQL completions.
                next_workspace={**workspace,'revision':workspace['revision']+1,'status':'draft'}
                updated=db.execute('UPDATE business_ontology_workspaces SET document=? WHERE workspace=? AND owner=? AND ontology_id=? AND document=?',
                    (json.dumps(next_workspace),*scope,'simpson',json.dumps(workspace))).rowcount
                if not updated:raise ApiFailure('BUSINESS_REVISION_CONFLICT','A newer draft exists.',409)
                previous=db.execute('SELECT document FROM business_ontology_versions WHERE workspace=? AND owner=?',scope).fetchall()
                previous=max((json.loads(r[0]) for r in previous),key=lambda v:v['revision'])
                version_id='bov_'+secrets.token_hex(16)
                evidence={d['source_id']:d for d in previous.get('sources',[])}
                evidence.update({d['source_id']:d for d in doc['payload']['documents']})
                version=dict(version_id=version_id,revision=next_workspace['revision'],created_at=now(),kind='draft',workspace=next_workspace,
                    layers=deepcopy(LAYERS),modules=[dict(id=i,label=l,description=d,layers=layers,concept_count=0) for i,l,d,layers in MODULES],
                    **{kind:doc['retained'][kind]+output[kind] for kind in ('concepts','relationships','rules')},
                    questions={**previous.get('questions',{}),doc['module_id']:output['questions']},sources=list(evidence.values()),
                    extraction=dict(module_id=doc['module_id'],job_id=job_id,**usage),validation=dict(schema='passed',citations='passed',references='passed',semantic_compilation='not_run',business_policy_verified=False))
                from .business_knowledge import preserve_knowledge
                preserve_knowledge(previous,version)
                for module in version['modules']:module['concept_count']=sum(c['module_id']==module['id'] for c in version['concepts'])
                db.execute('INSERT INTO business_ontology_versions VALUES (?,?,?,?)',(*scope,version_id,json.dumps(version)))
                db.execute('INSERT INTO business_ontology_events VALUES (?,?,?,?)',(*scope,'boe_'+secrets.token_hex(16),json.dumps(dict(action='extract_module',at=now(),version_id=version_id,module_id=doc['module_id'],job_id=job_id))))
                doc.pop('payload');doc.pop('retained');doc.update(version_id=version_id,usage=usage)
                db.execute("UPDATE business_ontology_jobs SET state='succeeded',document=?,claim=NULL,deadline=NULL WHERE job_id=? AND claim=?",(json.dumps(doc),job_id,claim))
        except ApiFailure as exc:self.finish_failure(job_id,claim,exc.code,str(exc))
        except Exception:self.finish_failure(job_id,claim,'BUSINESS_GENERATION_FAILED')
        return True

    def start(self):
        with self.guard:
            if self.thread and self.thread.is_alive():return
            self.stop_event.clear()
            def loop():
                while not self.stop_event.is_set():
                    try:worked=self.tick()
                    except Exception:worked=False
                    if not worked:self.wake.wait(1);self.wake.clear()
            self.thread=Thread(target=loop,name='business-ontology-generation',daemon=True);self.thread.start()

    def stop(self):
        self.stop_event.set();self.wake.set()
        if self.thread:self.thread.join(timeout=1)
