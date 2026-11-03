"""Owner-scoped, version-pinned read plans and source evidence for Phase 2."""
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
import secrets
import threading
import time
from weakref import WeakValueDictionary
from .business_ontology import identity
from .business_sources import BusinessSources, fields_for
from .business_graph import at
from .business_knowledge_model import canonical, digest, fail, convert, state_check, evaluate_rule
from .business_resolution import resolve
from .business_intent import IntentInterpreter
from .data_queries import QueryReader
from .data_write_adapter import pack, public_record, value_for
from .google_connections import now

LIMITS=dict(records_per_step=20,total_records=100,bytes=1_000_000,seconds=20,max_steps=8,max_knowledge_items=96)


def type_name(value):
    from bson import ObjectId
    if isinstance(value,ObjectId):return 'ObjectId'
    return {str:'string',int:'integer',float:'number',bool:'boolean'}.get(type(value),'unsupported')


def scalar_input(value):
    from bson import ObjectId
    return str(value) if isinstance(value,ObjectId) else value


class BusinessRetrieval:
    def __init__(self, ontology, manager, resolve_authority=None, reader=None, interpreter=None, env=None):
        self.ontology,self.store,self.manager=ontology,ontology.store,manager
        self.sources=BusinessSources(ontology,manager,resolve=resolve_authority)
        self.reader=reader or QueryReader(manager)
        self.interpreter=interpreter or IntentInterpreter(env)
        self.lock=threading.Lock()
        self.request_locks=WeakValueDictionary()
        with self.store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS business_retrieval_requests (workspace TEXT NOT NULL,owner TEXT NOT NULL,request_id TEXT NOT NULL,request_key TEXT NOT NULL,fingerprint TEXT NOT NULL,document TEXT NOT NULL,PRIMARY KEY(workspace,owner,request_id),UNIQUE(workspace,owner,request_key))')

    def latest(self,auth):
        with self.store.transaction(write=False) as db:
            row=db.execute("SELECT version_id FROM business_ontology_versions WHERE workspace=? AND owner=? ORDER BY CAST(json_extract(document,'$.revision') AS INTEGER) DESC LIMIT 1",identity(auth)).fetchone()
        if not row:fail('No saved ontology version.','BUSINESS_RETRIEVAL_KNOWLEDGE_REQUIRED',409)
        return row[0]

    def binding(self,auth,role,collection,fields):
        auth,scope=self.sources.authorize(auth)
        with self.store.transaction(write=False) as db:
            workspace=self.ontology.document(db,scope)
            cid=(workspace or {}).get('sources',{}).get(role)
            if not cid:fail('Mapped source role is not bound.','BUSINESS_SOURCE_UNAVAILABLE',409)
            workspace,secret,connection,snapshot=self.sources.bound(db,auth,cid)
        if connection['connection_status']!='connected' or connection.get('profiling_status','ready')!='ready' or not snapshot:
            fail('Current source metadata is not ready.','BUSINESS_SOURCE_UNAVAILABLE',409)
        dataset=next((d for d in snapshot['datasets'] if d['name']==collection),None)
        allowed={f['name']:f for f in fields_for(dataset)} if dataset else {}
        unavailable=sorted(set(fields)-set(allowed))
        stamp=digest([workspace['sources'],connection.get('generation',0),connection['metadata_revision'],
                      hashlib.sha256((secret or '').encode()).hexdigest(),snapshot])
        return dict(connection_id=cid,metadata_revision=connection['metadata_revision'],generation=connection.get('generation',0),
                    engine=connection['engine'],stamp=stamp,dataset=dataset,fields=allowed,unavailable=unavailable,secret=secret)

    def prepare(self,auth,snapshot,question,inputs=None,use_ai=False):
        """Metadata-only; shared with planner. Never executes or persists a source read."""
        inputs=inputs or {}
        if not snapshot.get('knowledge'):
            fail('This historical version predates Phase 1 knowledge.','BUSINESS_RETRIEVAL_KNOWLEDGE_REQUIRED',409)
        from .business_compiler import check_snapshot
        check_snapshot(snapshot)
        with self.store.transaction(write=False) as db:
            workspace=self.ontology.document(db,identity(auth))
        if not workspace or workspace['sources']!=snapshot['workspace']['sources']:
            fail('The saved version uses different source bindings.','BUSINESS_SOURCE_STALE',409)
        if inputs.get('policy_id') and not any(p['policy_id']==inputs['policy_id'] for p in snapshot['knowledge']['manifest']['policy_snapshots']):
            fail('Policy selection must name a revision pinned in this ontology version.')
        intent=self.interpreter.run(question,snapshot,inputs,use_ai)
        result=resolve(snapshot,question,inputs,intent,LIMITS['max_knowledge_items'])
        k=snapshot['knowledge']; mappings={m['id']:m for m in result['mappings']}
        identifiers=intent['identifiers']; groups={}; available=[]
        for m in result['mappings']:
            binding=self.binding(auth,m['source_role'],m['collection'],[m['field_path']])
            observed=set(binding['fields'].get(m['field_path'],{}).get('types',[]))-{'null'}
            status='field_unavailable' if binding['unavailable'] else 'type_mismatch' if not observed<=set(m['stored_datatypes']) else 'available'
            m['availability']=status;m['connection_id']=binding['connection_id'];m['metadata_revision']=binding['metadata_revision']
            if status!='available':result['missing'].append(dict(mapping_id=m['id'],reason=status));continue
            available.append(m['id']);groups.setdefault((m['source_role'],m['collection']),[]).append(m['id'])
        # Build only exact anchored or explicitly bounded root reads. No implicit joins.
        steps=[]; planned={};unplanned=dict(groups)
        serial_maps={mid:m for mid,m in mappings.items() if mid in available and mid in ('mapping:ticket_serial','mapping:invoice_serial','mapping:qa_serial')}
        if any(f['mapping_id'] not in available for f in intent['filters']):
            result['ready']=False
            result['missing'].append(dict(reason='filter_mapping_unavailable'))
        for key,mids in list(unplanned.items()):
            filters=[]
            if 'complaint_id' in identifiers and 'mapping:ticket_id' in mids:
                filters.append(dict(field_path=mappings['mapping:ticket_id']['field_path'],operator='eq',value=identifiers['complaint_id'],origin='explicit_identifier'))
            if 'serial' in identifiers:
                sm=next((m for m in serial_maps.values() if (m['source_role'],m['collection'])==key),None)
                if sm:filters.append(dict(field_path=sm['field_path'],operator='eq',value=identifiers['serial'],origin='submitted_serial_candidate'))
            anchored=bool(filters)
            for f in intent['filters']:
                m=mappings.get(f['mapping_id'])
                if m and f['mode']=='exact' and (m['source_role'],m['collection'])==key:
                    filters.append(dict(field_path=m['field_path'],operator='eq',value=f['value'],origin='supported_status_filter'))
            bounded_search=any(f['mode']!='exact' and f['mapping_id'] in mids for f in intent['filters'])
            if anchored or (not identifiers and (filters or bounded_search)):
                step=dict(id='read_'+str(len(steps)+1),source_role=key[0],collection=key[1],mapping_ids=mids,
                          filters=filters,reference=None,bounded_scan=bounded_search and not filters)
                steps.append(step);planned[key]=step;del unplanned[key]
        # Exact native-reference traversal in either direction. A conceptual edge alone is insufficient.
        for _ in range(LIMITS['max_steps']):
            progress=False
            for key,mids in list(unplanned.items()):
                for rule in k['identity_rules']:
                    if rule['kind']!='direct_reference':continue
                    a,b=rule['source'],rule['target'];ak=(a['source_role'],a['collection']);bk=(b['source_role'],b['collection'])
                    if key==ak and bk in planned:local,remote=a,b
                    elif key==bk and ak in planned:local,remote=b,a
                    else:continue
                    parent=planned[(remote['source_role'],remote['collection'])]
                    parent.setdefault('reference_fields',[]).append(remote['field_path'])
                    local_filters=[dict(field_path=mappings[f['mapping_id']]['field_path'],operator='eq',value=f['value'],origin='supported_status_filter') for f in intent['filters'] if f['mode']=='exact' and f['mapping_id'] in mids]
                    step=dict(id='read_'+str(len(steps)+1),source_role=key[0],collection=key[1],mapping_ids=mids,filters=local_filters,bounded_scan=False,
                              reference=dict(binding_id=rule['id'],parent_step=parent['id'],parent_field=remote['field_path'],field_path=local['field_path'],classification='direct_reference'))
                    steps.append(step);planned[key]=step;del unplanned[key];progress=True;break
            if not progress:break
        for key,mids in unplanned.items():result['missing'].append(dict(mapping_ids=mids,reason='no_supported_anchored_path'))
        for step in steps:
            fields={mappings[mid]['field_path'] for mid in step['mapping_ids']} | {'_id'} | set(step.get('reference_fields',[]))
            if step['reference']:fields.add(step['reference']['field_path'])
            binding=self.binding(auth,step['source_role'],step['collection'],fields)
            if binding['unavailable']:result['ready']=False;result['missing'].append(dict(step_id=step['id'],reason='reference_or_projection_unavailable',fields=binding['unavailable']))
            step.update(fields=sorted(fields),dataset_id=(binding['dataset'] or {}).get('dataset_id'),connection_id=binding['connection_id'],metadata_revision=binding['metadata_revision'],generation=binding['generation'],source_stamp=binding['stamp'],
                        limit=LIMITS['records_per_step'],conversions=[dict(mapping_id=mid,conversion=mappings[mid]['conversion']) for mid in step['mapping_ids']])
            for f in step['filters']:
                field=binding['fields'].get(f['field_path'])
                if not field:continue
                try:value_for(field,f['value'])
                except Exception:result['ready']=False;result['missing'].append(dict(step_id=step['id'],reason='invalid_typed_identifier_or_filter'))
        if not steps:result['ready']=False
        if len(steps)>LIMITS['max_steps']:result['ready']=False;result['missing'].append(dict(reason='step_limit'))
        result.update(steps=steps,limits=deepcopy(LIMITS),inputs=deepcopy(inputs),question=question,
                      identity_rules=[deepcopy(r) for r in k['identity_rules'] if r['id'] in {s['reference']['binding_id'] for s in steps if s['reference']} or r['kind']=='candidate' and all((r[side]['source_role'],r[side]['collection']) in planned for side in ('source','target'))],
                      physical_engine_identity='unresolved',read_only=True,company_reads=0)
        if len(canonical(result).encode())>150_000:result['ready']=False;result['missing'].append(dict(reason='knowledge_byte_limit'))
        return result

    def preview(self,auth,body):
        auth,scope=self.sources.authorize(auth)
        allowed={'question','version_id','request_key','inputs','use_ai'}
        if not isinstance(body,dict) or set(body)-allowed or not {'question','request_key'}<=set(body):fail('Provide question and request_key; client plans are not accepted.')
        if not isinstance(body['request_key'],str) or not 8<=len(body['request_key'])<=128:fail('Invalid request key.')
        if type(body.get('use_ai',False)) is not bool:fail('use_ai must be boolean.')
        if 'version_id' in body and (not isinstance(body['version_id'],str) or not 1<=len(body['version_id'])<=160):fail('Invalid ontology version ID.')
        inputs=body.get('inputs',{})
        if not isinstance(inputs,dict) or set(inputs)-{'serial','complaint_id','assessment_date','policy_id'}:fail('Unsupported explicit inputs.')
        if any(not isinstance(v,str) or len(v)>160 for v in inputs.values()):fail('Explicit inputs must be bounded strings.')
        if 'assessment_date' in inputs and convert(inputs['assessment_date'],'iso_date','date')['state']!='value':fail('Assessment date must be an ISO date.')
        fingerprint=digest(body)
        with self.store.transaction(write=False) as db:
            old=db.execute('SELECT fingerprint,document FROM business_retrieval_requests WHERE workspace=? AND owner=? AND request_key=?',(*scope,body['request_key'])).fetchone()
        if old:
            if old[0]!=fingerprint:fail('Request key belongs to another request.','BUSINESS_RETRIEVAL_CONFLICT',409)
            return json.loads(old[1])
        version_id=body.get('version_id') or self.latest(auth)
        snapshot=self.ontology.version(auth,version_id)
        result=self.prepare(auth,snapshot,body['question'],inputs,body.get('use_ai',False))
        result.update(request_id='retrieval_'+secrets.token_hex(16),created_at=now(),created_epoch=time.time())
        result['plan_sha256']=digest(result)
        self.sources.authorize(auth)
        with self.store.transaction() as db:
            # Serialize concurrent identical requests with the database unique key.
            db.execute('INSERT INTO business_retrieval_requests VALUES (?,?,?,?,?,?) ON CONFLICT(workspace,owner,request_key) DO NOTHING',(*scope,result['request_id'],body['request_key'],fingerprint,canonical(result)))
            row=db.execute('SELECT fingerprint,document FROM business_retrieval_requests WHERE workspace=? AND owner=? AND request_key=?',(*scope,body['request_key'])).fetchone()
        if row[0]!=fingerprint:fail('Request key conflict.','BUSINESS_RETRIEVAL_CONFLICT',409)
        return json.loads(row[1])

    def inspect(self,auth,request_id):
        auth,scope=self.sources.authorize(auth)
        with self.store.transaction(write=False) as db:
            row=db.execute('SELECT document FROM business_retrieval_requests WHERE workspace=? AND owner=? AND request_id=?',(*scope,request_id)).fetchone()
        if not row:fail('Retrieval request not found.','BUSINESS_RETRIEVAL_NOT_FOUND',404)
        return json.loads(row[0])

    def checked_binding(self,auth,step):
        binding=self.binding(auth,step['source_role'],step['collection'],step['fields'])
        if binding['stamp']!=step['source_stamp'] or binding['unavailable'] or binding['connection_id']!=step['connection_id']:
            fail('Source metadata, binding or access changed; make a new preview.','BUSINESS_SOURCE_STALE',409)
        return binding

    def execute(self,auth,request_id,body):
        if body!={}:fail('Execute accepts an empty object and a saved request ID only.')
        # Single-flight per scoped request; independent investigation reads may
        # execute concurrently without serializing every owner's source access.
        scope=identity(auth)
        with self.lock:
            key=(*scope,request_id)
            lock=self.request_locks.get(key)
            if lock is None:
                lock=threading.Lock();self.request_locks[key]=lock
        with lock:return self._execute(auth,request_id)

    def _execute(self,auth,request_id):
        plan=self.inspect(auth,request_id)
        original={k:v for k,v in plan.items() if k not in ('plan_sha256','evidence')}
        if digest(original)!=plan['plan_sha256']:fail('Saved retrieval plan hash mismatch.')
        snapshot=self.ontology.version(auth,plan['version_id'])
        if snapshot.get('knowledge_sha256')!=plan['knowledge_sha256'] or digest(snapshot['knowledge'])!=plan['knowledge_sha256']:fail('Pinned knowledge is inconsistent.')
        if plan['limits']!=LIMITS or len(plan['steps'])>LIMITS['max_steps']:fail('Invalid saved resource limits.')
        self.validate_plan(snapshot,plan)
        for step in plan['steps']:self.checked_binding(auth,step)
        if 'evidence' in plan:return plan['evidence']
        if not plan['ready']:fail('Resolve unsupported intent, ambiguity or plan gaps before execution.','BUSINESS_RETRIEVAL_NOT_READY',409)
        if time.time()-plan['created_epoch']>3600:fail('Preview expired; create a new request.','BUSINESS_RETRIEVAL_EXPIRED',409)
        self.manager.configured();deadline=time.monotonic()+LIMITS['seconds']
        raw_by_step={};native_records={};records=[];outcomes=[];issues=[];edges=[];byte_count=0;post_filters=plan['intent']['filters'];maps={m['id']:m for m in plan['mappings']}
        for step in plan['steps']:
            if time.monotonic()>=deadline:fail('Retrieval deadline exceeded.','BUSINESS_RETRIEVAL_TIMEOUT',504)
            binding=self.checked_binding(auth,step)
            if not binding['secret']:fail('Source credentials unavailable.','BUSINESS_SOURCE_UNAVAILABLE',409)
            config=json.loads(self.manager.cipher.decrypt(binding['secret'].encode()))
            fields=[binding['fields'][name] for name in step['fields']]
            filters={f['field_path']:f['value'] for f in step['filters']}
            ref=step['reference'];domains=[None];unresolved=[]
            if ref:
                vals=[at(r,ref['parent_field']) for r in raw_by_step.get(ref['parent_step'],[])]
                domains=[];seen=set();target_types=set(binding['fields'][ref['field_path']]['types'])-{'null'}
                for value in vals:
                    if value is None:unresolved.append('missing_reference');continue
                    kind=type_name(value)
                    if kind not in target_types:unresolved.append('native_reference_type_mismatch');continue
                    signature=(kind,str(value))
                    if signature not in seen:seen.add(signature);domains.append(value)
            raw=[];truncated=False
            for native in domains:
                remaining=step['limit']+1-len(raw)
                if remaining<=0:truncated=True;break
                if time.monotonic()>=deadline:fail('Retrieval deadline exceeded.','BUSINESS_RETRIEVAL_TIMEOUT',504)
                current=dict(filters)
                if ref:current[ref['field_path']]=scalar_input(native)
                batch=self.reader.objects(config,binding['dataset'],fields,['_id'],current,0,remaining,deadline)
                if len(batch)>remaining:fail('Source reader exceeded its bound.')
                # Guard native reference semantics after driver query conversion.
                if ref:batch=[r for r in batch if type(at(r,ref['field_path'])) is type(native) and at(r,ref['field_path'])==native]
                raw.extend(batch)
                if len(raw)>step['limit']:truncated=True;break
            if time.monotonic()>deadline:fail('Retrieval deadline exceeded.','BUSINESS_RETRIEVAL_TIMEOUT',504)
            self.checked_binding(auth,step)
            raw=raw[:step['limit']];accepted=[]
            for row in raw:
                values={};keep=True
                for mid in step['mapping_ids']:
                    m=maps[mid];v=at(row,m['field_path'])
                    if binding['engine']=='mongodb' and m['conversion']=='iso_datetime':
                        from datetime import datetime, timezone
                        if isinstance(v,datetime) and v.tzinfo is None:v=v.replace(tzinfo=timezone.utc)
                    converted=convert(v,m['conversion'],m['business_datatype'])
                    if converted['state']=='reference_unresolved':converted['value']=public_record(pack({'value':v},binding['engine']))['value']
                    values[mid]=converted
                    if converted['state']=='conversion_issue':issues.append(dict(step_id=step['id'],mapping_id=mid,record_reference=public_record(pack({'_id':at(row,'_id')},binding['engine'])),state='invalid_source_value'))
                    for f in post_filters:
                        if f['mapping_id']!=mid or f['mode']=='exact':continue
                        if converted['state']!='value':keep=False;continue
                        if f['operator']=='contains':keep=keep and f['value'].lower() in str(converted['value']).lower()
                        elif f['operator'] in ('gt','lt'):
                            a,b=Decimal(str(converted['value'])),Decimal(f['value']);keep=keep and (a>b if f['operator']=='gt' else a<b)
                        else:fail('Unsupported saved filter operator.')
                if not keep:continue
                projected={f:at(row,f) for f in step['fields']}
                native_record=pack(projected,binding['engine']);public=public_record(native_record)
                rid=digest([step['connection_id'],step['collection'],native_record.get('_id')])
                state_results=[dict(state_model_id=s['id'],result=state_check(s,at(row,maps[s['mapping_id']]['field_path']) if isinstance(at(row,maps[s['mapping_id']]['field_path']),str) else None)) for s in plan['state_models'] if s.get('mapping_id') in step['mapping_ids']]
                record=dict(record_id=rid,step_id=step['id'],source_role=step['source_role'],connection_id=step['connection_id'],collection=step['collection'],metadata_revision=step['metadata_revision'],
                            source_reference=dict(field='_id',native_value=native_record.get('_id')),fields=public,values=values,states=state_results,read_at=now(),qualification='Reported source values; not independently confirmed findings.')
                byte_count+=len(canonical(record).encode())
                if byte_count>LIMITS['bytes'] or len(records)>=LIMITS['total_records']:fail('Evidence exceeds total resource limits.','BUSINESS_RETRIEVAL_LIMIT',422)
                records.append(record);accepted.append(row)
                native_records.setdefault(step['id'],[]).append((row,rid))
                if ref:
                    for parent,parent_id in native_records.get(ref['parent_step'],[]):
                        a,b=at(row,ref['field_path']),at(parent,ref['parent_field'])
                        if a is not None and type(a) is type(b) and a==b:
                            edges.append(dict(record_id=rid,parent_record_id=parent_id,parent_step=ref['parent_step'],binding_id=ref['binding_id'],classification='direct_reference',physical_merge=False))
            raw_by_step[step['id']]=accepted
            outcomes.append(dict(step_id=step['id'],records=len(accepted),examined=len(raw),truncated=truncated,
                                 bounded_scan=step['bounded_scan'],unresolved=sorted(set(unresolved)),empty=not accepted))
        # Saved cross-source candidate bindings establish associations only, never joins or merges.
        candidates=[]
        for rule in plan['identity_rules']:
            if rule['kind']!='candidate':continue
            a,b=rule['source'],rule['target']
            left=[r for r in records if (r['source_role'],r['collection'])==(a['source_role'],a['collection'])]
            right=[r for r in records if (r['source_role'],r['collection'])==(b['source_role'],b['collection'])]
            for l in left:
                for r in right:
                    x,y=l['fields'].get(a['field_path']),r['fields'].get(b['field_path'])
                    if isinstance(x,str) and x and x==y:candidates.append(dict(binding_id=rule['id'],left=l['record_id'],right=r['record_id'],classification='candidate',physical_merge=False,qualification='Equal reported serial only; company/model context and physical identity remain unverified.'))
        self.sources.authorize(auth)
        for step in plan['steps']:self.checked_binding(auth,step)
        missing=deepcopy(plan['missing'])
        findings=[]
        for record in records:
            for mid,value in record['values'].items():
                findings.append(dict(state='fact_found' if value['state']=='value' else 'invalid_source_value' if value['state']=='conversion_issue' else 'fact_missing',mapping_id=mid,record_id=record['record_id'],value=value.get('value')))
        for provider in plan['fact_providers']:
            if provider['provider']=='source_mapping' and not any(f['state']=='fact_found' and f['mapping_id'] in provider['mapping_ids'] for f in findings):missing.append(dict(fact=provider['fact'],reason='no_valid_source_evidence'))
            if provider['provider']=='derived_check':missing.append(dict(fact=provider['fact'],reason='derived_fact_not_established'))
        rule_results=[]
        for record in records:
            facts={}
            if record['collection']=='tickets':
                hours=record['values'].get('mapping:complaint_hours',{})
                if hours.get('state')=='value':facts['operating_hours']=hours['value']
                if plan['inputs'].get('assessment_date'):facts['assessment_date']=plan['inputs']['assessment_date']
            if record['collection']=='jointinspectionreports':
                status=record['values'].get('mapping:inspection_status',{})
                if status.get('state')=='value':facts['report_status']=status['value']
            for rule in plan['rules']:
                target={'warranty:assessment_readiness':'tickets','inspection:report_readiness':'jointinspectionreports','replacement:readiness':'enginereplacements'}.get(rule['id'])
                if record['collection']==target:
                    rule_results.append(dict(record_id=record['record_id'],result=evaluate_rule(rule,{k:v for k,v in facts.items() if k in rule['fact_types']})))
        incomplete=any(o['truncated'] or o['unresolved'] for o in outcomes) or bool(missing) or bool(issues) or bool(candidates)
        population_limited=any(f['mode']!='exact' for f in post_filters)
        evidence=dict(retrieval_version=plan['retrieval_version'],request_id=request_id,version_id=plan['version_id'],knowledge_sha256=plan['knowledge_sha256'],plan_sha256=plan['plan_sha256'],
                      intent=plan['intent'],selected_concepts=plan['dependency_resolution']['concept_ids'],selected_mappings=plan['mappings'],dependencies=plan['dependency_resolution'],rules=plan['rules'],
                      fact_providers=plan['fact_providers'],policy_revisions=[{k:p[k] for k in ('policy_id','policy_key','revision','sha256')} for p in plan['policies']],temporal_models=plan['temporal_models'],identity_rules=plan['identity_rules'],
                      executed_steps=outcomes,records=records,findings=findings,missing=missing,ambiguous_associations=candidates,reference_edges=edges,conversion_issues=issues,
                      physical_engine_identity='unresolved',business_conclusions=[],rule_results=rule_results,limits=deepcopy(LIMITS),
                      completeness='incomplete' if incomplete else 'bounded_search' if population_limited else 'complete_for_scoped_reads',
                      record_reads_complete=not any(o['truncated'] or o['unresolved'] for o in outcomes) and not population_limited,
                      population_scope='Source records matching the saved read filters; no physical-engine cohort or business decision is inferred.',
                      population_complete=False if incomplete or population_limited else True,read_only=True,company_writes=0,model_calls=plan['intent']['model_calls'])
        if len(canonical(evidence).encode())>LIMITS['bytes']:fail('Complete evidence package exceeds the byte limit.','BUSINESS_RETRIEVAL_LIMIT',422)
        if time.monotonic()>deadline:fail('Evidence preparation exceeded the deadline.','BUSINESS_RETRIEVAL_TIMEOUT',504)
        plan['evidence']=evidence
        with self.store.transaction() as db:
            # Recheck current owner authority at commit; no company mutation.
            self.sources.authorize(auth)
            db.execute('UPDATE business_retrieval_requests SET document=? WHERE workspace=? AND owner=? AND request_id=?',(canonical(plan),*identity(auth),request_id))
        return evidence

    @staticmethod
    def validate_plan(snapshot,plan):
        """Verify executable grammar and saved mapping/reference authority again."""
        maps={m['id']:m for m in snapshot['knowledge']['source_mappings']}
        identities={r['id']:r for r in snapshot['knowledge']['identity_rules']}
        for m in plan['mappings']:
            saved=maps.get(m['id'])
            if not saved or any(m.get(k)!=v for k,v in saved.items()) or m['version_id']!=snapshot['version_id']:
                fail('Saved plan mapping differs from pinned knowledge.')
        for f in plan['intent']['filters']:
            if f['mapping_id'] not in maps or (f['operator'],f['mode']) not in {('eq','exact'),('contains','bounded_post_conversion'),('gt','bounded_post_conversion'),('lt','bounded_post_conversion')}:
                fail('Unsupported typed filter.')
        seen={}
        for step in plan['steps']:
            if step['limit']!=LIMITS['records_per_step'] or step['id'] in seen:fail('Invalid read step limit or identity.')
            reference_fields={s['reference']['parent_field'] for s in plan['steps'] if s['reference'] and s['reference']['parent_step']==step['id']}
            if set(step.get('reference_fields',[]))!=reference_fields:fail('Unsupported parent projection.')
            expected={'_id'} | reference_fields
            for mid in step['mapping_ids']:
                m=maps.get(mid)
                if not m or (m['source_role'],m['collection'])!=(step['source_role'],step['collection']):fail('Read step uses an unsupported mapping.')
                expected.add(m['field_path'])
            ref=step['reference']
            if ref:
                rule=identities.get(ref['binding_id']);parent=seen.get(ref['parent_step'])
                if not rule or rule['kind']!='direct_reference' or not parent:fail('Unsupported reference traversal.')
                a=dict(source_role=step['source_role'],collection=step['collection'],field_path=ref['field_path'])
                b=dict(source_role=parent['source_role'],collection=parent['collection'],field_path=ref['parent_field'])
                if not ((a==rule['source'] and b==rule['target']) or (b==rule['source'] and a==rule['target'])):fail('Reference does not match the saved binding.')
                expected.add(ref['field_path'])
            if set(step['fields'])!=expected:fail('Unsupported projection.')
            if any(f['operator']!='eq' or f['field_path'] not in expected for f in step['filters']):fail('Unsupported read filter.')
            if not ref and not step['filters'] and not step['bounded_scan']:fail('Unanchored read is unsupported.')
            seen[step['id']]=step


def planner_context(store,auth,question,manager):
    """Read-only entry point; never initializes tables or persists previews."""
    with store.transaction(write=False) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='business_ontology_versions'").fetchone():
            return dict(state='not_configured'),[]
    from .business_ontology import BusinessOntology
    ontology=object.__new__(BusinessOntology)
    ontology.store=store
    service=object.__new__(BusinessRetrieval)
    service.ontology,service.store,service.manager=ontology,store,manager
    # BusinessSources construction initializes evidence tables; planning is read-only.
    service.sources=object.__new__(BusinessSources)
    service.sources.ontology,service.sources.manager,service.sources.store,service.sources.resolve=ontology,manager,store,None
    service.interpreter=IntentInterpreter()
    version=ontology.version(auth,service.latest(auth))
    if not version.get('knowledge'):return dict(state='phase1_knowledge_required'),[]
    p=service.prepare(auth,version,question)
    datasets=list(dict.fromkeys(s['dataset_id'] for s in p['steps'] if s.get('dataset_id')))
    return dict(state='resolved' if p['ready'] else 'incomplete',version_id=p['version_id'],knowledge_sha256=p['knowledge_sha256'],intent=p['intent'],
                concepts=p['concepts'],relationships=p['relationships'],dependencies=p['dependency_resolution'],fact_providers=p['fact_providers'],
                mappings=p['mappings'],rules=p['rules'],missing=p['missing'],proposed_reads=p['steps'],company_reads=0),datasets
