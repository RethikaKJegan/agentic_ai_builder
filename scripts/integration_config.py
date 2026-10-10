"""Project-local configuration utilities; never log values."""
import json
import os
import re
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_env():
    values = {}
    for line in (ROOT / '.env').read_text().splitlines():
        match = re.match(r'^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$', line.strip())
        if match:
            key, value = match.groups()
            if value.startswith('"'):
                value = json.loads(value)
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            values[key] = value
    return values


def private_write(path, contents):
    path = Path(path)
    if path.is_symlink():
        raise ValueError('Refusing a symlink destination')
    fd, temp = tempfile.mkstemp(prefix='.integration-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as handle:
            handle.write(contents)
        os.chmod(temp, 0o600)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def save_value(key, value):
    path = ROOT / '.env'
    lines = path.read_text().splitlines()
    replacement = key + '=' + json.dumps(value)
    found = False
    for i, line in enumerate(lines):
        if re.match(r'^(?:export\s+)?' + re.escape(key) + r'\s*=', line.strip()):
            lines[i] = replacement
            found = True
    if not found:
        lines.append(replacement)
    private_write(path, '\n'.join(lines) + '\n')
