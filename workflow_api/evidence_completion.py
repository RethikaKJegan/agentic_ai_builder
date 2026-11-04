"""Case-local evidence completion. Never writes to a business source or grants authority."""
from copy import deepcopy
from datetime import datetime
from hashlib import sha256
import math
from jsonschema import Draft202012Validator, FormatChecker
from .service import ApiFailure

MISSING = object()
RANK = {'ACTUAL': 0, 'DERIVED': 1, 'INFERRED': 2, 'SYNTHETIC': 3}


def invalid(message, code='CASE_INPUT_INVALID'):
    raise ApiFailure(code, message, 422)


def conforms(value, schema):
    return not list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value))


def at(value, path):
    for part in path.split('.') if path else []:
        if isinstance(value, dict) and part in value:
            value = value[part]
        elif isinstance(value, list) and part.isdigit() and int(part) < len(value):
            value = value[int(part)]
        else:
            return MISSING
    return value


def artifact(value, kind, refs, method, timestamp, case_id, **extra):
    return dict(value=deepcopy(value), data_type=('null' if value is None else 'boolean' if isinstance(value, bool)
                else 'object' if isinstance(value, dict) else 'array' if isinstance(value, list)
                else 'integer' if isinstance(value, int) else 'number' if isinstance(value, float) else 'string'),
                provenance_type=kind, source_references=deepcopy(refs), generation_method=method,
                confidence=None, assumptions=[], generated_at=timestamp, validity_scope=case_id,
                permitted_uses=['analytical_continuation', *(['workflow_input', 'event_correlation'] if kind == 'ACTUAL' else [])], limitations=['Does not grant commercial authorization or verify physical activity.'],
                **extra)


def provisional(schema, seed, timestamp, depth=0):
    """Conservative bounded generator; unsupported constraints fail closed after validation."""
    if depth > 12:
        invalid('Synthetic schema nesting exceeds its bound.')
    if 'const' in schema:
        return deepcopy(schema['const'])
    if schema.get('enum'):
        return deepcopy(schema['enum'][int(seed[:8], 16) % len(schema['enum'])])
    if 'default' in schema:
        return deepcopy(schema['default'])
    kind = schema.get('type')
    if isinstance(kind, list):
        kind = next((k for k in kind if k != 'null'), 'null')
    if kind == 'object':
        return {k: provisional(schema.get('properties', {}).get(k, {}), sha256((seed+k).encode()).hexdigest(), timestamp, depth+1)
                for k in schema.get('required', [])}
    if kind == 'array':
        count = schema.get('minItems', 0)
        if count > 64:
            invalid('Synthetic arrays exceed their bound.')
        return [provisional(schema.get('items', {}), sha256((seed+str(i)).encode()).hexdigest(), timestamp, depth+1) for i in range(count)]
    if kind in ('number', 'integer'):
        value = schema.get('minimum', 0)
        if 'exclusiveMinimum' in schema:
            value = max(value, schema['exclusiveMinimum'] + 1)
        multiple = schema.get('multipleOf', 1)
        value = math.ceil(value / multiple) * multiple
        return int(value) if kind == 'integer' else value
    if kind == 'boolean':
        return False
    if kind == 'null':
        return None
    if kind == 'string':
        if schema.get('minLength', 0) > 4096:
            invalid('Supply an explicit bounded fallback for long strings.')
        if schema.get('format') == 'date':
            return timestamp[:10]
        if schema.get('format') == 'date-time':
            return timestamp
        value = 'provisional_' + seed[:16]
        value = value[:schema.get('maxLength', len(value))]
        return value.ljust(schema.get('minLength', 0), 'x')
    invalid('Supply an explicit schema-compatible fallback for this schema.')


class EvidenceCompletion:
    def __init__(self, case, stage, timestamp, config=None):
        self.case, self.stage, self.timestamp = case, stage, timestamp
        self.config = config or {}

    def binding(self, binding):
        source, path = binding['source'], binding['path']
        if source == 'input':
            name, _, rest = path.partition('.')
            entry = self.stage.get('resolved_inputs', {}).get(name)
            if entry:
                value = at(entry['value'], rest)
                return {**deepcopy(entry), 'value': value} if value is not MISSING else None
            return None
        if source.startswith('stage:'):
            parent = self.case['stages'].get(source[6:], {})
            name, _, rest = path.partition('.')
            entry = parent.get('outputs', {}).get(name)
            if entry:
                value = at(entry['value'], rest)
                return {**deepcopy(entry), 'value': value} if value is not MISSING else None
            return None
        if source == 'event':
            event = self.stage.get('event')
            if not event:
                return None
            value = at(event['payload'], path)
            if value is MISSING:
                return None
            return artifact(value, 'ACTUAL', [{'event_id': event['event_id'], 'source': event['source']}],
                            'authenticated_event_assertion', self.timestamp, self.case['case_id'])
        values = {'user': self.case['inputs'], 'config': self.config}
        if source not in values:
            return None
        value = at(values[source], path)
        if value is MISSING:
            return None
        return artifact(value, 'ACTUAL', [{'origin': source, 'path': path}], 'user_assertion' if source == 'user' else 'authorized_configuration', self.timestamp, self.case['case_id'])

    def evidence(self, mapping):
        entries = []
        for group in self.case.get('source_evidence', {}).values():
            for record in group.get('records', []):
                if mapping not in record.get('values', {}):
                    continue
                value = record['values'][mapping]
                if isinstance(value, dict) and 'state' in value:
                    if value['state'] != 'value':
                        continue
                    value = value.get('value')
                entries.append(artifact(value, 'ACTUAL', [{k: deepcopy(record[k]) for k in
                    ('record_id', 'collection', 'source_reference', 'read_at') if k in record} | {'mapping_id': mapping}],
                    'authorized_mapped_source', self.timestamp, self.case['case_id']))
        return entries

    def resolve(self, name, spec):
        schema = spec['schema']
        candidates = self.evidence(spec['evidence_mapping']) if spec.get('evidence_mapping') else []
        if spec.get('binding'):
            bound = self.binding(spec['binding'])
            if bound:
                candidates.append(bound)
        # Invalid authoritative evidence is a conflict, not permission to replace it.
        if any(c['provenance_type'] == 'ACTUAL' and not conforms(c['value'], schema) for c in candidates):
            self.case['conflicts'].append(dict(stage=self.stage['stage_instance_id'], input=name, reason='invalid_actual_value', evidence=deepcopy(candidates)))
            return None
        key = self.stage['stage_instance_id'] + ':' + name
        previous = self.case['assumptions'].get(key)
        bound_fallback = None
        if candidates:
            candidates.sort(key=lambda c: RANK[c['provenance_type']])
            chosen = candidates[0]
            if spec.get('protected_activity') and (chosen['provenance_type'] != 'ACTUAL' or chosen['generation_method'] not in ('authorized_mapped_source', 'authenticated_event_assertion', 'connector_receipt')):
                return None
            for other in candidates[1:] + ([previous] if previous else []):
                if chosen['value'] != other['value']:
                    conflict = dict(stage=self.stage['stage_instance_id'], input=name, preferred=deepcopy(chosen), alternative=deepcopy(other))
                    if conflict not in self.case['conflicts']:
                        self.case['conflicts'].append(conflict)
                    if other['provenance_type'] == chosen['provenance_type'] == 'ACTUAL':
                        return None
            if conforms(chosen['value'], schema):
                if chosen['provenance_type'] in ('ACTUAL', 'DERIVED'):
                    return deepcopy(chosen)
                bound_fallback = deepcopy(chosen)
        derivation = spec.get('derivation')
        entry = None
        if derivation:
            basis = [self.binding(b) for b in derivation['inputs']]
            if all(basis) and all(b['provenance_type'] in ('ACTUAL', 'DERIVED') for b in basis):
                values = [b['value'] for b in basis]
                try:
                    op = derivation['operation']
                    value = (values[0] if op == 'copy' else sum(values) if op == 'sum' else values[0]-values[1]
                             if op == 'difference' else ''.join(map(str, values)) if op == 'concat' else
                             (datetime.fromisoformat(values[1])-datetime.fromisoformat(values[0])).days)
                    entry = artifact(value, 'DERIVED', [r for b in basis for r in b['source_references']], op, self.timestamp, self.case['case_id'])
                except (TypeError, ValueError, IndexError):
                    entry = None
        inference = spec.get('inference')
        if entry is None and bound_fallback and bound_fallback['provenance_type'] == 'INFERRED':
            entry = bound_fallback
        if entry is None and inference:
            basis = [self.binding(b) for b in inference['basis']]
            if all(basis) and all(b['provenance_type'] in ('ACTUAL', 'DERIVED') for b in basis):
                entry = artifact(inference['value'], 'INFERRED', [r for b in basis for r in b['source_references']],
                                 'configured_evidence_grounded_rule', self.timestamp, self.case['case_id'])
                entry.update(confidence=inference.get('confidence'), assumptions=[inference['explanation']])
        if spec.get('protected_activity'):
            return None
        if entry is None and bound_fallback:
            entry = bound_fallback
        if entry is None and previous:
            return deepcopy(previous) if conforms(previous['value'], schema) else None
        if entry is None and spec.get('synthetic_fallback') and self.stage['definition']['provisional_continuation_policy']['allowed']:
            seed = sha256((self.case['case_id'] + ':' + key).encode()).hexdigest()
            try:
                value = deepcopy(spec['fallback_value']) if 'fallback_value' in spec else provisional(schema, seed, self.case['created_at'])
            except ApiFailure:
                return None
            entry = artifact(value, 'SYNTHETIC', [], 'schema_seeded_fallback_v1', self.timestamp, self.case['case_id'])
            entry['assumptions'] = ['Missing evidence; case-local analytical assumption.']
        if entry is None or not conforms(entry['value'], schema):
            return None
        if spec.get('policy'):
            entry.update(policy_version='case-policy-v1', authoritative=False, commercial_authorization=False)
            entry['limitations'].append('Excluded from authoritative policy publication.')
        if entry['provenance_type'] != 'ACTUAL':
            self.case['assumptions'][key] = deepcopy(entry)
        return entry
