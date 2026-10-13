"""Google HTTP access with separate extension credentials and explicit scopes."""
from functools import partial
import fcntl
import os
from pathlib import Path
import threading
import time
from .catalog import GOOGLE
from .common import JSONTransport, denied


class GoogleToken:
    def __init__(self, token_file):
        self.path = Path(token_file)
        self.lock = threading.Lock()

    def __call__(self, scopes, timeout):
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from requests import Session
        from scripts.integration_config import private_write
        if not self.path.is_file() or self.path.is_symlink():
            denied('GOOGLE_CONNECTION_REQUIRED', 'Authorize the separate extension Google connection.', 503)
        with self.lock, self.path.with_suffix('.lock').open('a') as lock:
            os.chmod(lock.name, 0o600)
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                credentials = Credentials.from_authorized_user_file(str(self.path))
                if not credentials.valid:
                    with Session() as session:
                        credentials.refresh(partial(Request(session=session), timeout=max(.1, timeout)))
                    private_write(self.path, credentials.to_json())
                # OAuth helper writes verified scopes; Google's endpoint still enforces access.
                grants = set(credentials.granted_scopes or credentials.scopes or [])
                for full, read in [('spreadsheets', 'spreadsheets.readonly'), ('calendar.events', 'calendar.events.readonly')]:
                    if GOOGLE + full in grants: grants.add(GOOGLE + read)
                if not credentials.token or not {GOOGLE + scope for scope in scopes} <= grants:
                    denied('GOOGLE_SCOPE_REQUIRED', 'The extension Google consent lacks a required operation scope.')
                return credentials.token
            except Exception as exc:
                from runtime.service import RuntimeFailure
                if isinstance(exc, RuntimeFailure): raise
                denied('GOOGLE_CONNECTION_FAILED', 'The extension Google token could not be loaded or refreshed.', 503)


class GoogleAPI:
    HOSTS = {'sheets': 'https://sheets.googleapis.com/v4',
             'calendar': 'https://www.googleapis.com/calendar/v3',
             'gmail': 'https://gmail.googleapis.com/gmail/v1/users/me'}

    def __init__(self, token, transport=None):
        self.token, self.transport = token, transport or JSONTransport()

    def request(self, provider, method, path, scopes, body=None, deadline=None):
        deadline = deadline or time.monotonic() + 30
        remaining = deadline - time.monotonic()
        if remaining <= 0: denied('CONNECTOR_TIMEOUT', 'The connector operation timed out.', 504)
        token = self.token(scopes, min(30, remaining))
        remaining = deadline - time.monotonic()
        if remaining <= 0: denied('CONNECTOR_TIMEOUT', 'The connector operation timed out.', 504)
        return self.transport.request(method, self.HOSTS[provider] + '/' + path,
            {'Authorization': 'Bearer ' + token, 'Accept': 'application/json', 'Content-Type': 'application/json'},
            body, timeout=min(30, remaining))
