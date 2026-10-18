"""Owned web OAuth connections; independent of existing execution credentials."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit

import httpx
from cryptography.fernet import Fernet
from .service import ApiFailure

IDENTITY = {"openid", "email"}
CAPABILITIES = {
    "gmail_read": ["https://www.googleapis.com/auth/gmail.readonly"],
    "gmail_draft": ["https://www.googleapis.com/auth/gmail.compose"],
    "gmail_send": ["https://www.googleapis.com/auth/gmail.send"],
    "sheets_read": ["https://www.googleapis.com/auth/spreadsheets.readonly"],
    "sheets_write": ["https://www.googleapis.com/auth/spreadsheets"],
    "calendar_read": ["https://www.googleapis.com/auth/calendar.events.readonly"],
    "calendar_write": ["https://www.googleapis.com/auth/calendar.events"],
}
CALLBACK = "/integrations/google/callback"
BROWSER_COOKIE = "builder_google_oauth"
ROOT = Path(__file__).resolve().parents[1]


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class GoogleConnections:
    def __init__(self, store, env):
        self.store, self.env = store, env
        self.config_error = None
        self.client = None
        self.cipher = None
        self.redirect_uri = env.get("BUILDER_GOOGLE_REDIRECT_URI", "")
        self.return_origin = ""
        self.registered_callback = False
        try:
            path = Path(env.get("BUILDER_GOOGLE_CLIENT_FILE", ""))
            keypath = Path(env.get("BUILDER_GOOGLE_KEY_FILE", ""))
            if not str(env.get("BUILDER_GOOGLE_CLIENT_FILE", "")) or not str(env.get("BUILDER_GOOGLE_KEY_FILE", "")):
                raise ValueError()
            doc = json.loads((path if path.is_absolute() else ROOT/path).read_text())
            self.client = doc["web"]
            if not self.client.get("client_id") or not self.client.get("client_secret"):
                raise ValueError()
            parsed = urlsplit(self.redirect_uri)
            if parsed.path != "/api/backend"+CALLBACK or parsed.query or parsed.fragment or parsed.username or parsed.password or not parsed.hostname:
                raise ValueError()
            if parsed.scheme != "https" and not (parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1"}):
                raise ValueError()
            self.return_origin = f"{parsed.scheme}://{parsed.netloc}"
            self.registered_callback = self.redirect_uri in self.client.get("redirect_uris", [])
            self.cipher = Fernet((keypath if keypath.is_absolute() else ROOT/keypath).read_bytes().strip())
        except (ValueError, KeyError, OSError, TypeError):
            self.config_error = "Configure a Google web client, encryption key and exact public callback on the server."
        # Additive component migration; works with the store's SQLite/Postgres adapter.
        with store.transaction() as db:
            db.execute("CREATE TABLE IF NOT EXISTS google_connection_migrations (version INTEGER PRIMARY KEY)")
            db.execute("INSERT INTO google_connection_migrations(version) VALUES (1) ON CONFLICT DO NOTHING")
            db.execute("CREATE TABLE IF NOT EXISTS google_connections (connection_id TEXT PRIMARY KEY, workspace TEXT NOT NULL, owner TEXT NOT NULL, account_id TEXT NOT NULL, email TEXT NOT NULL, scopes TEXT NOT NULL, status TEXT NOT NULL, credentials TEXT, revision INTEGER NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, verified_at TEXT, error_code TEXT, UNIQUE(workspace,owner,account_id))")
            db.execute("CREATE TABLE IF NOT EXISTS google_workflow_defaults (workspace TEXT NOT NULL, owner TEXT NOT NULL, connection_id TEXT NOT NULL, PRIMARY KEY(workspace,owner))")
            db.execute("CREATE TABLE IF NOT EXISTS google_oauth_sessions (state_hash TEXT PRIMARY KEY, workspace TEXT NOT NULL, owner TEXT NOT NULL, browser_hash TEXT NOT NULL, expires_at REAL NOT NULL, used INTEGER NOT NULL, connection_id TEXT, secret TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS google_connection_audit (event_id TEXT PRIMARY KEY, workspace TEXT NOT NULL, owner TEXT NOT NULL, connection_id TEXT, event_type TEXT NOT NULL, created_at TEXT NOT NULL)")

    def set_workflow_default(self, auth, identifier):
        workspace, owner = self.identity(auth, True)
        with self.store.transaction() as db:
            row = self.owned(db, auth, identifier)
            if row[6] not in {'connected', 'verification_failed'} or not row[7]:
                raise ApiFailure('GOOGLE_RECONNECT_REQUIRED', 'Reconnect the selected default Google account.', 409)
            db.execute('INSERT INTO google_workflow_defaults VALUES (?,?,?) ON CONFLICT(workspace,owner) DO UPDATE SET connection_id=excluded.connection_id',
                       (workspace, owner, identifier))
        return {'connection_id': identifier}

    def workflow_default(self, auth):
        workspace, owner = self.identity(auth)
        with self.store.transaction(write=False) as db:
            row = db.execute('SELECT connection_id FROM google_workflow_defaults WHERE workspace=? AND owner=?', (workspace, owner)).fetchone()
            if row:
                current = self.owned(db, auth, row[0])
                if current[6] not in {'connected', 'verification_failed'} or not current[7]:
                    raise ApiFailure('GOOGLE_RECONNECT_REQUIRED', 'Reconnect the default Google account; no other account was substituted.', 409)
                return row[0]
        return None

    def require_config(self):
        if self.config_error:
            raise ApiFailure("GOOGLE_SETUP_REQUIRED", self.config_error, 503)

    @staticmethod
    def identity(auth, write=False):
        permission = "tools.assign" if write else "tools.read"
        if auth.get("decision") != "allow" or permission not in auth.get("permissions", []):
            raise ApiFailure("OPERATION_NOT_AUTHORIZED", "Integration management permission is required.", 403)
        return auth["subject"]["workspace_id"], auth["subject"]["subject_id"]

    def audit(self, db, workspace, owner, connection_id, event):
        db.execute("INSERT INTO google_connection_audit VALUES (?,?,?,?,?,?)", ("ga_"+secrets.token_hex(16),workspace,owner,connection_id,event,now()))

    def owned(self, db, auth, connection_id):
        workspace, owner = self.identity(auth)
        row = db.execute("SELECT connection_id,workspace,owner,account_id,email,scopes,status,credentials,revision,created_at,updated_at,verified_at,error_code FROM google_connections WHERE connection_id=? AND workspace=? AND owner=?", (connection_id,workspace,owner)).fetchone()
        if not row:
            raise ApiFailure("CONNECTION_NOT_FOUND", "Google connection not found.", 404)
        return row

    @staticmethod
    def public(row):
        scopes = json.loads(row[5])
        effective = set(scopes)
        if "https://www.googleapis.com/auth/spreadsheets" in effective:
            effective.add("https://www.googleapis.com/auth/spreadsheets.readonly")
        if "https://www.googleapis.com/auth/calendar.events" in effective:
            effective.add("https://www.googleapis.com/auth/calendar.events.readonly")
        if "https://www.googleapis.com/auth/gmail.compose" in effective:
            effective.add("https://www.googleapis.com/auth/gmail.send")
        return dict(connection_id=row[0],account_email=row[4],granted_scopes=scopes,status=row[6],revision=row[8],created_at=row[9],updated_at=row[10],last_verified_at=row[11],last_error_code=row[12],capabilities={k: all(s in effective for s in v) for k,v in CAPABILITIES.items()})

    def list(self, auth):
        workspace, owner = self.identity(auth)
        with self.store.transaction(write=False) as db:
            rows = db.execute("SELECT connection_id,workspace,owner,account_id,email,scopes,status,credentials,revision,created_at,updated_at,verified_at,error_code FROM google_connections WHERE workspace=? AND owner=? ORDER BY created_at", (workspace,owner)).fetchall()
        return dict(configured=not bool(self.config_error), setup_message=self.config_error,
                    callback_uri=self.redirect_uri or None, callback_in_client_file=self.registered_callback,
                    items=[self.public(row) for row in rows], capabilities=list(CAPABILITIES), shared_demo_identity=True)

    def authorize(self, auth, browser, capabilities, connection_id=None):
        self.require_config()
        workspace, owner = self.identity(auth, True)
        if not isinstance(capabilities,list) or len(capabilities)>len(CAPABILITIES) or any(not isinstance(k,str) or k not in CAPABILITIES for k in capabilities):
            raise ApiFailure("INVALID_REQUEST", "Choose supported Google capabilities.", 400)
        scopes=set(IDENTITY)
        for k in capabilities: scopes.update(CAPABILITIES[k])
        state, verifier, nonce = secrets.token_urlsafe(32),secrets.token_urlsafe(48),secrets.token_urlsafe(32)
        with self.store.transaction() as db:
            if connection_id:
                row=self.owned(db,auth,connection_id)
                scopes.update(json.loads(row[5]))
            db.execute("DELETE FROM google_oauth_sessions WHERE expires_at<?",(time.time(),))
            secret=self.cipher.encrypt(json.dumps(dict(verifier=verifier,nonce=nonce,scopes=sorted(scopes))).encode()).decode()
            db.execute("INSERT INTO google_oauth_sessions VALUES (?,?,?,?,?,?,?,?)", (digest(state),workspace,owner,digest(browser),time.time()+600,0,connection_id,secret))
        challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
        url="https://accounts.google.com/o/oauth2/v2/auth?"+urlencode(dict(client_id=self.client["client_id"],redirect_uri=self.redirect_uri,response_type="code",scope=" ".join(sorted(scopes)),state=state,nonce=nonce,code_challenge=challenge,code_challenge_method="S256",access_type="offline",include_granted_scopes="true",prompt="consent select_account"))
        return {"authorization_url":url}

    def token_request(self, data):
        try:
            response=httpx.post("https://oauth2.googleapis.com/token",data={**data,"client_id":self.client["client_id"],"client_secret":self.client["client_secret"]},timeout=15)
            value=response.json()
            if response.status_code!=200:
                code="GOOGLE_RECONNECT_REQUIRED" if value.get("error")=="invalid_grant" else "GOOGLE_PROVIDER_FAILED"
                raise ApiFailure(code,"Google authorization could not be completed. Reconnect or retry.",409 if code=="GOOGLE_RECONNECT_REQUIRED" else 503)
            if not isinstance(value.get("access_token"),str): raise ValueError()
            return value
        except ApiFailure: raise
        except Exception: raise ApiFailure("GOOGLE_PROVIDER_FAILED","Google could not be reached. Retry verification.",503) from None

    def validate_identity(self, token, nonce=None):
        from google.oauth2 import id_token
        from google.auth.transport.requests import Request
        try:
            def certificates(url, method="GET", body=None, headers=None, **kwargs):
                return Request()(url,method=method,body=body,headers=headers,timeout=10)
            identity=id_token.verify_oauth2_token(token,certificates,self.client["client_id"])
            if not identity.get("sub") or not identity.get("email") or identity.get("email_verified") is not True: raise ValueError()
            if nonce is not None and not hmac.compare_digest(identity.get("nonce", ""),nonce):raise ValueError()
            return identity
        except Exception:raise ApiFailure("GOOGLE_IDENTITY_INVALID","Google account identity could not be verified.",400) from None

    def complete(self, state, browser, code=None, denied=False):
        self.require_config()
        with self.store.transaction() as db:
            row=db.execute("SELECT workspace,owner,browser_hash,expires_at,used,connection_id,secret FROM google_oauth_sessions WHERE state_hash=?",(digest(state),)).fetchone()
            if not row or row[3]<time.time() or row[4] or not hmac.compare_digest(row[2],digest(browser)):
                raise ApiFailure("OAUTH_SESSION_INVALID","Authorization expired or browser validation failed. Start Connect Google again.",400)
            db.execute("UPDATE google_oauth_sessions SET used=1 WHERE state_hash=?",(digest(state),))
        if denied:return "cancelled"
        if not code:raise ApiFailure("OAUTH_CODE_REQUIRED","Google did not return an authorization code.",400)
        secret=json.loads(self.cipher.decrypt(row[6].encode()))
        tokens=self.token_request(dict(code=code,code_verifier=secret["verifier"],redirect_uri=self.redirect_uri,grant_type="authorization_code"))
        identity=self.validate_identity(tokens.get("id_token", ""),secret["nonce"])
        # Never infer consent from requested scopes if Google omits scope information.
        scopes=sorted(set(str(tokens.get("scope", "")).split()))
        workspace, owner=row[:2]
        stamp=now()
        with self.store.transaction() as db:
            existing=db.execute("SELECT connection_id,credentials,account_id,revision FROM google_connections WHERE workspace=? AND owner=? AND account_id=?",(workspace,owner,identity["sub"])).fetchone()
            if row[5]:
                target=db.execute("SELECT account_id FROM google_connections WHERE connection_id=? AND workspace=? AND owner=?",(row[5],workspace,owner)).fetchone()
                if not target or target[0]!=identity["sub"]:raise ApiFailure("GOOGLE_ACCOUNT_MISMATCH","Select the same account when managing or reconnecting this connection.",409)
            prior=json.loads(self.cipher.decrypt(existing[1].encode())) if existing and existing[1] else {}
            refresh=tokens.get("refresh_token") or prior.get("refresh_token")
            if not refresh:raise ApiFailure("GOOGLE_OFFLINE_ACCESS_REQUIRED","Offline access was not granted. Reconnect and approve access.",409)
            credentials=dict(access_token=tokens["access_token"],refresh_token=refresh,expires_at=time.time()+int(tokens.get("expires_in",3600)),token_type="Bearer",encryption_key_version=1)
            encrypted=self.cipher.encrypt(json.dumps(credentials).encode()).decode()
            connection_id=existing[0] if existing else "gc_"+secrets.token_hex(16)
            if existing:
                db.execute("UPDATE google_connections SET email=?,scopes=?,status='connected',credentials=?,revision=revision+1,updated_at=?,verified_at=?,error_code=NULL WHERE connection_id=?",(identity["email"],json.dumps(scopes),encrypted,stamp,stamp,connection_id))
            else:
                db.execute("INSERT INTO google_connections VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",(connection_id,workspace,owner,identity["sub"],identity["email"],json.dumps(scopes),"connected",encrypted,1,stamp,stamp,stamp,None))
            self.audit(db,workspace,owner,connection_id,"authorized")
        return "connected"

    def credentials(self, auth, connection_id, force=False):
        self.require_config()
        # Existing store write transactions serialize refresh across API processes/workers.
        failure=None
        credentials=None
        with self.store.transaction() as db:
            row=self.owned(db,auth,connection_id)
            if row[6] not in {"connected","verification_failed"} or not row[7]:
                raise ApiFailure("GOOGLE_RECONNECT_REQUIRED","Reconnect this Google account before use.",409)
            credentials=json.loads(self.cipher.decrypt(row[7].encode()))
            if force or credentials["expires_at"]<time.time()+60:
                try:
                    token=self.token_request(dict(grant_type="refresh_token",refresh_token=credentials["refresh_token"]))
                    credentials.update(access_token=token["access_token"],expires_at=time.time()+int(token.get("expires_in",3600)))
                    if token.get("refresh_token"):credentials["refresh_token"]=token["refresh_token"]
                    encrypted=self.cipher.encrypt(json.dumps(credentials).encode()).decode()
                    scopes=json.dumps(sorted(set(str(token["scope"]).split()))) if token.get("scope") else row[5]
                    db.execute("UPDATE google_connections SET credentials=?,scopes=?,revision=revision+1,updated_at=? WHERE connection_id=?",(encrypted,scopes,now(),connection_id))
                except ApiFailure as exc:
                    failure=exc
                    status="reconnect_required" if exc.code=="GOOGLE_RECONNECT_REQUIRED" else "verification_failed"
                    db.execute("UPDATE google_connections SET status=?,error_code=?,updated_at=? WHERE connection_id=?",(status,exc.code,now(),connection_id))
        if failure:raise failure
        return credentials

    def verify(self, auth, connection_id):
        self.identity(auth,True)
        token=self.credentials(auth,connection_id,force=True)
        try:
            response=httpx.get("https://openidconnect.googleapis.com/v1/userinfo",headers={"Authorization":"Bearer "+token["access_token"]},timeout=15)
            value=response.json()
            if response.status_code!=200:raise ValueError()
            with self.store.transaction() as db:
                row=self.owned(db,auth,connection_id)
                if row[6] not in {"connected","verification_failed"} or not row[7]:raise ValueError()
                if value.get("sub")!=row[3] or value.get("email_verified") is not True:raise ValueError()
                db.execute("UPDATE google_connections SET status='connected',verified_at=?,error_code=NULL,updated_at=? WHERE connection_id=?",(now(),now(),connection_id))
                self.audit(db,row[1],row[2],connection_id,"verified")
                result=self.public(self.owned(db,auth,connection_id))
            return result
        except Exception:
            with self.store.transaction() as db:
                self.owned(db,auth,connection_id)
                db.execute("UPDATE google_connections SET status='verification_failed',error_code='GOOGLE_VERIFY_FAILED',updated_at=? WHERE connection_id=? AND credentials IS NOT NULL AND status!='disconnected'",(now(),connection_id))
            raise ApiFailure("GOOGLE_VERIFY_FAILED","Account verification failed. Retry or reconnect. Service operations were not tested.",503) from None

    def disconnect(self, auth, connection_id):
        self.identity(auth,True)
        with self.store.transaction() as db:
            row=self.owned(db,auth,connection_id)
            db.execute("UPDATE google_connections SET status='disconnected',credentials=NULL,revision=revision+1,updated_at=?,error_code=NULL WHERE connection_id=? AND credentials IS NOT NULL AND status!='disconnected'",(now(),connection_id))
            # Invalidate any pending consent that could silently reconnect this record.
            db.execute("UPDATE google_oauth_sessions SET used=1 WHERE workspace=? AND owner=? AND connection_id=?",(row[1],row[2],connection_id))
            self.audit(db,row[1],row[2],connection_id,"disconnected")
            return self.public(self.owned(db,auth,connection_id))
