"""Explicit test-only HTTP fixture server. Never used by the production launcher."""
from pathlib import Path
from copy import deepcopy
import json
import os
import sys
from contextlib import nullcontext
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import uvicorn
from planner import PlannerService
from planner.provider import RuleBasedStructuredOutputProvider
from workflow_api.main import create_app, ROLE_PERMISSIONS
from integration_config import load_env


class _OfflineConnector:
    """Deterministic browser fixture connector; it never reaches a provider."""
    def __init__(self, external_write=False, result=None):
        self.external_write = external_write
        self.result = result
        self.timeout = 30

    @staticmethod
    def reservation(grant):
        return {'tool_calls': 1, 'estimated_cost_usd': 0}

    def invoke(self, grant, inputs, effect_id):
        if self.external_write:
            return self.result or {'message_id': effect_id}
        return {'rows': []}


def _offline_model_factory(definition):
    from runtime.model import BoundedLLM
    def provider(messages, cap, duration):
        if definition.get('hierarchy_role') == 'master':
            result = {'action':'finish','reason':'Explicit offline provider fixture; no connector invocation.',
                      'output':{'summary':'Offline fixture result'}}
        else:
            result = {}
        return json.dumps(result), 0, 0
    return BoundedLLM(definition, provider, lambda messages: 1, 0, 0)

if __name__ == '__main__':
    (ROOT / '.local').mkdir(exist_ok=True)
    directory = Path(os.getenv('BUILDER_TEST_DATABASE_DIR', str(ROOT / '.local' / 'browser-ui'))).resolve()
    if not directory.is_relative_to(ROOT / '.local'):
        raise RuntimeError('Browser test databases must stay under this repository .local directory.')
    directory.mkdir(exist_ok=True)
    with (TemporaryDirectory(prefix="run-", dir=directory) if os.getenv("BUILDER_TEST_FRESH_DATABASE") == "1" else nullcontext(directory)) as database_directory:
        directory = Path(database_directory)
        # Explicit browser-only configured registry; never used by product startup.
        agent = json.loads((ROOT / 'shared/contracts/examples/agents/valid-classifier.json').read_text())
        agent.update(agent_id='reader_agent', capabilities=['read_spreadsheet'], permissions=['data.read'])
        agent['limits'].update(max_tool_calls=4, max_retries=2, max_estimated_cost_usd=1)
        agent['retry_policy']['max_retries'] = 2
        tool = json.loads((ROOT / 'shared/contracts/examples/tools/google-sheets-read.json').read_text())
        tool['availability'] = 'enabled'
        update_tool = json.loads((ROOT / 'shared/contracts/examples/tools/google-sheets-update-row.json').read_text())
        update_tool['availability'] = 'enabled'
        smtp_tool = json.loads((ROOT / 'shared/contracts/examples/tools/smtp-send-email.json').read_text())
        catalog_names = ('slack-send-notification.json', 'github-rest.json', 'open-meteo.json', 'open-library.json',
                         'generic-rest.json', 'google-drive-list.json', 'google-calendar-list.json',
                         'google-docs-read.json', 'webhook-send.json', 'brevo-send-email.json')
        catalog = [json.loads((ROOT / 'shared/contracts/examples/tools' / name).read_text()) for name in catalog_names]
        credential_references = {
            'cred_browser_sheets': dict(provider_id='google_sheets', scopes=['data.read', 'data.write', 'spreadsheets', 'spreadsheets.readonly']),
            'cred_browser_smtp': dict(provider_id='smtp', scopes=['communication.send', 'email.send']),
            'cred_browser_slack': dict(provider_id='slack', scopes=['communication.send', 'slack.access']),
            'cred_browser_github': dict(provider_id='github', scopes=['data.read', 'github.access']),
            'cred_browser_weather': dict(provider_id='open_meteo', scopes=['data.read', 'weather.access']),
            'cred_browser_books': dict(provider_id='open_library', scopes=['data.read', 'books.access']),
            'cred_browser_rest': dict(provider_id='generic_rest', scopes=['data.read', 'http.access']),
            'cred_browser_drive': dict(provider_id='google_drive', scopes=['data.read', 'drive.metadata.readonly']),
            'cred_browser_calendar': dict(provider_id='google_calendar', scopes=['data.read', 'calendar.events.readonly']),
            'cred_browser_docs': dict(provider_id='google_docs', scopes=['data.read', 'documents.readonly']),
            'cred_browser_webhook': dict(provider_id='webhook', scopes=['communication.send', 'webhook.access']),
            'cred_browser_brevo': dict(provider_id='brevo_smtp', scopes=['communication.send', 'email.send']),
        }
        config = dict(policy=dict(workspace_id='local-workspace', agent_permissions=['workflow.read_input', 'data.read', 'data.write', 'communication.send'],
            approved_providers=list({value['provider_id'] for value in credential_references.values()}),
            allowed_destinations=['verified_recipients', 'configured_spreadsheet', 'configured_slack_webhook', 'configured_webhook'], remaining_quota={},
            credential_references=credential_references),
            agents=[agent], tools=[dict(definition=smtp_tool, credential_reference='cred_browser_smtp')], bindings=[],
            subject_permissions=['data.read', 'data.write', 'communication.send'], subject_scopes=['data.read', 'data.write', 'spreadsheets.readonly', 'spreadsheets', 'communication.send', 'email.send', 'slack.access', 'github.access', 'weather.access', 'books.access', 'http.access', 'drive.metadata.readonly', 'calendar.events.readonly', 'documents.readonly', 'webhook.access'],
            operator_permissions=['tools.manage'],
            auto_resolve_planner=True)
        config['policy']['remaining_quota']['smtp_send_email'] = 10
        config['tools'].append(dict(definition=deepcopy(tool), credential_reference='cred_browser_sheets'))
        config['tools'].append(dict(definition=deepcopy(update_tool), credential_reference='cred_browser_sheets'))
        config['policy']['remaining_quota']['google_sheets_read_rows'] = 10
        config['policy']['remaining_quota']['google_sheets_update_row'] = 10
        for definition in catalog:
            definition['availability'] = 'enabled'
            reference = {
                'slack': 'cred_browser_slack', 'github': 'cred_browser_github', 'open_meteo': 'cred_browser_weather',
                'open_library': 'cred_browser_books', 'generic_rest': 'cred_browser_rest', 'google_drive': 'cred_browser_drive',
                'google_calendar': 'cred_browser_calendar', 'google_docs': 'cred_browser_docs', 'webhook': 'cred_browser_webhook',
                'brevo_smtp': 'cred_browser_brevo'}[definition['provider_id']]
            config['tools'].append(dict(definition=definition, credential_reference=reference))
            config['policy']['remaining_quota'][definition['tool_id']] = 10
        documents = []
        for kind in ('ready', 'pending', 'risky'):
            definition = {**deepcopy(tool), 'tool_id': f'sheets_{kind}', 'approval_required': kind == 'pending', 'risk_level': 'high' if kind == 'risky' else 'low'}
            config['tools'].append(dict(definition=definition, credential_reference='cred_browser_sheets'))
            config['policy']['remaining_quota'][definition['tool_id']] = 10
            for version in (1, 2):
                config['bindings'].append(dict(workflow_id=f'registry_{kind}', workflow_version=version, agent_id=agent['agent_id'],
                    capability='read_spreadsheet', tool_id=definition['tool_id'], input_schema=tool['input_schema'], output_schema=tool['output_schema']))
            workflow = json.loads((ROOT / 'shared/contracts/examples/workflows/support-triage.json').read_text())
            workflow.update(workflow_id=f'registry_{kind}', name=f'Registry {kind}', status='draft', version=1,
                agents=[{k: deepcopy(v) for k, v in agent.items() if k not in {'name', 'guardrails', 'retry_policy'}}],
                tools=[dict(tool_id=definition['tool_id'], capability='read_spreadsheet')],
                nodes=[dict(node_id='start', kind='trigger', label='Start'), dict(node_id='read_rows', kind='agent', label='Read rows', agent_id=agent['agent_id']), dict(node_id='finish', kind='output', label='Finish')],
                edges=[dict(edge_id='start_read', source='start', target='read_rows'), dict(edge_id='read_finish', source='read_rows', target='finish')],
                conditions=[], approval_gates=[], metadata={'execution_input_mode':'manual'})
            workflow['inputs'] = [dict(name='request_text',type='string',required=True), dict(name='spreadsheet_id',type='string',required=True), dict(name='range',type='string',required=True)]
            workflow['execution_policy']['allow_external_writes'] = False
            documents.append(workflow)
        source = Path(directory) / 'registry.json'
        source.write_text(json.dumps(config))
        app = create_app(dev_auth=True, roles=['admin', 'approver'], planning_available=True, runtime_enabled=True,
                         database=Path(directory) / 'workflows.sqlite3', registry_config=source)
        service = app.state.workflow_service
        service.planner = PlannerService(RuleBasedStructuredOutputProvider())
        from runtime import RuntimeService
        from runtime.crew import CrewExecutor
        from runtime.graph import GraphRunner
        connectors = {'smtp_send_email': _OfflineConnector(external_write=True),
                      'google_sheets_read_rows': _OfflineConnector(),
                      'google_sheets_update_row': _OfflineConnector(external_write=True, result={'updated_cells': 1})}
        trigger_defaults = {}
        if os.getenv('BUILDER_REAL_CONNECTORS') == '1':
            from runtime.connectors import GoogleAPIConnector, GoogleSheetsConnector, GoogleSheetsUpdateConnector, HTTPJSONConnector, SlackWebhookConnector, SMTPConnector
            env = load_env()
            allowed = [item.strip() for item in os.getenv('BUILDER_ALLOWED_RECIPIENTS', env.get('GMAIL_SMTP_USER', '')).split(',') if item.strip()]
            if not allowed:
                raise RuntimeError('BUILDER_ALLOWED_RECIPIENTS or GMAIL_SMTP_USER is required for real SMTP mode.')
            def resolve(reference):
                if reference == 'cred_browser_smtp':
                    return dict(host=env.get('GMAIL_SMTP_HOST'), port=int(env.get('GMAIL_SMTP_PORT', '587')),
                                username=env.get('GMAIL_SMTP_USER'), password=env.get('GMAIL_SMTP_PASSWORD'),
                                sender=env.get('GMAIL_SMTP_USER'))
                if reference == 'cred_browser_sheets':
                    return dict(provider_id='google_sheets')
                provider = credential_references.get(reference, {}).get('provider_id')
                if provider == 'slack':
                    return dict(provider_id='slack', webhook_url=env.get('SLACK_WEBHOOK_URL', ''))
                if provider == 'github':
                    return dict(provider_id='github', token=env.get('GITHUB_TOKEN', ''))
                if provider == 'smtp':
                    return dict(host=env.get('BREVO_SMTP_HOST'), port=int(env.get('BREVO_SMTP_PORT', '587')),
                                username=env.get('BREVO_SMTP_USER'), password=env.get('BREVO_SMTP_PASSWORD'),
                                sender=env.get('BREVO_SMTP_USER'))
                return dict(provider_id=provider)
            connectors = {
                'smtp_send_email': SMTPConnector(resolve, allowed, [env.get('GMAIL_SMTP_HOST', 'smtp.gmail.com')]),
                'google_sheets_read_rows': GoogleSheetsConnector(resolve, ROOT / env.get('GOOGLE_TOKEN_FILE', 'token.json')),
                'google_sheets_update_row': GoogleSheetsUpdateConnector(resolve, ROOT / env.get('GOOGLE_TOKEN_FILE', 'token.json')),
                'slack_send_notification': SlackWebhookConnector(resolve),
                'github_rest_request': HTTPJSONConnector(resolve, 'github', env.get('GITHUB_API_BASE_URL', 'https://api.github.com'), required_tool_id='github_rest_request'),
                'open_meteo_forecast': HTTPJSONConnector(resolve, 'open_meteo', env.get('OPEN_METEO_BASE_URL', 'https://api.open-meteo.com'), required_tool_id='open_meteo_forecast'),
                'open_library_search': HTTPJSONConnector(resolve, 'open_library', env.get('OPEN_LIBRARY_BASE_URL', 'https://openlibrary.org'), required_tool_id='open_library_search'),
                'generic_rest_request': HTTPJSONConnector(resolve, 'generic_rest', env.get('REST_API_BASE_URL', 'https://jsonplaceholder.typicode.com'), required_tool_id='generic_rest_request'),
                'google_drive_list_files': GoogleAPIConnector(resolve, ROOT / env.get('GOOGLE_TOKEN_FILE', 'token.json'), 'google_drive', 'https://www.googleapis.com/drive/v3', required_tool_id='google_drive_list_files'),
                'google_calendar_list_events': GoogleAPIConnector(resolve, ROOT / env.get('GOOGLE_TOKEN_FILE', 'token.json'), 'google_calendar', 'https://www.googleapis.com/calendar/v3', required_tool_id='google_calendar_list_events'),
                'google_docs_read': GoogleAPIConnector(resolve, ROOT / env.get('GOOGLE_TOKEN_FILE', 'token.json'), 'google_docs', 'https://docs.googleapis.com/v1', required_tool_id='google_docs_read'),
                'webhook_send': HTTPJSONConnector(resolve, 'webhook', 'http://127.0.0.1:8787', method='POST', external_write=True, required_tool_id='webhook_send'),
                'brevo_send_email': SMTPConnector(resolve, allowed, [env.get('BREVO_SMTP_HOST', 'smtp-relay.brevo.com')]),
            }
            trigger_defaults = {'google_sheets': env.get('GOOGLE_SHEETS_SPREADSHEET_ID', '')}
        service.runtime_runner = GraphRunner(RuntimeService(service),
            agents=CrewExecutor(service.registry_adapter, _offline_model_factory), connectors=connectors)
        from workflow_api.trigger_sources import ProviderTriggerSource
        service.trigger_poller = ProviderTriggerSource(service, connectors, trigger_defaults).poll
        auth = dict(subject=dict(subject_id='local-builder', workspace_id='local-workspace'), roles=['admin', 'approver'],
                    permissions=ROLE_PERMISSIONS['admin'] + ['data.read', 'communication.send'], scopes=['data.read', 'spreadsheets.readonly', 'communication.send', 'email.send'], decision='allow')
        for document in documents:
            result = service.handle(dict(request_id='req_browser_seed', operation='save_workflow_version',
                idempotency_key=f"browser_seed_{document['workflow_id']}", payload=dict(workflow_id=document['workflow_id'],
                workflow_version=1, base_version=0, workflow=document)), auth)
            if result['status'] != 200:
                raise RuntimeError('Browser-only registry setup failed.')
        # Explicit test control-plane checkpoint. This does not exist in the
        # production launcher and never grants tools or changes live resources.
        if os.getenv('BUILDER_TEST_OPERATOR_REVIEW') == '1' and os.getenv('BUILDER_ENVIRONMENT') == 'test' and os.getenv('BUILDER_REAL_CONNECTORS') != '1':
            from fastapi import Request
            from fastapi.responses import JSONResponse
            @app.post('/__test__/registry-review/{workflow_id}/{version}')
            async def review_fixture_agents(workflow_id: str, version: int, request: Request):
                authority = app.state.workflow_auth
                if ('admin' not in authority['roles'] or 'tools.manage' not in authority['permissions'] or
                        'workspace:write' not in authority['scopes'] or authority['decision'] != 'allow'):
                    return JSONResponse({'error':'OPERATOR_REVIEW_NOT_AUTHORIZED'},status_code=403)
                workspace = authority['subject']['workspace_id']
                with service.store.transaction(write=False) as db:
                    workflow = service.store.get(db, workspace, workflow_id, version)
                    latest = service.store.get(db, workspace, workflow_id)
                    active = db.execute('SELECT 1 FROM lifecycle_active WHERE workspace=? AND workflow_id=?',(workspace,workflow_id)).fetchone()
                if not workflow or not latest or latest['version'] != version or workflow['status'] not in {'draft','validated'} or active:
                    return JSONResponse({'error':'REVIEW_REQUIRES_EXACT_UNRELEASED_DRAFT'},status_code=409)
                reviewed=[]
                for candidate in workflow['agents']:
                    previous = service.registry_adapter.agents.get(candidate['agent_id'])
                    old = previous['definition'] if previous else {}
                    definition = {**deepcopy(candidate),'allowed_tool_ids':[],
                        'name':old.get('name',candidate['agent_id']),
                        'retry_policy':{'max_retries':candidate['limits']['max_retries'],'backoff_seconds':1},
                        'guardrails':deepcopy(old.get('guardrails',{'pii_redaction':True,'prompt_injection_detection':True,'output_validation':True}))}
                    response = service.registry_adapter.service.register_agent(definition,authority)
                    if response['status'] != 200:return JSONResponse(response,status_code=response['status'])
                    service.registry_adapter.agents[candidate['agent_id']] = response['data']['agent']
                    reviewed.append(candidate['agent_id'])
                return JSONResponse(service.envelope('req_test_registry_review',200,{'reviewed_agent_ids':reviewed,'tool_grants_issued':False}))
        uvicorn.run(app, host='127.0.0.1', port=int(os.getenv('BUILDER_TEST_API_PORT', '8011')), log_level='warning')
