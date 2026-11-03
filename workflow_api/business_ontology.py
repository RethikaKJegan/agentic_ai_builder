"""Isolated Simpson business foundation and immutable extracted draft views."""
from copy import deepcopy
from hashlib import sha256
import json
import secrets

from .google_connections import GoogleConnections, now
from .service import ApiFailure

LAYERS = [
    dict(id='foundational', label='Foundational', description='Objects, events, processes, identity, causality, time and place.'),
    dict(id='common', label='Common', description='Reusable enterprise organizations, assets, evidence, documents and decisions.'),
    dict(id='domain', label='Manufacturing domain', description='Manufacturing, warranty, field service, failure analysis and engineering change.'),
    dict(id='organization', label='Simpson organization', description='Simpson departments, OEM relationships, people and role assignments.'),
    dict(id='business', label='Simpson business', description='Simpson terminology, warranty rules, replacement decisions and effectivity.'),
]
MODULES = [
    ('organization', 'Organization and ecosystem', 'Organizations, OEM companies, accounts, departments and role assignments.', ['common','organization']),
    ('engines', 'Products and engines', 'Engine families, models, instances, components, invoices and manufacturing context.', ['common','domain']),
    ('complaints', 'Complaints and tickets', 'Complaint submissions, reported symptoms, usage and service cases.', ['domain','business']),
    ('warranty', 'Warranty eligibility', 'Policy inputs, coverage, exclusions, assessments and explainable decisions.', ['domain','business']),
    ('inspection', 'Investigation and inspection', 'Engineer assignment, joint inspections, observations and diagnostic evidence.', ['domain','business']),
    ('failure', 'Failure analysis', 'Symptoms, failure modes, components, mechanisms and qualified root causes.', ['domain']),
    ('replacement', 'Replacement and logistics', 'Part and engine replacement, commercial decisions, dispatch, returns and custody.', ['domain','business']),
    ('quality', 'Quality investigation', 'Returned-engine examination, tests, findings and quality conclusions.', ['domain','business']),
    ('capa', 'Corrective and preventive action', 'Containment, correction, CAPA, implementation and effectiveness reviews.', ['domain','business']),
    ('effectivity', 'Engineering change and cut-in', 'Change applicability, scoped serial boundaries, dates and incorporation evidence.', ['domain','business']),
    ('monitoring', 'Monitoring and reliability', 'Eligible populations, operating exposure, recurrence and change effectiveness.', ['domain']),
    ('evidence', 'Evidence and provenance', 'Source records, documents, assertions, verification status and temporal history.', ['foundational','common']),
]


def identity(auth, write=False):
    scope = GoogleConnections.identity(auth, write)
    required = {'workspace:read'} | ({'workspace:write'} if write else set())
    if not required <= set(auth.get('scopes', [])):
        raise ApiFailure('OPERATION_NOT_AUTHORIZED', 'Business ontology access is not authorized.', 403)
    return scope


class BusinessOntology:
    def __init__(self, store):
        self.store = store
        with store.transaction() as db:
            for table, key in [('workspaces', 'ontology_id'), ('versions', 'version_id'), ('events', 'event_id'), ('documents', 'document_id')]:
                db.execute(f'CREATE TABLE IF NOT EXISTS business_ontology_{table} (workspace TEXT NOT NULL, owner TEXT NOT NULL, {key} TEXT NOT NULL, document TEXT NOT NULL, PRIMARY KEY(workspace,owner,{key}))')

    @staticmethod
    def connections(db, scope):
        # Select metadata only, never encrypted credential columns or source records.
        rows = db.execute('SELECT connection_id,document FROM data_source_connections WHERE workspace=? AND owner=?', scope).fetchall()
        return {cid: {k: doc.get(k) for k in ('name', 'engine', 'connection_status', 'metadata_revision', 'generation')}
                for cid, raw in rows for doc in [json.loads(raw)]}

    @staticmethod
    def document(db, scope):
        row = db.execute('SELECT document FROM business_ontology_workspaces WHERE workspace=? AND owner=? AND ontology_id=?', (*scope, 'simpson')).fetchone()
        return json.loads(row[0]) if row else None

    def view(self, db, scope):
        workspace = self.document(db, scope)
        connections = self.connections(db, scope)
        versions = [json.loads(row[0]) for row in db.execute('SELECT document FROM business_ontology_versions WHERE workspace=? AND owner=?', scope).fetchall()]
        versions.sort(key=lambda v:v['revision'])
        latest=versions[-1] if versions else {}
        definitions={kind:deepcopy(latest.get(kind,[])) for kind in ('concepts','relationships','rules')}
        from .business_documents import BusinessDocuments, summarize
        documents=[summarize(d) for d in BusinessDocuments.rows(db,scope)]
        bindings = []
        for role, cid in (workspace or {}).get('sources', {}).items():
            current = connections.get(cid)
            bindings.append(dict(role=role, connection_id=cid, name=current.get('name') if current else None,
                status='unavailable' if not current or current['connection_status'] != 'connected' else
                       'metadata_changed' if current['metadata_revision'] != workspace['source_revisions'][role] else 'connected'))
        return dict(api_version=1, workspace=workspace, layers=deepcopy(LAYERS),
                    modules=[dict(id=i,label=l,description=d,layers=layers,concept_count=sum(c.get('module_id')==i for c in definitions['concepts'])) for i,l,d,layers in MODULES],
                    available_sources=[dict(connection_id=cid, **c) for cid,c in sorted(connections.items())
                                       if c['engine']=='mongodb' and c['connection_status']=='connected'],
                    source_bindings=bindings,
                    versions=[{k:v[k] for k in ('version_id','revision','created_at','kind')} for v in versions],
                    counts={kind:len(items) for kind,items in definitions.items()},
                    generation_status='draft_available' if definitions['concepts'] else 'not_started',
                    definitions=definitions,documents=documents,questions=latest.get('questions',{}),
                    current_version_id=latest.get('version_id'))

    def get(self, auth):
        scope = identity(auth)
        with self.store.transaction(write=False) as db:
            return self.view(db, scope)

    def initialize(self, auth, body):
        scope = identity(auth, True)
        if (not isinstance(body,dict) or set(body) != {'sources'} or not isinstance(body['sources'],dict)
            or set(body['sources']) != {'service','quality'}
            or any(not isinstance(cid,str) or not 1 <= len(cid) <= 128 for cid in body['sources'].values())
            or len(set(body['sources'].values())) != 2):
            raise ApiFailure('BUSINESS_ONTOLOGY_INVALID', 'Choose two distinct service and quality sources.', 422)
        sources = body['sources']
        with self.store.transaction() as db:
            available = self.connections(db, scope)
            if any(cid not in available or available[cid]['engine'] != 'mongodb' or available[cid]['connection_status'] != 'connected' for cid in sources.values()):
                raise ApiFailure('BUSINESS_SOURCE_UNAVAILABLE', 'Select two owned, connected MongoDB sources.', 422)
            version_id = 'bov_' + secrets.token_hex(16)
            timestamp = now()
            workspace = dict(ontology_id='simpson', title='Simpson Business Ontology',
                namespace='urn:simpson-business:' + sha256(json.dumps(scope).encode()).hexdigest()[:24] + ':',
                revision=1, status='foundation', created_at=timestamp, sources=deepcopy(sources),
                source_revisions={role:available[cid]['metadata_revision'] for role,cid in sources.items()})
            inserted = db.execute('INSERT INTO business_ontology_workspaces VALUES (?,?,?,?) ON CONFLICT DO NOTHING RETURNING document',
                                  (*scope, 'simpson', json.dumps(workspace))).fetchone()
            if inserted:
                version = dict(version_id=version_id,revision=1,created_at=timestamp,kind='foundation',workspace=workspace,
                               layers=deepcopy(LAYERS),modules=[dict(id=i,label=l,description=d,layers=layers,concept_count=0) for i,l,d,layers in MODULES],
                               concepts=[],relationships=[],rules=[])
                db.execute('INSERT INTO business_ontology_versions VALUES (?,?,?,?)', (*scope,version_id,json.dumps(version)))
                db.execute('INSERT INTO business_ontology_events VALUES (?,?,?,?)', (*scope,'boe_'+secrets.token_hex(16),json.dumps(dict(action='initialize',at=timestamp,revision=1,version_id=version_id))))
            elif self.document(db, scope)['sources'] != sources:
                raise ApiFailure('BUSINESS_ONTOLOGY_EXISTS', 'A foundation already exists with different sources.', 409)
            return self.view(db, scope)

    def version(self, auth, version_id):
        scope = identity(auth)
        with self.store.transaction(write=False) as db:
            row = db.execute('SELECT document FROM business_ontology_versions WHERE workspace=? AND owner=? AND version_id=?', (*scope,version_id)).fetchone()
        if not row:
            raise ApiFailure('BUSINESS_VERSION_NOT_FOUND', 'Business ontology version not found.', 404)
        return json.loads(row[0])
