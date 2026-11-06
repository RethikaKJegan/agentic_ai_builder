"""Existing Google connectors with tenant-local effects and owned OAuth tokens only."""
from copy import deepcopy
from pathlib import Path
from runtime.service import RuntimeFailure


def definitions():
    from connector_extension.catalog import CATALOG
    return [dict(deepcopy(d),availability='enabled') for d in CATALOG.values()
            if d['provider_id'] in {'gmail','google_calendar','google_sheets'}]


def extend_registry(config):
    tools=definitions();permissions={p for d in tools for p in d['permission_scopes']}
    scopes=permissions|{s for d in tools for s in d['authentication']['scopes']}
    policy=config['policy']
    for provider in {'gmail','google_calendar','google_sheets'}:
        reference='cred_extension_'+provider
        policy['credential_references'][reference]=dict(provider_id=provider,scopes=sorted({s for d in tools if d['provider_id']==provider for s in d['authentication']['scopes']+d['permission_scopes']}))
    for d in tools:
        config['tools'].append(dict(definition=d,credential_reference='cred_extension_'+d['provider_id']))
        policy['remaining_quota'][d['tool_id']]=10000
    policy['approved_providers']=sorted(set(policy['approved_providers'])|{'gmail','google_calendar','google_sheets'})
    policy['agent_permissions']=sorted(set(policy['agent_permissions'])|permissions)
    policy['allowed_destinations']=sorted(set(policy['allowed_destinations'])|{v for d in tools for v in d.get('allowed_destinations',[])})
    config['subject_permissions']=sorted(set(config['subject_permissions'])|permissions)
    config['subject_scopes']=sorted(set(config['subject_scopes'])|scopes)


def install(app,env):
    from connector_extension.google import GoogleAPI
    from connector_extension.common import EffectJournal,ArtifactStore
    from connector_extension.sheet_creation import SheetsSetup,SheetResourceStore
    from connector_extension.sheet_report import ReportSheetsSetup
    from connector_extension.sheets import SheetsDiscover,SheetsRead,SheetsWrite
    from connector_extension.calendar import CalendarConnector
    from connector_extension.mail import MailConnector
    service=app.state.workflow_service
    if app.state.google_connections.config_error:raise ValueError('Configure tenant Google OAuth before enabling workflow connectors.')
    state=Path(env['BUILDER_DATABASE_URL']).resolve().parent/'google-tools';state.mkdir(mode=0o700,exist_ok=True)
    def unbound(*args,**kwargs):
        raise RuntimeFailure('GOOGLE_CONNECTION_REQUIRED','Choose a connected Google account for this workflow.',403)
    api=GoogleAPI(unbound);journal=EffectJournal(state);artifacts=ArtifactStore(state);resources=SheetResourceStore(state)
    for d in definitions():
        tid=d['tool_id'];provider=d['provider_id']
        if tid in {'extension_sheets_create','extension_sheets_add_tabs','extension_sheets_create_report'}:
            factory=ReportSheetsSetup if tid=='extension_sheets_create_report' else SheetsSetup
            connector=factory(d,api,journal,resources,[],[])
        elif tid=='extension_sheets_discover':connector=SheetsDiscover(d,api,[])
        elif tid=='google_sheets_read_rows':connector=SheetsRead(d,api,[])
        elif tid=='google_sheets_upsert_record':connector=SheetsWrite(d,api,journal,[],unbound,state/'sheet-locks')
        elif provider=='google_calendar':connector=CalendarConnector(d,api,journal,[])
        elif provider=='gmail':connector=MailConnector(d,api,journal,artifacts,None,[])
        else:raise ValueError('Unsupported owned Google connector.')
        service.runtime_runner.connectors[tid]=connector
