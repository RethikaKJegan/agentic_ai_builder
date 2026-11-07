"""One logical account graph, with permission-preserving owner projections.

Adapters ingest only existing backend-validated knowledge/evidence. Immutable
projection revisions share the workflow store; no model output grants authority,
no identifier-only entity merge and no new graph database are introduced.
"""
from copy import deepcopy
from functools import wraps
from threading import Lock
import json
import time

from registry.safety import reject_secrets
from runtime.service import RuntimeService,RuntimeFailure,digest


def projection_digest(value):
    def stable(item):
        if isinstance(item,list):return [stable(v) for v in item]
        if isinstance(item,dict):return {k:stable(v) for k,v in item.items() if k not in ('read_at','created_at','request_id')}
        return item
    return digest(stable(value))


def observed(operation):
    def decorate(function):
        @wraps(function)
        def measured(self,*args,**kwargs):
            started=time.monotonic();failed=False
            try:return function(self,*args,**kwargs)
            except Exception:
                failed=True
                raise
            finally:
                with self.metrics_lock:
                    self.metrics[operation+'_calls']+=1
                    self.metrics[operation+'_seconds']+=time.monotonic()-started
                    self.metrics[operation+'_failures']+=int(failed)
        return measured
    return decorate


class AccountKnowledge:
    def __init__(self,store,service=None,clock=time.time):
        self.store,self.service,self.clock=store,service,clock
        self.metrics_lock=Lock()
        self.metrics={name+suffix:0 for name in ('sync','retrieval') for suffix in ('_calls','_seconds','_failures')}
        with store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS account_graph_revisions (workspace TEXT NOT NULL, owner TEXT NOT NULL, source_key TEXT NOT NULL, revision BIGINT NOT NULL, sha256 TEXT NOT NULL, document TEXT NOT NULL, PRIMARY KEY(workspace,owner,source_key,revision))')
            db.execute('CREATE TABLE IF NOT EXISTS account_graph_heads (workspace TEXT NOT NULL, owner TEXT NOT NULL, source_key TEXT NOT NULL, revision BIGINT NOT NULL, checked_at DOUBLE PRECISION NOT NULL, state TEXT NOT NULL, PRIMARY KEY(workspace,owner,source_key))')
            db.execute('CREATE TABLE IF NOT EXISTS account_graph_execution (workspace TEXT NOT NULL, owner TEXT NOT NULL, run_id TEXT NOT NULL, document TEXT NOT NULL, PRIMARY KEY(workspace,owner,run_id))')

    @staticmethod
    def scope(auth,write=False):
        RuntimeService.authorize(auth,'workflow.plan' if write else 'runs.view',{'admin','builder'} if write else {'admin','builder','viewer','approver'})
        return auth['subject']['workspace_id'],auth['subject']['subject_id']

    @staticmethod
    def identity(scope,kind,*parts):return kind+'_'+digest([*scope,*parts])[:40]

    def _sync(self,auth,source_key,kind,pins,nodes,edges):
        scope=self.scope(auth,True)
        # This private method is reached by trusted adapters, never a public JSON
        # ingestion route. All values remain untrusted reference data to agents.
        reject_secrets([pins,nodes,edges])
        if len(nodes)>1000 or len(edges)>2000 or len(json.dumps([nodes,edges]).encode())>1_000_000:
            raise RuntimeFailure('ACCOUNT_GRAPH_LIMIT','Knowledge projection exceeds the existing bounded evidence allowance.',422)
        payload=dict(kind=kind,pins=deepcopy(pins),nodes=nodes,edges=edges)
        sha=projection_digest(payload)
        with self.store.transaction() as db:
            head=db.execute('SELECT revision FROM account_graph_heads WHERE workspace=? AND owner=? AND source_key=?',(*scope,source_key)).fetchone()
            revision=head[0] if head else 0
            old=db.execute('SELECT sha256,document FROM account_graph_revisions WHERE workspace=? AND owner=? AND source_key=? AND revision=?',(*scope,source_key,revision)).fetchone() if head else None
            if old and kind=='preparation':
                # Keep historical hash semantics. A new read can produce a new
                # preflight ID without changing business evidence; refresh the
                # existing pin only when every other hashed field is identical.
                candidate=deepcopy(payload)
                candidate['pins']['preflight_id']=json.loads(old[1])['pins']['preflight_id']
                if projection_digest(candidate)==old[0]:sha=old[0]
            if not old or old[0]!=sha:
                revision+=1
                doc=dict(schema_version='account-knowledge-v1',graph_id='account_'+digest(scope[0])[:32],source_key=source_key,revision=revision,sha256=sha,created_at=self.clock(),**payload)
                db.execute('INSERT INTO account_graph_revisions VALUES (?,?,?,?,?,?)',(*scope,source_key,revision,sha,json.dumps(doc)))
            db.execute("INSERT INTO account_graph_heads VALUES (?,?,?,?,?,'current') ON CONFLICT(workspace,owner,source_key) DO UPDATE SET revision=excluded.revision,checked_at=excluded.checked_at,state=excluded.state",(*scope,source_key,revision,self.clock()))
        return dict(graph_id='account_'+digest(scope[0])[:32],source_key=source_key,revision=revision,sha256=sha)

    @observed('sync')
    def sync_preparation(self,auth,preparation,preflight_id):
        scope=self.scope(auth,True)
        doc=preparation.checked(auth,preflight_id)
        if doc['scope']['workspace_id']!=scope[0] or doc['scope']['owner_id']!=scope[1]:
            raise RuntimeFailure('ACCOUNT_GRAPH_SCOPE','Knowledge belongs to a different owner.',403)
        version=preparation.service.ontology.version(auth,doc['pins']['ontology_version'])
        knowledge=version.get('knowledge',{})
        nodes={};edges={};record_ids={};concepts={};mappings={}
        for task in doc['tasks'].values():
            for c in task['concepts']:
                nid=self.identity(scope,'concept',c['id']);nodes[nid]=dict(node_id=nid,kind='concept',reference=c['id'],label=c.get('label',c['id']),status='confirmed',qualification='Saved ontology definition, not a source fact.')
                concepts[c['id']]=nid
            for m in task['mappings']:mappings[m['id']]=m
        def edge(source,target,predicate,status,evidence,reference,kind):
            eid=self.identity(scope,'edge',reference,source,target,predicate)
            edges[eid]=dict(edge_id=eid,source=source,target=target,predicate=predicate,direction='source_to_target',status=status,kind=kind,
                evidence=deepcopy(evidence),source_references=deepcopy(evidence),ontology_version=doc['pins']['ontology_version'],mapping_version=doc['pins']['mapping_sha256'],confidence=None,read_at=self.clock())
        for packet in doc['available_evidence'].values():
            for r in packet.get('records',[]):
                nid=self.identity(scope,'record',r.get('connection_id'),r['collection'],r.get('source_reference',r['record_id']))
                record_ids[r['record_id']]=nid
                current=dict(node_id=nid,kind='record',reference=r['record_id'],source=dict(connection_id=r.get('connection_id'),role=r.get('source_role'),collection=r['collection'],native_identity=deepcopy(r.get('source_reference'))),
                    values=deepcopy(r.get('values',{})),read_at=r.get('read_at'),status='reported',qualification='Reported mapped source values; not independently confirmed business conclusions.')
                if nid in nodes:
                    previous=nodes[nid]['values']
                    if nodes[nid]['status']=='conflicting' or any(previous[k]!=current['values'][k] for k in previous.keys()&current['values'].keys()):
                        current['status']='conflicting'
                        observations=nodes[nid].get('conflicting_observations',[previous])
                        current['conflicting_observations']=observations+([current['values']] if current['values'] not in observations else [])
                    current['values']={**previous,**current['values']}
                nodes[nid]=current
                for mid in r.get('values',{}):
                    concept=mappings.get(mid,{}).get('concept_id')
                    if concept in concepts:edge(nid,concepts[concept],'mapped_to','confirmed',[dict(record_id=r['record_id'],mapping_id=mid)],mid,'mapping')
        details={r['binding_id']:r for r in knowledge.get('relationship_details',[]) if r.get('traversable') and r.get('binding_id')}
        bindings={r['id']:r for r in knowledge.get('identity_rules',[])}
        relationships={r['id']:r for r in version.get('relationships',[])}
        for packet in doc['available_evidence'].values():
            for r in packet.get('reference_edges',[]):
                source,target=record_ids.get(r['record_id']),record_ids.get(r['parent_record_id'])
                if not source or not target:continue
                detail=details.get(r['binding_id']);definition=relationships.get(detail['relationship_id'],{}) if detail else {}
                # A directly observed native reference is confirmed as a technical
                # link. A saved semantic label stays inferred without review.
                edge(source,target,'direct_reference','confirmed',[r],r['binding_id'],'source_reference')
                if definition:
                    predicate=definition.get('label') or definition.get('name') or definition['id']
                    binding=bindings.get(r['binding_id'],{})
                    expected=binding.get('source',{})
                    observed=nodes[source]['source']
                    reverse=nodes[target]['source']
                    if (observed.get('role'),observed['collection'])==(expected.get('source_role'),expected.get('collection')):
                        edge(source,target,predicate,'inferred',[r,detail['provenance']],definition['id'],'business_relationship')
                    elif (reverse.get('role'),reverse['collection'])==(expected.get('source_role'),expected.get('collection')):
                        edge(target,source,predicate,'inferred',[r,detail['provenance']],definition['id'],'business_relationship')
            for r in packet.get('ambiguous_associations',[]):
                source,target=record_ids.get(r.get('left')),record_ids.get(r.get('right'))
                if source and target:edge(source,target,'candidate_association','ambiguous',[r],r['binding_id'],'candidate')
        key='preparation:'+digest([doc.get('domain_context',{}),doc.get('inputs',{}),sorted(doc['tasks'])])
        pins={**deepcopy(doc['pins']),'preflight_id':preflight_id}
        return self._sync(auth,key,'preparation',pins,sorted(nodes.values(),key=lambda n:n['node_id']),sorted(edges.values(),key=lambda e:e['edge_id']))

    @observed('sync')
    def sync_package_definition(self,auth,packages,package):
        scope=self.scope(auth,True)
        p=packages.get(auth,package['package_id'],package['revision'])
        if p['sha256']!=package['sha256']:raise RuntimeFailure('ACCOUNT_GRAPH_VERSION','Client knowledge changed.')
        nodes=[dict(node_id=self.identity(scope,'concept',p['package_id'],c['id']),kind='concept',reference=c['id'],label=c.get('label',c['id']),status='confirmed',qualification='Saved package definition; no source records have been observed.') for c in p['concepts']]
        return self._sync(auth,'package-definition:'+p['package_id'],'package_definition',dict(package_id=p['package_id'],revision=p['revision'],package_sha256=p['sha256']),nodes,[])

    @observed('sync')
    def sync_package(self,auth,packages,package,evidence,capability):
        scope=self.scope(auth,True)
        p=packages.get(auth,package['package_id'],package['revision'])
        if p['sha256']!=package['sha256']:raise RuntimeFailure('ACCOUNT_GRAPH_VERSION','Client knowledge changed.')
        nodes=[];edges=[];concepts={}
        for c in p['concepts']:
            nid=self.identity(scope,'concept',p['package_id'],c['id']);concepts[c['id']]=nid
            nodes.append(dict(node_id=nid,kind='concept',reference=c['id'],label=c.get('label',c['id']),status='confirmed'))
        binding=p['resource_bindings'][capability];mappings={m['id']:m for m in p['source_mappings']}
        records={}
        for r in evidence['records']:
            nid=self.identity(scope,'record',p['package_id'],binding['source_id'],r['record_id'])
            current=dict(node_id=nid,kind='record',reference=r['record_id'],source_reference=binding['source_id'],values=deepcopy(r['values']),status='conflicting' if evidence['coverage']['state']=='conflicting_evidence' else 'reported',read_at=r['read_at'])
            if nid in records:
                previous=records[nid]
                observations=previous.get('conflicting_observations',[previous['values']])
                if current['values'] not in observations:observations=observations+[current['values']]
                current['conflicting_observations']=observations
                current['status']='conflicting' if len(observations)>1 else previous['status']
            records[nid]=current
            for mid in r['values']:
                target=concepts.get(mappings[mid]['concept'])
                if target:edges.append(dict(edge_id=self.identity(scope,'edge',nid,target,mid),source=nid,target=target,predicate='mapped_to',direction='source_to_target',status='confirmed',kind='mapping',evidence=[dict(record_id=r['record_id'],mapping_id=mid)],source_references=[binding['source_id']],ontology_version=p['ontology_version'],mapping_version=p['sha256'],confidence=None))
        nodes.extend(records.values())
        edges=list({e['edge_id']:e for e in edges}.values())
        return self._sync(auth,'package:'+p['package_id']+':'+capability,'package',dict(package_id=p['package_id'],revision=p['revision'],package_sha256=p['sha256'],capability_id=capability),nodes,edges)

    @observed('sync')
    def sync_semantic(self,auth,semantic):
        scope=self.scope(auth,True);view=semantic.get(auth)
        if view['stale']:raise RuntimeFailure('ACCOUNT_GRAPH_STALE','Refresh source metadata before graph synchronization.')
        nodes={};edges=[]
        for r in view['relationships']:
            for key in ('source_dataset_id','target_dataset_id'):
                nid=self.identity(scope,'dataset',r[key]);nodes[nid]=dict(node_id=nid,kind='dataset',reference=r[key],status='metadata')
            if not r.get('predicate'):continue
            source,target=r['source_dataset_id'],r['target_dataset_id']
            if r.get('reversed'):source,target=target,source
            edges.append(dict(edge_id=self.identity(scope,'edge',r['relationship_id']),source=self.identity(scope,'dataset',source),target=self.identity(scope,'dataset',target),
                predicate=r['predicate'],direction='source_to_target',status=r['status'],kind='semantic_metadata',evidence=deepcopy(r.get('evidence_refs',[])),provenance=deepcopy(r.get('provenance',{})),semantic_evidence_hash=r.get('semantic_evidence_hash'),source_references=[r['relationship_id']],ontology_version=None,mapping_version=view['revision'],confidence=None))
        return self._sync(auth,'semantic','semantic',{'revision':view['revision']},list(nodes.values()),edges)

    @observed('retrieval')
    def get(self,auth,pin,*,historical=False,max_age=300):
        scope=self.scope(auth)
        if type(max_age) not in (int,float) or not 0<max_age<=300:raise RuntimeFailure('ACCOUNT_GRAPH_LIMIT','Use a bounded freshness allowance.',422)
        if not isinstance(pin,dict) or set(pin)!={'graph_id','source_key','revision','sha256'}:
            raise RuntimeFailure('ACCOUNT_GRAPH_PIN','Use an exact backend-issued graph pin.',422)
        if (not isinstance(pin['source_key'],str) or not 1<=len(pin['source_key'])<=256 or
                type(pin['revision']) is not int or pin['revision']<1 or not isinstance(pin['sha256'],str) or len(pin['sha256'])!=64):
            raise RuntimeFailure('ACCOUNT_GRAPH_PIN','Graph pin values must match their backend types.',422)
        if pin['graph_id']!='account_'+digest(scope[0])[:32]:raise RuntimeFailure('ACCOUNT_GRAPH_SCOPE','Cross-account graph access is denied.',403)
        with self.store.transaction(write=False) as db:
            row=db.execute('SELECT document FROM account_graph_revisions WHERE workspace=? AND owner=? AND source_key=? AND revision=? AND sha256=?',(*scope,pin['source_key'],pin['revision'],pin['sha256'])).fetchone()
            head=db.execute('SELECT revision,checked_at,state FROM account_graph_heads WHERE workspace=? AND owner=? AND source_key=?',(*scope,pin['source_key'])).fetchone()
        if not row:raise RuntimeFailure('ACCOUNT_GRAPH_NOT_FOUND','Graph projection not found in this owner scope.',404)
        stale=not head or head[0]!=pin['revision'] or head[2]!='current' or self.clock()-head[1]>max_age
        if stale and not historical:raise RuntimeFailure('ACCOUNT_GRAPH_STALE','Pinned graph is stale; prepare reviewed current evidence.',409)
        result=json.loads(row[0]);result['stale']=stale
        if projection_digest({k:v for k,v in result.items() if k in ('kind','pins','nodes','edges')})!=pin['sha256']:
            raise RuntimeFailure('ACCOUNT_GRAPH_INTEGRITY','Saved graph projection failed integrity validation.',409)
        if not historical and self.service:
            if result['kind']=='preparation':
                self.service.business_preparation.checked(auth,result['pins']['preflight_id'])
            elif result['kind']=='semantic':
                semantic=getattr(self.service,'account_semantic',None)
                if semantic is None:raise RuntimeFailure('ACCOUNT_GRAPH_SOURCE','Current metadata authority is unavailable.',403)
                current=semantic.get(auth)
                if current['stale'] or current['revision']!=result['pins']['revision']:
                    raise RuntimeFailure('ACCOUNT_GRAPH_STALE','Source metadata changed; refresh the projection.',409)
            elif result['kind']=='package_definition':
                p=result['pins'];package=self.service.business_composition.packages.get(auth,p['package_id'],p['revision'])
                if package['sha256']!=p['package_sha256']:raise RuntimeFailure('ACCOUNT_GRAPH_VERSION','Client knowledge changed.')
            elif result['kind']=='package':
                p=result['pins'];packages=self.service.business_composition.packages
                package=packages.get(auth,p['package_id'],p['revision'])
                binding=package['resource_bindings'][p['capability_id']]
                if 'tools.read' not in auth.get('permissions',[]) or (*scope,binding['source_id']) not in packages.providers:
                    raise RuntimeFailure('ACCOUNT_GRAPH_SOURCE','Current package source authority is unavailable.',403)
        return result

    def invalidate(self,auth,source_key):
        scope=self.scope(auth,True)
        with self.store.transaction() as db:
            db.execute("UPDATE account_graph_heads SET state='stale' WHERE workspace=? AND owner=? AND source_key=?",(*scope,source_key))

    def traverse(self,auth,pin,seeds,*,depth=2,limit=32,seconds=.1,include_inferred=False):
        if type(depth) is not int or not 0<=depth<=4 or type(limit) is not int or not 1<=limit<=64 or type(seconds) not in (int,float) or not 0<seconds<=1:
            raise RuntimeFailure('ACCOUNT_GRAPH_LIMIT','Traversal requires bounded depth, results and time.',422)
        doc=self.get(auth,pin);nodes={n['node_id']:n for n in doc['nodes']}
        if not isinstance(seeds,list) or len(seeds)>16 or any(not isinstance(s,str) or s not in nodes for s in seeds):raise RuntimeFailure('ACCOUNT_GRAPH_SEED','Seed nodes must belong to the pinned projection.',422)
        if len(set(seeds))>limit:raise RuntimeFailure('ACCOUNT_GRAPH_LIMIT','Seed count exceeds the requested result bound.',422)
        deadline=time.monotonic()+seconds;seen=set(seeds);front=set(seeds);selected=[]
        for _ in range(depth):
            next_front=set()
            for edge in doc['edges']:
                if time.monotonic()>deadline:raise RuntimeFailure('ACCOUNT_GRAPH_TIMEOUT','Graph traversal deadline exceeded.',504)
                if edge['status'] not in ({'confirmed','inferred'} if include_inferred else {'confirmed'}):continue
                if edge['source'] not in front:continue
                if edge['target'] not in seen and len(seen)>=limit:continue
                selected.append(edge);seen.add(edge['target']);next_front.add(edge['target'])
                if len(selected)>=limit:break
            front=next_front
            if not front or len(selected)>=limit:break
        return dict(pin=deepcopy(pin),nodes=[nodes[n] for n in sorted(seen)],edges=selected,missing_relationships=not bool(selected),qualification='Directional saved mappings and reported evidence; inferred meanings are not verified business facts.')

    def context(self,auth,pin,objective='',limit=12):
        doc=self.get(auth,pin)
        words={w.lower() for w in objective.split() if len(w)>2}
        ranked=sorted(doc['nodes'],key=lambda n:(-sum(w in json.dumps(n).lower() for w in words),n['node_id']))
        # Return references and provenance, not an unbounded copy of account data.
        chosen=ranked[:min(max(limit,1),16)];ids={n['node_id'] for n in chosen}
        edges=[e for e in doc['edges'] if e['source'] in ids and e['target'] in ids and e['status'] in ('confirmed','inferred')][:16]
        references=[r for r in self.execution_references(auth) if any(p['sha256']==pin['sha256'] for p in r.get('graph_pins',[r['graph_pin']]))][:2]
        result=dict(pin=deepcopy(pin),nodes=chosen,edges=edges,execution_memory_references=references,authority='Reference evidence only; current Registry/source authority and approvals remain mandatory.')
        while len(json.dumps(result).encode())>12000 and result['nodes']:
            result['nodes'].pop();ids={n['node_id'] for n in result['nodes']};result['edges']=[e for e in result['edges'] if e['source'] in ids and e['target'] in ids]
        while len(json.dumps(result).encode())>12000 and result['execution_memory_references']:
            result['execution_memory_references'].pop()
        return result

    def record_execution(self,db,run,workflow):
        pin=workflow.get('metadata',{}).get('account_graph_pin')
        candidates=[pin] if pin else []
        for checkpoint in run.get('task_checkpoints',{}).values():
            for evidence in checkpoint.get('result',{}).get('source_evidence',[]):
                observed=evidence.get('account_graph_pin')
                if observed and observed not in candidates:candidates.append(observed)
        pins=[]
        for candidate in candidates[:32]:
            if not isinstance(candidate,dict) or set(candidate)!={'graph_id','source_key','revision','sha256'}:continue
            if candidate['graph_id']!='account_'+digest(run['workspace_id'])[:32]:continue
            row=db.execute('SELECT 1 FROM account_graph_revisions WHERE workspace=? AND owner=? AND source_key=? AND revision=? AND sha256=?',(run['workspace_id'],run['subject_id'],candidate['source_key'],candidate['revision'],candidate['sha256'])).fetchone()
            if row:pins.append(deepcopy(candidate))
        if not pins:return
        doc=dict(run_id=run['run_id'],workflow_id=run['workflow_id'],workflow_version=run['workflow_version'],status=run['status'],graph_pin=pins[0],graph_pins=pins,
            checkpoint_references=[dict(task_id=k,sha256=digest(v),classification='validated_execution_output_not_verified_company_fact') for k,v in run.get('task_checkpoints',{}).items()],
            memory_reference=dict(kind='execution_memory',run_id=run['run_id']),usage=deepcopy(run.get('usage',{})))
        db.execute('INSERT INTO account_graph_execution VALUES (?,?,?,?) ON CONFLICT(workspace,owner,run_id) DO UPDATE SET document=excluded.document',(run['workspace_id'],run['subject_id'],run['run_id'],json.dumps(doc)))

    def execution_references(self,auth,limit=16):
        scope=self.scope(auth)
        if type(limit) is not int or not 1<=limit<=32:raise RuntimeFailure('ACCOUNT_GRAPH_LIMIT','Use a bounded history limit.',422)
        with self.store.transaction(write=False) as db:
            rows=db.execute('SELECT document FROM account_graph_execution WHERE workspace=? AND owner=? ORDER BY rowid DESC LIMIT ?',(*scope,limit)).fetchall()
        return [json.loads(r[0]) for r in rows]

    def diagnostics(self):
        with self.metrics_lock:return dict(self.metrics)

    def view(self,auth,limit=32):
        scope=self.scope(auth)
        if type(limit) is not int or not 1<=limit<=64:raise RuntimeFailure('ACCOUNT_GRAPH_LIMIT','Use a bounded projection limit.',422)
        with self.store.transaction(write=False) as db:
            rows=db.execute('SELECT h.source_key,h.revision,h.checked_at,h.state,r.sha256 FROM account_graph_heads h JOIN account_graph_revisions r ON r.workspace=h.workspace AND r.owner=h.owner AND r.source_key=h.source_key AND r.revision=h.revision WHERE h.workspace=? AND h.owner=? ORDER BY h.source_key LIMIT ?',(*scope,limit+1)).fetchall()
        graph_id='account_'+digest(scope[0])[:32]
        return dict(graph_id=graph_id,projections=[dict(pin=dict(graph_id=graph_id,source_key=k,revision=r,sha256=s),state=state if self.clock()-checked<=300 else 'stale',checked_at=checked) for k,r,checked,state,s in rows[:limit]],has_more=len(rows)>limit,execution_references=self.execution_references(auth),qualification='One logical account graph; only projections authorized to this owner are visible. No cross-owner permission is implied.')
