"""Operator-configured local Slack/Gmail bootstrap, separate from test servers."""
from copy import deepcopy
import json
import os
from pathlib import Path
import re

from registry.contracts import validate
from registry.safety import reject_secrets
from scripts.integration_config import load_env, private_write
from .main import create_app, ROLE_PERMISSIONS
from .slack_socket import SlackSocketReceiver

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = ROOT / '.local/slack-gmail.json'
REGISTRY = ROOT / '.local/slack-gmail-registry.json'


def environment():
    return {**(load_env() if (ROOT / '.env').exists() else {}), **os.environ}


def validate_settings(settings):
    if set(settings) != {'team_id', 'conversation_id', 'sender_id', 'recipient'}:
        raise ValueError('Use team_id, conversation_id, sender_id and recipient settings.')
    for key, prefix in (('team_id', 'T'), ('conversation_id', 'D')):
        if not isinstance(settings[key], str) or not re.fullmatch(prefix + '[A-Z0-9]+', settings[key]):
            raise ValueError('Configure the Slack team ID (T...) and DM conversation ID (D...).')
    if not isinstance(settings['sender_id'], str) or (settings['sender_id'] and not re.fullmatch('[UW][A-Z0-9]+', settings['sender_id'])):
        raise ValueError('Use a Slack member ID (U...) for the optional sender filter.')
    if not isinstance(settings['recipient'], str) or not re.fullmatch(r'[^\s<>@,;]+@[^\s<>@,;]+\.[^\s<>@,;]+', settings['recipient']):
        raise ValueError('Configure one notification email address.')
    reject_secrets(settings)
    return settings


def registry_configuration(env):
    if not env.get('GMAIL_SMTP_USER') or not env.get('GMAIL_SMTP_PASSWORD'):
        raise ValueError('Save GMAIL_SMTP_USER and GMAIL_SMTP_PASSWORD using scripts/set_integration_secret.py.')
    if env.get('GMAIL_SMTP_HOST', 'smtp.gmail.com') != 'smtp.gmail.com' or env.get('GMAIL_SMTP_PORT', '587') != '587':
        raise ValueError('This Gmail launcher requires smtp.gmail.com and STARTTLS port 587.')
    definition = json.loads((ROOT / 'shared/contracts/examples/tools/smtp-send-email.json').read_text())
    definition['retry_policy'] = {'max_retries': 0, 'retryable_errors': []}
    definition['input_schema'] = {'type': 'object', 'properties': {k: {'type': 'string'} for k in ('to', 'subject', 'body')},
                                'required': ['to', 'subject', 'body'], 'additionalProperties': False}
    definition['output_schema'] = {'type': 'object', 'properties': {'message_id': {'type': 'string'}}, 'required': ['message_id'], 'additionalProperties': False}
    return dict(auto_resolve_planner=True, policy=dict(workspace_id='local-workspace',
                agent_permissions=['workflow.read_input', 'communication.send'], approved_providers=['smtp'],
                allowed_destinations=['verified_recipients'], remaining_quota={'smtp_send_email': 300},
                credential_references={'cred_gmail_smtp': {'provider_id': 'smtp', 'scopes': ['communication.send', 'email.send']}},
                approval_roles=['admin', 'approver']), agents=[], tools=[{'definition': definition, 'credential_reference': 'cred_gmail_smtp'}],
                bindings=[], subject_permissions=['communication.send'], subject_scopes=['communication.send', 'email.send'],
                operator_permissions=['tools.manage'])


def operator_auth():
    return dict(subject=dict(subject_id='local-builder', workspace_id='local-workspace'), roles=['admin', 'approver'],
                permissions=sorted(set(ROLE_PERMISSIONS['admin']) | {'workflow.execute', 'communication.send', 'tools.manage'}),
                scopes=['workspace:read', 'workspace:write', 'communication.send', 'email.send'], decision='allow')


def authenticate(service, workspace, subject):
    auth = operator_auth()
    if workspace != auth['subject']['workspace_id']:
        return None
    if subject == 'local-builder':
        return auth
    if not subject.startswith('automation:'):
        return None
    with service.store.transaction() as db:
        rows = db.execute('SELECT document, authority FROM lifecycle_identities WHERE workspace=?', (workspace,)).fetchall()
    for document, authority in rows:
        identity, previous = json.loads(document), json.loads(authority)
        if identity.get('active') is True and identity.get('subject_id') == subject:
            origin = previous.get('_registry_assignment_subject')
            if origin != auth['subject']:
                return None
            resolved = deepcopy(auth)
            resolved['subject'] = {'workspace_id': workspace, 'subject_id': subject}
            resolved['_registry_assignment_subject'] = deepcopy(auth['subject'])
            resolved['_registry_approval_auth'] = deepcopy(auth)
            return resolved
    return None


def mapped_draft(settings):
    validate_settings(settings)
    agent = json.loads((ROOT / 'shared/contracts/examples/agents/valid-classifier.json').read_text())
    agent.update(agent_id='slack_gmail_sender', name='Slack email sender', role='Notification sender',
                 goal='Send approved Slack DM notifications.', instructions='Use the reviewed SMTP tool inputs.',
                 capabilities=['send_email'], permissions=['workflow.read_input', 'communication.send'], approval_requirements=['email_review'])
    agent['limits'].update(max_llm_calls=0, max_tool_calls=1, max_retries=0, timeout_seconds=60)
    agent['retry_policy']['max_retries'] = 0
    workflow = json.loads((ROOT / 'shared/contracts/examples/workflows/support-triage.json').read_text())
    workflow.update(workflow_id='slack-dm-gmail', name='Slack DM → Gmail', description='Notify the configured recipient of a matching personal Slack DM after action approval.',
                    inputs=[{'name': name, 'type': 'string', 'required': True} for name in ('email_to', 'email_subject', 'email_body')], outputs=[],
                    agents=[{k: v for k, v in agent.items() if k not in {'name', 'guardrails', 'retry_policy'}}],
                    tools=[{'tool_id': 'smtp_send_email', 'capability': 'send_email'}],
                    nodes=[{'node_id': 'slack_dm', 'kind': 'trigger', 'label': 'Personal Slack DM'},
                           {'node_id': 'review_email', 'kind': 'approval', 'label': 'Approve email', 'approval_gate_id': 'email_review'},
                           {'node_id': 'send_email', 'kind': 'tool', 'label': 'Send Gmail notification', 'tool_id': 'smtp_send_email', 'agent_id': agent['agent_id'],
                            'configuration': {'input_mapping': {'to': 'inputs.email_to', 'subject': 'inputs.email_subject', 'body': 'inputs.email_body'}}},
                           {'node_id': 'done', 'kind': 'output', 'label': 'Notification submitted'}],
                    edges=[{'edge_id': 'dm_review', 'source': 'slack_dm', 'target': 'review_email'},
                           {'edge_id': 'review_send', 'source': 'review_email', 'target': 'send_email', 'outcome': 'approved'},
                           {'edge_id': 'send_done', 'source': 'send_email', 'target': 'done'}],
                    approval_gates=[{'approval_gate_id': 'email_review', 'approver_roles': ['admin', 'approver'], 'on_reject': 'stop', 'timeout_seconds': 3300}],
                    metadata={'trigger_templates': [dict(provider_id='slack_events', resource_id=settings['conversation_id'], event_type='message.im', delivery='push',
                        credential_reference='cred_slack_socket', event_schema={'type': 'object', 'required': ['event_id', 'body', 'sender_id', 'team_id', 'channel_id']},
                        filters={'team_id': settings['team_id'], 'channel_id': settings['conversation_id'], **({'sender_id': settings['sender_id']} if settings['sender_id'] else {})},
                        input_mapping={'email_to': {'constant': settings['recipient']}, 'email_subject': {'constant': 'New Slack DM notification'}, 'email_body': 'body'})]})
    workflow['execution_policy']['allow_external_writes'] = True
    workflow['execution_policy']['limits'].update(max_llm_calls=0, max_tool_calls=1, max_retries=0, timeout_seconds=3600)
    validate(workflow, 'workflow')
    return workflow


def prepare_draft(service, settings):
    workflow = mapped_draft(settings)
    with service.store.transaction() as db:
        current = service.store.get(db, 'local-workspace', workflow['workflow_id'])
    if current:
        if current.get('metadata', {}).get('trigger_templates') != workflow['metadata']['trigger_templates']:
            raise ValueError('Existing Slack DM draft uses different source or recipient settings. Keep its settings or update its trigger mappings in a new revision first.')
        return False
    result = service.handle(dict(request_id='req_slack_gmail_setup', operation='save_workflow_version', idempotency_key='slack_gmail_setup_v1',
        payload={'workflow_id': workflow['workflow_id'], 'workflow_version': 1, 'base_version': 0, 'workflow': workflow}), operator_auth())
    if result['status'] != 200:
        raise ValueError('The mapped draft could not be saved: ' + result['data']['error']['error_code'])
    return True


def create_configured_app(settings=None, env=None, database=None, receiver_factory=SlackSocketReceiver):
    env = environment() if env is None else env
    if settings is None:
        try:
            settings = json.loads(SETTINGS.read_text())
        except (OSError, ValueError):
            raise ValueError('Run scripts/configure_slack_gmail.py first to configure the Slack DM source.') from None
    validate_settings(settings)
    if not env.get('SLACK_APP_TOKEN', '').startswith('xapp-'):
        raise ValueError('Save SLACK_APP_TOKEN privately: python3 scripts/set_integration_secret.py SLACK_APP_TOKEN')
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    private_write(REGISTRY, json.dumps(registry_configuration(env), indent=2) + '\n')
    # Construct without workers; attach real adapters before anything can dispatch.
    app = create_app(dev_auth=True, roles=['admin', 'approver'], runtime_enabled=True,
                     registry_config=REGISTRY, database=database, start_workers=False)
    service = app.state.workflow_service
    from runtime.connectors import SMTPConnector
    def resolve(reference):
        if reference != 'cred_gmail_smtp':
            raise ValueError('Unknown Gmail credential reference.')
        return dict(host='smtp.gmail.com', port=587, username=env['GMAIL_SMTP_USER'], password=env['GMAIL_SMTP_PASSWORD'], sender=env['GMAIL_SMTP_USER'])
    service.runtime_runner.connectors = {'smtp_send_email': SMTPConnector(resolve, [settings['recipient']], ['smtp.gmail.com'], timeout=15)}
    receiver = receiver_factory(service, lambda workspace, subject: authenticate(service, workspace, subject),
                                settings['team_id'], settings['conversation_id'], settings['sender_id'])
    from runtime.worker import RuntimeWorker
    from .scheduler import TriggerScheduler
    lookup = lambda workspace, subject: authenticate(service, workspace, subject)
    workers = [TriggerScheduler(service, lookup, interval=1), RuntimeWorker(service.runtime_runner, lookup)]
    app.state.slack_receiver = receiver

    @app.on_event('startup')
    def start_integration():
        try:
            receiver.start(env['SLACK_APP_TOKEN'])
            for worker in workers:
                worker.start()
        except Exception:
            for worker in workers:
                worker.stop()
            receiver.stop()
            raise

    @app.on_event('shutdown')
    def stop_integration():
        receiver.stop()
        for worker in workers:
            worker.stop()

    return app
