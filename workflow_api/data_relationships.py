"""Metadata-only relationship graph. No cloud adapters, business values or LLM calls."""
from __future__ import annotations

import hashlib
import itertools
import json
import re
import secrets
import time

from .google_connections import GoogleConnections, now
from .service import ApiFailure

MAX_NODES = 12000
MAX_RELATIONSHIPS = 2000
MAX_CANDIDATE_PAIRS = 20000


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def identifier(name):
    return re.sub(r'[^a-z0-9]', '', name.lower())


def scalar_types(field):
    aliases = {'text':'string','character varying':'string','character':'string', 'smallint':'integer','bigint':'integer', 'numeric':'number','real':'number','double precision':'number'}
    types = {aliases.get(t,t) for t in field['types']} - {'null'}
    return types if types and types <= {'string', 'integer', 'number', 'boolean', 'date', 'datetime', 'timestamp'} else set()


def compatible(left, right):
    a, b = scalar_types(left), scalar_types(right)
    # Mixed observed types and implicit text/numeric casts are not join evidence.
    return len(a) == len(b) == 1 and a == b


def mongo_reference_compatible(left, right):
    # ObjectId evidence can describe a Mongo reference, but does not extend the
    # executable query engine's scalar-key support or introduce string coercion.
    a, b = set(left['types'])-{'null'}, set(right['types'])-{'null'}
    return compatible(left,right) or a == b == {'ObjectId'}


def build_graph(sources):
    nodes, relationships, warnings, candidates = [], [], [], {}
    datasets = {}
    for source in sources:
        connection, snapshot = source['connection'], source['snapshot']
        cid = connection['connection_id']
        nodes.append(dict(node_id=cid, kind='connection', label=connection['name'], connection_id=cid,
                          parent_id=None, types=[], discovery_method='declared'))
        if snapshot['coverage'] != 'declared' or snapshot['warnings']:
            warnings.append(f"{connection['name']}: metadata is sampled or limited; absence is not proof of deletion.")
        for dataset in snapshot['datasets']:
            did = dataset['dataset_id']
            if len(nodes) + 1 + len(dataset['fields']) > MAX_NODES:
                warnings.append('Graph node limit reached; some datasets are omitted.')
                continue
            datasets[(cid, dataset['schema'], dataset['name'])] = dataset
            nodes.append(dict(node_id=did, kind='dataset', label=(dataset['schema']+'.' if dataset['schema'] else '')+dataset['name'],
                              connection_id=cid, parent_id=cid, types=[], discovery_method=dataset['discovery_method']))
            for field in dataset['fields']:
                nodes.append(dict(node_id=field['field_id'], kind='field', label=field['name'], connection_id=cid,
                                  parent_id=did, types=field['types'], discovery_method=field['discovery_method']))
                key = identifier(field['name'])
                if re.search(r'(?:ID|Id|_id|-id| id)$', field['name']) and len(key) > 2 and '.' not in field['name'] and '[' not in field['name'] and scalar_types(field) in ({'string'}, {'integer'}):
                    candidates.setdefault(key, []).append((cid, did, field))
    seen_links = set()
    def relationship(kind, left, right, pairs, evidence):
        link = tuple(sorted(tuple(sorted((p['source_field_id'],p['target_field_id']))) for p in pairs))
        if kind=='suggested' and link in seen_links:
            return
        seen_links.add(link)
        rid = 'rel_' + fingerprint([kind, left, right, pairs])[:32]
        relationships.append(dict(relationship_id=rid, kind=kind, source_dataset_id=left,
                                  target_dataset_id=right, field_pairs=pairs, evidence=evidence,
                                  evidence_hash=fingerprint(evidence), status='declared' if kind=='declared' else 'proposed'))
    for source in sources:
        cid = source['connection']['connection_id']
        for dataset in source['snapshot']['datasets']:
            if (cid, dataset['schema'], dataset['name']) not in datasets:
                continue
            for constraint in dataset['constraints']:
                if constraint.get('kind') != 'foreign_key':
                    continue
                target = datasets.get((cid, constraint.get('referenced_schema'), constraint.get('referenced_table')))
                columns, refs = constraint.get('columns', []), constraint.get('referenced_columns', [])
                if not target or not columns or len(columns) != len(refs):
                    warnings.append(f"{dataset['name']}: foreign key target is outside discovered coverage or incomplete.")
                    continue
                left = {f['name']: f for f in dataset['fields']}
                right = {f['name']: f for f in target['fields']}
                if any(a not in left or b not in right for a, b in zip(columns, refs)):
                    warnings.append(f"{dataset['name']}: foreign key fields are outside discovered coverage.")
                    continue
                if len(relationships) >= MAX_RELATIONSHIPS:
                    warnings.append('Relationship limit reached.')
                    break
                pairs = [dict(source_field_id=left[a]['field_id'], target_field_id=right[b]['field_id']) for a,b in zip(columns,refs)]
                relationship('declared', dataset['dataset_id'], target['dataset_id'], pairs,
                             ['Database foreign key: '+constraint.get('name',''), json.dumps(constraint, sort_keys=True)])
    checked = 0
    by_id = {d['dataset_id']: d for d in datasets.values()}
    for key in sorted(candidates):
        group = sorted(candidates[key], key=lambda x: (x[0],x[1],x[2]['field_id']))
        for (ac,ad,af),(bc,bd,bf) in itertools.combinations(group,2):
            checked += 1
            if checked > MAX_CANDIDATE_PAIRS or len(relationships) >= MAX_RELATIONSHIPS:
                warnings.append('Candidate comparison limit reached; suggestions are incomplete.')
                break
            mongo_same = ac == bc and ad != bd and by_id[ad].get('schema') is None and by_id[bd].get('schema') is None
            if (ac == bc and not mongo_same) or ad == bd or not compatible(af,bf):
                continue
            relationship('suggested',ad,bd,[dict(source_field_id=af['field_id'],target_field_id=bf['field_id'])],
                         [f'Normalized identifier name matches: {key}', 'Compatible normalized scalar type: '+','.join(sorted(scalar_types(af))),
                          'Source field: '+json.dumps({k:v for k,v in af.items() if k!='present_in_samples'},sort_keys=True), 'Target field: '+json.dumps({k:v for k,v in bf.items() if k!='present_in_samples'},sort_keys=True),
                          'Metadata only. Value overlap, uniqueness, join direction and cardinality are unverified.'])
        if checked > MAX_CANDIDATE_PAIRS or len(relationships) >= MAX_RELATIONSHIPS:
            break
    # Collection-qualified Mongo references may point to a target _id. These are
    # additional proposals only; generic id-to-id matching is never inferred.
    from .data_graph_v2 import singular, field_stem
    mongo = [d for d in datasets.values() if d.get('schema') is None]
    for target in mongo:
        target_id = next((f for f in target['fields'] if f['name']=='_id'), None)
        if not target_id:
            continue
        for source in mongo:
            if source is target:
                continue
            for field in source['fields']:
                checked += 1
                if checked > MAX_CANDIDATE_PAIRS or len(relationships)>=MAX_RELATIONSHIPS:
                    warnings.append('Candidate comparison limit reached; suggestions are incomplete.')
                    break
                if identifier(field_stem(field['name'])) != identifier(singular(target['name'])) or not mongo_reference_compatible(field,target_id):
                    continue
                if set(field['types'])-{'null'} == {'ObjectId'}:
                    warnings.append('ObjectId reference suggestions describe metadata only; current query key types remain restricted.')
                relationship('suggested', source['dataset_id'], target['dataset_id'], [dict(source_field_id=field['field_id'],target_field_id=target_id['field_id'])],
                             ['Collection-qualified identifier suggests a reference to the target _id.',
                              'Source field: '+json.dumps({k:v for k,v in field.items() if k!='present_in_samples'},sort_keys=True),
                              'Target field: '+json.dumps({k:v for k,v in target_id.items() if k!='present_in_samples'},sort_keys=True),
                              'Metadata only. Value overlap, uniqueness, join direction and cardinality are unverified.'])
            if checked > MAX_CANDIDATE_PAIRS or len(relationships)>=MAX_RELATIONSHIPS:
                break
        if checked > MAX_CANDIDATE_PAIRS or len(relationships)>=MAX_RELATIONSHIPS:
            break
    return dict(nodes=nodes, relationships=relationships, warnings=sorted(set(warnings)))


class DataRelationships:
    def __init__(self, store):
        self.store = store
        with store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS data_relationship_graphs (workspace TEXT NOT NULL, owner TEXT NOT NULL, revision INTEGER NOT NULL, input_hash TEXT NOT NULL, document TEXT NOT NULL, PRIMARY KEY(workspace,owner))')
            db.execute('CREATE TABLE IF NOT EXISTS data_relationship_jobs (workspace TEXT NOT NULL, owner TEXT NOT NULL, state TEXT NOT NULL, token TEXT, lease_until REAL NOT NULL, attempts INTEGER NOT NULL, error TEXT, PRIMARY KEY(workspace,owner))')
            db.execute('CREATE TABLE IF NOT EXISTS data_relationship_reviews (workspace TEXT NOT NULL, owner TEXT NOT NULL, relationship_id TEXT NOT NULL, evidence_hash TEXT NOT NULL, status TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(workspace,owner,relationship_id))')
            db.execute('CREATE TABLE IF NOT EXISTS data_relationship_annotations (workspace TEXT NOT NULL, owner TEXT NOT NULL, node_id TEXT NOT NULL, description TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(workspace,owner,node_id))')
        from .data_graph_v2 import DataGraphV2
        self.detailed = DataGraphV2(self)
        from .data_ontology import BusinessOntology
        self.ontology = BusinessOntology(self)

    @staticmethod
    def inputs(db, workspace, owner):
        rows = db.execute('SELECT document FROM data_source_connections WHERE workspace=? AND owner=? ORDER BY connection_id',(workspace,owner)).fetchall()
        sources, versions = [], []
        for row in rows:
            connection = json.loads(row[0])
            if connection['connection_status'] != 'connected' or connection.get('profiling_status', 'ready') != 'ready':
                continue
            snapshot = db.execute('SELECT document FROM data_source_snapshots WHERE connection_id=? AND revision=?',(connection['connection_id'],connection['metadata_revision'])).fetchone()
            if snapshot:
                sources.append(dict(connection=connection,snapshot=json.loads(snapshot[0])))
                versions.append(dict(connection_id=connection['connection_id'],revision=connection['metadata_revision'],generation=connection['generation']))
        return sources, versions, fingerprint(versions)

    @staticmethod
    def enqueue(db, workspace, owner):
        db.execute("INSERT INTO data_relationship_jobs VALUES (?,?,'queued',NULL,0,0,NULL) ON CONFLICT(workspace,owner) DO UPDATE SET state='queued',token=NULL,lease_until=0,attempts=0,error=NULL",(workspace,owner))

    def request(self, auth):
        workspace, owner = GoogleConnections.identity(auth, True)
        with self.store.transaction() as db:
            job = db.execute('SELECT state FROM data_relationship_jobs WHERE workspace=? AND owner=?',(workspace,owner)).fetchone()
            if not job or job[0] not in {'queued','running'}:
                self.enqueue(db,workspace,owner)
        return self.get(auth)

    def get_in_transaction(self, db, workspace, owner):
        _, versions, current_hash = self.inputs(db,workspace,owner)
        row = db.execute('SELECT document,input_hash FROM data_relationship_graphs WHERE workspace=? AND owner=?',(workspace,owner)).fetchone()
        job = db.execute('SELECT state,error FROM data_relationship_jobs WHERE workspace=? AND owner=?',(workspace,owner)).fetchone()
        graph = json.loads(row[0]) if row else None
        if graph:
            # Hide disconnected sources immediately, even before the worker rebuilds.
            active = {v['connection_id'] for v in versions}
            graph['nodes'] = [n for n in graph['nodes'] if n['connection_id'] in active]
            ids = {n['node_id'] for n in graph['nodes']}
            graph['relationships'] = [r for r in graph['relationships'] if r['source_dataset_id'] in ids and r['target_dataset_id'] in ids]
            reviews = {r[0]: r[1:] for r in db.execute('SELECT relationship_id,evidence_hash,status,updated_at FROM data_relationship_reviews WHERE workspace=? AND owner=?',(workspace,owner)).fetchall()}
            for edge in graph['relationships']:
                review = reviews.get(edge['relationship_id'])
                edge['reviewed_at'] = None
                if edge['kind']=='suggested' and review and review[0]==edge['evidence_hash']:
                    edge['status'],edge['reviewed_at'] = review[1:]
            annotations = {r[0]:r[1] for r in db.execute('SELECT node_id,description FROM data_relationship_annotations WHERE workspace=? AND owner=?',(workspace,owner)).fetchall()}
            for node in graph['nodes']:
                node['description'] = annotations.get(node['node_id'],'')
        return dict(graph=graph, stale=bool(row and row[1]!=current_hash), build_status=job[0] if job else 'idle', last_error=job[1] if job else None)

    def get(self, auth):
        workspace, owner = GoogleConnections.identity(auth)
        with self.store.transaction(write=False) as db:
            return self.get_in_transaction(db,workspace,owner)

    def edit(self, auth, kind, item_id, body):
        workspace, owner = GoogleConnections.identity(auth, True)
        if not isinstance(body,dict) or set(body) != ({'revision','status'} if kind=='review' else {'revision','description'}) or type(body.get('revision')) is not int:
            raise ApiFailure('DATA_RELATIONSHIP_INPUT_INVALID','Supply a graph revision and valid edit.',400)
        with self.store.transaction() as db:
            view = self.get_in_transaction(db,workspace,owner)
            graph = view['graph']
            if not graph:
                raise ApiFailure('DATA_RELATIONSHIP_NOT_FOUND','Graph item not found.',404)
            if view['stale'] or graph['revision'] != body['revision']:
                raise ApiFailure('DATA_RELATIONSHIP_STALE','Metadata or graph changed. Rebuild and reload relationships before editing.',409)
            if kind=='review':
                edge = next((r for r in graph['relationships'] if r['relationship_id']==item_id),None)
                if not edge:
                    raise ApiFailure('DATA_RELATIONSHIP_NOT_FOUND','Graph item not found.',404)
                if edge['kind']!='suggested' or not isinstance(body['status'],str) or body['status'] not in {'proposed','accepted','rejected'}:
                    raise ApiFailure('DATA_RELATIONSHIP_INPUT_INVALID','Review only suggested relationships with a valid status.',400)
                db.execute('INSERT INTO data_relationship_reviews VALUES (?,?,?,?,?,?) ON CONFLICT(workspace,owner,relationship_id) DO UPDATE SET evidence_hash=excluded.evidence_hash,status=excluded.status,updated_at=excluded.updated_at',
                           (workspace,owner,item_id,edge['evidence_hash'],body['status'],now()))
            else:
                if not any(n['node_id']==item_id for n in graph['nodes']):
                    raise ApiFailure('DATA_RELATIONSHIP_NOT_FOUND','Graph item not found.',404)
                description = body['description']
                if not isinstance(description,str) or len(description)>1000:
                    raise ApiFailure('DATA_RELATIONSHIP_INPUT_INVALID','Description must be text of at most 1000 characters.',400)
                db.execute('INSERT INTO data_relationship_annotations VALUES (?,?,?,?,?) ON CONFLICT(workspace,owner,node_id) DO UPDATE SET description=excluded.description,updated_at=excluded.updated_at',
                           (workspace,owner,item_id,description.strip(),now()))
            # Version every edit as well as builds, preventing concurrent lost updates.
            graph['revision'] += 1
            db.execute('UPDATE data_relationship_graphs SET revision=?,document=? WHERE workspace=? AND owner=?',
                       (graph['revision'],json.dumps(graph),workspace,owner))
            return self.get_in_transaction(db,workspace,owner)

    def tick(self):
        with self.store.transaction() as db:
            job = db.execute("SELECT workspace,owner,attempts FROM data_relationship_jobs WHERE state='queued' OR (state='running' AND lease_until<?) ORDER BY workspace,owner LIMIT 1",(time.time(),)).fetchone()
            if not job:
                return False
            workspace,owner,attempts = job
            token = secrets.token_hex(16)
            db.execute("UPDATE data_relationship_jobs SET state='running',token=?,lease_until=?,attempts=? WHERE workspace=? AND owner=?",(token,time.time()+120,attempts+1,workspace,owner))
            sources, versions, input_hash = self.inputs(db,workspace,owner)
        try:
            if attempts >= 3:
                raise RuntimeError('Build repeatedly interrupted')
            result = build_graph(sources)
            result.update(sources=versions,built_at=now())
            if len(json.dumps(result).encode())>8_000_000:
                raise RuntimeError('Graph size limit')
            error = None
        except Exception:
            result = None
            error = 'Graph build failed or exceeded its limits. Rebuild to retry; the last graph is retained.'
        with self.store.transaction() as db:
            claim = db.execute('SELECT state,token FROM data_relationship_jobs WHERE workspace=? AND owner=?',(workspace,owner)).fetchone()
            if claim != ('running',token):
                return True
            if self.inputs(db,workspace,owner)[2] != input_hash:
                self.enqueue(db,workspace,owner)
                return True
            if result is not None:
                prior = db.execute('SELECT revision FROM data_relationship_graphs WHERE workspace=? AND owner=?',(workspace,owner)).fetchone()
                result['revision'] = prior[0]+1 if prior else 1
                db.execute('INSERT INTO data_relationship_graphs VALUES (?,?,?,?,?) ON CONFLICT(workspace,owner) DO UPDATE SET revision=excluded.revision,input_hash=excluded.input_hash,document=excluded.document',
                           (workspace,owner,result['revision'],input_hash,json.dumps(result)))
            db.execute('UPDATE data_relationship_jobs SET state=?,token=NULL,error=? WHERE workspace=? AND owner=?',('failed' if error else 'ready',error,workspace,owner))
        return True
