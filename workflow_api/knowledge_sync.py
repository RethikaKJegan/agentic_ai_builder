"""Bounded singleton polling of previously authorized graph projections."""
import json
import time
from threading import Event,Thread


class KnowledgeSyncWorker:
    def __init__(self,service,authenticate,interval=30,batch_size=16,clock=time.time):
        self.service,self.authenticate,self.clock=service,authenticate,clock
        self.interval=max(30,interval);self.batch_size=min(32,max(1,batch_size))
        self.stop_event=Event();self.thread=None
        self.health=dict(state='starting',last_success=None,last_error=None)

    def tick(self):
        graph=self.service.account_graph
        with graph.store.transaction(write=False) as db:
            rows=db.execute('SELECT h.workspace,h.owner,h.source_key,h.revision,r.document FROM account_graph_heads h JOIN account_graph_revisions r ON r.workspace=h.workspace AND r.owner=h.owner AND r.source_key=h.source_key AND r.revision=h.revision WHERE h.checked_at<? ORDER BY h.checked_at,h.workspace,h.owner,h.source_key LIMIT ?',(self.clock()-self.interval,self.batch_size)).fetchall()
        updated=failed=0
        for workspace,owner,key,revision,raw in rows:
            if self.stop_event.is_set():break
            try:
                auth=self.authenticate(workspace,owner)
                if auth is None or auth['subject']!={'workspace_id':workspace,'subject_id':owner}:raise ValueError('Current authority unavailable.')
                doc=json.loads(raw);pins=doc['pins']
                if doc['kind']=='package':
                    packages=self.service.business_composition.packages
                    packages.read(auth,dict(package_id=pins['package_id'],revision=pins['revision'],capability_id=pins['capability_id']))
                elif doc['kind']=='package_definition':
                    packages=self.service.business_composition.packages
                    graph.sync_package_definition(auth,packages,packages.get(auth,pins['package_id'],pins['revision']))
                elif doc['kind']=='semantic':graph.sync_semantic(auth,self.service.account_semantic)
                elif doc['kind']=='preparation':
                    preparation=self.service.business_preparation
                    prior=preparation.checked(auth,pins['preflight_id'])
                    current=preparation.prepare(auth,dict(objective=prior['goal']['objective'],inputs=prior['inputs'],version_id=prior['version_id'],**({'evidence_context':{k:prior['evidence_context'][k] for k in ('dataset_id','case_id')}} if prior.get('evidence_context') else {}),**prior.get('domain_context',{})))
                    graph.sync_preparation(auth,preparation,current['preflight_id'])
                else:raise ValueError('Unsupported projection adapter.')
                updated+=1
            except Exception:
                # No stored roles or fallback identities; do not refresh evidence
                # from revoked sources. Retain old versions and retry with backoff.
                with graph.store.transaction() as db:
                    db.execute("UPDATE account_graph_heads SET state='stale',checked_at=? WHERE workspace=? AND owner=? AND source_key=? AND revision=?",(self.clock(),workspace,owner,key,revision))
                failed+=1
        self.health=dict(state='error' if failed else 'ready',last_success=self.clock() if not failed else self.health['last_success'],last_error='KNOWLEDGE_SYNC_FAILED' if failed else None,advanced=updated,capacity=self.batch_size)
        return dict(updated=updated,failed=failed)

    def start(self):
        if self.thread and self.thread.is_alive():return
        self.stop_event.clear()
        def loop():
            while not self.stop_event.is_set():
                try:self.tick()
                except Exception:self.health.update(state='error',last_error='KNOWLEDGE_SYNC_UNAVAILABLE')
                self.stop_event.wait(self.interval)
        self.thread=Thread(target=loop,name='builder-knowledge-sync',daemon=True);self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:self.thread.join(timeout=5)
