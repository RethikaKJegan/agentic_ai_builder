"""Versioned metadata-only graph projection. Entity reviews confer no query grants."""
from __future__ import annotations

import json
import re
from copy import deepcopy

from .data_relationships import fingerprint, identifier
from .google_connections import GoogleConnections, now
from .service import ApiFailure


def singular(name):
    words = re.sub(r'([a-z])([A-Z])', r'\1 \2', name).replace('_', ' ').replace('-', ' ').split()
    if not words:
        return ''
    word = words[-1].lower()
    if word.endswith('ies') and len(word) > 3:
        word = word[:-3] + 'y'
    elif word.endswith('s') and not word.endswith(('ss', 'us')) and len(word) > 3:
        word = word[:-1]
    return ' '.join([*words[:-1], word]).strip().title()[:80]


def entity_id(name):
    return 'entity_' + fingerprint(' '.join(name.casefold().split()))[:32]


def field_stem(name):
    if '.' in name or '[' in name or not re.search(r'(?:ID|Id|_id|-id| id)$', name):
        return ''
    stem = re.sub(r'(?:ID|Id|_id|-id| id)$', '', name).strip('_- ')
    return singular(stem) if len(identifier(stem)) > 1 else ''


def structural(value):
    if isinstance(value, dict):
        return {k: structural(v) for k, v in value.items() if k not in {'sample_count', 'present_in_samples'}}
    if isinstance(value, list):
        return [structural(v) for v in value]
    return value


def qualify(edge, datasets):
    target = datasets.get(edge['target_dataset_id'], {})
    names = {f['field_id']: f['name'] for f in target.get('fields', [])}
    columns = [names.get(p['target_field_id']) for p in edge['field_pairs']]
    unique = any(c.get('kind') in {'primary_key', 'unique'} and len(c.get('columns', [])) == len(columns)
                 and set(c['columns']) == set(columns) for c in target.get('constraints', []))
    reported_indexes = [i['name'] for i in target.get('indexes', []) if i.get('unique') and
                        [c.get('name') for c in i.get('columns', [])] == columns]
    declared = edge['kind'] == 'declared'
    return dict(
        confidence='database_declaration' if declared else 'metadata_candidate',
        direction='source_references_target' if declared else 'unknown',
        cardinality='At most one target per source key by declared foreign key; source multiplicity and optionality are not asserted.' if declared else
                    'Target key has a declared uniqueness constraint; matching source values and relationship cardinality remain unverified.' if unique else 'Unknown; metadata matching is not proof of cardinality.',
        target_key_evidence='Declared primary/unique constraint' if unique else
                            'Reported unique index: '+', '.join(reported_indexes)+'; sparse/partial/collation applicability is unverified.' if reported_indexes else 'No applicable declared uniqueness evidence in the discovered snapshot.',
        value_overlap='not_checked', review_basis='User review permits the existing query validator to consider this relationship; runtime join checks still apply.' if edge['status']=='accepted' else 'No user acceptance asserted.',
    )


class DataGraphV2:
    def __init__(self, relationships):
        self.relationships = relationships
        self.store = relationships.store
        with self.store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS data_graph_entity_reviews (workspace TEXT NOT NULL, owner TEXT NOT NULL, node_id TEXT NOT NULL, evidence_hash TEXT NOT NULL, entity_name TEXT NOT NULL, role TEXT NOT NULL, status TEXT NOT NULL, reviewed_at TEXT NOT NULL, PRIMARY KEY(workspace,owner,node_id))')
            db.execute('CREATE TABLE IF NOT EXISTS data_graph_audit (event_id TEXT PRIMARY KEY, workspace TEXT NOT NULL, owner TEXT NOT NULL, node_id TEXT NOT NULL, action TEXT NOT NULL, created_at TEXT NOT NULL)')

    def project(self, db, workspace, owner):
        view = deepcopy(self.relationships.get_in_transaction(db, workspace, owner))
        view['version'] = 2
        if not view['graph']:
            return view
        graph = view['graph']
        nodes = {n['node_id']: n for n in graph['nodes']}
        datasets, fields, hierarchy = {}, {}, {}
        # Project the snapshots used by this graph, not newer snapshots during a rebuild.
        for version in graph['sources']:
            cid = version['connection_id']
            if cid not in nodes:
                continue
            row = db.execute('SELECT document FROM data_source_snapshots WHERE connection_id=? AND revision=?', (cid, version['revision'])).fetchone()
            if not row:
                raise ApiFailure('DATA_GRAPH_SNAPSHOT_UNAVAILABLE', 'The graph snapshot is unavailable. Rebuild metadata and relationships.', 409)
            snapshot = json.loads(row[0])
            for dataset in snapshot['datasets']:
                did = dataset['dataset_id']
                if did not in nodes:
                    continue
                datasets[did] = dataset
                database = dataset['database']
                dbid = 'database_' + fingerprint([cid, database])[:32]
                hierarchy[dbid] = dict(node_id=dbid, kind='database', label=database, connection_id=cid, parent_id=cid, types=[], discovery_method='declared', description='', metadata={})
                parent = dbid
                if dataset.get('schema') is not None:
                    parent = 'schema_' + fingerprint([cid, database, dataset['schema']])[:32]
                    hierarchy[parent] = dict(node_id=parent, kind='schema', label=dataset['schema'], connection_id=cid, parent_id=dbid, types=[], discovery_method='declared', description='', metadata={})
                nodes[did]['parent_id'] = parent
                nodes[did]['metadata'] = {k: dataset.get(k) for k in ('name', 'database', 'schema', 'kind', 'indexes', 'constraints', 'discovery_method', 'sample_count', 'has_validation_rules', 'validation_schema_json')}
                for field in dataset['fields']:
                    if field['field_id'] in nodes:
                        fields[field['field_id']] = (did, field)
                        nodes[field['field_id']]['metadata'] = field
        for node in nodes.values():
            node.setdefault('metadata', {})
        reviews = {r[0]: r[1:] for r in db.execute('SELECT node_id,evidence_hash,entity_name,role,status,reviewed_at FROM data_graph_entity_reviews WHERE workspace=? AND owner=?', (workspace, owner)).fetchall()}
        mappings, entities = [], {}

        def mapping(nid, proposed, role, evidence):
            if not proposed:
                return
            digest = fingerprint(structural(evidence))
            review = reviews.get(nid)
            name, chosen_role, status, reviewed = proposed, role, 'suggested', None
            if review:
                name, chosen_role = review[1:3]
                status = review[3] if review[0] == digest else 'needs_review'
                reviewed = review[4]
            eid = entity_id(name)
            entities[eid] = dict(node_id=eid, kind='entity', label=name, connection_id='', parent_id=None, types=[], discovery_method='reviewable_concept', description='', metadata={'execution_authority': False})
            mappings.append(dict(node_id=nid, entity_id=eid, entity_name=name, proposed_name=proposed, role=chosen_role, status=status, evidence_hash=digest, reviewed_at=reviewed,
                                 evidence=['Dataset/identifier naming suggests a business concept; this is not a proven business fact.', 'Confirmation supplies meaning only, never a join or tool permission.']))

        for did, dataset in datasets.items():
            mapping(did, singular(dataset['name']), 'represents', dataset)
        for fid, (did, field) in fields.items():
            dataset = datasets[did]
            name = field_stem(field['name'])
            own_key = field['name']=='_id' and dataset.get('schema') is None or any(c.get('kind')=='primary_key' and c.get('columns')==[field['name']] for c in dataset.get('constraints', []))
            if own_key and identifier(field['name'])=='id':
                name = singular(dataset['name'])
            if name or fid in reviews:
                proposed = name or singular(dataset['name'])
                role = 'identifier' if identifier(proposed) == identifier(singular(dataset['name'])) else 'reference'
                mapping(fid, proposed, role, dict(field=field, dataset=dataset['name'], schema=dataset.get('schema'), keys=dataset.get('constraints', []), indexes=dataset.get('indexes', [])))
        graph['nodes'] = [*nodes.values(), *hierarchy.values(), *entities.values()]
        graph['mappings'] = mappings
        review_hashes = dict(db.execute('SELECT relationship_id,evidence_hash FROM data_relationship_reviews WHERE workspace=? AND owner=?', (workspace, owner)).fetchall())
        for edge in graph['relationships']:
            edge['qualification'] = qualify(edge, datasets)
            edge['review_stale'] = bool(edge['relationship_id'] in review_hashes and review_hashes[edge['relationship_id']] != edge['evidence_hash'])
        graph['warnings'] = sorted(set([*graph['warnings'], 'Business entities are naming suggestions until reviewed. Entity mappings never authorize execution.']))
        if len(graph['nodes']) > 16000 or len(json.dumps(view).encode()) > 8_000_000:
            raise ApiFailure('DATA_GRAPH_LIMIT', 'The detailed graph exceeds its bounded view. Reduce the profiled source scope.', 422)
        return view

    def get(self, auth):
        workspace, owner = GoogleConnections.identity(auth)
        with self.store.transaction(write=False) as db:
            return self.project(db, workspace, owner)

    def edit(self, auth, node_id, body):
        workspace, owner = GoogleConnections.identity(auth, True)
        if not isinstance(body, dict) or set(body) != {'revision', 'entity_name', 'role', 'status'} or type(body.get('revision')) is not int:
            raise ApiFailure('DATA_GRAPH_INPUT_INVALID', 'Supply the exact graph revision, entity name, mapping role and review status.', 400)
        name = body['entity_name']
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80 or not re.fullmatch(r'[\w -]+', name.strip(), flags=re.UNICODE):
            raise ApiFailure('DATA_GRAPH_INPUT_INVALID', 'Entity names must be 1–80 letters, digits, spaces, underscores or hyphens.', 400)
        if body['status'] not in ('suggested', 'confirmed', 'rejected') or body['role'] not in ('represents', 'identifier', 'reference', 'attribute'):
            raise ApiFailure('DATA_GRAPH_INPUT_INVALID', 'Use a supported mapping role and review status.', 400)
        with self.store.transaction() as db:
            view = self.project(db, workspace, owner)
            graph = view['graph']
            if not graph or view['stale'] or graph['revision'] != body['revision']:
                raise ApiFailure('DATA_RELATIONSHIP_STALE', 'Metadata or graph changed. Rebuild and reload before editing.', 409)
            node = next((n for n in graph['nodes'] if n['node_id'] == node_id and n['kind'] in ('dataset', 'field')), None)
            if not node:
                raise ApiFailure('DATA_RELATIONSHIP_NOT_FOUND', 'Graph item not found.', 404)
            if (node['kind']=='dataset') != (body['role']=='represents'):
                raise ApiFailure('DATA_GRAPH_INPUT_INVALID', 'Datasets represent entities; fields use identifier, reference or attribute roles.', 400)
            mapping = next((m for m in graph['mappings'] if m['node_id']==node_id), None)
            if mapping is None:
                # Ordinary attributes are explicitly assigned by the user, never guessed.
                parent = next(n for n in graph['nodes'] if n['node_id']==node['parent_id'])
                evidence = dict(field=node['metadata'], dataset=parent['metadata']['name'], schema=parent['metadata'].get('schema'), keys=parent['metadata'].get('constraints', []), indexes=parent['metadata'].get('indexes', []))
                digest = fingerprint(structural(evidence))
            else:
                digest = mapping['evidence_hash']
            if body['status']=='suggested':
                db.execute('DELETE FROM data_graph_entity_reviews WHERE workspace=? AND owner=? AND node_id=?', (workspace, owner, node_id))
            else:
                db.execute('INSERT INTO data_graph_entity_reviews VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(workspace,owner,node_id) DO UPDATE SET evidence_hash=excluded.evidence_hash,entity_name=excluded.entity_name,role=excluded.role,status=excluded.status,reviewed_at=excluded.reviewed_at',
                           (workspace, owner, node_id, digest, ' '.join(name.split()), body['role'], body['status'], now()))
            raw = json.loads(db.execute('SELECT document FROM data_relationship_graphs WHERE workspace=? AND owner=?', (workspace, owner)).fetchone()[0])
            raw['revision'] += 1
            db.execute('UPDATE data_relationship_graphs SET revision=?,document=? WHERE workspace=? AND owner=?', (raw['revision'], json.dumps(raw), workspace, owner))
            import secrets
            db.execute('INSERT INTO data_graph_audit VALUES (?,?,?,?,?,?)', ('dga_'+secrets.token_hex(16), workspace, owner, node_id, 'entity_mapping_'+body['status'], now()))
            return self.project(db, workspace, owner)
