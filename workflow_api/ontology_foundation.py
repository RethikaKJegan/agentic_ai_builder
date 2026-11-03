"""Versioned business ontology. No planner, context engine or recovery executor."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import math
import secrets

from .data_relationships import fingerprint, compatible, mongo_reference_compatible
from .google_connections import GoogleConnections, now
from .ontology_model import validate_record, dependencies, graph_errors, select_concepts
from .data_profiles import overlap
from .service import ApiFailure

MAX_RECORDS = 2500
MAX_SUBSET = 200


def fail(message, status=422, code='ONTOLOGY_INVALID'):
    raise ApiFailure(code,message,status)


def exact(body, required, optional=()):
    from registry.safety import reject_secrets
    from registry.contracts import RegistryError
    try:reject_secrets(body)
    except RegistryError:fail('Raw credentials are not accepted in ontology metadata.',422,'SENSITIVE_DATA_DETECTED')
    if not isinstance(body,dict) or not set(required)<=set(body) or set(body)-set(required)-set(optional):
        fail('Supply the documented ontology action fields.')


def identity(auth, write=False):
    return GoogleConnections.identity(auth,write)


def new_id(prefix):
    return prefix+'_'+secrets.token_hex(16)



def calibration_statistics(labels,minimum,n):
    train=[x for x in labels.values() if not x[2]];test=[x for x in labels.values() if x[2]]
    bins=[]
    for i in range(5):
        group=[x for x in train if min(4,int(x[0]*5))==i]
        bins.append(dict(lower=i/5,n=len(group),probability=sum(x[1] for x in group)/len(group) if group else None))
    predicted=[x for x in test if bins[min(4,int(x[0]*5))]['probability'] is not None and bins[min(4,int(x[0]*5))]['probability']>=minimum]
    count=len(predicted);correct=sum(x[1] for x in predicted);precision=correct/count if count else None
    z=1.96
    lower=((precision+z*z/(2*count)-z*math.sqrt(precision*(1-precision)/count+z*z/(4*count*count)))/(1+z*z/count)) if count else None
    return dict(training_examples=len(train),held_out_examples=len(test),predicted_positive=count,precision=precision,
        false_positive_rate=(count-correct)/sum(not x[1] for x in test) if any(not x[1] for x in test) else None,
        precision_lower_bound=lower,bins=bins,eligible=bool(len(train)>=n and count>=n and lower>=minimum))

class SourceReferences(dict):
    def __init__(self):
        super().__init__()
        self.connections=set()


class OntologyFoundation:
    def __init__(self, manager):
        self.manager, self.store = manager, manager.store
        self.workflow_service = None
        with self.store.transaction() as db:
            for name, key in [('records','record_id'),('versions','version_id'),('selections','selection_id'),('impacts','impact_id'),('calibrations','calibration_id')]:
                db.execute(f'CREATE TABLE IF NOT EXISTS ontology_{name} (workspace TEXT NOT NULL, owner TEXT NOT NULL, {key} TEXT NOT NULL, document TEXT NOT NULL, PRIMARY KEY(workspace,owner,{key}))')
            db.execute('CREATE TABLE IF NOT EXISTS ontology_events (event_id TEXT PRIMARY KEY, workspace TEXT NOT NULL, owner TEXT NOT NULL, record_id TEXT NOT NULL, document TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS ontology_profile_requests (job_id TEXT PRIMARY KEY)')
            db.execute('CREATE TABLE IF NOT EXISTS ontology_source_profiles (connection_id TEXT PRIMARY KEY, document TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS ontology_source_observations (connection_id TEXT PRIMARY KEY, document TEXT NOT NULL)')
            db.execute('CREATE INDEX IF NOT EXISTS ontology_events_scope ON ontology_events(workspace,owner,record_id)')

    @staticmethod
    def rows(db, table, scope):
        return [json.loads(row[0]) for row in db.execute(f'SELECT document FROM ontology_{table} WHERE workspace=? AND owner=?',scope).fetchall()]

    @staticmethod
    def save(db, table, key, scope, rid, value):
        db.execute(f'INSERT INTO ontology_{table} (workspace,owner,{key},document) VALUES (?,?,?,?) ON CONFLICT(workspace,owner,{key}) DO UPDATE SET document=excluded.document',(*scope,rid,json.dumps(value,allow_nan=False)))

    def event(self, db, scope, rid, action, **data):
        event=dict(action=action,at=now(),reviewer=scope[1],**data)
        db.execute('INSERT INTO ontology_events (event_id,workspace,owner,record_id,document) VALUES (?,?,?,?,?)',(new_id('oe'),*scope,rid,json.dumps(event,allow_nan=False)))

    def sources(self, db, scope):
        refs=SourceReferences();catalogue=[]
        for raw, in db.execute('SELECT document FROM data_source_connections WHERE workspace=? AND owner=?',scope).fetchall():
            c=json.loads(raw)
            if c.get('connection_status')!='connected':continue
            refs.connections.add(c['connection_id'])
            row=db.execute('SELECT document FROM data_source_snapshots WHERE connection_id=? AND revision=?',(c['connection_id'],c['metadata_revision'])).fetchone()
            if not row:continue
            snapshot=json.loads(row[0]);cid=c['connection_id']
            from .data_drift import rename_candidates
            previous=db.execute('SELECT document FROM data_source_snapshots WHERE connection_id=? AND revision<? ORDER BY revision DESC LIMIT 1',(cid,snapshot['revision'])).fetchone()
            renames=rename_candidates(json.loads(previous[0]) if previous else None,snapshot)
            datasets=[]
            profile_row=db.execute('SELECT document FROM ontology_source_profiles WHERE connection_id=?',(cid,)).fetchone()
            profile=json.loads(profile_row[0]) if profile_row else {}
            for dataset in snapshot['datasets']:
                d=deepcopy(dataset);did=d['dataset_id']
                if profile.get('metadata_revision')==snapshot['revision'] and profile.get('generation')==c.get('generation'):
                    evidence=profile.get('profiles',{}).get(did,{})
                    d['value_profiles']=evidence.get('fields',{})
                    d['composite_profiles']=evidence.get('composite_keys',[])
                    d['profile_basis']=evidence.get('basis','unavailable')
                    d['profiled_at']=profile.get('at')
                # Ignore observation timestamps/counts in structural signatures.
                from .data_graph_v2 import structural
                signature=fingerprint(structural({k:v for k,v in d.items() if k!='profiled_at'}))
                base=dict(connection_id=cid,dataset_id=did,signature=signature,revision=snapshot['revision'],freshness=c.get('last_profiled_at'))
                refs[did]=dict(base,kind='dataset',label=d['name'],metadata=d)
                for f in d['fields']:
                    refs[f['field_id']]=dict(base,signature=fingerprint([signature,structural(f)]),kind='field',label=f['name'],metadata=f)
                datasets.append(d)
            catalogue.append(dict(connection_id=cid,name=c.get('name',cid),engine=c.get('engine','unknown'),
                owner=scope[1],description=c.get('description',''),metadata_revision=snapshot['revision'],
                discovered_at=snapshot.get('discovered_at'),freshness=c.get('last_profiled_at'),
                permissions=dict(scope='connection_owner',discovery=True,grant_enumeration='unavailable',record_profiling='connector_read_authority'),
                capabilities=dict(metadata=True,value_profiles=any('value_profiles' in d for d in datasets),
                    pagination='bounded_driver_cursor',incremental_sync=False,change_detection='scheduled_snapshot_comparison',
                    rate_limits='driver_timeouts_and_worker_backoff',limits=snapshot.get('limits',{})),
                possible_renames=renames,source_owner='unavailable',changes=snapshot.get('changes',{}),rename_policy='Ambiguous additions/removals require reviewed continuity; sampled omissions do not prove deletion.',
                coverage=snapshot.get('coverage'),warnings=snapshot.get('warnings',[]),datasets=datasets))
        return refs,catalogue

    @staticmethod
    def signatures(record, refs):
        return {rid:refs[rid]['signature'] for rid in record['source_refs'] if rid in refs}

    @staticmethod
    def visible(records, refs):
        allowed={r['id'] for r in records if OntologyFoundation.evidence_access(r,refs)}
        while True:
            removed={r['id'] for r in records if r['id'] in allowed and not dependencies(r)<=allowed}
            if not removed:break
            allowed-=removed
        return [deepcopy(r) for r in records if r['id'] in allowed]

    def state(self, db, scope):
        refs,catalogue=self.sources(db,scope)
        records=self.visible(self.rows(db,'records',scope),refs)
        revisions={r['id']:r['revision'] for r in records}
        for r in records:
            r['stale']=r['source_signatures']!=self.signatures(r,refs) or (r['status']=='approved' and any(r.get('dependency_revisions',{}).get(dep)!=revisions.get(dep) for dep in dependencies(r)))
            original=r.get('original_proposal',{})
            if not self.evidence_access(original,refs,r.get('source_lineage',{})):r.pop('original_proposal',None)
        # A changed concept invalidates only its transitive consumers.
        stale={r['id'] for r in records if r['stale']}
        while True:
            more={r['id'] for r in records if dependencies(r)&stale}-stale
            if not more:break
            stale|=more
        for r in records:r['stale']=r['id'] in stale
        return records,refs,catalogue

    @staticmethod
    def revision(records):
        return fingerprint(sorted([(r['id'],r['revision'],r['stale']) for r in records]))

    def get(self, auth):
        scope=identity(auth)
        with self.store.transaction(write=False) as db:
            records,refs,catalogue=self.state(db,scope)
            versions=self.rows(db,'versions',scope)
            visible_ids={r['id'] for r in records}
            consumers=self.rows(db,'selections',scope)
            dependents={rid:[] for rid in visible_ids}
            for other in records:
                for dep in dependencies(other):
                    if dep in dependents:dependents[dep].append(other['id'])
            for r in records:
                r['dependents']=sorted(dependents[r['id']])
                r['consumers']=[{k:s.get(k) for k in ('selection_id','workflow_id','workflow_version','run_id','valid')} for s in consumers if r['id'] in s['record_ids']]
            impacts=[i for i in self.rows(db,'impacts',scope) if set(i['record_ids'])<=visible_ids]
            events=self.rows_events(db,scope)
            labels=[e for e in events if e['action'] in {'accept','reject','correct'} and e.get('original') and e['original']['id'] in visible_ids]
            calibrations=self.rows(db,'calibrations',scope)
            calibration=max(calibrations,key=lambda c:c['created_at']) if calibrations else None
            reviewed=len(labels);rejected=sum(e['action']=='reject' for e in labels)
            return dict(api_version=1,warnings=['Ontology import bound reached; narrow the source scope.'] if len(records)>=MAX_RECORDS else [],revision=self.revision(records),records=records,catalogue=catalogue,
                versions=[dict(version_id=v['version_id'],published_at=v['published_at'],record_count=len(v['records'])) for v in versions if self.version_access(v,refs)],
                review_queue=sorted([r['id'] for r in records if r['status']=='draft' or r['stale']],key=lambda rid:(-self.priority(rid,records,impacts+consumers),rid)),
                impacts=impacts,metrics=dict(unresolved=sum(r['status']=='draft' or r['stale'] for r in records),
                    reviewed=reviewed,rejections=rejected,corrections=sum(e['action']=='correct' for e in labels),
                    correction_rate=sum(e['action']=='correct' for e in labels)/reviewed if reviewed else None,
                    precision=calibration['precision'] if calibration else None,false_positive_rate=calibration['false_positive_rate'] if calibration else None,held_out_examples=calibration['held_out_examples'] if calibration else 0,evaluation_note='Use held-out calibration metrics; review rejection alone is not a false-positive estimate.',
                    drift=sum(r['stale'] for r in records),downstream_failures=sum(i.get('failed',False) for i in impacts)))

    @staticmethod
    def priority(rid, records, impacts):
        r=next(r for r in records if r['id']==rid)
        return 5*(len(r['dependents']) if 'dependents' in r else sum(rid in dependencies(other) for other in records))+10*sum(rid in i['record_ids'] for i in impacts)+dict(low=0,medium=20,high=50).get(r['properties'].get('risk','medium'),20)+(30 if r['stale'] else 0)

    @staticmethod
    def rows_events(db, scope):
        return [json.loads(row[0]) for row in db.execute('SELECT document FROM ontology_events WHERE workspace=? AND owner=? ORDER BY rowid',scope).fetchall()]

    def put(self, auth, body):
        scope=identity(auth,True);exact(body,{'record','expected_revision'})
        validate_record(body['record'])
        if type(body['expected_revision']) is not int or body['expected_revision']<0:fail('Supply the expected record revision.')
        with self.store.transaction() as db:
            records,refs,_=self.state(db,scope)
            all_records=self.rows(db,'records',scope)
            old=next((r for r in all_records if r['id']==body['record']['id']),None)
            if old and old['id'] not in {r['id'] for r in records}:fail('Record unavailable.',404,'ONTOLOGY_NOT_FOUND')
            if (old['revision'] if old else 0)!=body['expected_revision']:fail('Record changed. Reload before editing.',409,'ONTOLOGY_STALE')
            if not old and len(all_records)>=MAX_RECORDS:fail('Ontology record limit reached.')
            r=deepcopy(body['record'])
            if not set(r['source_refs'])<=set(refs):fail('Source evidence is unavailable.',403,'ONTOLOGY_SOURCE_FORBIDDEN')
            if not dependencies(r)<={x['id'] for x in records}:fail('A referenced concept or dependency is unavailable.')
            r.update(revision=(old['revision'] if old else 0)+1,status='draft',source_signatures=self.signatures(r,refs),
                source_lineage={rid:{k:refs[rid][k] for k in ('connection_id','dataset_id','revision','signature')} for rid in r['source_refs']},
                created_at=old['created_at'] if old else now(),updated_at=now(),original_proposal=old['original_proposal'] if old else deepcopy(body['record']))
            r['dependency_revisions']={dep:next(x['revision'] for x in records if x['id']==dep) for dep in dependencies(r)}
            r['assessment']=self.assess(r,refs)
            errors=graph_errors([x for x in records if x['id']!=r['id']]+[r])
            if errors:fail('Ontology graph validation failed.',422,'ONTOLOGY_GRAPH_INVALID')
            self.save(db,'records','record_id',scope,r['id'],r)
            self.event(db,scope,r['id'],'edit' if old else 'propose',original=old,record=r)
            if old:self.invalidate(db,scope,{r['id']},'definition_changed')
        return self.get(auth)

    @staticmethod
    def assess(r,refs):
        p=r['properties'];pairs=p.get('field_pairs',[]);signals={k:None for k in ('schema_compatibility','key_compatibility','semantic_similarity','value_overlap','referential_consistency','constraint_consistency','freshness')}
        contradictions=list(p.get('contradictions',[]))
        if r['source_refs']:
            try:
                ages=[(datetime.now(timezone.utc)-datetime.fromisoformat(refs[x]['freshness'].replace('Z','+00:00'))).total_seconds() for x in r['source_refs']]
                signals['freshness']=float(all(0<=age<=86400 for age in ages))
            except (KeyError,TypeError,ValueError,AttributeError):pass
        compatible_pairs=[];profiles=[]
        for pair in pairs:
            a,b=(refs.get(pair[k]) for k in ('source_field_id','target_field_id'))
            if not a or not b:continue
            good=mongo_reference_compatible(a['metadata'],b['metadata']);compatible_pairs.append(good)
            if not good:contradictions.append('Incompatible source field types.')
            da=refs.get(a['dataset_id'],{}).get('metadata',{})
            db=refs.get(b['dataset_id'],{}).get('metadata',{})
            pa=da.get('value_profiles',{}).get(pair['source_field_id']);pb=db.get('value_profiles',{}).get(pair['target_field_id'])
            if good and pa and pb:profiles.append(overlap(pa,pb))
            # Verify actual declared key membership, never infer it from an ID-like label.
            signals['key_compatibility']=bool(any(c.get('kind')=='foreign_key' and a['label'] in c.get('columns',[]) and b['label'] in c.get('referenced_columns',[]) for c in da.get('constraints',[])))
        if len(pairs)>1:
            profiles=[]
            source_refs=[refs.get(p['source_field_id']) for p in pairs];target_refs=[refs.get(p['target_field_id']) for p in pairs]
            if all(source_refs+target_refs) and all(compatible_pairs):
                source=refs[source_refs[0]['dataset_id']]['metadata'];target=refs[target_refs[0]['dataset_id']]['metadata']
                left=next((p for p in source.get('composite_profiles',[]) if p['columns']==[x['label'] for x in source_refs]),None)
                right=next((p for p in target.get('composite_profiles',[]) if p['columns']==[x['label'] for x in target_refs]),None)
                if left and right:profiles=[overlap(left,right)]
        if compatible_pairs:signals['schema_compatibility']=sum(compatible_pairs)/len(compatible_pairs)
        if profiles:
            values=[x['referential_consistency'] for x in profiles if x['referential_consistency'] is not None]
            signals['value_overlap']=sum(values)/len(values) if values else None
            signals['referential_consistency']=signals['value_overlap']
        if r['definition'] and all(refs.get(x,{}).get('label') for x in r['source_refs']) and r['source_refs']:
            words=set(r['definition'].casefold().split())
            names=set(' '.join(refs[x]['label'] for x in r['source_refs']).casefold().replace('_',' ').split())
            signals['semantic_similarity']=len(words&names)/len(words|names) if words|names else None
        measured=[float(v) for v in signals.values() if v is not None]
        return dict(method_version='evidence-signals-v1',signals=signals,heuristic_score=sum(measured)/len(measured) if measured else None,
            calibrated_score=None,calibration_id=None,contradictions=sorted(set(contradictions)),value_evidence=profiles,status='uncalibrated')

    def sync(self, auth):
        scope=identity(auth,True)
        with self.store.transaction() as db:
            records,refs,catalogue=self.state(db,scope);existing={r['id']:r for r in self.rows(db,'records',scope)}
            detailed=self.manager.relationships.detailed.project(db,*scope)
            graph=detailed.get('graph') or {}
            legacy_mappings={m['node_id']:m for m in graph.get('mappings',[]) if m['status']!='rejected'}
            legacy_nodes={n['node_id']:n for n in graph.get('nodes',[])}
            concepts={}
            available=set(existing)
            for ref_id,ref in refs.items():
                if ref['kind']!='dataset':continue
                rid='source:'+ref_id;concepts[ref_id]=rid
                if rid in existing:continue
                r=dict(id=rid,kind='concept',layer='organization',label=legacy_mappings.get(ref_id,{}).get('entity_name',ref['label'])[:160],definition=legacy_nodes.get(ref_id,{}).get('description') or 'Source dataset; business definition requires review.',dependencies=[],source_refs=[ref_id],evidence_class='unverified_hypothesis',properties={})
                self.import_record(db,scope,r,refs,'source_catalogue',legacy_mapping=legacy_mappings.get(ref_id))
                available.add(rid)
            for ref_id,ref in refs.items():
                if ref['kind']!='field':continue
                rid='field:'+ref_id
                if rid in existing or len(available)>=MAX_RECORDS:continue
                types=set(ref['metadata']['types'])-{'null'}
                datatype=next(iter(types)) if len(types)==1 else 'unknown'
                aliases={'text':'string','character varying':'string','bigint':'integer','numeric':'number'}
                datatype=aliases.get(datatype,datatype)
                if datatype not in {'string','integer','number','boolean','date','datetime','object','array'}:datatype='unknown'
                r=dict(id=rid,kind='attribute',layer='organization',label=ref['label'][:160],definition='Source field type; business meaning requires review.',dependencies=[],source_refs=[ref_id],evidence_class='observed_fact',properties=dict(source=concepts[ref['dataset_id']],datatype=datatype))
                self.import_record(db,scope,r,refs,'source_field');available.add(rid)
            detailed=self.manager.relationships.detailed.project(db,*scope)
            for edge in (detailed.get('graph') or {}).get('relationships',[]):
                rid='structural:'+edge['relationship_id']
                a,b=(concepts.get(edge[k]) for k in ('source_dataset_id','target_dataset_id'))
                if rid in existing or not a or not b or len(available)>=MAX_RECORDS:continue
                pairs=[{k:p[k] for k in ('source_field_id','target_field_id')} for p in edge['field_pairs']]
                r=dict(id=rid,kind='relationship',layer='organization',label='Structural reference',definition='Source key evidence; business meaning is reviewed separately.',dependencies=[],source_refs=sorted({p[k] for p in pairs for k in ('source_field_id','target_field_id')}),evidence_class='observed_fact' if edge['kind']=='declared' else 'unverified_hypothesis',properties=dict(source=a,target=b,predicate='references',method='source_foreign_key' if edge['kind']=='declared' else 'metadata_candidate',technical_relationship_id=edge['relationship_id'],field_pairs=pairs))
                self.import_record(db,scope,r,refs,'structural_evidence');available.add(rid)
            # Preserve existing semantic suggestions/reviews as drafts with original evidence.
            view=self.manager.semantic.project(db,*scope)
            for edge in view['relationships']:
                a,b=(concepts.get(edge[k]) for k in ('source_dataset_id','target_dataset_id'))
                if not a or not b or not edge.get('predicate'):continue
                if edge.get('reversed'):a,b=b,a
                rid='legacy:'+edge['relationship_id']
                if rid in existing or len(available)>=MAX_RECORDS:continue
                available.add(rid)
                r=dict(id=rid,kind='relationship',layer='organization',label=edge['predicate'],definition=edge.get('rationale',''),
                    dependencies=[],source_refs=[edge['source_dataset_id'],edge['target_dataset_id']],evidence_class='model_inference',
                    properties=dict(source=a,target=b,predicate=edge['predicate'],method=edge.get('inference_method','legacy'),
                        technical_relationship_id=edge['technical_relationship_id'],field_pairs=[{k:p[k] for k in ('source_field_id','target_field_id')} for p in edge['field_pairs']]))
                self.import_record(db,scope,r,refs,'legacy_semantic',legacy=deepcopy(edge))
            self.construct_candidates(db,scope,refs)
            self.invalidate(db,scope,{r['id'] for r in records if r['stale']},'source_evidence_changed')
        return self.get(auth)

    def import_record(self,db,scope,r,refs,method,**extra):
        validate_record(r)
        r.update(revision=1,status='draft',created_at=now(),updated_at=now(),source_signatures=self.signatures(r,refs),original_proposal=deepcopy(r))
        r['assessment']=self.assess(r,refs)
        r['source_lineage']={ref:{k:refs[ref][k] for k in ('connection_id','dataset_id','revision','signature')} for ref in r['source_refs']}
        current={v['id']:v['revision'] for v in self.rows(db,'records',scope)}
        r['dependency_revisions']={dep:current.get(dep) for dep in dependencies(r)}
        self.save(db,'records','record_id',scope,r['id'],r)
        self.event(db,scope,r['id'],'import',method=method,record=deepcopy(r),**extra)

    def templates(self,auth):
        scope=identity(auth,True)
        with self.store.transaction() as db:
            existing={r['id'] for r in self.rows(db,'records',scope)}
            definitions=[('common:party','Party','A person or organization participating in business.','common',None,[]),
                ('sales:customer','Customer','A party that buys goods or services.','domain','Sales',['common:party']),
                ('procurement:supplier','Supplier','A party providing goods or services.','domain','Procurement',['common:party']),
                ('finance:invoice','Invoice','A document requesting payment for goods or services.','domain','Finance',[]),
                ('service:case','Service case','A tracked customer request or issue.','domain','Customer Service',[])]
            for rid,label,definition,layer,domain,deps in definitions:
                if rid not in existing:
                    r=dict(id=rid,kind='concept',layer=layer,domain=domain,label=label,definition=definition,dependencies=deps,source_refs=[],evidence_class='unverified_hypothesis',properties=dict(method='documented_starter_definition_v1'))
                    self.import_record(db,scope,r,{},'starter_definition_v1')
        return self.get(auth)

    def review(self,auth,rid,body):
        scope=identity(auth,True);exact(body,{'expected_revision','action','reason'},{'record','target_id'})
        if body['action'] not in {'accept','reject','correct','merge'} or not isinstance(body['reason'],str) or not 1<=len(body['reason'])<=2000:fail('Choose a review action and give a reason.')
        with self.store.transaction() as db:
            records,refs,_=self.state(db,scope);by_id={r['id']:r for r in records};r=by_id.get(rid)
            if not r:fail('Record not found.',404,'ONTOLOGY_NOT_FOUND')
            if type(body['expected_revision']) is not int or r['revision']!=body['expected_revision']:fail('Record changed.',409,'ONTOLOGY_STALE')
            if r['stale'] and body['action']=='accept':fail('Evidence changed. Correct and revalidate the mapping first.',409,'ONTOLOGY_STALE')
            original=deepcopy(r)
            if body['action']=='correct':
                validate_record(body.get('record'))
                if body['record']['id']!=rid:fail('Corrections preserve stable identity.')
                r={**deepcopy(body['record']),**{k:r[k] for k in ('revision','status','created_at','original_proposal')}}
                if not set(r['source_refs'])<=set(refs) or not dependencies(r)<=set(by_id):fail('Correction references unavailable evidence or concepts.')
                r['source_signatures']=self.signatures(r,refs);r['source_lineage']={ref:{k:refs[ref][k] for k in ('connection_id','dataset_id','revision','signature')} for ref in r['source_refs']};r['assessment']=self.assess(r,refs)
            if body['action']=='merge':
                target=by_id.get(body.get('target_id'))
                if not target or target['id']==rid or r['kind'] not in {'concept','mapping'} or target['kind']!=r['kind'] or r['layer']!=target['layer'] or target.get('redirect') or target['status']!='approved' or target['stale']:fail('Choose a compatible approved concept to merge into.')
                if r['kind']=='mapping' and any(r['properties'][k]!=target['properties'][k] for k in ('source','target')):fail('Merged mappings must refer to the same concepts.')
                if any(rid in dependencies(other) for other in records):fail('Correct dependent mappings to the target before merging this concept.')
                r['redirect']=target['id'];r['dependencies']=sorted(set(r['dependencies'])|{target['id']})
            if body['action'] in {'accept','correct'}:
                r['dependency_revisions']={dep:by_id[dep]['revision'] for dep in dependencies(r)}
            r['status']='rejected' if body['action']=='reject' else 'approved'
            r.update(revision=r['revision']+1,reviewed_at=now(),reviewed_by=scope[1],review_reason=body['reason'],updated_at=now())
            if r['status']=='approved' and r['assessment']['contradictions']:fail('Resolve contradictory evidence before approval.')
            if graph_errors([x for x in records if x['id']!=rid]+[r]):fail('The reviewed graph violates its typed rules.')
            self.save(db,'records','record_id',scope,rid,r)
            self.event(db,scope,rid,body['action'],original=original,record=r,reason=body['reason'])
            self.invalidate(db,scope,{rid},'expert_'+body['action'])
        return self.get(auth)

    def invalidate(self,db,scope,changed,reason):
        if not changed:return
        records=self.rows(db,'records',scope);affected=set(changed)
        while True:
            more={r['id'] for r in records if dependencies(r)&affected}-affected
            if not more:break
            affected|=more
        for s in self.rows(db,'selections',scope):
            hit=set(s['record_ids'])&affected
            if not hit:continue
            iid='impact:'+fingerprint([s['selection_id'],sorted(changed),reason])[:32]
            impact=dict(impact_id=iid,selection_id=s['selection_id'],record_ids=sorted(hit),reason=reason,at=now(),
                workflow_id=s.get('workflow_id'),workflow_version=s.get('workflow_version'),run_id=s.get('run_id'),
                eligibility='requires_existing_submission_checks',revalidation='required',replay_state='not_submitted')
            self.save(db,'impacts','impact_id',scope,iid,impact)
            s['valid']=False;self.save(db,'selections','selection_id',scope,s['selection_id'],s)

    @staticmethod
    def evidence_access(value,refs,lineage=None):
        if isinstance(value,dict):
            lineage={**(lineage or {}),**value.get('source_lineage',{})}
            if 'source_refs' in value:
                for ref in value['source_refs']:
                    if ref not in refs and lineage.get(ref,{}).get('connection_id') not in getattr(refs,'connections',set()):return False
            return all(OntologyFoundation.evidence_access(v,refs,lineage) for v in value.values())
        if isinstance(value,list):return all(OntologyFoundation.evidence_access(v,refs,lineage) for v in value)
        return True

    @staticmethod
    def version_access(version,refs):
        return OntologyFoundation.evidence_access(version,refs)

    def publish(self,auth,body):
        scope=identity(auth,True);exact(body,{'revision'})
        with self.store.transaction() as db:
            records,refs,_=self.state(db,scope)
            if body['revision']!=self.revision(records):fail('Ontology changed. Reload before publishing.',409,'ONTOLOGY_STALE')
            approved=[r for r in records if r['status']=='approved']
            if not approved:fail('Review at least one record before publishing.')
            errors=graph_errors(approved)
            if errors or any(r['stale'] for r in approved):fail('Approved records have stale evidence or unresolved dependencies.',409,'ONTOLOGY_PUBLICATION_BLOCKED')
            vid='ov_'+fingerprint(sorted([(r['id'],r['revision'],r['source_signatures']) for r in approved]))[:40]
            previous=next((v for v in self.rows(db,'versions',scope) if v['version_id']==vid),None)
            if previous:return dict(version_id=vid,published_at=previous['published_at'],record_count=len(approved))
            calibration_ids={r['assessment'].get('calibration_id') for r in approved}-{None}
            calibration_evidence=[c for c in self.rows(db,'calibrations',scope) if c['calibration_id'] in calibration_ids]
            document=dict(calibrations=calibration_evidence,version_id=vid,published_at=now(),published_by=scope[1],records=approved,validation=dict(errors=[],method='typed_graph_v1'))
            self.save(db,'versions','version_id',scope,vid,document)
            self.event(db,scope,vid,'publish',record_ids=[r['id'] for r in approved])
            return dict(version_id=vid,published_at=document['published_at'],record_count=len(approved))

    def version(self,auth,vid):
        scope=identity(auth)
        with self.store.transaction(write=False) as db:
            refs,_=self.sources(db,scope)
            value=next((v for v in self.rows(db,'versions',scope) if v['version_id']==vid),None)
            if not value or not self.version_access(value,refs):fail('Ontology version unavailable.',404,'ONTOLOGY_NOT_FOUND')
            value['stale']=any(r['source_signatures']!=self.signatures(r,refs) for r in value['records'])
            return value

    def lookup(self,auth,vid,kind,value):
        if kind not in {'concept','source_field','entity','relationship_type'}:fail('Unsupported ontology lookup.')
        version=self.version(auth,vid)
        matches=[r for r in version['records'] if (kind in {'concept','entity'} and r['id']==value) or (kind=='source_field' and value in r['source_refs']) or (kind=='relationship_type' and r['kind']=='relationship' and r['properties'].get('predicate')==value)]
        return dict(version_id=vid,stale=version['stale'],records=matches)

    def select(self,auth,body):
        scope=identity(auth);exact(body,{'version_id','concept_ids'})
        seeds=body['concept_ids']
        if not isinstance(seeds,list) or not 1<=len(seeds)<=50 or any(not isinstance(x,str) for x in seeds):fail('Select one to fifty ontology concepts.')
        # No new context engine: select graph dependencies, then hand IDs to consumers.
        with self.store.transaction() as db:
            records,refs,_=self.state(db,scope)
            v=next((v for v in self.rows(db,'versions',scope) if v['version_id']==body['version_id']),None)
            if not v or not self.version_access(v,refs):fail('Version unavailable.',404,'ONTOLOGY_NOT_FOUND')
            current={r['id']:r for r in records}
            chosen=select_concepts(v['records'],seeds,MAX_SUBSET)
            selected={r['id'] for r in chosen}
            by_id={r['id']:r for r in chosen}
            if any(rid not in current or current[rid]['revision']!=by_id[rid]['revision'] or current[rid]['stale'] for rid in selected):fail('Selected ontology definitions need revalidation.',409,'ONTOLOGY_STALE')
            sid=new_id('os');manifest=dict(selection_id=sid,version_id=v['version_id'],record_ids=sorted(selected),
                record_revisions={r['id']:r['revision'] for r in chosen},evidence={r['id']:r['source_signatures'] for r in chosen},
                valid=True,created_at=now())
            self.save(db,'selections','selection_id',scope,sid,manifest)
            return dict(manifest=manifest,records=chosen)

    def history(self,auth,rid):
        scope=identity(auth)
        with self.store.transaction(write=False) as db:
            records,refs,_=self.state(db,scope)
            if rid not in {r['id'] for r in records}:fail('Record unavailable.',404,'ONTOLOGY_NOT_FOUND')
            events=[e for e in self.rows_events(db,scope) if any(e.get(k,{}).get('id')==rid for k in ('record','original'))]
            # Historical changes may reference sources no longer accessible.
            return dict(record_id=rid,events=[e for e in events if self.evidence_access(e,refs)])

    def calibrate(self,auth,body):
        scope=identity(auth,True);exact(body,{'minimum_precision','minimum_examples'},{'kind','domain'})
        kind=body.get('kind','mapping');domain=body.get('domain')
        if kind not in {'concept','attribute','mapping','constraint','relationship'} or domain not in {None,'Sales','Procurement','Finance','Customer Service'}:fail('Choose a supported calibration kind and domain.')
        minimum=body['minimum_precision'];n=body['minimum_examples']
        if type(minimum) not in (int,float) or not math.isfinite(minimum) or not .8<=minimum<=1 or type(n) is not int or n<20:fail('Calibration needs at least twenty examples and precision from 0.8 to 1.')
        with self.store.transaction() as db:
            records,refs,_=self.state(db,scope);allowed={r['id'] for r in records}
            # Latest label per independent source family; deterministic held-out groups avoid label leakage.
            labels={}
            for e in self.rows_events(db,scope):
                r=e.get('original')
                if e['action'] not in {'accept','reject','correct'} or not r or r['id'] not in allowed or r['kind']!=kind or r.get('domain')!=domain or r['assessment']['heuristic_score'] is None:continue
                families=sorted({(refs[ref]['connection_id'],refs[ref]['dataset_id']) for ref in r['source_refs'] if ref in refs})
                group=fingerprint(families or [r['id']])
                labels[group]=(r['assessment']['heuristic_score'],e['action']=='accept',int(group[:8],16)%3==0)
            stats=calibration_statistics(labels,minimum,n)
            cid=new_id('oc');result=dict(kind=kind,domain=domain,calibration_id=cid,method='grouped_empirical_bins_v1',created_at=now(),
                minimum_precision=minimum,minimum_examples=n,label_digest=fingerprint(sorted(labels.items())),**stats)
            self.save(db,'calibrations','calibration_id',scope,cid,result)
            self.event(db,scope,cid,'calibrate',calibration=result)
            return result

    def bind(self,db,auth,selection_id,workflow_id,workflow_version,run_id=None):
        scope=identity(auth)
        manifest=self.validate_selection(db,auth,selection_id)
        # Consumption copies keep multiple workflows/runs distinct.
        key='binding:'+fingerprint([selection_id,workflow_id,workflow_version,run_id])[:40]
        binding={**manifest,'selection_id':key,'origin_selection_id':selection_id,'workflow_id':workflow_id,'workflow_version':workflow_version,'run_id':run_id}
        self.save(db,'selections','selection_id',scope,key,binding)
        return binding

    def request_profile(self,auth,cid):
        identity(auth,True)
        self.manager.configured()
        with self.store.transaction() as db:
            secret,doc=self.manager.owned(db,auth,cid)
            if not secret or doc['connection_status']!='connected':fail('Connect this source before profiling.',409)
            active=db.execute("SELECT job_id FROM data_source_profile_jobs WHERE connection_id=? AND state IN ('queued','running')",(cid,)).fetchone()
            if active:fail('Wait for current source discovery before profiling.',409)
            job=self.manager.queue(db,doc,invalidate=False);self.manager.save(db,doc)
            db.execute('INSERT INTO ontology_profile_requests (job_id) VALUES (?)',(job,))
            return dict(job_id=job,status='queued',limits=dict(rows_per_dataset=100,seconds=60),basis='bounded_sample')

    @staticmethod
    def store_profiles(db,cid,generation,revision,profiles):
        document=dict(generation=generation,metadata_revision=revision,profiles=profiles,at=now())
        db.execute('INSERT INTO ontology_source_profiles (connection_id,document) VALUES (?,?) ON CONFLICT(connection_id) DO UPDATE SET document=excluded.document',(cid,json.dumps(document)))

    def source_changed(self,db,scope):
        records,refs,_=self.state(db,scope)
        changed={r['id'] for r in records if r['stale']}
        changed|={r['id'] for r in self.rows(db,'records',scope) if not self.evidence_access(r,refs)}
        self.invalidate(db,scope,changed,'source_evidence_changed')

    def replay(self,auth,iid,body):
        scope=identity(auth,True);exact(body,{'action'},{'inputs','idempotency_key','workflow_version'})
        if body['action'] not in {'assess','submit'}:fail('Choose assess or submit.')
        with self.store.transaction() as db:
            row=db.execute('SELECT document FROM ontology_impacts WHERE workspace=? AND owner=? AND impact_id=?',(*scope,iid)).fetchone()
            if not row:fail('Impact unavailable.',404,'ONTOLOGY_NOT_FOUND')
            impact=json.loads(row[0]);service=self.workflow_service
            records,_,_=self.state(db,scope)
            if not set(impact['record_ids'])<={r['id'] for r in records}:fail('Impact unavailable.',404,'ONTOLOGY_NOT_FOUND')
            target_version=body.get('workflow_version',impact.get('workflow_version'))
            if target_version is not None and (type(target_version) is not int or target_version<1):fail('Choose an existing workflow revision.')
            workflow=service.store.get(db,scope[0],impact['workflow_id'],target_version) if service and impact.get('workflow_id') else None
            # Never decide write reconciliation from caller-provided outcome flags.
            readonly=bool(workflow) and workflow.get('status') in {'approved','published'} and not workflow.get('execution_policy',{}).get('allow_external_writes',False)
            readonly_tools={'database_read_record','database_read_query','google_sheets_read_rows'}
            if workflow and any(t['tool_id'] not in readonly_tools for t in workflow.get('tools',[])):readonly=False
            selection=workflow.get('metadata',{}).get('ontology_selection_id') if workflow else None
            if selection:
                try:self.validate_selection(db,auth,selection)
                except ApiFailure:readonly=False
            impact['eligibility']='eligible_for_authorized_submission' if readonly else 'requires_reconciliation_or_workflow_binding'
            impact['revalidation']='validated_for_submission' if readonly else 'required'
            impact['target_workflow_version']=target_version
            self.save(db,'impacts','impact_id',scope,iid,impact)
        if body['action']=='assess':return impact
        if not readonly:fail('Replay requires reconciliation or an existing workflow binding.',409,'ONTOLOGY_REPLAY_INELIGIBLE')
        if not isinstance(body.get('inputs'),dict) or not isinstance(body.get('idempotency_key'),str) or not 1<=len(body['idempotency_key'])<=100:fail('Supply inputs and an idempotency key for existing authorised submission.')
        # Canonical service owns workflow validation, scopes, approvals and execution.
        request=dict(operation='execute_workflow',request_id=new_id('req'),idempotency_key='ontology_'+fingerprint([iid,body['idempotency_key']]),payload=dict(workflow_id=impact['workflow_id'],workflow_version=workflow['version'],inputs=body['inputs']))
        try:
            result=service.handle(request,auth)
        except Exception:
            with self.store.transaction() as db:
                impact['replay_state']='submission_outcome_unknown'
                self.save(db,'impacts','impact_id',scope,iid,impact)
                self.event(db,scope,iid,'replay_submission_unknown',request_id=request['request_id'])
            fail('Submission outcome unknown. Reconcile through the existing run service with the same retry key.',503,'ONTOLOGY_SUBMISSION_UNKNOWN')
        with self.store.transaction() as db:
            impact['replay_state']='submitted' if result.get('status',500)<400 else 'rejected'
            impact['submitted_run_id']=result.get('data',{}).get('run',{}).get('run_id')
            impact['last_submission_at']=now()
            self.save(db,'impacts','impact_id',scope,iid,impact)
            self.event(db,scope,iid,'replay_submission',status=result.get('status'),request_id=request['request_id'])
        return result

    def apply_calibration(self,auth,body):
        scope=identity(auth,True);exact(body,{'record_id','expected_revision','calibration_id','auto_accept'})
        if type(body['auto_accept']) is not bool:fail('Choose whether to request low-risk automatic acceptance.')
        with self.store.transaction() as db:
            records,_,_=self.state(db,scope);r=next((r for r in records if r['id']==body['record_id']),None)
            c=next((c for c in self.rows(db,'calibrations',scope) if c['calibration_id']==body['calibration_id']),None)
            if not r or not c:fail('Record or calibration unavailable.',404,'ONTOLOGY_NOT_FOUND')
            if r['revision']!=body['expected_revision'] or r['stale']:fail('Record needs revalidation.',409,'ONTOLOGY_STALE')
            if r['kind']!=c['kind'] or r.get('domain')!=c['domain']:fail('Calibration does not apply to this kind and domain.',409,'ONTOLOGY_UNCALIBRATED')
            if not c['eligible']:fail('Calibration lacks representative held-out precision evidence.',409,'ONTOLOGY_UNCALIBRATED')
            score=r['assessment']['heuristic_score'];bin_=c['bins'][min(4,int(score*5))] if score is not None else None
            if not bin_ or bin_['n']<c['minimum_examples']:fail('Insufficient calibration support for this score range.',409,'ONTOLOGY_UNCALIBRATED')
            if body['auto_accept']:
                high_impact=any(r['id'] in dependencies(other) for other in records) or any(r['id'] in s['record_ids'] for s in self.rows(db,'selections',scope))
                if r['properties'].get('risk')!='low' or r['kind']!='mapping' or high_impact or r['assessment']['contradictions'] or bin_['probability']<c['minimum_precision']:fail('This mapping requires expert review.',409,'ONTOLOGY_REVIEW_REQUIRED')
                by_id={x['id']:x for x in records}
                if any(by_id[dep]['status']!='approved' or by_id[dep]['stale'] for dep in dependencies(r)):fail('Mapping dependencies require expert validation.',409,'ONTOLOGY_REVIEW_REQUIRED')
                r['dependency_revisions']={dep:by_id[dep]['revision'] for dep in dependencies(r)}
                r['status']='approved';r['reviewed_by']='validated_low_risk_policy';r['reviewed_at']=now()
            r['assessment'].update(calibrated_score=bin_['probability'],calibration_id=c['calibration_id'],status='calibrated')
            r['revision']+=1;r['updated_at']=now()
            self.save(db,'records','record_id',scope,r['id'],r)
            self.event(db,scope,r['id'],'auto_accept' if body['auto_accept'] else 'calibrated_assessment',record=r,calibration_id=c['calibration_id'])
            self.invalidate(db,scope,{r['id']},'assessment_changed')
        return self.get(auth)

    def validate_selection(self,db,auth,selection_id):
        scope=identity(auth)
        row=db.execute('SELECT document FROM ontology_selections WHERE workspace=? AND owner=? AND selection_id=?',(*scope,selection_id)).fetchone()
        if not row:fail('Ontology selection unavailable.',409,'ONTOLOGY_STALE')
        manifest=json.loads(row[0]);records,_,_=self.state(db,scope);by_id={r['id']:r for r in records}
        if not manifest['valid'] or any(rid not in by_id or by_id[rid]['revision']!=rev or by_id[rid]['stale'] for rid,rev in manifest['record_revisions'].items()):fail('Ontology selection requires revalidation.',409,'ONTOLOGY_STALE')
        return manifest

    def construct_candidates(self,db,scope,refs):
        """Bounded ontology construction using definitions and sampled value evidence."""
        from difflib import SequenceMatcher
        from .data_graph_v2 import singular
        records=self.rows(db,'records',scope);existing={r['id'] for r in records}
        concepts={r['id']:r for r in records if r['kind']=='concept' and r['status']!='rejected'}
        shared=[r for r in concepts.values() if r['layer'] in {'common','domain'}]
        for source in concepts.values():
            if source['layer']!='organization':continue
            for target in shared:
                score=SequenceMatcher(None,singular(source['label']).casefold(),singular(target['label']).casefold()).ratio()
                if score<.8:continue
                rid='mapping:'+fingerprint([source['id'],target['id']])[:32]
                if rid in existing or len(existing)>=MAX_RECORDS:continue
                r=dict(id=rid,kind='mapping',layer='organization',domain=target.get('domain'),label=(source['label']+' mapping')[:160],
                    definition=('Naming suggests a mapping to '+target['label']+'. '+target['definition'])[:2000],
                    dependencies=[],source_refs=list(source['source_refs']),evidence_class='unverified_hypothesis',
                    properties=dict(source=source['id'],target=target['id'],risk='medium',method='ontology_definition_similarity_v1'))
                self.import_record(db,scope,r,refs,'definition_candidate');existing.add(rid)
        fields=[]
        for fid,ref in refs.items():
            if ref['kind']!='field':continue
            profile=refs[ref['dataset_id']]['metadata'].get('value_profiles',{}).get(fid,{})
            if profile.get('comparable',0)>=10 and profile.get('uniqueness',0)>=.9:fields.append((fid,ref,profile))
        checked=0;added=0
        for i,(left,a,pa) in enumerate(fields):
            for right,b,pb in fields[i+1:]:
                checked+=1
                if checked>20000 or added>=24 or len(existing)>=MAX_RECORDS:return
                if a['dataset_id']==b['dataset_id'] or not compatible(a['metadata'],b['metadata']):continue
                evidence=overlap(pa,pb)
                if evidence['referential_consistency'] is None or evidence['referential_consistency']<.8:continue
                source,target='source:'+a['dataset_id'],'source:'+b['dataset_id']
                if source not in concepts or target not in concepts:continue
                rid='observation:'+fingerprint(sorted([left,right]))[:32]
                if rid in existing or len(existing)>=MAX_RECORDS:continue
                r=dict(id=rid,kind='relationship',layer='organization',label='Sample key overlap',
                    definition='Bounded samples contain overlapping typed values. This does not establish a business relationship or population referential integrity.',
                    dependencies=[],source_refs=[left,right],evidence_class='statistical_finding',
                    properties=dict(source=source,target=target,predicate='sample_overlap',risk='medium',method='typed_sample_overlap_v1',field_pairs=[dict(source_field_id=left,target_field_id=right)]))
                self.import_record(db,scope,r,refs,'sample_observation');existing.add(rid);added+=1

    def metrics(self,auth,version_id=None,calibration_id=None):
        scope=identity(auth)
        with self.store.transaction(write=False) as db:
            records,_,_=self.state(db,scope)
            calibrations=self.rows(db,'calibrations',scope)
            selected=next((c for c in calibrations if c['calibration_id']==calibration_id),None) if calibration_id else (max(calibrations,key=lambda c:c['created_at']) if calibrations else None)
            if calibration_id and not selected:fail('Calibration unavailable.',404,'ONTOLOGY_NOT_FOUND')
        if version_id:
            version=self.version(auth,version_id);ids={r['id'] for r in version['records']};records=[r for r in records if r['id'] in ids]
        return dict(version_id=version_id,record_count=len(records),unresolved=sum(r['status']=='draft' or r['stale'] for r in records),drift=sum(r['stale'] for r in records),
            calibration=selected,evaluation_note='Precision and false positives use the selected held-out calibration artifact; unavailable without labels.')
