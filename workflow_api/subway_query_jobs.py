"""Native Subway reads on the existing fenced, encrypted query queue.

The native query engine and business semantics remain authoritative. Only the
workflow adapter dispatches durable work; direct query clients remain synchronous.
"""
from copy import deepcopy
import json
from jsonschema import Draft202012Validator
from .business_knowledge_model import digest
from .service import ApiFailure
from .subway_queries import INPUT, OUTPUT
from .data_query_jobs import identity
from .workflow_queries import QueryPending


class SubwayJobEngine:
    def __init__(self, queries):
        self.queries=queries
        self.result_validator=Draft202012Validator(OUTPUT)

    def bound_queries(self,auth,saved):
        if hasattr(self.queries,'for_workflow'):
            return self.queries.for_workflow({'metadata':{'action_binding_context':{'validated_context':saved.get('source_binding',{})}}},auth)
        return self.queries

    def validate(self, auth, saved, db=None):
        queries=self.bound_queries(auth,saved)
        queries.authorize(auth)
        pin=saved['package_pin']
        packages=self.queries.app.state.client_packages
        package=packages.get(auth,pin['package_id'],pin['revision'])
        if package['sha256']!=pin['package_sha256'] or package['ontology_version']!=pin['ontology_version']:
            raise ApiFailure('SUBWAY_QUERY_STALE','Pinned Subway package changed.',409)
        catalog=queries.catalog(auth)
        if digest(catalog['stamps'])!=saved['context_hash']:
            raise ApiFailure('SUBWAY_QUERY_STALE','Reviewed Subway source authority changed.',409)
        selected,_,_=queries.validate(saved['plan'],catalog)
        if set(selected)!=set(saved['source_ids']):
            raise ApiFailure('SUBWAY_QUERY_STALE','Reviewed query source scope changed.',409)

    def execute(self, auth, saved):
        return self.bound_queries(auth,saved).execute(auth,saved['plan'])


class DurableSubwayQuery:
    external_write=False
    retry_safe=True
    durable_query=True
    timeout=10

    def __init__(self, bound, jobs, reference=None,source_binding=None):
        self.bound,self.jobs,self.queries,self.reference=bound,jobs,bound.queries,reference
        self.manager=jobs.manager
        self.source_binding=deepcopy(source_binding or {})

    def reservation(self, grant):return self.bound.reservation(grant)

    def bind_context(self, workflow, run, auth, node):
        bound=self.bound.bind_context(workflow,run,auth,node)
        # Historical standalone invocation without a run keeps its original path.
        if not run.get('run_id'):return bound
        context=workflow.get('metadata',{}).get('action_binding_context',{}).get('validated_context',{})
        return DurableSubwayQuery(bound,self.jobs,dict(run_id=run['run_id'],node_id=node['node_id']),{k:context[k] for k in ('demo_context','source_resolution') if k in context})

    def invoke(self, grant, inputs, effect_id):
        try:return self.execute(grant,inputs,effect_id)
        except ApiFailure as exc:
            from runtime.service import RuntimeFailure
            raise RuntimeFailure(exc.code,str(exc),exc.status) from None

    def execute(self, grant, inputs, effect_id):
        if not self.reference:return self.bound.invoke(grant,inputs,effect_id)
        auth=self.bound.auth
        if grant.get('tool_id')!='subway_query' or list(Draft202012Validator(INPUT).iter_errors(inputs)):
            raise ApiFailure('SUBWAY_QUERY_DENIED','Use the reviewed structured Subway query.',403)
        retry='native_'+digest([auth['subject'],effect_id])
        with self.jobs.store.transaction(write=False) as db:
            row=db.execute('SELECT document,job_id FROM data_query_jobs WHERE workspace=? AND owner=? AND retry_key=?',(*identity(auth),retry)).fetchone()
        if row:
            saved=json.loads(row[0])
            if saved.get('engine')!='subway' or saved['plan']!=inputs['query'] or saved['package_pin']!=self.bound.pin or saved.get('source_binding',{})!=self.source_binding:
                raise ApiFailure('DATA_QUERY_CONFLICT','Durable Subway query identity changed.',409)
            job=self.jobs.get(auth,row[1],_workflow=True)
        else:
            catalog=self.queries.catalog(auth)
            selected,_,_=self.queries.validate(inputs['query'],catalog)
            pid='dq_'+digest([auth['subject'],effect_id,inputs])[:32]
            saved=dict(source_binding=deepcopy(self.source_binding),engine='subway',plan_id=pid,plan=deepcopy(inputs['query']),package_pin=deepcopy(self.bound.pin),source_ids=sorted(selected),context_hash=digest(catalog['stamps']),expires_at=self.jobs.clock()+1800)
            self.jobs.engine(saved).validate(auth,saved)
            with self.jobs.store.transaction() as db:
                db.execute('INSERT INTO data_query_plans VALUES (?,?,?,?,?) ON CONFLICT DO NOTHING',(pid,*identity(auth),saved['expires_at'],json.dumps(saved)))
            job=self.jobs.submit(auth,{'plan_id':pid},retry,runtime_reference=self.reference)
        if job['state'] not in ('succeeded','failed','cancelled'):raise QueryPending(job)
        if job['state']!='succeeded':
            error=job.get('error') or dict(code='DATA_QUERY_CANCELLED',message='The owning workflow stopped.')
            raise ApiFailure(error['code'],error['message'],409)
        return self.jobs.result(auth,job['job_id'],_workflow=True)
