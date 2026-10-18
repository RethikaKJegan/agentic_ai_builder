"""Owned, metadata-only lexical retrieval before workflow planning.

The persistent inverted index never stores business rows or credentials. Saved
metadata changes invalidate it; unchanged automatic profiles do not rebuild it.
"""
from collections import defaultdict, deque
import json
import re

from .data_relationships import fingerprint
from .google_connections import GoogleConnections, now
from .service import ApiFailure

STOP = set('a an the this that these those i we my our me please workflow create build find show list get with from for of in on at and or to by as is are be all only use using then into it its them their should can could would need want track tracking report review send email calendar schedule meeting'.split())


def terms(value):
    value = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', str(value))
    result = set()
    for word in re.findall(r'[^\W_]+', value.lower(), re.UNICODE):
        if len(word) < 2 or word in STOP or word.isdigit():
            continue
        if len(word) > 4 and word.endswith('ies'):
            word = word[:-3]+'y'
        elif len(word) > 3 and word.endswith('s') and not word.endswith(('ss', 'us')):
            word = word[:-1]
        result.add(word)
    return result


class KnowledgeRetrieval:
    def __init__(self, coordinator):
        self.c, self.store = coordinator, coordinator.store
        with self.store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS kg_retrieval_state (workspace TEXT NOT NULL, owner TEXT NOT NULL, revision TEXT NOT NULL, document TEXT NOT NULL, PRIMARY KEY(workspace,owner))')
            db.execute('CREATE TABLE IF NOT EXISTS kg_retrieval_sources (workspace TEXT NOT NULL, owner TEXT NOT NULL, dataset_id TEXT NOT NULL, document TEXT NOT NULL, PRIMARY KEY(workspace,owner,dataset_id))')
            db.execute('CREATE TABLE IF NOT EXISTS kg_retrieval_terms (workspace TEXT NOT NULL, owner TEXT NOT NULL, term TEXT NOT NULL, dataset_id TEXT NOT NULL, weight INTEGER NOT NULL, reason TEXT NOT NULL, PRIMARY KEY(workspace,owner,term,dataset_id,reason))')
            db.execute('CREATE INDEX IF NOT EXISTS kg_retrieval_lookup ON kg_retrieval_terms(workspace,owner,term)')

    def signature(self, auth):
        workspace, owner = GoogleConnections.identity(auth)
        with self.store.transaction(write=False) as db:
            connections = [json.loads(row[0]) for row in db.execute('SELECT document FROM data_source_connections WHERE workspace=? AND owner=? ORDER BY connection_id', (workspace,owner)).fetchall()]
            stamps = []
            for table, columns, order in (
                ('data_relationship_graphs', 'revision,input_hash', 'revision'),
                ('data_relationship_jobs', 'state,error', 'state'),
                ('data_relationship_annotations', 'node_id,description', 'node_id'),
                ('data_relationship_reviews', 'relationship_id,evidence_hash,status', 'relationship_id'),
                ('data_graph_entity_reviews', 'node_id,evidence_hash,entity_name,role,status', 'node_id'),
                ('data_ontology_reviews', 'relationship_id,evidence_hash,predicate,reversed,status', 'relationship_id'),
                ('kg_semantic_proposals', 'relationship_id,evidence_hash,document', 'relationship_id'),
                ('kg_semantic_reviews', 'relationship_id,evidence_hash,predicate,reversed,status', 'relationship_id')):
                stamps.append(db.execute(f'SELECT {columns} FROM {table} WHERE workspace=? AND owner=? ORDER BY {order}', (workspace, owner)).fetchall())
        revision = fingerprint([[(c['connection_id'],c['generation'],c['metadata_revision'],c['connection_status']) for c in connections], stamps, self.c.operations.policy(), 1])
        return workspace, owner, revision, connections

    def sync(self, auth):
        # Double-check around construction: a concurrent metadata edit must never
        # publish a mixed index under the old revision.
        for _ in range(3):
            workspace, owner, revision, connections = self.signature(auth)
            with self.store.transaction(write=False) as db:
                cached = db.execute('SELECT revision,document FROM kg_retrieval_state WHERE workspace=? AND owner=?', (workspace,owner)).fetchone()
            if cached and cached[0] == revision:
                return revision, json.loads(cached[1])
            catalog = self.c.catalog(auth, bounded=False)
            view = self.c.manager.semantic.get(auth)
            detailed = self.c.manager.relationships.detailed.get(auth)
            graph = detailed.get('graph') or {}
            annotations = {n['node_id']:n.get('description','') for n in graph.get('nodes', [])}
            field_parents = {f['field_id']:s['dataset_id'] for s in catalog['sources'] for f in s['fields']}
            mapped = defaultdict(list)
            for mapping in catalog['business_mappings']:
                did = field_parents.get(mapping['node_id'], mapping['node_id'])
                mapped[did].append(mapping['entity_name'])
            predicates = defaultdict(list)
            if not view['stale']:
                for edge in view['relationships']:
                    if edge['status'] in {'confirmed','inferred'} and edge['predicate']:
                        for did in (edge['source_dataset_id'],edge['target_dataset_id']):
                            predicates[did].append((edge['predicate'],edge['status']))
            available_ids={s['dataset_id'] for s in catalog['sources']}
            executable_edges=[e for e in catalog['relationships'] if e['status'] in {'declared','accepted'} and {e['source_dataset_id'],e['target_dataset_id']}<=available_ids]
            state = dict(graph_hash=catalog['graph_hash'], relationships=executable_edges,
                         business_mappings=catalog['business_mappings'], business_relationships=[e for e in view['relationships'] if e['status'] in {'confirmed','inferred'} and e['predicate']] if not view['stale'] else [], warnings=list(graph.get('warnings', [])),
                         indexed_at=now(), connection_count=sum(c['connection_status']=='connected' for c in connections),
                         dataset_count=len(catalog['sources']), graph_stale=bool(view['stale'] or not detailed.get('graph')),
                         unprofiled_connections=sum(c['connection_status']!='disconnected' and not c['metadata_revision'] for c in connections))
            if self.signature(auth)[2] != revision:
                continue
            with self.store.transaction() as db:
                for table in ('kg_retrieval_terms','kg_retrieval_sources'):
                    db.execute(f'DELETE FROM {table} WHERE workspace=? AND owner=?', (workspace,owner))
                for source in catalog['sources']:
                    did = source['dataset_id']
                    db.execute('INSERT INTO kg_retrieval_sources VALUES (?,?,?,?)', (workspace,owner,did,json.dumps(source)))
                    entries = [(source['label'].split(' / ')[-1], 10, 'dataset name'),
                               (source['label'], 2, 'source path'), (annotations.get(did,''), 6, 'saved description')]
                    entries += [(f['name'], 5, 'field '+f['name']) for f in source['fields']]
                    entries += [(annotations.get(f['field_id'],''), 4, 'field description '+f['name']) for f in source['fields']]
                    entries += [(name, 9, 'confirmed concept '+name) for name in mapped[did]]
                    entries += [(label, 6 if status=='confirmed' else 4, status+' semantic relationship '+label) for label,status in predicates[did]]
                    rows = set((workspace,owner,term,did,weight,reason) for text,weight,reason in entries for term in terms(text))
                    for row in rows:
                        db.execute('INSERT INTO kg_retrieval_terms VALUES (?,?,?,?,?,?)',row)
                db.execute('INSERT INTO kg_retrieval_state VALUES (?,?,?,?) ON CONFLICT(workspace,owner) DO UPDATE SET revision=excluded.revision,document=excluded.document', (workspace,owner,revision,json.dumps(state)))
            if self.signature(auth)[2] != revision:
                continue
            return revision, state
        raise ApiFailure('KG_RETRIEVAL_CHANGED','Metadata changed while preparing the source preview. Retry the preview.',409)

    def retrieve(self, auth, objective, selection=None, *, planning=False):
        auth = self.c.current(auth)
        if not isinstance(objective,str) or not 1 <= len(objective.strip()) <= 12000:
            raise ApiFailure('KG_RETRIEVAL_INPUT','Provide a workflow description of 1–12000 characters.',400)
        if selection is not None and (not isinstance(selection,dict) or set(selection)!={'revision','source_ids'} or
            not isinstance(selection['revision'],str) or not isinstance(selection['source_ids'],list) or
            not 1 <= len(selection['source_ids']) <= 4 or any(not isinstance(x,str) for x in selection['source_ids']) or len(set(selection['source_ids'])) != len(selection['source_ids'])):
            raise ApiFailure('KG_RETRIEVAL_INPUT','Select one to four current source IDs and the preview revision.',400)
        revision, state = self.sync(auth)
        workspace, owner = GoogleConnections.identity(auth)
        if selection and selection['revision'] != revision:
            raise ApiFailure('KG_RETRIEVAL_STALE','Knowledge graph metadata changed. Refresh the source preview before generating.',409)
        query = sorted(terms(objective))[:48]
        hits, reasons, matched = defaultdict(dict), defaultdict(set), defaultdict(set)
        with self.store.transaction(write=False) as db:
            for term in query:
                rows = db.execute('SELECT dataset_id,weight,reason FROM kg_retrieval_terms WHERE workspace=? AND owner=? AND term=? ORDER BY weight DESC,dataset_id,reason LIMIT 2001', (workspace,owner,term)).fetchall()
                if len(rows)>2000:
                    state={**state,'warnings':[*state['warnings'],'A broad search term exceeded 2000 matches. Use more specific dataset or field names.']}
                for did,weight,reason in rows[:2000]:
                    hits[did][term]=max(hits[did].get(term,0),weight)
                    reasons[did].add(f'{reason} matches “{term}”.')
                    matched[did].add(term)
            scores={did:sum(weights.values()) for did,weights in hits.items()}
            ranked=sorted(scores,key=lambda did:(-scores[did],did))
            candidates=ranked[:12]
            seeds=[did for did in ranked if any(w>=6 for w in hits[did].values())]
            covered=set().union(*(matched[did] for did in seeds)) if seeds else set()
            for did in ranked:
                if did not in seeds and any(w>=5 and term not in covered for term,w in hits[did].items()):
                    seeds.append(did);covered.update(matched[did])
            chosen=list(selection['source_ids']) if selection else seeds[:4]
            # Explicit selection may choose any currently owned indexed source,
            # but cannot inject source descriptors, tools, fields or grants.
            for did in chosen:
                row=db.execute('SELECT document FROM kg_retrieval_sources WHERE workspace=? AND owner=? AND dataset_id=?',(workspace,owner,did)).fetchone()
                if not row:
                    raise ApiFailure('KG_RETRIEVAL_SOURCE','A selected source is no longer available in your workspace.',403)
                if did not in candidates:candidates.append(did)
            def load(did):
                row=db.execute('SELECT document FROM kg_retrieval_sources WHERE workspace=? AND owner=? AND dataset_id=?',(workspace,owner,did)).fetchone()
                return json.loads(row[0])
            indexed={did:load(did) for did in candidates}
        warnings=list(state['warnings'])
        if state['graph_stale']:warnings.append('The relationship graph is stale; refresh it before planning joined database operations.')
        if state['unprofiled_connections']:warnings.append('Some connections have no discovered metadata and cannot be searched yet.')
        # Equally ranked alternatives with the same matching vocabulary require a
        # user choice instead of silently selecting a database by ID order.
        ambiguous=not selection and any(scores[a]==scores[b] and matched[a]==matched[b] for i,a in enumerate(seeds) for b in seeds[i+1:])
        over_budget=not selection and len(seeds)>4
        if ambiguous:warnings.append('Several sources match equally. The planner must justify its source choice or record unresolved meaning.' if planning else 'Several sources match equally. Choose the intended sources and refresh the preview.')
        if over_budget:warnings.append('More than four sources match. The planner must select only the required one to four execution sources from the bounded candidates.' if planning else 'More than four sources match. Choose up to four sources for this workflow.')
        edges=state['relationships']
        adjacency=defaultdict(list)
        for e in edges:
            a,b=e['source_dataset_id'],e['target_dataset_id']
            adjacency[a].append(b);adjacency[b].append(a)
        # Connect selected seeds through at most three technical hops, never
        # through a merely semantic or suggested link.
        expanded=set(chosen)
        if chosen and not state['graph_stale']:
            for target in chosen[1:]:
                queue=deque([(chosen[0],[chosen[0]])]);seen={chosen[0]};path=None
                while queue:
                    item,trail=queue.popleft()
                    if item==target:path=trail;break
                    if len(trail)>=4:continue
                    for neighbor in sorted(adjacency[item]):
                        if neighbor not in seen:seen.add(neighbor);queue.append((neighbor,[*trail,neighbor]))
                if path:
                    expanded.update(path)
                else:warnings.append('Selected sources have no declared/accepted path within three hops. Cross-source joins must remain unresolved.')
        if len(expanded)>4:
            warnings.append('The relationship path needs more than four sources. Narrow this workflow.');over_budget=True
        else:
            for did in sorted(expanded-set(chosen)):
                with self.store.transaction(write=False) as db:
                    row=db.execute('SELECT document FROM kg_retrieval_sources WHERE workspace=? AND owner=? AND dataset_id=?',(workspace,owner,did)).fetchone()
                if row:
                    indexed[did]=json.loads(row[0])
                    if did not in candidates:candidates.append(did)
                    chosen.append(did)
                    reasons[did].add('Required intermediate dataset on a declared/accepted relationship path.')
        selected=[indexed[did] for did in chosen]
        if len(json.dumps(selected).encode())>70000:
            raise ApiFailure('KG_RETRIEVAL_LIMIT','The selected field metadata is too large. Choose fewer sources.',422)
        selected_ids=set(chosen)
        path_edges=[e for e in edges if {e['source_dataset_id'],e['target_dataset_id']}<=selected_ids]
        semantic_edges=[{k:e[k] for k in ('relationship_id','technical_relationship_id','source_dataset_id','target_dataset_id','predicate','reversed','status','semantic_evidence_hash','evidence_refs','confidence')} for e in state.get('business_relationships',[]) if {e['source_dataset_id'],e['target_dataset_id']}<=selected_ids]
        preview=dict(version=2,semantic_relationships=semantic_edges,revision=revision,indexed_at=state['indexed_at'],
            coverage=dict(connections=state['connection_count'],datasets=state['dataset_count'],matched_datasets=len(ranked),candidate_limit=12,source_limit=4,metadata_only=True),
            query_terms=query,requires_selection=bool((ambiguous or over_budget) and not planning),graph_stale=state['graph_stale'],
            candidates=[dict(dataset_id=did,connection_id=indexed[did]['connection_id'],label=indexed[did]['label'],engine=indexed[did]['engine'],
                score=scores.get(did,0),selected=did in selected_ids,reasons=sorted(reasons[did])[:12] or ['Explicitly selected current source.'],
                fields=[f['name'] for f in indexed[did]['fields']][:64],operations=indexed[did]['operations']) for did in candidates],
            source_ids=chosen,relationships=[dict(relationship_id=e['relationship_id'],source_dataset_id=e['source_dataset_id'],target_dataset_id=e['target_dataset_id'],status=e['status'],field_pairs=e['field_pairs']) for e in path_edges],
            warnings=sorted(set(warnings)),tools=[])
        if not ranked and state['dataset_count']:
            preview['warnings'].append('No metadata names, descriptions or confirmed concepts match this prompt. Database sources will not be guessed; use a more specific prompt.')
        if planning and selection is None:
            # Retrieval proposes bounded candidates; only validated model choices
            # become the execution scope in bind_generated. No extra model call.
            pool=list(dict.fromkeys([*candidates,*chosen]))[:16]
            pool_sources=[indexed[did] for did in pool]
            if len(json.dumps(pool_sources).encode())>70000:
                raise ApiFailure('KG_RETRIEVAL_LIMIT','Relevant source metadata exceeds the bounded planning context.',422)
            pool_ids=set(pool)
            selected=pool_sources
            path_edges=[e for e in edges if {e['source_dataset_id'],e['target_dataset_id']}<=pool_ids]
            preview['semantic_relationships']=[{k:e[k] for k in ('relationship_id','technical_relationship_id','source_dataset_id','target_dataset_id','predicate','reversed','status','semantic_evidence_hash','evidence_refs','confidence')} for e in state.get('business_relationships',[]) if {e['source_dataset_id'],e['target_dataset_id']}<=pool_ids]
            selected_ids=pool_ids
        catalog=dict(semantic_revision=revision,business_relationships=[e for e in state.get('business_relationships',[]) if {e['source_dataset_id'],e['target_dataset_id']}<=selected_ids],sources=selected,graph_hash=state['graph_hash'],relationships=path_edges,
                     business_mappings=[m for m in state['business_mappings'] if m['node_id'] in selected_ids or m['node_id'] in {f['field_id'] for s in selected for f in s['fields']}])
        return preview,catalog
