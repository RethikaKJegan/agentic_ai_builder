"""Metadata-only ontology. Business predicates never authorize technical joins."""
import json
import re

from .data_relationships import fingerprint
from .google_connections import GoogleConnections, now
from .service import ApiFailure


class BusinessOntology:
    def __init__(self, relationships):
        self.relationships, self.store = relationships, relationships.store
        with self.store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS data_ontology_reviews (workspace TEXT NOT NULL, owner TEXT NOT NULL, relationship_id TEXT NOT NULL, evidence_hash TEXT NOT NULL, predicate TEXT NOT NULL, reversed INTEGER NOT NULL, status TEXT NOT NULL, reviewed_at TEXT NOT NULL, PRIMARY KEY(workspace,owner,relationship_id))')
            db.execute('CREATE TABLE IF NOT EXISTS data_ontology_audit (event_id TEXT PRIMARY KEY, workspace TEXT NOT NULL, owner TEXT NOT NULL, relationship_id TEXT NOT NULL, action TEXT NOT NULL, created_at TEXT NOT NULL)')

    def project(self, db, workspace, owner):
        detailed=self.relationships.detailed.project(db,workspace,owner)
        graph=detailed['graph']
        result=dict(version=1, revision='', stale=detailed['stale'], build_status=detailed['build_status'],
                    last_error=detailed['last_error'], graph_revision=graph['revision'] if graph else 0,
                    built_at=graph['built_at'] if graph else None, entities=[], relationships=[], warnings=[])
        if not graph:
            result['revision']=fingerprint([workspace,owner,'empty'])
            return result
        nodes={n['node_id']:n for n in graph['nodes']}
        mappings=[m for m in graph['mappings'] if m['status']!='rejected']
        by_node={m['node_id']:m for m in mappings}
        entities={}

        def path(nid):
            parts=[]; seen=set()
            while nid in nodes and nid not in seen:
                seen.add(nid); node=nodes[nid]
                parts.append(node['metadata'].get('name',node['label']) if node['kind']=='dataset' else node['label'])
                nid=node['parent_id']
            return ' / '.join(reversed(parts))

        for mapping in mappings:
            node=nodes[mapping['node_id']]
            entity=entities.setdefault(mapping['entity_id'],dict(entity_id=mapping['entity_id'],label=mapping['entity_name'],sources=[]))
            entity['sources'].append(dict(node_id=node['node_id'],connection_id=node['connection_id'],
                label=path(node['node_id']),kind=node['kind'],role=mapping['role'],status=mapping['status'],
                types=node['types'],metadata=node['metadata']))
        reviews={row[0]:row[1:] for row in db.execute('SELECT relationship_id,evidence_hash,predicate,reversed,status,reviewed_at FROM data_ontology_reviews WHERE workspace=? AND owner=?',(workspace,owner)).fetchall()}
        edges=[]
        for technical in graph['relationships']:
            if technical['status']=='rejected':
                continue
            left,right=(by_node.get(technical[k]) for k in ('source_dataset_id','target_dataset_id'))
            if not left or not right:
                continue
            rid='ontology_'+fingerprint(technical['relationship_id'])[:32]
            digest=fingerprint([technical['evidence_hash'],
                [{k:m[k] for k in ('entity_id','evidence_hash','status','role')} for m in (left,right)]])
            predicate='references' if technical['kind']=='declared' else 'is related to'
            reverse=False; status='suggested'; reviewed=None
            if rid in reviews:
                evidence,predicate,reverse,status,reviewed=reviews[rid]
                reverse=bool(reverse)
                if evidence!=digest:
                    status='needs_review'
            source,target=left['entity_id'],right['entity_id']
            if reverse:
                source,target=target,source
            edges.append(dict(relationship_id=rid,source_entity_id=source,target_entity_id=target,
                predicate=predicate,reversed=reverse,status=status,reviewed_at=reviewed,evidence_hash=digest,
                technical_relationship_id=technical['relationship_id'],technical_status=technical['status'],
                source_dataset_id=technical['source_dataset_id'],target_dataset_id=technical['target_dataset_id'],
                field_pairs=[dict(source_field_id=p['source_field_id'],target_field_id=p['target_field_id'],
                                 source_label=path(p['source_field_id']),target_label=path(p['target_field_id'])) for p in technical['field_pairs']],
                evidence=technical['evidence'],qualification=technical['qualification']))
        result.update(entities=list(entities.values()),relationships=edges,warnings=[*graph['warnings'],
            'Business labels and arrow direction are reviewable meaning, not executable joins. No business records were read for this view.'])
        # Independent semantic version: reviews do not invalidate query grants.
        result['revision']=fingerprint([graph['revision'],result['entities'],edges])
        if len(json.dumps(result).encode())>8_000_000:
            raise ApiFailure('DATA_ONTOLOGY_LIMIT','The knowledge graph exceeds its bounded view. Reduce the profiled source scope.',422)
        return result

    def get(self, auth):
        workspace,owner=GoogleConnections.identity(auth)
        with self.store.transaction(write=False) as db:
            return self.project(db,workspace,owner)

    def edit(self, auth, rid, body):
        workspace,owner=GoogleConnections.identity(auth,True)
        if (not isinstance(body,dict) or set(body)!={'revision','predicate','reversed','status'}
                or not isinstance(body['revision'],str) or type(body['reversed']) is not bool
                or body['status'] not in {'suggested','confirmed','rejected'}
                or not isinstance(body['predicate'],str)
                or not re.fullmatch(r'[\w][\w /-]{0,79}',body['predicate'].strip(),re.UNICODE)):
            raise ApiFailure('DATA_ONTOLOGY_INVALID','Supply the current revision, a label of 1–80 characters, direction and review status.',400)
        with self.store.transaction() as db:
            view=self.project(db,workspace,owner)
            if view['stale'] or view['revision']!=body['revision']:
                raise ApiFailure('DATA_ONTOLOGY_STALE','The knowledge graph changed. Reload current metadata before reviewing.',409)
            edge=next((e for e in view['relationships'] if e['relationship_id']==rid),None)
            if edge is None:
                raise ApiFailure('DATA_ONTOLOGY_NOT_FOUND','Business relationship not found.',404)
            if body['status']=='suggested':
                db.execute('DELETE FROM data_ontology_reviews WHERE workspace=? AND owner=? AND relationship_id=?',(workspace,owner,rid))
            else:
                db.execute('INSERT INTO data_ontology_reviews VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(workspace,owner,relationship_id) DO UPDATE SET evidence_hash=excluded.evidence_hash,predicate=excluded.predicate,reversed=excluded.reversed,status=excluded.status,reviewed_at=excluded.reviewed_at',
                    (workspace,owner,rid,edge['evidence_hash'],body['predicate'].strip(),int(body['reversed']),body['status'],now()))
            import secrets
            db.execute('INSERT INTO data_ontology_audit VALUES (?,?,?,?,?,?)',('onto_'+secrets.token_hex(16),workspace,owner,rid,body['status'],now()))
            semantic=getattr(self,'semantic',None)
            if semantic is not None:semantic.capture_legacy(db,workspace,owner)
            return self.project(db,workspace,owner)
