"""Reviewed native query scope for existing durable automation occurrences.

The annotation pins an authorized catalogue, not a model-generated query. Runtime
validation still applies every native query rule and exact occurrence date bounds.
"""
from copy import deepcopy
from .business_knowledge_model import digest
from .service import ApiFailure
from .temporal_queries import window

ANNOTATION = 'x-praxi-subway-scope-v1'


def deny(message):
    raise ApiFailure('AUTOMATION_SCOPE_DENIED', message, 403)


def date_filters(overview, run):
    pin = overview['subway_temporal']
    due = run.get('automation_reference', {}).get('scheduled_due')
    if due is None:
        deny('A scheduled query requires its durable logical occurrence time.')
    lower, upper = window(pin['period'], pin['timezone'], due, pin['days'])
    return [dict(field_id=pin['field_id'], op=op, value=value)
            for op, value in (('gte', lower), ('lt', upper))]


def query_consent(doc, intent):
    from .subway_queries import INPUT
    catalog = doc['binding_context']['validated_context']['subway_query_catalog']
    schema = deepcopy(INPUT)
    schema[ANNOTATION] = dict(catalog_sha256=digest(catalog), temporal=deepcopy(intent.get('subway_temporal')))
    if catalog.get('demo_context'):schema[ANNOTATION]['demo_context']=deepcopy(catalog['demo_context'])
    return schema


def validate_consent(schema, zone):
    from .subway_queries import INPUT
    plain = deepcopy(schema)
    pin = plain.pop(ANNOTATION, None)
    if plain != INPUT or not isinstance(pin, dict) or set(pin) not in ({'catalog_sha256','temporal'},{'catalog_sha256','temporal','demo_context'}):
        deny('Native recurring queries require the reviewed bounded catalogue.')
    if not isinstance(pin['catalog_sha256'], str) or len(pin['catalog_sha256']) != 64:
        deny('Invalid recurring catalogue fingerprint.')
    temporal = pin['temporal']
    if temporal is not None:
        if not isinstance(temporal, dict) or set(temporal) != {'period','timezone','days','field_id'} or temporal['timezone'] != zone:
            deny('Reporting timezone must match the reviewed schedule.')
        window(temporal['period'], zone, 0, temporal['days'])


def check_query(schema, inputs, workflow, run, queries, auth):
    overview = workflow['metadata'].get('overview_intent', {})
    catalog = workflow['metadata']['action_binding_context']['validated_context']['subway_query_catalog']
    pin = (schema or {}).get(ANNOTATION, {})
    expected=dict(catalog_sha256=digest(catalog), temporal=overview.get('subway_temporal'))
    if catalog.get('demo_context'):expected['demo_context']=deepcopy(catalog['demo_context'])
    if pin != expected:
        deny('Recurring query catalogue differs from the approved scope.')
    datasets = {d['dataset_id']:d for d in catalog['sources']}
    fields = {f['field_id']:{**f,'dataset_id':d['dataset_id']} for d in datasets.values() for f in d['fields']}
    relationships = {r['relationship_id']:r for r in catalog['relationships']}
    queries=queries.for_workflow(workflow,auth)
    queries.authorize(auth)
    queries.validate(inputs['query'], dict(datasets=datasets,fields=fields,relationships=relationships))
    if pin['temporal']:
        for expected in date_filters(overview, run):
            if inputs['query']['filters'].count(expected) != 1:
                deny('Recurring query must preserve the logical reporting window.')

    for expected in run.get('automation_reference',{}).get('trigger',{}).get('query_filters',[]):
        if inputs['query']['filters'].count(expected)!=1:
            deny('Event query must preserve the authenticated source entity binding.')


DEMO_ASSESSMENT = 'x-praxi-subway-demo-assessment-v1'

def assessment_schema(pin):
    from .subway_assessments import INPUT
    from .subway_demo_data import POLICY
    schema=deepcopy(INPUT)
    schema['properties']['assessment']={'const':pin['assessment']}
    schema['properties']['as_of']={'const':POLICY['as_of']}
    schema['properties']['delay_days']={'const':POLICY['approval_delay_days']}
    schema[DEMO_ASSESSMENT]=deepcopy(pin)
    return schema

def assessment_consent(doc,intent,action):
    from .action_bindings import binding_value
    catalog=doc['binding_context']['validated_context']['subway_query_catalog']
    if not catalog.get('demo_context'):deny('Modeled recurring assessments require an explicit demonstration dataset.')
    binding=next((b for b in action['bindings'] if b['target']==['assessment']),None)
    if not binding or binding['kind'] not in {'literal','context','configuration','evidence'}:deny('Review the exact assessment kind before scheduling.')
    assessment=binding_value(binding,doc['binding_context'],{a['action_id']:a for a in doc['action_plan']['actions']})
    pin=dict(assessment=assessment,query_scope=query_consent(doc,intent)[ANNOTATION])
    schema=assessment_schema(pin);validate_assessment_consent(schema,intent['schedule']['timezone'] if intent.get('schedule') else intent.get('event_subscription',{}).get('timezone','Asia/Kolkata'))
    return schema

def validate_assessment_consent(schema,zone):
    from .subway_assessments import ASSESSMENTS
    from .subway_queries import INPUT
    pin=schema.get(DEMO_ASSESSMENT,{})
    if set(pin)!={'assessment','query_scope'} or pin['assessment'] not in ASSESSMENTS or not pin['query_scope'].get('demo_context') or schema!=assessment_schema(pin):deny('Recurring modeled assessments require the exact reviewed kind, policy and dataset scope.')
    query=deepcopy(INPUT);query[ANNOTATION]=pin['query_scope'];validate_consent(query,zone)

def check_assessment(schema,inputs,workflow,run,queries,auth):
    pin=(schema or {}).get(DEMO_ASSESSMENT,{})
    if not workflow['metadata']['action_binding_context']['validated_context'].get('demo_context') or inputs.get('assessment')!=pin.get('assessment'):deny('Assessment differs from reviewed modeled scope.')
    from .subway_queries import INPUT
    query=deepcopy(INPUT);query[ANNOTATION]=pin.get('query_scope',{})
    check_query(query,{'query':inputs['query']},workflow,run,queries,auth)
