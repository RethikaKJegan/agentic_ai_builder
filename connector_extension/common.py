"""Extension-owned bounded I/O, authorization, effect journal and artifacts."""
from copy import copy
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import time
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError
from jsonschema import Draft202012Validator
from registry.safety import reject_secrets
from runtime.service import RuntimeFailure, digest

MAX_RESPONSE = 8 * 1024 * 1024
MAX_ATTACHMENT = 5 * 1024 * 1024


def denied(code, message, status=403):
    raise RuntimeFailure(code, message, status)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        denied('PROVIDER_REDIRECT_DENIED', 'Provider redirects are not authorized.')


class JSONTransport:
    def __init__(self, opener=None, max_bytes=MAX_RESPONSE):
        self.opener = opener or build_opener(NoRedirect()).open
        self.max_bytes = max_bytes

    def request(self, method, url, headers, body=None, timeout=30):
        if urlparse(url).scheme != 'https' or not 0 < timeout <= 30:
            denied('PROVIDER_REQUEST_INVALID', 'Use a bounded HTTPS provider request.', 400)
        data = None if body is None else json.dumps(body, allow_nan=False).encode()
        request = Request(url, headers=headers, data=data, method=method)
        try:
            with self.opener(request, timeout=timeout) as response:
                if response.geturl() != url:
                    denied('PROVIDER_REDIRECT_DENIED', 'Provider redirects are not authorized.')
                raw = response.read(self.max_bytes + 1)
                if len(raw) > self.max_bytes:
                    denied('PROVIDER_RESPONSE_TOO_LARGE', 'The provider response exceeds the configured bound.', 502)
                return json.loads(raw) if raw else {}
        except RuntimeFailure:
            raise
        except HTTPError as exc:
            # Retain a bounded, secret-checked message, never the complete body,
            # headers, response URL or arbitrary provider JSON.
            status=exc.code if type(exc.code) is int and 100<=exc.code<=599 else 0
            diagnostic={'http_status':status}
            try:
                error=json.loads(exc.read(16385)).get('error',{})
                message=error.get('message')
                if isinstance(message,str) and len(message)<=2000:
                    reject_secrets(message)
                    diagnostic['message']=re.sub(r'https?://\S+','[provider URL omitted]',message)
                category=error.get('status')
                if isinstance(category,str) and re.fullmatch('[A-Z_]{1,80}',category):diagnostic['status']=category
            except Exception:pass
            failure=RuntimeFailure('PROVIDER_HTTP_'+str(status),'The provider rejected the request; response details are suppressed.',502)
            failure.provider_diagnostic=diagnostic
            raise failure from None
        except Exception:
            denied('PROVIDER_REQUEST_FAILED', 'Provider request failed; details are suppressed.', 502)


class EffectJournal:
    """Commit intent before writes; unknown results can never be replayed silently."""
    def __init__(self, root):
        self.path = Path(root) / 'effects.sqlite3'
        if self.path.is_symlink(): denied('STATE_PATH_INVALID', 'The effect journal cannot be a symlink.')
        with sqlite3.connect(self.path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS effects (key TEXT PRIMARY KEY, fingerprint TEXT, state TEXT, result TEXT)')
        os.chmod(self.path, 0o600)

    def perform(self, tool_id, effect_id, inputs, action):
        key = digest([tool_id, effect_id]); fingerprint = digest(inputs)
        with sqlite3.connect(self.path, timeout=10) as db:
            db.execute('BEGIN IMMEDIATE')
            old = db.execute('SELECT fingerprint,state,result FROM effects WHERE key=?', (key,)).fetchone()
            if old:
                if old[0] != fingerprint:
                    denied('EFFECT_REFERENCE_MISMATCH', 'This action reference belongs to different inputs.')
                if old[1] == 'completed': return json.loads(old[2])
                denied('UNKNOWN_INVOCATION_RESULT', 'A previous write attempt has an unknown result; reconcile it before proceeding.')
            db.execute('INSERT INTO effects VALUES (?,?,?,NULL)', (key, fingerprint, 'started'))
        try:
            result = action()
            reject_secrets(result)
        except Exception as exc:
            category=exc.code if isinstance(exc,RuntimeFailure) and isinstance(exc.code,str) and re.fullmatch(r'[A-Z][A-Z0-9_]{1,99}',exc.code) else 'PROVIDER_ACTION_FAILED'
            diagnostic={'failure_category':category}
            if isinstance(exc,RuntimeFailure) and hasattr(exc,'provider_diagnostic'):diagnostic['provider_diagnostic']=exc.provider_diagnostic
            with sqlite3.connect(self.path) as db:
                db.execute("UPDATE effects SET result=? WHERE key=? AND state='started'",
                           (json.dumps(diagnostic),key))
            denied('UNKNOWN_INVOCATION_RESULT', 'The external write result is uncertain; no automatic replay is permitted.', 502)
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE effects SET state='completed',result=? WHERE key=?", (json.dumps(result), key))
        return result


class ArtifactStore:
    """Opaque immutable references, isolated by workspace/workflow/revision."""
    def __init__(self, root):
        self.root = Path(root) / 'artifacts'
        if self.root.is_symlink(): denied('ARTIFACT_INVALID', 'The artifact directory cannot be a symlink.')
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)

    def directory(self, namespace):
        if not namespace: denied('ARTIFACT_SCOPE_REQUIRED', 'Bind artifacts to an exact workflow revision.')
        folder = self.root / digest(namespace)
        if folder.is_symlink(): denied('ARTIFACT_INVALID', 'The workflow artifact directory cannot be a symlink.')
        folder.mkdir(mode=0o700, exist_ok=True)
        return folder

    def put(self, namespace, content):
        if not isinstance(content, bytes) or len(content) > MAX_ATTACHMENT:
            denied('ATTACHMENT_TOO_LARGE', 'Attachments must be at most five MiB.', 400)
        identifier = 'artifact_' + hashlib.sha256(content).hexdigest()
        path = self.directory(namespace) / identifier
        # O_NOFOLLOW and immutable content hashes prevent local path substitution.
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
        try:
            fd = os.open(path, flags, 0o600)
        except FileExistsError:
            if self.get(namespace, identifier) != content:
                denied('ARTIFACT_INVALID', 'The existing artifact does not match its reference.')
        else:
            with os.fdopen(fd, 'wb') as handle: handle.write(content)
        return identifier

    def get(self, namespace, identifier):
        if not isinstance(identifier, str) or not re.fullmatch(r'artifact_[a-f0-9]{64}', identifier):
            denied('ARTIFACT_INVALID', 'Use an opaque extension artifact reference.', 400)
        path = self.directory(namespace) / identifier
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, 'rb') as handle: content = handle.read(MAX_ATTACHMENT + 1)
        except OSError:
            denied('ARTIFACT_NOT_FOUND', 'The artifact was not found in this workflow revision.', 404)
        if len(content) > MAX_ATTACHMENT or hashlib.sha256(content).hexdigest() != identifier[9:]:
            denied('ARTIFACT_INVALID', 'The artifact content no longer matches its reference.')
        return content


def decode_data(value, maximum=MAX_ATTACHMENT):
    try:
        if not isinstance(value, str) or len(value) > (maximum * 4 // 3 + 8): raise ValueError()
        result = base64.b64decode(value + '=' * (-len(value) % 4), altchars=b'-_', validate=True)
        if len(result) > maximum: raise ValueError()
        return result
    except (ValueError, TypeError):
        denied('ATTACHMENT_INVALID', 'Provider attachment data is invalid or exceeds its bound.', 502)


class Connector:
    retry_safe = False
    timeout = 30

    def __init__(self, definition, api, journal=None, artifacts=None):
        self.definition, self.api = definition, api
        self.journal, self.artifacts = journal, artifacts
        self.external_write = bool(definition['approval_required'])
        self.namespace = None

    def bind_workflow(self, workflow):
        bound = copy(self)
        bound.namespace = [workflow.get('metadata', {}).get('workspace_id'), workflow['workflow_id'], workflow['version']]
        if not bound.namespace[0]: denied('WORKSPACE_REQUIRED', 'Use an exact workspace-bound revision.')
        return bound

    @staticmethod
    def reservation(grant):
        return {'tool_calls': 1, 'estimated_cost_usd': 0}

    def invoke(self, grant, inputs, effect_id):
        reject_secrets(inputs)
        tool = self.definition
        if (grant.get('tool_id') != tool['tool_id'] or grant.get('authorization_state') != 'authorized'
                or not grant.get('authorization_reference') or grant.get('credential_reference') != 'cred_extension_' + tool['provider_id']
                or grant.get('input_schema') != tool['input_schema'] or grant.get('output_schema') != tool['output_schema']):
            denied('CONNECTOR_NOT_AUTHORIZED', 'Use an exact current Registry tool binding.')
        if self.external_write and (not grant.get('approval_reference') or
                grant.get('destination') not in tool.get('allowed_destinations', [])):
            denied('APPROVAL_REQUIRED', 'This connector requires a reviewed write binding.')
        if list(Draft202012Validator(tool['input_schema']).iter_errors(inputs)):
            denied('CONNECTOR_INPUT_INVALID', 'Inputs do not match this connector operation.', 400)
        deadline = time.monotonic() + self.timeout
        result = self.execute(grant, inputs, effect_id, deadline)
        reject_secrets(result)
        if list(Draft202012Validator(tool['output_schema']).iter_errors(result)):
            denied('CONNECTOR_OUTPUT_INVALID', 'The provider result does not match this operation.', 502)
        return result

    def write(self, effect_id, inputs, action):
        if self.journal is None: denied('EFFECT_JOURNAL_REQUIRED', 'Configure the extension effect journal.')
        def checked():
            result = action()
            if list(Draft202012Validator(self.definition['output_schema']).iter_errors(result)):
                denied('CONNECTOR_OUTPUT_INVALID', 'The write response is not confirmed.', 502)
            return result
        return self.journal.perform(self.definition['tool_id'], effect_id, inputs, checked)
