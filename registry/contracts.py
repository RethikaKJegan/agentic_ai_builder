"""Canonical contract validation with privacy-safe errors."""
import json
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = {
    'workflow': 'workflow-schema-v1', 'agent': 'agent-contract-v1',
    'tool': 'tool-contract-v1', 'api': 'api-payloads-v1',
    'error': 'error-format-v1', 'auth': 'auth-permissions-v1',
    'branching': 'branching-approvals-v1', 'run_status': 'run-status-versioning-v1',
    'lifecycle': 'workflow-operations-v2',
}


def schema(name):
    return json.loads((ROOT / 'shared/contracts' / f'{VERSIONS[name]}.json').read_text())


class RegistryError(Exception):
    def __init__(self, code, message, field=None, details=None, status=400):
        super().__init__(message)
        self.code, self.field, self.details, self.status = code, field, details or {}, status

    def envelope(self, request_id):
        result = dict(error_code=self.code, message=str(self), request_id=request_id,
                      retryable=False, field=self.field, details=self.details)
        Draft202012Validator(schema('error')).validate(result)
        return result


def validate(value, name):
    errors = list(Draft202012Validator(schema(name)).iter_errors(value))
    if errors:
        # Never include validator messages or values: they may contain a secret.
        first = errors[0]
        path = '.'.join(str(part) for part in first.path)
        details = {}
        if first.validator == 'required' and isinstance(first.instance, dict):
            details['missing_fields'] = [key for key in first.validator_value if key not in first.instance]
        raise RegistryError('VALIDATION_FAILED', f'The {name} contract is invalid.', path or name, details)


def validate_json_schema(value):
    if not isinstance(value, dict):
        raise RegistryError('INVALID_SCHEMA', 'A tool or agent schema must be an object.')
    try:
        Draft202012Validator.check_schema(value)
    except Exception as exc:
        raise RegistryError('INVALID_SCHEMA', 'A tool or agent schema is invalid.') from exc
    def check(item):
        if isinstance(item, dict):
            if any(key in item for key in ('$ref', '$dynamicRef')):
                raise RegistryError('UNSUPPORTED_SCHEMA', 'Registry schemas must be self-contained without references.')
            for child in item.values():
                check(child)
        elif isinstance(item, list):
            for child in item:
                check(child)
    check(value)
