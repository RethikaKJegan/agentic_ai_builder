"""Bounded application evidence for the authorized UI; never private model reasoning."""
import re
from registry.safety import reject_secrets

SENSITIVE = re.compile(r'password|secret|token|credential|authorization|api.?key|private.?key|reasoning|chain.?of.?thought', re.I)


def snapshot(value, depth=0, budget=None):
    budget = [16000] if budget is None else budget
    budget[0] -= 32
    if budget[0] <= 0:
        return '[truncated]'
    if depth > 6:
        return '[truncated]'
    if isinstance(value, dict):
        result = {}
        for index, (key, child) in enumerate(list(value.items())[:40]):
            if budget[0] <= 0:
                result['_truncated'] = True
                break
            safe_key = snapshot(str(key), depth + 1, budget)
            if SENSITIVE.search(str(key)):
                result[f'[redacted field {index}]'] = '[REDACTED]'
            else:
                result[safe_key] = snapshot(child, depth + 1, budget)
        if len(value) > 40:
            result['_truncated'] = True
        return result
    if isinstance(value, list):
        return [snapshot(child, depth + 1, budget) for child in value[:40] if budget[0] > 0] + (['[truncated]'] if len(value) > 40 else [])
    if isinstance(value, str):
        try:
            reject_secrets(value)
        except Exception:
            return '[REDACTED]'
        cap = min(2000, max(0, budget[0]))
        budget[0] -= min(len(value), cap)
        return value[:cap] + ('… [truncated]' if len(value) > cap else '')
    return value if value is None or isinstance(value, (bool, int, float)) else '[unsupported]'
