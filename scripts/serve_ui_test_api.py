"""Explicit test-only HTTP fixture server. Never used by the production launcher."""
from pathlib import Path
from copy import deepcopy
import json
import os
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import uvicorn
from planner import PlannerService
from planner.provider import RuleBasedStructuredOutputProvider
from workflow_api.main import create_app, ROLE_PERMISSIONS
from integration_config import load_env


class _OfflineConnector:
    """Deterministic browser fixture connector; it never reaches a provider."""
    def __init__(self, external_write=False):
        self.external_write = external_write
        self.timeout = 30

    @staticmethod
    def reservation(grant):
        return {'tool_calls': 1, 'estimated_cost_usd': 0}

    def invoke(self, grant, inputs, effect_id):
        if self.external_write:
            return {'message_id': effect_id}
        return {'rows': []}


def _offline_model_factory(definition):
    from runtime.model import BoundedLLM
    return BoundedLLM(definition, lambda messages, cap, duration: ('{}', 0, 0), lambda messages: 1, 0, 0)

if __name__ == '__main__':
    (ROOT / '.local').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='browser-tests-', dir=ROOT / '.local') as directory:
        # Explicit browser-only configured registry; never used by product startup.
        agent = json.loads((ROOT / 'shared/contracts/examples/agents/valid-classifier.json').read_text())
        agent.update(agent_id='reader_agent', capabilities=['read_spreadsheet'], permissions=['data.read'])
        agent['limits'].update(max_tool_calls=4, max_retries=2, max_estimated_cost_usd=1)
        agent['retry_policy']['max_retries'] = 2
        tool = json.loads((ROOT / 'shared/contracts/examples/tools/google-sheets-read.json').read_text())
        tool['availability'] = 'enabled'
        smtp_tool = json.loads((ROOT / 'shared/contracts/examples/tools/smtp-send-email.json').read_text())
        config = dict(policy=dict(workspace_id='local-workspace', agent_permissions=['workflow.read_input', 'data.read', 'communication.send'],
            approved_providers=['google_sheets', 'smtp'], allowed_destinations=['verified_recipients'], remaining_quota={},
            credential_references={'cred_browser_sheets': dict(provider_id='google_sheets', scopes=['data.read', 'spreadsheets.readonly']),
                                   'cred_browser_smtp': dict(provider_id='smtp', scopes=['communication.send', 'email.send'])}),
            agents=[agent], tools=[dict(definition=smtp_tool, credential_reference='cred_browser_smtp')], bindings=[],
            subject_permissions=['data.read', 'communication.send'], subject_scopes=['data.read', 'spreadsheets.readonly', 'communication.send', 'email.send'],
            operator_permissions=['tools.manage'],
            auto_resolve_planner=True)
        config['policy']['remaining_quota']['smtp_send_email'] = 10
        config['tools'].append(dict(definition=deepcopy(tool), credential_reference='cred_browser_sheets'))
        config['policy']['remaining_quota']['google_sheets_read_rows'] = 10
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
                conditions=[], approval_gates=[], metadata={})
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
                      'google_sheets_read_rows': _OfflineConnector()}
        if os.getenv('BUILDER_REAL_CONNECTORS') == '1':
            from runtime.connectors import GoogleSheetsConnector, SMTPConnector
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
                raise RuntimeError('Unknown credential reference')
            connectors = {
                'smtp_send_email': SMTPConnector(resolve, allowed, [env.get('GMAIL_SMTP_HOST', 'smtp.gmail.com')]),
                'google_sheets_read_rows': GoogleSheetsConnector(resolve, ROOT / env.get('GOOGLE_TOKEN_FILE', 'token.json')),
            }
        service.runtime_runner = GraphRunner(RuntimeService(service),
            agents=CrewExecutor(service.registry_adapter, _offline_model_factory), connectors=connectors)
        auth = dict(subject=dict(subject_id='local-builder', workspace_id='local-workspace'), roles=['admin', 'approver'],
                    permissions=ROLE_PERMISSIONS['admin'] + ['data.read', 'communication.send'], scopes=['data.read', 'spreadsheets.readonly', 'communication.send', 'email.send'], decision='allow')
        for document in documents:
            result = service.handle(dict(request_id='req_browser_seed', operation='save_workflow_version',
                idempotency_key=f"browser_seed_{document['workflow_id']}", payload=dict(workflow_id=document['workflow_id'],
                workflow_version=1, base_version=0, workflow=document)), auth)
            if result['status'] != 200:
                raise RuntimeError('Browser-only registry setup failed.')
        uvicorn.run(app, host='127.0.0.1', port=int(os.getenv('BUILDER_TEST_API_PORT', '8011')), log_level='warning')
