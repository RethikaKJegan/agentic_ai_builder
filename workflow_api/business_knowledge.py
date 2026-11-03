"""Explicit versioned knowledge imports and backend-only inspection.

Authoring files are read only on import. Inspection/diagnostics use saved snapshots.
No model requests, company reads/writes, workflow submission or worker startup.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
import secrets
from registry.safety import reject_secrets
from .business_ontology import identity
from .business_documents import source_stamp
from .business_knowledge_model import SCHEMA, canonical, digest, fail, validate_knowledge, convert, evaluate_rule, state_check, associate

ROOT=Path(__file__).resolve().parents[1]
AUTHORING=ROOT/'ontology/business-reference'


def reference_sources(bundle):
    """Existing supplied model excerpts, preserving their original file hashes."""
    basis=json.loads((AUTHORING/'identity-basis.json').read_text())
    text='Supplied application model excerpts; not deployed-index verification.\n'+ '\n'.join(s['path']+' ['+s['sha256']+']\n'+'\n'.join(s['quotes']) for s in basis['sources'])
    source=dict(source_id='phase1_identity_basis',title='Existing typed identity reference excerpts',kind='application_code',module_ids=['organization','engines','complaints','warranty','quality'],text=text,sha256=sha256(text.encode()).hexdigest(),origin='existing_identity_basis')
    contract=json.loads((AUTHORING/'retrieval-contract.json').read_text())
    return deepcopy(bundle['documents'])+[source,contract]


def load_package():
    pack=json.loads((AUTHORING/'knowledge-pack.json').read_text())
    rules=json.loads((AUTHORING/'configured-rules.json').read_text())
    pack['knowledge']['structured_rules']=rules['rules']
    pack['configuration_revision']=rules['revision']
    bundle=json.loads((AUTHORING/'simpson-evidence.json').read_text())
    if digest(bundle)!=pack['evidence_bundle_sha256']:fail('The source evidence bundle changed; update the knowledge package explicitly.')
    pack['sources']=reference_sources(bundle)
    pack['source_catalog']=json.loads((AUTHORING/'source-mappings.json').read_text())
    # Auxiliary projections are pinned with the package, outside the legacy
    # saved-graph inventory and without exposing unrelated user fields.
    pack['source_catalog']['items'].extend(json.loads((AUTHORING/'retrieval-mappings.json').read_text())['items'])
    pack['identity_basis']=json.loads((AUTHORING/'identity-basis.json').read_text())
    return pack


def metadata_coverage(db,scope,workspace,mappings,identities):
    """Only saved metadata is read; missing sampled fields stay unavailable."""
    roles={}
    for role,cid in workspace['sources'].items():
        row=db.execute('SELECT document FROM data_source_connections WHERE connection_id=? AND workspace=? AND owner=?',(cid,*scope)).fetchone()
        if not row:fail('A bound source is no longer owned.','BUSINESS_SOURCE_UNAVAILABLE',409)
        connection=json.loads(row[0])
        if connection['connection_status']!='connected':fail('A bound source is disconnected.','BUSINESS_SOURCE_UNAVAILABLE',409)
        row=db.execute('SELECT document FROM data_source_snapshots WHERE connection_id=? AND revision=?',(cid,connection['metadata_revision'])).fetchone()
        roles[role]=json.loads(row[0]).get('datasets',[]) if row else []
    fields=[dict(id=m['id'],source_role=m['source_role'],collection=m['collection'],field_path=m['field_path'],stored_datatypes=m['stored_datatypes']) for m in mappings]
    for i in identities:
        for side in ('source','target'):
            if i[side]:fields.append(dict(id=i['id']+':'+side,**i[side],stored_datatypes=[]))
    result=[]
    for m in fields:
        datasets=roles.get(m['source_role'],[]);dataset=next((d for d in datasets if d['name']==m['collection']),None)
        field=next((f for f in (dataset or {}).get('fields',[]) if f['name']==m['field_path']),None)
        observed=set((field or {}).get('types',[]))-{'null'}
        status='collection_unavailable' if dataset is None else 'field_unavailable' if field is None or not observed else 'type_mismatch' if m['stored_datatypes'] and not observed<=set(m['stored_datatypes']) else 'observed_in_metadata'
        result.append(dict(id=m['id'],source_role=m['source_role'],collection=m['collection'],field_path=m['field_path'],status=status,observed_types=sorted(observed),metadata_only=True))
    return result


def apply_package(previous, package, coverage, policy_snapshots, source_stamps=None):
    """Pure construction; persistence and authority are handled by the service."""
    allowed={'package_id','revision','schema_version','evidence_bundle_sha256','configuration_revision','sources','source_catalog','identity_basis','new_concepts','concept_changes','relationships','knowledge'}
    if not isinstance(package,dict) or set(package)!=allowed or package['schema_version']!=SCHEMA:fail('Invalid knowledge-package envelope.')
    result=deepcopy(previous)
    sources={s['source_id']:s for s in result.get('sources',[])}
    for s in package['sources']:
        if sha256(s['text'].encode()).hexdigest()!=s['sha256']:fail('Knowledge source hash mismatch.')
        if s['source_id'] in sources and sources[s['source_id']]!=s:fail('An existing evidence source cannot be replaced.')
        sources[s['source_id']]=deepcopy(s)
    result['sources']=list(sources.values())
    protected={name:set(previous.get('knowledge',{}).get('manifest',{}).get('protected',{}).get(name,[])) for name in ('concepts','relationships','rules')}
    concepts={c['id']:c for c in result['concepts']}
    for c in package['new_concepts']:
        if c['id'] in concepts:
            # A previous import may already have added attributes to this class.
            # Preserve those enrichments while rejecting unrelated ID reuse.
            if {k:v for k,v in concepts[c['id']].items() if k!='properties'}!={k:v for k,v in c.items() if k!='properties'}:
                fail('A new-concept ID already has a different definition.')
            existing_properties={p['name']:p for p in concepts[c['id']]['properties']}
            if any(existing_properties.get(p['name'])!=p for p in c['properties']):fail('A new-concept property conflicts with saved knowledge.')
        else:result['concepts'].append(deepcopy(c));concepts[c['id']]=result['concepts'][-1]
        protected['concepts'].add(c['id'])
    for change in package['concept_changes']:
        if not isinstance(change,dict) or set(change)-{'id','parent_id','layer','definition','properties','optional','property_descriptions'} or 'id' not in change:fail('Unsupported concept update.')
        c=concepts.get(change['id'])
        if c is None and change.get('optional') is True:continue
        if c is None:fail('The knowledge package needs an existing concept: '+change['id'])
        for name in ('parent_id','layer','definition'):
            if name in change:c[name]=deepcopy(change[name])
        props={p['name']:p for p in c['properties']}
        for p in change.get('properties',[]):
            if p['name'] in props:
                if props[p['name']]['datatype']!=p['datatype']:fail('Attribute datatype conflicts with an existing definition.')
            else:c['properties'].append(deepcopy(p));props[p['name']]=c['properties'][-1]
        for name,description in change.get('property_descriptions',{}).items():
            if not isinstance(description,str) or not description.strip():fail('Property descriptions must be nonempty strings.')
            if name in props:props[name]['description']=description
        protected['concepts'].add(c['id'])
    rels={r['id']:r for r in result['relationships']}
    for r in package['relationships']:
        if r['id'] in rels and rels[r['id']]!=r:fail('A relationship ID already has a different definition.')
        if r['id'] not in rels:result['relationships'].append(deepcopy(r))
        protected['relationships'].add(r['id'])
    knowledge=deepcopy(package['knowledge'])
    protected['concepts'].update(d['concept_id'] for d in knowledge['concept_details'])
    # Bind mapping catalogue fields to the existing authoritative allowlist.
    catalog={(m['role'],m['collection']):set(m['fields']) for m in package['source_catalog']['items']}
    for m in knowledge['source_mappings']:
        if m['field_path'] not in catalog.get((m['source_role'],m['collection']),set()):fail('A mapping field is outside the source catalogue: '+m['id'])
    for i in knowledge['identity_rules']:
        for side in ('source','target'):
            b=i[side]
            if b and b['field_path'] not in catalog.get((b['source_role'],b['collection']),set()):fail('Identity binding is outside the source catalogue.')
    policies=deepcopy(policy_snapshots)
    knowledge['manifest']=dict(package_id=package['package_id'],package_revision=package['revision'],configuration_revision=package['configuration_revision'],package_sha256=digest(package),base_version_id=previous['version_id'],source_catalog_sha256=digest(package['source_catalog']),identity_basis_sha256=digest(package['identity_basis']),source_stamps=deepcopy(source_stamps or {}),policy_refs=[{f:p[f] for f in ('policy_id','policy_key','revision','sha256')} for p in policies],policy_snapshots=policies,source_status=coverage,protected={n:sorted(v) for n,v in protected.items()})
    result['knowledge']=knowledge;result['knowledge_sha256']=digest(knowledge)
    result['schema_version']='simpson-business-snapshot-v2'
    from .business_compiler import check_snapshot
    check_snapshot(result)
    return result


def preserve_knowledge(previous, generated):
    """Regeneration may add knowledge but cannot overwrite protected definitions."""
    if 'knowledge' not in previous:return
    for group,ids in previous['knowledge']['manifest']['protected'].items():
        old={x['id']:x for x in previous[group]};new={x['id']:x for x in generated[group]}
        from .business_extraction import OUTPUT_SCHEMA
        fields=set(OUTPUT_SCHEMA['properties'][group]['items']['properties'])|{'module_id','status'}|({'executable'} if group=='rules' else set())
        for rid in ids:
            if rid not in new or {k:v for k,v in new[rid].items() if k in fields}!={k:v for k,v in old[rid].items() if k in fields}:
                fail('Regeneration conflicts with protected knowledge: '+rid,'BUSINESS_KNOWLEDGE_REGENERATION_CONFLICT',409)
            new[rid].update(deepcopy(old[rid]))
    generated['knowledge']=deepcopy(previous['knowledge'])
    generated['knowledge_sha256']=previous['knowledge_sha256']
    generated['schema_version']=previous['schema_version']
    validate_knowledge(generated)


class BusinessKnowledge:
    def __init__(self,ontology,resolve=None):
        self.ontology=ontology;self.store=ontology.store;self.resolve=resolve

    def authority(self,auth,write=False):
        scope=identity(auth,write)
        if self.resolve:
            current=self.resolve(*scope)
            if not current or current.get('subject')!=auth['subject']:fail('Current knowledge authority is unavailable.','OPERATION_NOT_AUTHORIZED',403)
            identity(current,write)
        return scope

    def import_package(self,auth,body,package=None):
        scope=self.authority(auth,True)
        if not isinstance(body,dict) or set(body)!={'expected_revision','request_key'} or type(body['expected_revision']) is not int or body['expected_revision']<1 or not isinstance(body['request_key'],str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,100}',body['request_key']):fail('Provide expected_revision and request_key.')
        pack=deepcopy(package) if package is not None else load_package()
        reject_secrets(pack)
        if len(canonical(pack))>1500000:fail('Knowledge package exceeds its size limit.')
        package_hash=digest(pack);fingerprint=digest([body['expected_revision'],package_hash])
        with self.store.transaction() as db:
            # Existing immutable events form the import receipt; no new state store.
            event_id='knowledge_'+sha256(body['request_key'].encode()).hexdigest()
            receipt=db.execute('SELECT document FROM business_ontology_events WHERE workspace=? AND owner=? AND event_id=?',(*scope,event_id)).fetchone()
            if receipt:
                event=json.loads(receipt[0])
                if event['fingerprint']!=fingerprint:fail('Request key was used for different knowledge.','IDEMPOTENCY_KEY_REUSED',409)
                return dict(version_id=event['version_id'],revision=event['revision'],package_sha256=package_hash,idempotent=True)
            workspace=self.ontology.document(db,scope)
            if not workspace:fail('Initialize the existing business foundation first.','BUSINESS_FOUNDATION_REQUIRED',409)
            if workspace['revision']!=body['expected_revision']:fail('Knowledge revision changed.','BUSINESS_REVISION_CONFLICT',409)
            exists=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='business_ontology_jobs'").fetchone()
            if exists and db.execute("SELECT 1 FROM business_ontology_jobs WHERE workspace=? AND owner=? AND state IN ('queued','running')",scope).fetchone():fail('Wait for active generation to finish.','BUSINESS_GENERATION_ACTIVE',409)
            stamp=source_stamp(self.ontology,db,scope,workspace)
            rows=db.execute('SELECT document FROM business_ontology_versions WHERE workspace=? AND owner=?',scope).fetchall()
            previous=max((json.loads(r[0]) for r in rows),key=lambda x:x['revision'])
            coverage=metadata_coverage(db,scope,workspace,pack['knowledge']['source_mappings'],pack['knowledge']['identity_rules'])
            policy_snapshots=[]
            if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='business_policy_heads'").fetchone():
                policy_snapshots=[json.loads(r[0]) for r in db.execute('SELECT v.document FROM business_policy_versions v JOIN business_policy_heads h ON v.workspace=h.workspace AND v.owner=h.owner AND v.policy_key=h.policy_key AND v.revision=h.revision WHERE v.workspace=? AND v.owner=? ORDER BY v.policy_key',scope)]
            previous_manifest=previous.get('knowledge',{}).get('manifest',{})
            same_package=previous_manifest.get('package_sha256')==package_hash
            if same_package and previous_manifest['policy_snapshots']==policy_snapshots and previous_manifest['source_stamps']==stamp:
                db.execute('INSERT INTO business_ontology_events VALUES (?,?,?,?)',(*scope,event_id,json.dumps(dict(action='knowledge_import_noop',fingerprint=fingerprint,version_id=previous['version_id'],revision=previous['revision']))))
                return dict(version_id=previous['version_id'],revision=previous['revision'],package_sha256=package_hash,idempotent=True)
            if previous_manifest and not same_package and (pack['revision'],pack['configuration_revision']) <= (previous_manifest['package_revision'],previous_manifest['configuration_revision']):
                fail('Changed authoring content requires a newer package or configuration revision.')
            version=apply_package(previous,pack,coverage,policy_snapshots,stamp)
            self.authority(auth,True)
            if source_stamp(self.ontology,db,scope,workspace)!=stamp:fail('Source metadata changed during import.','BUSINESS_SOURCE_CHANGED',409)
            next_workspace={**workspace,'revision':workspace['revision']+1,'status':'draft','source_revisions':{role:s['revision'] for role,s in stamp.items()}}
            updated=db.execute('UPDATE business_ontology_workspaces SET document=? WHERE workspace=? AND owner=? AND ontology_id=? AND document=?',(json.dumps(next_workspace),*scope,'simpson',json.dumps(workspace))).rowcount
            if not updated:fail('Knowledge revision changed.','BUSINESS_REVISION_CONFLICT',409)
            from .google_connections import now
            version.update(version_id='bov_'+secrets.token_hex(16),revision=next_workspace['revision'],created_at=now(),workspace=next_workspace)
            for module in version['modules']:module['concept_count']=sum(c['module_id']==module['id'] for c in version['concepts'])
            db.execute('INSERT INTO business_ontology_versions VALUES (?,?,?,?)',(*scope,version['version_id'],json.dumps(version)))
            event=dict(action='import_knowledge',fingerprint=fingerprint,version_id=version['version_id'],revision=version['revision'],package_sha256=package_hash,at=now())
            db.execute('INSERT INTO business_ontology_events VALUES (?,?,?,?)',(*scope,event_id,json.dumps(event)))
            return dict(version_id=version['version_id'],revision=version['revision'],package_sha256=package_hash,idempotent=False)

    def inspect(self,auth,version_id,concept_id=None):
        self.authority(auth)
        snapshot=self.ontology.version(auth,version_id)
        from .business_compiler import check_snapshot
        if snapshot['kind']=='draft':check_snapshot(snapshot)
        knowledge=deepcopy(snapshot.get('knowledge'))
        concepts=snapshot['concepts']
        if concept_id:
            concept=next((c for c in concepts if c['id']==concept_id),None)
            if concept is None:fail('Concept not found.','BUSINESS_CONCEPT_NOT_FOUND',404)
            return dict(version_id=version_id,concept=concept,parents=[c for c in concepts if c['id']==concept['parent_id']],children=[c for c in concepts if c['parent_id']==concept_id],relationships=[r for r in snapshot['relationships'] if concept_id in (r['source'],r['target'])],details=next((d for d in (knowledge or {}).get('concept_details',[]) if d['concept_id']==concept_id),None),mappings=[m for m in (knowledge or {}).get('source_mappings',[]) if m['concept_id']==concept_id],states=[s for s in (knowledge or {}).get('state_models',[]) if s['concept_id']==concept_id],dates=[t for t in (knowledge or {}).get('temporal_models',[]) if t['concept_id']==concept_id],dependencies=[d for d in (knowledge or {}).get('dependencies',[]) if d['subject_id']==concept_id],knowledge_sha256=snapshot.get('knowledge_sha256'))
        return dict(version_id=version_id,revision=snapshot['revision'],concepts=concepts,relationships=snapshot['relationships'],rules=snapshot['rules'],knowledge=knowledge,knowledge_sha256=snapshot.get('knowledge_sha256'))

    def diagnose(self,auth,version_id,body):
        view=self.inspect(auth,version_id);k=view['knowledge']
        if k is None:fail('This version has no Phase 1 knowledge.','BUSINESS_KNOWLEDGE_REQUIRED',409)
        if not isinstance(body,dict):fail('Provide a diagnostic operation.')
        if len(canonical(body))>100000:fail('Diagnostic inputs exceed their size limit.')
        reject_secrets(body)
        op=body.get('operation');rid=body.get('id')
        group={'convert':'source_mappings','state':'state_models','rule':'structured_rules','associate':'identity_rules'}.get(op)
        allowed={'convert':{'operation','id','value'},'state':{'operation','id','value','target','facts'},'rule':{'operation','id','facts'},'associate':{'operation','id','left','right'}}
        if group is None or set(body)-allowed[op] or not {'operation','id'}<=body.keys():fail('Unsupported diagnostic operation or inputs.')
        definition=next((d for d in k[group] if d['id']==rid),None)
        if definition is None:fail('Definition not found in this version.','BUSINESS_DEFINITION_NOT_FOUND',404)
        if op=='convert':
            result=convert(body.get('value'),definition['conversion'],definition['business_datatype'])
            details=next((d for d in k['concept_details'] if d['concept_id']==definition['concept_id']),{})
            attribute=next((a for a in details.get('attributes',[]) if a['name']==definition['attribute']),{})
            if result['state']=='value' and attribute.get('allowed_values') and result['value'] not in attribute['allowed_values']:
                result=dict(state='unsupported_value',value=None)
        elif op=='state':result=state_check(definition,body.get('value'),body.get('target'),body.get('facts'))
        elif op=='rule':result=evaluate_rule(definition,body.get('facts',{}))
        else:result=associate(definition,body.get('left'),body.get('right'))
        return dict(version_id=version_id,knowledge_sha256=view['knowledge_sha256'],operation=op,result=result,company_reads=0,company_writes=0,model_calls=0)
