"""Strict transport for the canonical investigation assessment.

Open JSON values travel as JSON-encoded strings; the decoded decision still
passes the unchanged canonical validator and the runtime evidence verifier.
"""
from copy import deepcopy
import json

from jsonschema import Draft202012Validator

from .errors import PlannerFailure


INSTRUCTIONS = (
    'Use the supplied strict transport_schema for the response. Fields described '
    'as JSON-encoded values contain a single serialized JSON value, not prose. '
    'In particular findings.value encodes the EXACT source value: the number 100 '
    'is "100", the string abc is "\\\"abc\\\"", and null is "null". '
    'Optional fields use null when absent. The decoded result must match schema. '
    'Copy original_objective exactly into assessment.objective, without paraphrasing. '
    'When frozen_requirements is nonempty, copy its IDs and descriptions exactly '
    'in the same order; only status and evidence_ids may change. '
    'Finding and calculation operand paths are relative to '
    'context.evidence[evidence_id].output: do NOT prefix the path with output, '
    'evidence, or the evidence ID. For example coverage.complete_scan is '
    '["coverage","complete_scan"], not ["output","coverage","complete_scan"]. '
    'invalid_assumptions lists unsupported assumptions actually relied on, not '
    'general cautions. Put snapshot and freshness cautions in source_limitations. '
    'Do not reproduce entire result rows as findings; cite a small number of exact '
    'source paths needed to establish the requirements. No invented evidence.'
)


def _opaque(schema):
    kind = schema.get('type', [])
    return not schema or ('object' in ([kind] if isinstance(kind, str) else kind)
                         and schema.get('additionalProperties') is not False)


def transport_schema(schema):
    if _opaque(schema):
        return dict(type='string', description='JSON-encoded value matching canonical schema: '+json.dumps(schema))
    result = {k: deepcopy(v) for k, v in schema.items()
              if k not in ('$schema', '$id', 'uniqueItems', 'properties', 'items', 'required')}
    if 'enum' in result and 'type' not in result:
        result['type'] = 'string'
    if 'properties' in schema:
        properties = {}
        for name, child in schema['properties'].items():
            value = transport_schema(child)
            if name not in schema.get('required', []):
                value = {'anyOf': [value, {'type': 'null'}]}
            properties[name] = value
        result.update(properties=properties, required=list(properties), additionalProperties=False)
    if 'items' in schema:
        result['items'] = transport_schema(schema['items'])
    return result


def bind_context(schema, context):
    """Constrain immutable goal/requirement identities before generation."""
    result = deepcopy(schema)
    assessment = result['properties']['assessment']['properties']
    if context.get('original_objective'):
        assessment['objective']['enum'] = [context['original_objective']]
    frozen = context.get('frozen_requirements', [])
    if frozen:
        variants = []
        for requirement in frozen:
            item = deepcopy(assessment['requirements']['items'])
            for name in ('id', 'description'):
                item['properties'][name]['enum'] = [requirement[name]]
            variants.append(item)
        assessment['requirements'].update(items={'anyOf': variants}, minItems=len(frozen), maxItems=len(frozen))
    return result


def encode(value, schema):
    """Adapter/test encoder; provider emits the same transport directly."""
    if _opaque(schema):
        return json.dumps(value, allow_nan=False)
    if isinstance(value, dict) and 'properties' in schema:
        return {name: encode(value[name], child) if name in value else None
                for name, child in schema['properties'].items()}
    if isinstance(value, list) and 'items' in schema:
        return [encode(item, schema['items']) for item in value]
    return value


def _decode(value, schema):
    if _opaque(schema):
        return json.loads(value, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    if isinstance(value, dict) and 'properties' in schema:
        return {name: _decode(item, schema['properties'][name]) for name, item in value.items()
                if item is not None or name in schema.get('required', [])}
    if isinstance(value, list) and 'items' in schema:
        return [_decode(item, schema['items']) for item in value]
    return value


def decode(response, schema, wire_schema):
    stage = 'response'
    try:
        if getattr(response, 'status', None) == 'incomplete':
            stage = 'incomplete'
            raise ValueError()
        wire = json.loads(response.output_text)
        stage = 'transport'
        errors = list(Draft202012Validator(wire_schema).iter_errors(wire))
        if errors:
            raise ValueError()
        stage = 'encoded_value'
        result = _decode(wire, schema)
        stage = 'canonical'
        errors = list(Draft202012Validator(schema).iter_errors(result))
        if errors:
            raise ValueError()
        return result
    except (ValueError, TypeError, AttributeError, RecursionError):
        # No raw response, model-generated keys, values or validator messages.
        raise PlannerFailure('ADAPTIVE_DECISION_INVALID',
            'The evaluator did not return a valid structured decision.',
            details={'validation_stage': stage}) from None
