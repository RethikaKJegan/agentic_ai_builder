"""Owned metadata lifecycle and bounded source evidence for Business Ontology."""
from copy import deepcopy
import hashlib
import json
import threading
import time
from pathlib import Path
from jsonschema import Draft202012Validator
from .business_ontology import identity
from .business_graph import specs, safe_name, at
from .data_relationships import fingerprint
from .data_queries import QueryReader
from .data_write_adapter import pack, public_record
from .google_connections import now
from .service import ApiFailure
from .source_evidence import SourceEvidence


def fail(message, code='BUSINESS_SOURCE_INVALID', status=422):
    raise ApiFailure(code,message,status)


def fields_for(dataset):
    return [f for f in dataset['fields'] if safe_name(f['name']) and not any(c in f['name'] for c in '[$\x00')
            and set(f['types'])-{'null'} <= {'string','ObjectId','integer','number','boolean','date','datetime','decimal','Decimal128','numeric'}
            and bool(set(f['types'])-{'null'})]


def diff(previous,current):
    before={d['dataset_id']:d for d in (previous or {}).get('datasets',[])}
    after={d['dataset_id']:d for d in (current or {}).get('datasets',[])}
    result=[]
    for did in sorted(before.keys() | after.keys()):
        old,new=before.get(did),after.get(did)
        a={f['field_id']:f for f in (old or {}).get('fields',[])};b={f['field_id']:f for f in (new or {}).get('fields',[])}
        added=[b[k]['name'] for k in sorted(b.keys()-a.keys())]
        omitted=[a[k]['name'] for k in sorted(a.keys()-b.keys())]
        changed=[dict(field=b[k]['name'],previous_types=a[k]['types'],current_types=b[k]['types']) for k in sorted(a.keys()&b.keys()) if set(a[k]['types'])!=set(b[k]['types'])]
        if added or omitted or changed or not old or not new:
            result.append(dict(dataset_id=did,name=(new or old)['name'],state='added' if not old else 'not_observed' if not new else 'changed',added_fields=added,not_observed_fields=omitted,type_changes=changed))
    return result


class BusinessSources:
    def __init__(self, ontology, manager, reader=None, resolve=None):
        self.ontology,self.manager,self.store=ontology,manager,manager.store
        self.reader,self.resolve=reader or QueryReader(manager),resolve
        self.evidence=SourceEvidence(manager)
        self.lock=threading.Lock();self.active=set()

    def authorize(self,auth,write=False):
        scope=identity(auth,write)
        current=self.resolve(*scope) if self.resolve else auth
        if not current or current.get('subject')!=auth.get('subject'):
            fail('Current source access is unavailable.','BUSINESS_SOURCE_DENIED',403)
        identity(current,write)
        return current,scope

    def bound(self,db,auth,cid):
        workspace=self.ontology.document(db,identity(auth))
        if not workspace or cid not in workspace['sources'].values():
            fail('Choose a source connected to this business workspace.','BUSINESS_SOURCE_NOT_FOUND',404)
        secret,connection=self.manager.owned(db,auth,cid)
        row=db.execute('SELECT document FROM data_source_snapshots WHERE connection_id=? AND revision=?',(cid,connection['metadata_revision'])).fetchone()
        snapshot=json.loads(row[0]) if row else None
        return workspace,secret,connection,snapshot

    def get(self,auth):
        auth,scope=self.authorize(auth)
        with self.store.transaction(write=False) as db:
            workspace=self.ontology.document(db,scope)
            version=db.execute('SELECT document FROM business_ontology_versions WHERE workspace=? AND owner=? ORDER BY CAST(json_extract(document,\'$.revision\') AS INTEGER) DESC LIMIT 1',scope).fetchone()
            definitions=json.loads(version[0]) if version else {}
            sources=[]
            for role,cid in (workspace or {}).get('sources',{}).items():
                try:_,_,connection,snapshot=self.bound(db,auth,cid)
                except ApiFailure as exc:
                    if exc.status!=404:raise
                    sources.append(dict(role=role,connection_id=cid,name='Source unavailable',status='unavailable',metadata_revision=0,generation=0,baseline_revision=workspace['source_revisions'][role],profile=None,refresh=None,datasets=[],changes=[],impacts=dict(modules=[],concepts=[],rules=[],workflows=[],workflows_limited=False)))
                    continue
                baseline_revision=workspace['source_revisions'][role]
                baseline=db.execute('SELECT document FROM data_source_snapshots WHERE connection_id=? AND revision=?',(cid,baseline_revision)).fetchone()
                changes=diff(json.loads(baseline[0]) if baseline else None,snapshot) if connection['metadata_revision']!=baseline_revision else []
                changed_names={d['name'] for d in changes}
                inventory={s['collection']:s for s in specs() if s['role']==role}
                impacted_modules=sorted({m for name in changed_names for m in inventory.get(name,{}).get('modules',[])})
                impacted={kind:[dict(id=c['id'],label=c['label'],module_id=c['module_id']) for c in definitions.get(kind,[]) if c['module_id'] in impacted_modules] for kind in ('concepts','rules')}
                workflows=[]
                if changes or connection['connection_status']!='connected':
                    rows=db.execute("SELECT r.document FROM revisions r WHERE r.workspace=? AND r.version=(SELECT MAX(s.version) FROM revisions s WHERE s.workspace=r.workspace AND s.workflow_id=r.workflow_id) AND json_extract(r.document,'$.metadata.business_ontology') IS NOT NULL ORDER BY r.rowid DESC LIMIT 201",(scope[0],)).fetchall()
                    for (raw,) in rows[:200]:
                        w=json.loads(raw)
                        if any(s.get('connection_id')==cid for s in w.get('metadata',{}).get('database_scope',{}).get('sources',[])):
                            workflows.append(dict(workflow_id=w['workflow_id'],version=w['version'],status=w['status']))
                    limited=len(rows)>200
                else:limited=False
                profile=self.evidence.profile(db,cid)
                # A profile is current only for this exact source generation/revision.
                current_profile=profile and profile.get('generation')==connection.get('generation',0) and profile.get('metadata_revision')==connection['metadata_revision']
                datasets=[]
                for d in (snapshot or {}).get('datasets',[]):
                    fields=fields_for(d)
                    details=profile.get('profiles',{}).get(d['dataset_id'],{}) if current_profile else {}
                    # Only statistics on non-sensitive projected fields are exposed.
                    statistics={f['name']:{k:v for k,v in details.get('fields',{}).get(f['field_id'],{}).items() if k in {'basis','sample_size','present','missing','nulls','null_rate','distinct','comparable','uniqueness','unsupported_values','anomalies'}} for f in fields}
                    datasets.append(dict(dataset_id=d['dataset_id'],name=d['name'],module_ids=inventory.get(d['name'],{}).get('modules',[]),mapping_basis='supplied_source_inventory' if d['name'] in inventory else 'unmapped',sample_count=d.get('sample_count',0),fields=[dict(field_id=f['field_id'],name=f['name'],types=f['types']) for f in fields],field_count=len(d['fields']),profile_rows=details.get('rows'),statistics=statistics,can_browse=any(f['name']=='_id' for f in fields)))
                status='unavailable' if connection['connection_status']!='connected' else 'profiling' if connection.get('profiling_status')!='ready' else 'metadata_changed' if connection['metadata_revision']!=baseline_revision else 'current'
                sources.append(dict(role=role,connection_id=cid,name=connection['name'],status=status,metadata_revision=connection['metadata_revision'],generation=connection.get('generation',0),baseline_revision=baseline_revision,profile=dict(at=profile['at'],current=bool(current_profile)) if profile else None,refresh=self.manager.refresh.view(db,cid,connection),datasets=datasets,changes=changes,impacts=dict(modules=impacted_modules,**impacted,workflows=workflows,workflows_limited=limited)))
        return dict(api_version=1,sources=sources,limits=dict(profile_rows_per_dataset=100,record_rows=25,record_fields=12,record_bytes=2_000_000),qualification='Source references identify relevant modules; they do not verify concept mappings, business policy or cross-database joins. Sampled omissions do not prove deletion.',model_calls=0)

    def profile(self,auth,cid):
        auth,_=self.authorize(auth,True)
        with self.store.transaction(write=False) as db:self.bound(db,auth,cid)
        return self.evidence.request_profile(auth,cid)

    def binding(self,auth,body):
        auth,_=self.authorize(auth)
        with self.store.transaction(write=False) as db:
            workspace,secret,connection,snapshot=self.bound(db,auth,body['connection_id'])
        if not secret or connection['connection_status']!='connected' or connection.get('profiling_status')!='ready' or not snapshot:
            fail('Source discovery must be ready before browsing records.','BUSINESS_SOURCE_UNAVAILABLE',409)
        if (connection['metadata_revision'],connection.get('generation',0))!=(body['metadata_revision'],body['generation']):
            fail('Source metadata changed. Refresh the source list before browsing.','BUSINESS_SOURCE_STALE',409)
        dataset=next((d for d in snapshot['datasets'] if d['dataset_id']==body['dataset_id']),None)
        if not dataset:fail('Dataset is unavailable.','BUSINESS_SOURCE_NOT_FOUND',404)
        fields=fields_for(dataset)
        keys=['_id'] if connection['engine']=='mongodb' else next((c['columns'] for c in dataset.get('constraints',[]) if c['kind']=='primary_key'),[])
        by_name={f['name']:f for f in fields}
        if not keys or not set(keys)<=set(by_name):fail('A supported native identity is required to browse records.')
        fields=[by_name[k] for k in keys]+[f for f in fields if f['name'] not in keys][:12-len(keys)]
        self.manager.configured()
        return dict(connection=connection,dataset=dataset,fields=fields,keys=keys,secret=secret,stamp=fingerprint([workspace['sources'],connection.get('generation',0),connection['metadata_revision'],hashlib.sha256(secret.encode()).hexdigest()]))

    def records(self,auth,body):
        schema=json.loads((Path(__file__).resolve().parents[1]/'shared/contracts/data-sources/business-source-record-request-v1.schema.json').read_text())
        if list(Draft202012Validator(schema).iter_errors(body)) or any(type(body[k]) is not int for k in ('metadata_revision','generation','offset','limit')):
            fail('Choose a current source dataset and a page of 1–25 records.')
        auth,scope=self.authorize(auth)
        with self.lock:
            if scope in self.active:fail('A record read is already running.','BUSINESS_SOURCE_BUSY',409)
            self.active.add(scope)
        try:
            binding=self.binding(auth,body)
            config=json.loads(self.manager.cipher.decrypt(binding['secret'].encode()))
            raw=self.reader.objects(config,binding['dataset'],binding['fields'],binding['keys'],{},body['offset'],body['limit']+1,time.monotonic()+10)
            after=self.binding(auth,body)
            if after['stamp']!=binding['stamp']:fail('Source authority changed during retrieval.','BUSINESS_SOURCE_STALE',409)
            if len(raw)>body['limit']+1:fail('Source exceeded the record limit.')
            records=[public_record(pack({f['name']:at(r,f['name']) for f in binding['fields']},binding['connection']['engine'])) for r in raw[:body['limit']]]
            if len(json.dumps(records).encode())>2_000_000:fail('Source projection exceeded the byte limit.')
            with self.store.transaction() as db:self.manager.audit(db,auth,body['connection_id'],'business_record_read')
            more=len(raw)>body['limit']
            return dict(records=records,fields=[f['name'] for f in binding['fields']],offset=body['offset'],limit=body['limit'],has_more=more,next_offset=body['offset']+body['limit'] if more else None,source=dict(connection_id=body['connection_id'],dataset_id=body['dataset_id'],metadata_revision=body['metadata_revision'],generation=body['generation'],read_at=now()),qualification='Read-only source records; reported values do not establish confirmed findings or cross-database relationships.',model_calls=0)
        finally:
            with self.lock:self.active.discard(scope)
