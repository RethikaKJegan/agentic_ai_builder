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
    return schema


def validate_consent(schema, zone):
    from .subway_queries import INPUT
    plain = deepcopy(schema)
    pin = plain.pop(ANNOTATION, None)
    if plain != INPUT or not isinstance(pin, dict) or set(pin) != {'catalog_sha256','temporal'}:
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
    if pin != dict(catalog_sha256=digest(catalog), temporal=overview.get('subway_temporal')):
        deny('Recurring query catalogue differs from the approved scope.')
    datasets = {d['dataset_id']:d for d in catalog['sources']}
    fields = {f['field_id']:{**f,'dataset_id':d['dataset_id']} for d in datasets.values() for f in d['fields']}
    relationships = {r['relationship_id']:r for r in catalog['relationships']}
    queries.authorize(auth)
    queries.validate(inputs['query'], dict(datasets=datasets,fields=fields,relationships=relationships))
    if pin['temporal']:
        for expected in date_filters(overview, run):
            if inputs['query']['filters'].count(expected) != 1:
                deny('Recurring query must preserve the logical reporting window.')

    for expected in run.get('automation_reference',{}).get('trigger',{}).get('query_filters',[]):
        if inputs['query']['filters'].count(expected)!=1:
            deny('Event query must preserve the authenticated source entity binding.')
