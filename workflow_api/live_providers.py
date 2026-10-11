"""Reusable live providers for workflows authored and published in the UI."""
from copy import deepcopy
import json
import os
import re

from scripts.integration_config import ROOT, load_env, private_write
from .main import create_app, ROLE_PERMISSIONS

REGISTRY = ROOT / '.local/live-provider-registry.json'


def environment():
    return {**(load_env() if (ROOT / '.env').exists() else {}), **os.environ}


def recipients(env):
    items = [item.strip() for item in env.get('BUILDER_EMAIL_RECIPIENTS', '').split(',') if item.strip()]
    if not items or any(not re.fullmatch(r'[^\s<>@,;]+@[^\s<>@,;]+\.[^\s<>@,;]+', item) for item in items):
        raise ValueError('Set BUILDER_EMAIL_RECIPIENTS to the approved notification addresses.')
    return items


def model_configuration(env):
    model = env.get('OPENAI_MODEL', '')
    if not env.get('OPENAI_API_KEY') or not model:
        raise ValueError('Configure OPENAI_API_KEY and OPENAI_MODEL privately in .env.')
    # Standard short-context rates, verified against the official model page
    # 2026-10-10. Agent/workspace ceilings keep requests well below long context.
    defaults = {'gpt-5.6-luna': {'input_per_token': .20 / 1_000_000, 'output_per_token': 1.20 / 1_000_000}}
    rates = json.loads(env['BUILDER_MODEL_RATES']) if env.get('BUILDER_MODEL_RATES') else defaults
    if model not in rates:
        raise ValueError('Set BUILDER_MODEL_RATES JSON for the exact OPENAI_MODEL; unknown models fail closed.')
    tokenizers = {model: env['BUILDER_MODEL_TOKENIZER']} if env.get('BUILDER_MODEL_TOKENIZER') else {}
    return model, rates, tokenizers


def registry_configuration(env):
    from .slack_gmail import registry_configuration as gmail_registry
    config = gmail_registry(env)
    config['tools'][0]['definition']['approval_required'] = env.get('BUILDER_EMAIL_DIRECT_SEND') != '1'
    recipients(env)
    token = ROOT / env.get('GOOGLE_TOKEN_FILE', 'missing-google-token')
    if not token.is_file():
        raise ValueError('Authorize Google first with .venv-integrations/bin/python scripts/authorize_google.py.')
    definition = json.loads((ROOT / 'shared/contracts/examples/tools/google-sheets-read.json').read_text())
    definition['availability'] = 'enabled'
    definition['retry_policy'] = {'max_retries': 0, 'retryable_errors': []}
    definition['input_schema'] = {'type': 'object', 'properties': {'spreadsheet_id': {'type': 'string'}, 'range': {'type': 'string'}},
                                  'required': ['spreadsheet_id', 'range'], 'additionalProperties': False}
    definition['output_schema'] = {'type': 'object', 'properties': {'rows': {'type': 'array', 'items': {'type': 'array'}}},
                                   'required': ['rows'], 'additionalProperties': False}
    config['tools'].append({'definition': definition, 'credential_reference': 'cred_google_sheets'})
    config['policy']['approved_providers'].append('google_sheets')
    config['policy']['agent_permissions'].append('data.read')
    config['policy']['credential_references']['cred_google_sheets'] = {'provider_id': 'google_sheets', 'scopes': ['data.read', 'spreadsheets.readonly']}
    config['policy']['remaining_quota']['google_sheets_read_rows'] = 10000
    config['subject_permissions'].append('data.read')
    config['subject_scopes'] += ['data.read', 'spreadsheets.readonly']
    return config


def operator_auth(config):
    return dict(subject=dict(subject_id='local-builder', workspace_id='local-workspace'), roles=['admin', 'approver'],
                permissions=sorted(set(ROLE_PERMISSIONS['admin']) | {'workflow.execute', 'tools.manage'} | set(config['subject_permissions'])),
                scopes=['workspace:read', 'workspace:write', *config['subject_scopes']], decision='allow')


def authenticate(service, auth, workspace, subject):
    if workspace != auth['subject']['workspace_id']:
        return None
    if subject == auth['subject']['subject_id']:
        return deepcopy(auth)
    if not subject.startswith('automation:'):
        return None
    with service.store.transaction() as db:
        rows = db.execute('SELECT document, authority FROM lifecycle_identities WHERE workspace=?', (workspace,)).fetchall()
    for document, authority in rows:
        identity, previous = json.loads(document), json.loads(authority)
        if identity.get('active') is True and identity.get('subject_id') == subject and previous.get('_registry_assignment_subject') == auth['subject']:
            resolved = deepcopy(auth)
            resolved['subject'] = {'workspace_id': workspace, 'subject_id': subject}
            resolved['_registry_assignment_subject'] = deepcopy(auth['subject'])
            resolved['_registry_approval_auth'] = deepcopy(auth)
            return resolved
    return None


class LivePlannerProvider:
    """Inject only nonsecret server capabilities into the ordinary planner."""
    def __init__(self, model, allowed_recipients, client, direct_send=False):
        from planner.provider import OpenAIStructuredOutputProvider
        self.provider = OpenAIStructuredOutputProvider(client=client, model=model)
        self.context = {'runtime_model': {'provider': 'openai', 'model_id': model},
                        'available_tools': ['google_sheets_read_rows', 'smtp_send_email'],
                        'available_capabilities': ['read_spreadsheet', 'send_email', 'classify_text', 'generate_report'],
                        'allowed_agent_permissions': ['workflow.read_input', 'data.read', 'communication.send'],
                        'allowed_email_recipients': allowed_recipients}
        self.context['email_action_approval_required'] = not direct_send

    def generate(self, objective, context):
        from .service import WorkflowService
        from planner.errors import PlannerFailure
        from runtime.expressions import validate_expression
        from registry.safety import reject_secrets
        from registry.contracts import RegistryError
        import ast
        supplied = {**context, **self.context}
        # At most two bounded planning calls. A correction edits the draft;
        # neither call registers grants, publishes, executes or approves it.
        for attempt in range(2):
            workflow = self.provider.generate(objective, supplied)
            errors = []
            # Match the API/Registry boundary before returning or caching model
            # output. Rejected content never enters correction feedback.
            try:
                reject_secrets(workflow)
            except RegistryError as exc:
                if exc.code != 'SENSITIVE_DATA_DETECTED':
                    raise
                if attempt == 0:
                    supplied['validation_feedback'] = [{'code': 'REMOVE_UNSAFE_PROVIDER_FIELDS'}]
                    continue
                raise PlannerFailure('PLANNER_OUTPUT_UNSAFE',
                    'The planner generated unsafe metadata. No draft was saved. Try generating again.',
                    retryable=True) from None
            try:
                WorkflowService.validate_document(workflow)
            except PlannerFailure as exc:
                errors.append({'code': exc.code, 'field': exc.field})
            agents_by_id = {agent['agent_id']: agent for agent in workflow.get('agents', [])}
            reserved_cost = sum(agents_by_id.get(node.get('agent_id'), {}).get('limits', {}).get('max_estimated_cost_usd', 0)
                                for node in workflow.get('nodes', []) if node.get('kind') == 'agent')
            workflow_cost = workflow.get('execution_policy', {}).get('limits', {}).get('max_estimated_cost_usd', 0)
            if round(reserved_cost, 12) > round(workflow_cost, 12):
                errors.append({'code': 'WORKFLOW_COST_BUDGET_REQUIRED',
                               'field': 'execution_policy.limits.max_estimated_cost_usd'})
            node_ids = {node['node_id'] for node in workflow.get('nodes', [])}
            for agent in workflow.get('agents', []):
                if any(agent.get('model', {}).get(key) != value for key, value in self.context['runtime_model'].items()):
                    errors.append({'code': 'USE_CONFIGURED_RUNTIME_MODEL', 'field': agent['agent_id']})
                if set(agent.get('permissions', [])) - set(self.context['allowed_agent_permissions']):
                    errors.append({'code': 'USE_ALLOWED_PERMISSIONS', 'field': agent['agent_id']})
                if set(agent.get('capabilities', [])) - set(self.context['available_capabilities']):
                    errors.append({'code': 'USE_AVAILABLE_CAPABILITIES', 'field': agent['agent_id']})
            for tool in workflow.get('tools', []):
                if 'configuration_reference' in tool:
                    errors.append({'code': 'REMOVE_CLIENT_TOOL_ASSIGNMENT', 'field': tool['tool_id']})
            for node in workflow.get('nodes', []):
                for expression in node.get('configuration', {}).get('input_mapping', {}).values():
                    try:
                        tree = validate_expression(expression)
                        for part in ast.walk(tree):
                            if isinstance(part, ast.Attribute) and isinstance(part.value, ast.Name) and part.value.id in {'outputs', 'nodes'} and part.attr not in node_ids:
                                errors.append({'code': 'REFERENCE_GRAPH_NODE_ID', 'field': node['node_id']})
                    except Exception:
                        errors.append({'code': 'USE_RESTRICTED_MAPPING_EXPRESSION', 'field': node['node_id']})
            if not errors:
                return workflow
            if attempt == 0:
                supplied['validation_feedback'] = errors
        raise RuntimeError('Live planning could not satisfy execution validation within two attempts.')


def create_configured_app(env=None, database=None, client=None, model_factory=None):
    env = environment() if env is None else env
    config = registry_configuration(env)
    model, rates, tokenizers = model_configuration(env)
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    private_write(REGISTRY, json.dumps(config, indent=2) + '\n')
    app = create_app(dev_auth=True, roles=['admin', 'approver'], runtime_enabled=True,
                     registry_config=REGISTRY, database=database, start_workers=False, planning_available=True)
    service = app.state.workflow_service
    from openai import OpenAI
    from planner import PlannerService
    from runtime.connectors import SMTPConnector, GoogleSheetsConnector
    from runtime.crew import CrewExecutor
    from runtime.model import OpenAIModelFactory
    from runtime.worker import RuntimeWorker
    from .scheduler import TriggerScheduler
    from .trigger_sources import ProviderTriggerSource
    client = client if client is not None else OpenAI(api_key=env['OPENAI_API_KEY'], base_url=env.get('OPENAI_BASE_URL'), max_retries=0, timeout=60)
    direct_send = env.get('BUILDER_EMAIL_DIRECT_SEND') == '1'
    service.planner = PlannerService(provider=LivePlannerProvider(model, recipients(env), client, direct_send))
    def resolve(reference):
        if reference == 'cred_google_sheets':
            return {'provider_id': 'google_sheets'}
        if reference == 'cred_gmail_smtp':
            return dict(host='smtp.gmail.com', port=587, username=env['GMAIL_SMTP_USER'], password=env['GMAIL_SMTP_PASSWORD'], sender=env['GMAIL_SMTP_USER'])
        raise ValueError('Unknown provider credential reference.')
    runner = service.runtime_runner
    runner.connectors = {'google_sheets_read_rows': GoogleSheetsConnector(resolve, ROOT / env['GOOGLE_TOKEN_FILE'], timeout=15),
                         'smtp_send_email': SMTPConnector(resolve, recipients(env), ['smtp.gmail.com'], timeout=15, require_approval=not direct_send)}
    runner.direct_write_tools = frozenset({'smtp_send_email'} if direct_send else ())
    runner.agents = CrewExecutor(service.registry_adapter, model_factory or OpenAIModelFactory(rates, client, tokenizers))
    service.trigger_poller = ProviderTriggerSource(service, runner.connectors).poll
    auth = operator_auth(config)
    lookup = lambda workspace, subject: authenticate(service, auth, workspace, subject)
    workers = [TriggerScheduler(service, lookup, interval=1), RuntimeWorker(runner, lookup)]
    app.state.live_operator_auth = auth
    app.state.live_workers = workers

    @app.on_event('startup')
    def start():
        try:
            for worker in workers:
                worker.start()
        except Exception:
            for worker in workers:
                worker.stop()
            raise

    @app.on_event('shutdown')
    def stop():
        for worker in workers:
            worker.stop()

    return app
