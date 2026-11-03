"""Durable owner-scoped UI jobs; never replay interrupted paid invocations."""
import json
import secrets
from threading import Event,Thread
import time
from .business_knowledge_model import canonical,digest
from .investigation_graph import fail
from .google_connections import now


class InvestigationJobs:
    def __init__(self,service,resolve,clock=time.time):
        self.service,self.store,self.resolve,self.clock=service,service.store,resolve,clock
        self.stop_event=Event();self.thread=None;self.health=dict(state='starting',last_success=None,last_error=None)
        with self.store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS business_investigation_jobs (workspace TEXT NOT NULL,owner TEXT NOT NULL,job_id TEXT NOT NULL,request_key TEXT NOT NULL,fingerprint TEXT NOT NULL,state TEXT NOT NULL,claim TEXT,deadline REAL,document TEXT NOT NULL,PRIMARY KEY(workspace,owner,job_id),UNIQUE(workspace,owner,request_key))')

    @staticmethod
    def public(doc):return {k:v for k,v in doc.items() if k!='payload'}

    def submit(self,auth,body):
        if not isinstance(body,dict) or set(body)!={'request_key','kind','payload'} or body['kind'] not in ('plan','execute','resume'):fail('Choose plan, execute or resume with an explicit request key.')
        auth,scope=self.service.authorize(auth,body['kind']!='plan');key=self.service.key(body)
        if body['kind']=='plan':
            if 'workflow.plan' not in auth.get('permissions',[]):fail('Workflow planning permission is required.','INVESTIGATION_DENIED',403)
            payload=body['payload']
            if not isinstance(payload,dict) or set(payload)-{'objective','request_key','inputs','version_id','planning_mode','analysis_mode','wait_for_information'}:fail('Invalid planning payload.')
            from .investigation_graph import requirements
            requirements(payload.get('objective'))
            if payload.get('planning_mode','model')!='model' or payload.get('analysis_mode','crewai')!='crewai':fail('Website jobs use the configured model and CrewAI.')
            self.service.key(payload)
        else:
            if not isinstance(body['payload'],dict) or set(body['payload'])!={'run_id'}:fail('Supply a saved run ID only.')
            self.service.get_run(auth,body['payload']['run_id'])
        fingerprint=digest(body)
        doc=dict(job_id='investigation_job_'+secrets.token_hex(12),kind=body['kind'],state='queued',created_at=now(),updated_at=now(),payload=body['payload'],workflow_id=None,run_id=body['payload'].get('run_id'),error=None)
        with self.store.transaction() as db:
            db.execute('INSERT INTO business_investigation_jobs VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(workspace,owner,request_key) DO NOTHING',(*scope,doc['job_id'],key,fingerprint,'queued',None,None,canonical(doc)))
            row=db.execute('SELECT fingerprint,document FROM business_investigation_jobs WHERE workspace=? AND owner=? AND request_key=?',(*scope,key)).fetchone()
        if row[0]!=fingerprint:fail('Job request key conflict.','INVESTIGATION_CONFLICT',409)
        return self.public(json.loads(row[1]))

    def get(self,auth,job_id):
        auth,scope=self.service.authorize(auth)
        with self.store.transaction(write=False) as db:
            row=db.execute('SELECT document FROM business_investigation_jobs WHERE workspace=? AND owner=? AND job_id=?',(*scope,job_id)).fetchone()
        if not row:fail('Investigation job not found.','INVESTIGATION_NOT_FOUND',404)
        d=json.loads(row[0])
        if d['workflow_id']:self.service.get_plan(auth,d['workflow_id'])
        if d['run_id']:self.service.get_run(auth,d['run_id'])
        return self.public(d)

    def list(self,auth):
        auth,scope=self.service.authorize(auth)
        with self.store.transaction(write=False) as db:
            rows=db.execute('SELECT document FROM business_investigation_plans WHERE workspace=? AND owner=? ORDER BY rowid DESC LIMIT 50',scope).fetchall()
            runs=db.execute('SELECT document FROM business_investigation_runs WHERE workspace=? AND owner=? ORDER BY rowid DESC LIMIT 100',scope).fetchall()
            jobs=db.execute('SELECT document FROM business_investigation_jobs WHERE workspace=? AND owner=? ORDER BY rowid DESC LIMIT 50',scope).fetchall()
        run_docs=[json.loads(r[0]) for r in runs];items=[]
        for row in rows:
            p=json.loads(row[0]);r=next((r for r in run_docs if r['workflow_id']==p['workflow_id']),None)
            items.append(dict(workflow_id=p['workflow_id'],objective=p['objective'],created_at=p['created_at'],node_count=len(p['graph']['nodes']),run_id=r['run_id'] if r else None,status=r['status'] if r else 'planned'))
        return dict(items=items,jobs=[self.public(json.loads(r[0])) for r in jobs])

    def tick(self):
        with self.store.transaction() as db:
            for w,o,j,raw in db.execute("SELECT workspace,owner,job_id,document FROM business_investigation_jobs WHERE state='running' AND deadline<?",(self.clock(),)).fetchall():
                d=json.loads(raw);d.update(state='failed',updated_at=now(),error=dict(code='INVESTIGATION_INTERRUPTED',message='Work was interrupted. Inspect the saved run before explicitly resuming; it was not automatically replayed.'))
                db.execute('UPDATE business_investigation_jobs SET state=?,claim=NULL,document=? WHERE workspace=? AND owner=? AND job_id=?',('failed',canonical(d),w,o,j))
            row=db.execute("SELECT workspace,owner,job_id,document FROM business_investigation_jobs WHERE state='queued' ORDER BY rowid LIMIT 1").fetchone()
            if not row:return False
            w,o,j,raw=row;d=json.loads(raw);token=secrets.token_hex(16)
            cursor=db.execute("UPDATE business_investigation_jobs SET state='running',claim=?,deadline=? WHERE workspace=? AND owner=? AND job_id=? AND state='queued'",(token,self.clock()+360,w,o,j))
            if cursor.rowcount!=1:return False
            d.update(state='running',updated_at=now());db.execute('UPDATE business_investigation_jobs SET document=? WHERE workspace=? AND owner=? AND job_id=?',(canonical(d),w,o,j))
        try:
            auth=self.resolve(w,o)
            if not auth or auth['subject']!={'workspace_id':w,'subject_id':o}:fail('Current job authority is unavailable.','INVESTIGATION_DENIED',403)
            self.service.authorize(auth,d['kind']!='plan')
            if d['kind']=='plan':
                if 'workflow.plan' not in auth.get('permissions',[]):fail('Workflow planning permission was revoked.','INVESTIGATION_DENIED',403)
                result=self.service.plan(auth,d['payload']);d['workflow_id']=result['workflow_id']
            else:
                result=self.service.execute(auth,d['run_id'],{},d['kind']=='resume');d['workflow_id']=result['workflow_id']
            d.update(state='succeeded',error=None)
        except Exception as exc:
            d.update(state='failed',error=dict(code=getattr(exc,'code','INVESTIGATION_JOB_FAILED'),message=str(exc)[:700] if getattr(exc,'code',None) else 'Investigation work failed. Inspect the saved run and current source/model configuration.'))
        d['updated_at']=now()
        with self.store.transaction() as db:
            db.execute('UPDATE business_investigation_jobs SET state=?,document=?,claim=NULL,deadline=NULL WHERE workspace=? AND owner=? AND job_id=? AND claim=?',(d['state'],canonical(d),w,o,j,token))
        self.health.update(state='ready',last_success=now(),last_error=d['error']['code'] if d['error'] else None)
        return True

    def start(self):
        if self.thread and self.thread.is_alive():return
        self.stop_event.clear()
        def work():
            while not self.stop_event.is_set():
                try:
                    if not self.tick():self.stop_event.wait(1)
                except Exception:self.health.update(state='unavailable',last_error='INVESTIGATION_WORKER_FAILED');self.stop_event.wait(1)
        self.thread=Thread(target=work,daemon=True,name='investigation-jobs');self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:self.thread.join(timeout=5)
