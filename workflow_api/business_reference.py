"""Explicit curated reference module import; never a model-generation shortcut."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
import secrets

from .business_compiler import canonical
from .business_documents import BusinessDocuments, REFERENCE, source_stamp
from .business_extraction import validate_result
from .business_ontology import identity, MODULES, LAYERS
from .google_connections import now
from .service import ApiFailure

KIT=Path(__file__).resolve().parents[1]/'ontology/business-reference/module-drafts.json'
GROUPS=('concepts','relationships','rules')


def load_kit():
    kit=json.loads(KIT.read_text());raw=REFERENCE.read_bytes();bundle=json.loads(raw)
    if sha256(raw).hexdigest()!=kit['bundle_sha256']:raise ApiFailure('BUSINESS_REFERENCE_CHANGED','Reference evidence changed; the draft kit needs revalidation.',409)
    for source in bundle['documents']:
        if sha256(source['text'].encode()).hexdigest()!=source['sha256']:raise ApiFailure('BUSINESS_REFERENCE_CHANGED','Reference source hash mismatch.',409)
    return kit,bundle


def additions(previous,kit,bundle):
    populated={c['module_id'] for c in previous['concepts']}
    missing=[m[0] for m in MODULES if m[0] not in populated]
    result={kind:deepcopy(previous[kind]) for kind in GROUPS};questions=deepcopy(previous.get('questions',{}))
    available={c['id'] for c in result['concepts']}|{c['id'] for module in missing for c in kit['modules'][module]['concepts']}
    for module in missing:
        draft=deepcopy(kit['modules'][module])
        unresolved=[r for r in draft['relationships'] if r['source'] not in available or r['target'] not in available]
        draft['relationships']=[r for r in draft['relationships'] if r not in unresolved]
        for edge in unresolved:draft['questions'].append('Reference relationship '+edge['id']+' needs an explicit existing concept binding; '+edge['target']+' was not added or inferred.')
        questions[module]=draft['questions']
        # Validate against the complete final concept catalogue, including future
        # modules. Their actual definitions are validated individually below.
        retained={kind:deepcopy(result[kind]) for kind in GROUPS}
        retained['concepts'] += [dict(c,module_id=m,status='draft') for m in missing if m!=module for c in kit['modules'][m]['concepts'] if c['id'] not in {x['id'] for x in retained['concepts']}]
        clean=validate_result(draft,module,bundle['documents'],retained)
        for kind in GROUPS:
            for item in clean[kind]:item['source_basis']='curated_supplied_blueprint_draft'
            result[kind]+=clean[kind]
    return missing,result,questions


class BusinessReference:
    def __init__(self,ontology,resolve):
        self.ontology=ontology;self.store=ontology.store;self.resolve=resolve
        with self.store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS business_ontology_reference_imports (workspace TEXT NOT NULL,owner TEXT NOT NULL,request_key TEXT NOT NULL,fingerprint TEXT NOT NULL,version_id TEXT NOT NULL,PRIMARY KEY(workspace,owner,request_key))')

    def authority(self,auth):
        scope=identity(auth,True);current=self.resolve(*scope) if self.resolve else auth
        if not current or current.get('subject')!=auth['subject']:raise ApiFailure('OPERATION_NOT_AUTHORIZED','Current reference-import authority is unavailable.',403)
        identity(current,True);return scope

    def coverage(self,auth,version_id):
        scope=identity(auth);version=self.ontology.version(auth,version_id);kit,bundle=load_kit()
        with self.store.transaction(write=False) as db:
            workspace=self.ontology.document(db,scope)
            documents=BusinessDocuments.rows(db,scope)
            connections=self.ontology.connections(db,scope)
        bindings_match=bool(workspace and workspace['sources']==bundle['required_sources'])
        connected=bindings_match and all(cid in connections and connections[cid]['connection_status']=='connected' for cid in workspace['sources'].values())
        latest=bool(workspace and workspace['revision']==version['revision'])
        modules=[]
        for mid,label,description,layers in MODULES:
            counts={kind:sum(i['module_id']==mid for i in version[kind]) for kind in GROUPS}
            module_sources=[d for d in version.get('sources',[]) if mid in d['module_ids']]
            modules.append(dict(module_id=mid,label=label,description=description,counts=counts,status='draft_available' if counts['concepts'] else 'not_started',
                source_documents=len(module_sources),available_documents=sum(mid in d['module_ids'] for d in documents),questions=version.get('questions',{}).get(mid,[]),
                curated_concepts=sum(c['module_id']==mid and c.get('source_basis')=='curated_supplied_blueprint_draft' for c in version['concepts']),
                reference_concepts=len(kit['modules'][mid]['concepts']),business_policy_verified=False))
        missing=[m['module_id'] for m in modules if m['status']=='not_started']
        reason=None if connected and latest and missing else 'All modules already contain drafts.' if not missing else 'Choose the latest saved version.' if not latest else 'The supplied reference requires its original owned, connected Simpson source bindings.'
        return dict(version_id=version_id,revision=version['revision'],kit_version=kit['kit_version'],modules=modules,missing_modules=missing,import_available=reason is None,unavailable_reason=reason,source_basis=kit['source_basis'],business_policy_verified=False)

    def apply(self,auth,body):
        scope=self.authority(auth)
        if (not isinstance(body,dict) or set(body)!={'expected_revision','request_key'} or type(body['expected_revision']) is not int or body['expected_revision']<1
            or not isinstance(body['request_key'],str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,100}',body['request_key'])):
            raise ApiFailure('BUSINESS_REFERENCE_INVALID','Choose the current revision and a request key.',422)
        kit,bundle=load_kit();fingerprint=sha256(canonical([body['expected_revision'],kit['kit_version'],kit['bundle_sha256']]).encode()).hexdigest()
        with self.store.transaction() as db:
            existing=db.execute('SELECT fingerprint,version_id FROM business_ontology_reference_imports WHERE workspace=? AND owner=? AND request_key=?',(*scope,body['request_key'])).fetchone()
            if existing:
                if existing[0]!=fingerprint:raise ApiFailure('IDEMPOTENCY_KEY_REUSED','This key belongs to another reference import.',409)
                return dict(version_id=existing[1],state=self.ontology.view(db,scope))
            workspace=self.ontology.document(db,scope)
            if not workspace or workspace['sources']!=bundle['required_sources']:raise ApiFailure('BUSINESS_REFERENCE_SCOPE','The supplied reference belongs to different source bindings.',403)
            if workspace['revision']!=body['expected_revision']:raise ApiFailure('BUSINESS_REVISION_CONFLICT','Refresh before adding reference drafts.',409)
            stamp=source_stamp(self.ontology,db,scope,workspace)
            active=db.execute("SELECT job_id FROM business_ontology_jobs WHERE workspace=? AND owner=? AND state IN ('queued','running')",scope).fetchone()
            if active:raise ApiFailure('BUSINESS_GENERATION_ACTIVE','Wait for the current module generation before importing reference drafts.',409)
            rows=db.execute('SELECT document FROM business_ontology_versions WHERE workspace=? AND owner=?',scope).fetchall()
            previous=max((json.loads(r[0]) for r in rows),key=lambda v:v['revision'])
            missing,definitions,questions=additions(previous,kit,bundle)
            if not missing:raise ApiFailure('BUSINESS_REFERENCE_COMPLETE','All modules already contain drafts; existing work was preserved.',409)
            self.authority(auth)
            if source_stamp(self.ontology,db,scope,workspace)!=stamp:raise ApiFailure('BUSINESS_SOURCE_CHANGED','Source state changed during reference import.',409)
            updated={**workspace,'revision':workspace['revision']+1,'status':'draft'}
            changed=db.execute('UPDATE business_ontology_workspaces SET document=? WHERE workspace=? AND owner=? AND ontology_id=? AND document=?',(json.dumps(updated),*scope,'simpson',json.dumps(workspace))).rowcount
            if not changed:raise ApiFailure('BUSINESS_REVISION_CONFLICT','A newer draft exists.',409)
            version_id='bov_'+secrets.token_hex(16);timestamp=now();evidence={d['source_id']:d for d in previous.get('sources',[])}
            evidence.update({d['source_id']:d for d in bundle['documents']})
            version=dict(version_id=version_id,revision=updated['revision'],created_at=timestamp,kind='draft',workspace=updated,layers=deepcopy(LAYERS),
                modules=[dict(id=i,label=l,description=d,layers=layers,concept_count=sum(c['module_id']==i for c in definitions['concepts'])) for i,l,d,layers in MODULES],
                **definitions,sources=list(evidence.values()),questions=questions,
                reference_import=dict(kit_version=kit['kit_version'],source_basis=kit['source_basis'],added_modules=missing,bundle_sha256=kit['bundle_sha256']),
                validation=dict(schema='passed',citations='passed',references='passed',semantic_compilation='not_run',business_policy_verified=False))
            BusinessDocuments.save(db,scope,bundle['documents'])
            db.execute('INSERT INTO business_ontology_versions VALUES (?,?,?,?)',(*scope,version_id,json.dumps(version)))
            db.execute('INSERT INTO business_ontology_reference_imports VALUES (?,?,?,?,?)',(*scope,body['request_key'],fingerprint,version_id))
            db.execute('INSERT INTO business_ontology_events VALUES (?,?,?,?)',(*scope,'boe_'+secrets.token_hex(16),json.dumps(dict(action='import_reference_modules',at=timestamp,version_id=version_id,added_modules=missing))))
            return dict(version_id=version_id,state=self.ontology.view(db,scope))
