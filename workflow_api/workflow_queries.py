"""Account-scoped query capability over the existing planner, jobs and graph runtime."""
from copy import deepcopy
import json
from pathlib import Path

from runtime.service import RuntimeFailure
from .business_knowledge_model import digest
from .data_queries import SCHEMA
from .data_relationships import fingerprint
from .google_connections import GoogleConnections
from .service import ApiFailure

INPUT = dict(type='object', additionalProperties=False, required=['query'], properties={'query':deepcopy(SCHEMA)})
INPUT['properties']['query'].pop('$id', None)
INPUT['properties']['query'].pop('$schema', None)
# Equivalent JSON Schema union, compatible with the runtime's strict payload check.
value_schema=INPUT['properties']['query']['properties']['filters']['items']['properties']['value']
value_types=value_schema.pop('type')
value_schema['anyOf']=[dict(type=kind) for kind in value_types]
for collection,field in [('filters','op'),('metrics','op'),('order_by','direction')]:
    INPUT['properties']['query']['properties'][collection]['items']['properties'][field]['type']='string'
RESULT = json.loads((Path(__file__).resolve().parents[1]/'shared/contracts/data-sources/queries-v1.schema.json').read_text())

def inline(value):
    if isinstance(value,list):return [inline(v) for v in value]
    if not isinstance(value,dict):return value
    if '$ref' in value:return inline(RESULT['$defs'][value['$ref'].split('/')[-1]])
    return {k:inline(v) for k,v in value.items() if k not in ('$id','$schema')}

OUTPUT = dict(type='object', additionalProperties=False, required=['query_id','result','coverage','scope','metadata_revision'], properties={
    'query_id':{'type':'string'},'result':inline(RESULT['$defs']['result']),
    'coverage':dict(type='object',required=['complete_scan','aggregate_complete','returned_rows','total_result_rows','has_more'],properties={
        'complete_scan':{'type':'boolean'},'aggregate_complete':{'type':'boolean'},'returned_rows':{'type':'integer'},
        'total_result_rows':{'type':'integer'},'has_more':{'type':'boolean'}}),
    'scope':dict(type='object',required=['workspace_id','owner_id'],properties={'workspace_id':{'type':'string'},'owner_id':{'type':'string'}}),
    'metadata_revision':{'type':'string'}})

class QueryPending(RuntimeFailure):
    """Only a persisted, read-only query may yield the graph's execution lease."""
    def __init__(self, job):
        super().__init__('DATA_QUERY_PENDING','Waiting for the durable data query.',409)
        self.job=job



class QueryClarification(RuntimeFailure):
    """A typed query requests business meaning before any source invocation."""
    def __init__(self, question):
        super().__init__('ACTION_INPUT_REQUIRED',question,422)
        self.question=question


def query_clarifications(run, workflow):
    """Project persisted questions, including old failed runs, without mutation."""
    result={}
    if not run or not workflow:return result
    for node in workflow.get('nodes',[]):
        nid=node['node_id'];entry=run.get('action_instances',{}).get(nid,{})
        if (node.get('tool_id')!='workflow_data_query' or
                run.get('node_states',{}).get(nid) not in ('failed','blocked') or
                entry.get('error_code',run.get('error_code'))!='ACTION_INPUT_REQUIRED'):
            continue
        question=entry.get('clarification') or entry.get('resolved_inputs',{}).get('query',{}).get('clarification')
        if isinstance(question,str) and question.strip():result[nid]=question
    return result


def planning_contract():
    from .capability_contracts import contract, INPUT_SCHEMA
    return contract('data.plan_query','prepare_validated_query_content',
        'Prepare a typed account-scoped query from the goal and data_query_catalog. No complaint identifier is needed for population queries.',
        inputs=INPUT_SCHEMA,outputs=INPUT)


def definition():
    from .business_preparation import retrieval_tool_definition
    tool=retrieval_tool_definition()
    tool.update(tool_id='workflow_data_query',capability='data.query',input_schema=INPUT,output_schema=OUTPUT,
        description='Execute a validated account-scoped read-only data query as a durable job. Supports authorized filters, reviewed joins, grouping and exact aggregates. Display limits never define aggregate denominators. No complaint ID required.',timeout_seconds=10)
    return tool


class WorkflowQueries:
    external_write=False
    retry_safe=True
    timeout=1
    durable_query=True
    def __init__(self, queries, jobs, auth=None, pin=None, source_ids=None):
        self.queries,self.jobs,self.auth,self.pin=queries,jobs,auth,pin
        self.source_ids=source_ids
    def reservation(self,grant):return dict(tool_calls=1,tokens=0,llm_calls=0,estimated_cost_usd=0)
    def bind_context(self,workflow,run,auth,node):
        catalog=workflow.get('metadata',{}).get('action_binding_context',{}).get('validated_context',{}).get('data_query_catalog',{})
        pin=catalog.get('context_hash')
        if not pin:raise RuntimeFailure('DATA_QUERY_SCOPE_REQUIRED','Review an account-scoped query workflow first.',403)
        try:
            GoogleConnections.identity(auth,True)
            if fingerprint(self.queries.context(auth)[0])!=pin:
                raise RuntimeFailure('DATA_QUERY_STALE','Source mappings or access changed. Review the query workflow again.',409)
        except ApiFailure as exc:
            raise RuntimeFailure(exc.code,str(exc),exc.status) from exc
        return WorkflowQueries(self.queries,self.jobs,deepcopy(auth),pin,
            {d['dataset_id'] for d in catalog['datasets']} if 'datasets' in catalog else None)
    def invoke(self,grant,inputs,effect_id):
        if self.auth is None or grant.get('tool_id')!='workflow_data_query':
            raise RuntimeFailure('DATA_QUERY_SCOPE_REQUIRED','Use the workflow-bound query capability.',403)
        try:
            return self.execute(inputs,effect_id)
        except ApiFailure as exc:
            raise RuntimeFailure(exc.code,str(exc),exc.status) from exc
    def execute(self,inputs,effect_id):
        from jsonschema import Draft202012Validator
        if list(Draft202012Validator(INPUT).iter_errors(inputs)):
            raise RuntimeFailure('DATA_QUERY_INVALID','Use the registered typed query schema.',422)
        GoogleConnections.identity(self.auth,True)
        if fingerprint(self.queries.context(self.auth)[0])!=self.pin:
            raise RuntimeFailure('DATA_QUERY_STALE','Reviewed query metadata changed.',409)
        query=deepcopy(inputs['query'])
        if query['clarification']:
            raise QueryClarification(query['clarification'])
        if self.source_ids is not None and not {query['base_dataset_id'],*[j['target_dataset_id'] for j in query['joins']]} <= self.source_ids:
            raise RuntimeFailure('DATA_QUERY_SCOPE_DENIED','Query references a source outside the reviewed objective metadata.',403)
        retry='workflow_'+digest([self.auth['subject'],effect_id])
        # Job's immutable snapshot survives executable-plan TTL/retention. Reattach
        # before preparing anything; never silently rerun a failed/expired job.
        with self.jobs.store.transaction(write=False) as db:
            row=db.execute('SELECT document,job_id FROM data_query_jobs WHERE workspace=? AND owner=? AND retry_key=?',
                (*GoogleConnections.identity(self.auth,True),retry)).fetchone()
        if row:
            saved=json.loads(row[0])
            if saved['plan']!=query or saved['context_hash']!=self.pin:
                raise RuntimeFailure('DATA_QUERY_CONFLICT','Durable query identity changed.',409)
            job=self.jobs.get(self.auth,row[1])
        else:
            saved=self.queries.save_typed_plan(self.auth,'Reviewed workflow data query',query,context_hash=self.pin,
                plan_id='dq_'+digest([self.auth['subject'],effect_id,query])[:32])
            job=self.jobs.submit(self.auth,{'plan_id':saved['plan_id']},retry)
        if job['state'] not in ('succeeded','failed','cancelled'):
            raise QueryPending(job)
        if job['state']!='succeeded':
            error=job.get('error') or dict(code='DATA_QUERY_CANCELLED',message='The query was cancelled.')
            raise RuntimeFailure(error['code'],error['message'],409)
        result=self.jobs.result(self.auth,job['job_id'])
        if result.get('execution',{}).get('strategy')=='mongodb_evidence_sample':
            raise RuntimeFailure('DATA_QUERY_INCOMPLETE','Sampled evidence cannot supply population results.',422)
        return dict(query_id=job['job_id'],result=result,scope=dict(workspace_id=self.auth['subject']['workspace_id'],owner_id=self.auth['subject']['subject_id']),
            metadata_revision=self.pin,coverage=dict(complete_scan=True,aggregate_complete=bool(query['metrics']),
                returned_rows=len(result['rows']),total_result_rows=result['total_result_rows'],has_more=result['limited']))


def install(service,queries,jobs,authority):
    """Trusted server installation; grants still pass normal Registry review."""
    service.workflow_queries=WorkflowQueries(queries,jobs)
    if service.registry_adapter is None:return
    registry=service.registry_adapter.service
    auth=dict(subject=dict(subject_id='workflow-query-registration',workspace_id=authority['subject']['workspace_id']),
        roles=['admin'],permissions=['tools.manage'],scopes=[],decision='allow')
    policy=registry.trusted_policy_snapshot(auth);policy.version+=1
    policy.approved_providers.add('builder_business');policy.remaining_quota['workflow_data_query']=10000
    if registry.update_policy(policy,auth)['status']!=200 or registry.register_tool(definition(),auth)['status']!=200:
        raise ValueError('Workflow query capability could not be registered.')
    if getattr(service,'runtime_runner',None):service.runtime_runner.connectors['workflow_data_query']=service.workflow_queries
