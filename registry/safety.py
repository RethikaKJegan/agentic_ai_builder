"""Reject secrets throughout metadata before storing or logging it."""
import re
from .contracts import RegistryError

_PATTERNS = (
    re.compile(r'(?:api[_-]?key|secret|password|token)\s*[:=]\s*[^\s,}]+', re.I),
    re.compile(r'\bsk-[A-Za-z0-9_-]{8,}\b'),
    re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'),
    re.compile(r'\bBearer\s+\S+', re.I),
    re.compile(r'://[^/\s:@]+:[^/\s@]+@'),
)
_SECRET_KEYS = {'password', 'secret', 'api_key', 'access_token', 'refresh_token', 'private_key', 'authorization'}


def reject_secrets(value):
    if isinstance(value, str):
        if any(pattern.search(value) for pattern in _PATTERNS):
            raise RegistryError('SENSITIVE_DATA_DETECTED', 'Raw credentials are not accepted.')
    elif isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise RegistryError('INVALID_REQUEST', 'Metadata keys must be strings.')
            if key.lower() in _SECRET_KEYS:
                raise RegistryError('SENSITIVE_DATA_DETECTED', 'Raw credentials are not accepted.')
            reject_secrets(key)
            reject_secrets(child)
    elif isinstance(value, list):
        for child in value:
            reject_secrets(child)
