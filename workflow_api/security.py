"""Deployment origin validation. Production login is deliberately deferred."""
from urllib.parse import urlsplit
from contextvars import ContextVar

request_correlation = ContextVar("builder_request_correlation", default=None)

PUBLIC_ORIGIN = 'https://praxi.bellcorpstudio.com'
LOCAL_ORIGINS = tuple(f'http://{host}:{port}' for host in ('localhost', '127.0.0.1') for port in (3000, 3001, 3100))


def deployment_mode(mode):
    if mode not in {'development', 'test', 'production'}:
        raise ValueError('Use an explicit supported environment.')
    if mode == 'production':
        raise ValueError('Production authentication is not configured. Google Workspace setup is deferred.')
    return mode


def origins(value=None, production=False):
    entries = value.split(',') if isinstance(value, str) else value
    entries = entries if entries is not None else ([PUBLIC_ORIGIN] if production else LOCAL_ORIGINS)
    result = set()
    for entry in entries:
        entry = entry.strip()
        parsed = urlsplit(entry)
        try:
            port = parsed.port
        except ValueError:
            raise ValueError('Invalid origin port.') from None
        if (parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password or
                parsed.path or parsed.query or parsed.fragment or '*' in entry or
                (production and parsed.scheme != 'https')):
            raise ValueError('Origins must be exact scheme, host and optional port, without a path.')
        if not production and parsed.hostname not in {'localhost', '127.0.0.1', '::1'}:
            raise ValueError('Development origins must be loopback origins.')
        # Retain explicit port spelling: incoming Origin must match configuration exactly.
        if port == 0:
            raise ValueError('Invalid origin port.')
        result.add(entry)
    if not result:
        raise ValueError('Configure at least one UI origin.')
    return frozenset(result)



def planning_deadline(seconds):
    if type(seconds) is not int or not 30 <= seconds <= 300:
        raise ValueError('Planner timeout must be an integer between 30 and 300 seconds.')
    return seconds * 4 + 30
