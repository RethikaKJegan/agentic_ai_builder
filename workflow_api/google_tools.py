"""Connection-backed runtime adapters. Phase 1 OAuth/account management is unchanged."""
from copy import copy, deepcopy
from types import SimpleNamespace
from contextvars import ContextVar
from contextlib import contextmanager
import base64
import hashlib
import json
import re
import time
from email.message import EmailMessage

from runtime.service import RuntimeFailure
from .service import ApiFailure

KEY = 'google_connection_id'
GOOGLE = 'https://www.googleapis.com/auth/'
PROVIDERS = {'google_sheets', 'gmail', 'google_calendar'}
PLANNING = ContextVar('selected_google_planning', default=None)


def connection_id(workflow):
    value=workflow.get('metadata',{}).get(KEY)
    if value is not None and (not isinstance(value,str) or not re.fullmatch(r'gc_[a-f0-9]{32}',value)):
        raise ApiFailure('GOOGLE_CONNECTION_INVALID','Select a saved Google connection.',400)
    return value


def effective_scopes(scopes):
    result=set(scopes)
    for write,read in [('spreadsheets','spreadsheets.readonly'),('calendar.events','calendar.events.readonly'),('gmail.compose','gmail.send')]:
        if GOOGLE+write in result:result.add(GOOGLE+read)
    return result


class OwnedToken:
    def __init__(self,manager,auth,identifier):
        self.manager,self.auth,self.identifier=manager,deepcopy(auth),identifier

    def record(self):
        with self.manager.store.transaction(write=False) as db:
            row=self.manager.owned(db,self.auth,self.identifier)
        if row[6] not in {'connected','verification_failed'} or not row[7]:
            raise ApiFailure('GOOGLE_RECONNECT_REQUIRED','Reconnect the selected Google account. No other account was used.',409)
        return row

    def __call__(self,scopes,timeout):
        try:
            row=self.record()
            required={s if s.startswith('https://') else GOOGLE+s for s in scopes}
            if not required <= effective_scopes(json.loads(row[5])):
                raise ApiFailure('GOOGLE_SCOPE_REQUIRED','Grant the selected account access for this operation under Integrations.',403)
            # Phase 1 owns encrypted storage and coordinated token refresh.
            credentials=self.manager.credentials(self.auth,self.identifier)
            row=self.record()
            if not required <= effective_scopes(json.loads(row[5])):
                raise ApiFailure('GOOGLE_SCOPE_REQUIRED','Google no longer grants the required operation scope.',403)
            return credentials['access_token']
        except ApiFailure as exc:raise RuntimeFailure(exc.code,str(exc),exc.status) from None

    def legacy(self,write=False):
        token=self(['spreadsheets' if write else 'spreadsheets.readonly'],15)
        return SimpleNamespace(token=token,scopes=json.loads(self.record()[5]))


class GoogleTools:
    def __init__(self,manager,service):self.manager,self.service=manager,service

    @contextmanager
    def planning(self, auth, context):
        identifier=context.get(KEY) if isinstance(context,dict) else None
        if identifier:
            with self.service.store.transaction(write=False) as db:
                self.validate({'metadata':{KEY:identifier}},auth,db)
        marker=PLANNING.set((deepcopy(auth),identifier) if identifier else None)
        try:yield identifier
        finally:PLANNING.reset(marker)

    def discover(self, connector, resource):
        selected=PLANNING.get()
        if not selected:return connector.discover(resource)
        auth,identifier=selected
        bound=copy(connector)
        token=OwnedToken(self.manager,auth,identifier)
        bound.token_file=lambda:token.legacy(False)
        return bound.discover(resource)

    def validate(self,workflow,auth,db):
        identifier=connection_id(workflow)
        if not identifier:return
        row=self.manager.owned(db,auth,identifier)
        if row[6] not in {'connected','verification_failed'} or not row[7]:
            raise ApiFailure('GOOGLE_RECONNECT_REQUIRED','Reconnect the selected Google account before saving this binding.',409)

    def bind(self,connector,workflow,run,auth,grant):
        identifier=connection_id(workflow)
        if not identifier:return connector
        tool_id=grant['tool_id']
        # Domain coordinators do not contact Google themselves; child actions inherit the reference.
        definition=getattr(connector,'definition',{})
        provider=definition.get('provider_id') or getattr(connector,'provider_id',None)
        if provider in {'google_drive','google_docs'}:
            raise RuntimeFailure('GOOGLE_TOOL_UNSUPPORTED','Selected-account Drive and Docs operations are not enabled in this phase.',403)
        is_sheets=tool_id in {'google_sheets_read_rows','google_sheets_update_row','google_sheets_upsert_record'}
        if provider not in PROVIDERS and not is_sheets and tool_id!='smtp_send_email':return connector
        token=OwnedToken(self.manager,auth,identifier)
        try:row=token.record()
        except ApiFailure as exc:raise RuntimeFailure(exc.code,str(exc),exc.status) from None
        required=definition.get('authentication',{}).get('scopes',[])
        if is_sheets:required=['spreadsheets' if connector.external_write else 'spreadsheets.readonly']
        if tool_id in {'smtp_send_email','extension_mail_send'}:required=['gmail.send']
        if tool_id=='extension_mail_draft':required=['gmail.compose']
        if tool_id=='extension_mail_reply':required=['gmail.readonly','gmail.send']
        if provider=='google_calendar' and not required:required=['calendar.events.readonly']
        if not {s if s.startswith('https://') else GOOGLE+s for s in required} <= effective_scopes(json.loads(row[5])):
            raise RuntimeFailure('GOOGLE_SCOPE_REQUIRED','Grant the selected account access for this operation under Integrations.',403)
        bound=self.adapt(connector,token,tool_id)
        bound.google_connection_info={'connection_id':identifier,'account_email':row[4],'provider_id':provider or ('gmail' if tool_id=='smtp_send_email' else 'google_sheets')}
        return bound

    def adapt(self,connector,token,tool_id):
        from connector_extension.google import GoogleAPI
        # ScopedConnector delegates __getattr__; construct it explicitly instead of copy's reconstruction hooks.
        from .procurement import ScopedConnector
        if isinstance(connector,ScopedConnector):
            return ScopedConnector(self.adapt(connector.connector,token,tool_id),connector.procurement,connector.workflow)
        bound=copy(connector)
        if hasattr(connector,'connector'):
            bound.connector=self.adapt(connector.connector,token,tool_id)
            return bound
        if hasattr(connector,'api') and isinstance(connector.api,GoogleAPI):
            bound.api=GoogleAPI(token,connector.api.transport)
            if connector.definition.get('provider_id')=='gmail':bound.account=token.record()[4]
        if tool_id in {'google_sheets_read_rows','google_sheets_update_row','google_sheets_upsert_record'}:
            bound.token_file=lambda:token.legacy(bool(bound.external_write))
        if getattr(connector,'provider_id',None)=='google_calendar':
            bound.token_file=lambda:SimpleNamespace(token=token(['calendar.events.readonly'],15))
            bound.headers=dict(connector.headers)
        if tool_id=='smtp_send_email':
            # Same input/output contract and recipient/approval checks; delivery uses selected Gmail OAuth.
            bound.google_sender=lambda inputs,effect_id:self.send_mail(token,inputs,effect_id)
        return bound

    def send_mail(self,token,inputs,effect_id):
        from connector_extension.google import GoogleAPI
        from connector_extension.common import EffectJournal
        from pathlib import Path
        api=GoogleAPI(token)
        record=token.record()
        message=EmailMessage()
        message['From']=record[4];message['To']=inputs['to'];message['Subject']=inputs['subject']
        message['Message-ID']='<'+hashlib.sha256(effect_id.encode()).hexdigest()+'@agentic-ai-builder.local>'
        message.set_content(inputs['body'])
        payload={'raw':base64.urlsafe_b64encode(message.as_bytes()).decode().rstrip('=')}
        journal=EffectJournal(Path(__file__).resolve().parents[1]/'.local/google-tool-effects',database_url=getattr(self.service,'auxiliary_database_url',None))
        def action():
            result=api.request('gmail','POST','messages/send',['gmail.send'],payload,deadline=time.monotonic()+15)
            return {'message_id':result['id']}
        return journal.perform('selected_gmail_send',effect_id,{'connection_id':token.identifier,**inputs},action)

    def inherit(self,workspace,job,workflow):
        owner=job.get('owner_workflow')
        if not owner:return workflow
        with self.service.store.transaction(write=False) as db:
            parent=self.service.store.get(db,workspace,owner['workflow_id'],owner['version'])
        if not parent:raise RuntimeFailure('GOOGLE_OWNER_REVISION_REQUIRED','The owning workflow revision is unavailable.',403)
        identifier=connection_id(parent)
        if not identifier:return workflow
        result=deepcopy(workflow)
        existing=connection_id(result)
        if existing and existing!=identifier:raise RuntimeFailure('GOOGLE_CONNECTION_MISMATCH','Child action selected a different Google connection.',403)
        result.setdefault('metadata',{})[KEY]=identifier
        return result


def install(service,manager):
    tools=GoogleTools(manager,service)
    service.google_tools=tools
    service.validate_google_binding=tools.validate
    service.bind_google_connector=tools.bind
    return tools
