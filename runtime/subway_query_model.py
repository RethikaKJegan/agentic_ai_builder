"""Model-only query constraints; the query executor retains all authority."""
from copy import deepcopy
import json
from workflow_api.query_predicates import FILTER_GUIDANCE

GUIDANCE = (
    '\nSubway query rules: choose one query mode. Detail queries project fields and have '
    'empty metrics and group_by. The executor returns coverage.matched_records for the '
    'complete matching population even when detail rows are paginated; never add a count '
    'metric to projected details to obtain that count. Aggregate queries have empty fields '
    'and one or more metrics; group_by declares grouping columns. All metrics are per group. '
    'Use a separate aggregate query when the task requires independent aggregate results. '
    'Use only supplied canonical IDs, selected directed joins, and fields of the base or '
    'joined datasets. Detail sorting supports authorized base-dataset fields, including '
    'fields not displayed in the detail projection. Aggregate sorting must name an exact '
    'group_by field ID or metric label returned by that query. Preserve explicit '
    'filters and requested numeric measures; keep currencies separate for monetary '
    'aggregation. Downstream reporting and email are separate actions. Never invent '
    'IDs, joins, filters, business results, currency conversions or coverage.\n'
    'When context.subway_query_catalog.interpretation.business_resolution has status '
    'descriptive_measures, preserve its exact source, grouping and every op/field_id '
    'metric pair. Give distinct source measures distinct informative metric labels. '
    'Never substitute one candidate measure or sum them together.\n'
) + FILTER_GUIDANCE


def response_schema(definition, inputs):
    schema = deepcopy(definition['output_schema'])
    catalog = inputs.get('context', {}).get('subway_query_catalog', {})
    sources = catalog.get('sources', [])
    query = schema.get('properties', {}).get('query', {})
    if not sources or not {'base_dataset_id', 'fields', 'metrics', 'group_by'} <= set(query.get('properties', {})):
        return schema
    # Separate mutually exclusive executor modes before asking the model.
    detail = deepcopy(query)
    detail['properties']['fields']['minItems'] = 1
    detail['properties']['metrics']['maxItems'] = 0
    detail['properties']['group_by']['maxItems'] = 0
    aggregate = deepcopy(query)
    aggregate['properties']['fields']['maxItems'] = 0
    aggregate['properties']['metrics']['minItems'] = 1
    from workflow_api.descriptive_measures import pin
    resolution=pin(catalog)
    schema['properties']['query'] = {'anyOf': [aggregate] if resolution else [detail, aggregate]}
    shaped = deepcopy(schema)
    choices = dict(
        subway_datasets=[d['dataset_id'] for d in sources],
        subway_fields=[f['field_id'] for d in sources for f in d['fields']],
        subway_metric_fields=['', *[f['field_id'] for d in sources for f in d['fields']]],
        subway_relationships=[r['relationship_id'] for r in catalog.get('relationships', [])],
    )
    definitions = {}
    for name, values in choices.items():
        values = list(dict.fromkeys(values))
        if values:
            definitions[name] = {'anyOf': [{'type': 'string', 'enum': values[i:i+200]} for i in range(0, len(values), 200)]}
    schema['$defs'] = definitions
    for branch in (detail, aggregate):
        p = branch['properties']
        p['base_dataset_id'] = {'$ref': '#/$defs/subway_datasets'}
        for name in ('fields', 'group_by'):
            if choices['subway_fields']:
                p[name]['items'] = {'$ref': '#/$defs/subway_fields'}
        if choices['subway_fields']:
            p['filters']['items']['properties']['field_id'] = {'$ref': '#/$defs/subway_fields'}
            if branch is detail:
                p['order_by']['items']['properties']['column'] = {'$ref': '#/$defs/subway_fields'}
        p['metrics']['items']['properties']['field_id'] = {'$ref': '#/$defs/subway_metric_fields'}
        if choices['subway_relationships']:
            p['joins']['items'] = {'$ref': '#/$defs/subway_relationships'}
        else:
            p['joins']['maxItems'] = 0
        pinned=inputs.get('context',{}).get('subway_filter_branch')
        if pinned:
            p['base_dataset_id']={'type':'string','enum':[pinned['base_dataset_id']]}
            alternatives=[]
            for predicate in pinned['filters']:
                item=deepcopy(query['properties']['filters']['items'])
                for key,value in predicate.items():
                    kind='null' if value is None else 'boolean' if type(value) is bool else 'number' if isinstance(value,(int,float)) else 'string'
                    item['properties'][key]={'type':kind,'enum':[value]}
                alternatives.append(item)
            p['filters']={'type':'array','minItems':len(alternatives),'maxItems':len(alternatives),'items':{'anyOf':alternatives}}
        if resolution:
            p['base_dataset_id']={'type':'string','enum':[resolution['base_dataset_id']]}
            groups=resolution['group_by']
            p['group_by']={'type':'array','minItems':len(groups),'maxItems':len(groups),'items':{'type':'string',**({'enum':groups} if groups else {})}}
            metrics=[]
            for metric in resolution['metrics']:
                item=deepcopy(query['properties']['metrics']['items'])
                for key,value in metric.items():item['properties'][key]={'type':'string','enum':[value]}
                metrics.append(item)
            p['metrics']={'type':'array','minItems':len(metrics),'maxItems':len(metrics),'items':{'anyOf':metrics}}
    # Provider transport constraints must not introduce a new execution failure.
    from workflow_api.subway_queries import schema_identity_budget
    if min(schema_identity_budget(schema)) < 0 or len(json.dumps(schema).encode()) > 100000:
        return shaped
    return schema


def canonical_projection(query):
    """Remove only redundant generated group projections; never change measures."""
    result = deepcopy(query)
    if (isinstance(result, dict) and result.get('metrics') and result.get('group_by')
            and result.get('fields') and set(result['fields']) <= set(result['group_by'])):
        result['fields'] = []
    return result
