"""Compatibility guard for saved historical workflow references; no editing API."""
from copy import deepcopy
import json
from .data_graph_v2 import structural
from .data_relationships import fingerprint
from .google_connections import GoogleConnections, now

identity = GoogleConnections.identity
from .service import ApiFailure


def dependencies(record):
    return set(record['dependencies']) | {record['properties'][k] for k in ('source','target','attribute') if k in record['properties']}


class References(dict):
    def __init__(self):super().__init__();self.connections=set()


class HistoricalSelections:
    def __init__(self,manager):self.manager,self.store=manager,manager.store

    @staticmethod
    def exists(db):
        return bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='ontology_selections'").fetchone())

    @staticmethod
    def rows(db,table,scope):
        return [json.loads(r[0]) for r in db.execute(f'SELECT document FROM ontology_{table} WHERE workspace=? AND owner=?',scope)]

    @staticmethod
    def save(db,table,key,scope,rid,document):
        db.execute(f'INSERT INTO ontology_{table} (workspace,owner,{key},document) VALUES (?,?,?,?) ON CONFLICT(workspace,owner,{key}) DO UPDATE SET document=excluded.document',(*scope,rid,json.dumps(document)))

    def refs(self,db,scope):
        refs=References()
        for (raw,) in db.execute('SELECT document FROM data_source_connections WHERE workspace=? AND owner=?',scope):
            c=json.loads(raw)
            if c['connection_status']!='connected':continue
            refs.connections.add(c['connection_id'])
            row=db.execute('SELECT document FROM data_source_snapshots WHERE connection_id=? AND revision=?',(c['connection_id'],c['metadata_revision'])).fetchone()
            if not row:continue
            snapshot=json.loads(row[0]);profile=self.manager.source_evidence.profile(db,c['connection_id']) or {}
            for original in snapshot['datasets']:
                d=deepcopy(original)
                if profile.get('metadata_revision')==snapshot['revision'] and profile.get('generation')==c.get('generation'):
                    evidence=profile.get('profiles',{}).get(d['dataset_id'],{})
                    d.update(value_profiles=evidence.get('fields',{}),composite_profiles=evidence.get('composite_keys',[]),profile_basis=evidence.get('basis','unavailable'))
                signature=fingerprint(structural({k:v for k,v in d.items() if k!='profiled_at'}))
                refs[d['dataset_id']]=dict(connection_id=c['connection_id'],signature=signature)
                for f in d['fields']:refs[f['field_id']]=dict(connection_id=c['connection_id'],signature=fingerprint([signature,structural(f)]))
        return refs

    @staticmethod
    def access(value,refs,lineage=None):
        if isinstance(value,dict):
            lineage={**(lineage or {}),**value.get('source_lineage',{})}
            if any(ref not in refs and lineage.get(ref,{}).get('connection_id') not in refs.connections for ref in value.get('source_refs',[])):return False
            return all(HistoricalSelections.access(v,refs,lineage) for v in value.values())
        if isinstance(value,list):return all(HistoricalSelections.access(v,refs,lineage) for v in value)
        return True

    def state(self,db,scope):
        refs=self.refs(db,scope);records=self.rows(db,'records',scope)
        allowed={r['id'] for r in records if self.access(r,refs)}
        while True:
            removed={r['id'] for r in records if r['id'] in allowed and not dependencies(r)<=allowed}
            if not removed:break
            allowed-=removed
        records=[r for r in records if r['id'] in allowed];revisions={r['id']:r['revision'] for r in records}
        stale={r['id'] for r in records if r['source_signatures']!={ref:refs[ref]['signature'] for ref in r['source_refs'] if ref in refs} or (r['status']=='approved' and any(r.get('dependency_revisions',{}).get(dep)!=revisions.get(dep) for dep in dependencies(r)))}
        while True:
            more={r['id'] for r in records if dependencies(r)&stale}-stale
            if not more:break
            stale|=more
        return records,stale

    def validate_selection(self,db,auth,selection_id):
        scope=identity(auth)
        if not self.exists(db):raise ApiFailure('ONTOLOGY_STALE','Historical selection unavailable.',409)
        row=db.execute('SELECT document FROM ontology_selections WHERE workspace=? AND owner=? AND selection_id=?',(*scope,selection_id)).fetchone()
        if not row:raise ApiFailure('ONTOLOGY_STALE','Historical selection unavailable.',409)
        manifest=json.loads(row[0]);records,stale=self.state(db,scope);by_id={r['id']:r for r in records}
        if not manifest['valid'] or any(rid not in by_id or by_id[rid]['revision']!=rev or rid in stale for rid,rev in manifest['record_revisions'].items()):
            raise ApiFailure('ONTOLOGY_STALE','Historical selection requires revalidation.',409)
        return manifest

    def bind(self,db,auth,selection_id,workflow_id,workflow_version,run_id=None):
        manifest=self.validate_selection(db,auth,selection_id)
        key='binding:'+fingerprint([selection_id,workflow_id,workflow_version,run_id])[:40]
        binding={**manifest,'selection_id':key,'origin_selection_id':selection_id,'workflow_id':workflow_id,'workflow_version':workflow_version,'run_id':run_id}
        self.save(db,'selections','selection_id',identity(auth),key,binding)
        return binding

    def source_changed(self,db,scope):
        if not self.exists(db):return
        records,stale=self.state(db,scope);allowed={r['id'] for r in records}
        changed=stale | {r['id'] for r in self.rows(db,'records',scope) if r['id'] not in allowed}
        if not changed:return
        affected=set(changed)
        while True:
            more={r['id'] for r in self.rows(db,'records',scope) if dependencies(r)&affected}-affected
            if not more:break
            affected|=more
        for s in self.rows(db,'selections',scope):
            hit=set(s['record_ids'])&affected
            if not hit:continue
            reason='source_evidence_changed';iid='impact:'+fingerprint([s['selection_id'],sorted(changed),reason])[:32]
            impact=dict(impact_id=iid,selection_id=s['selection_id'],record_ids=sorted(hit),reason=reason,at=now(),workflow_id=s.get('workflow_id'),workflow_version=s.get('workflow_version'),run_id=s.get('run_id'),eligibility='requires_existing_submission_checks',revalidation='required',replay_state='not_submitted')
            self.save(db,'impacts','impact_id',scope,iid,impact)
            s['valid']=False;self.save(db,'selections','selection_id',scope,s['selection_id'],s)
