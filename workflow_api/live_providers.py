"""Reusable live providers for workflows authored and published in the UI."""
from copy import deepcopy
import json
import os
import re

from scripts.integration_config import ROOT, load_env, private_write
from .main import create_app, ROLE_PERMISSIONS
from .security import origins, deployment_mode

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
    if env.get('BUILDER_SHEETS_WRITE_TARGETS'):
        from runtime.sheet_records import write_targets
        write_targets(env['BUILDER_SHEETS_WRITE_TARGETS'])
    # Destinations belong to reviewed workflow revisions; environment targets
    # are an optional operator ceiling for deployments that need one.
    record = json.loads((ROOT / 'shared/contracts/examples/tools/google-sheets-upsert-record.json').read_text())
    record['availability'] = 'enabled'
    record['approval_required'] = env.get('BUILDER_SHEETS_DIRECT_WRITE') != '1'
    config['tools'].append({'definition': record, 'credential_reference': 'cred_google_sheets'})
    config['policy']['agent_permissions'].append('data.write')
    config['policy']['allowed_destinations'].append('configured_spreadsheet')
    config['policy']['credential_references']['cred_google_sheets']['scopes'] += ['data.write', 'spreadsheets']
    config['policy']['remaining_quota']['google_sheets_upsert_record'] = 10000
    config['subject_permissions'].append('data.write')
    config['subject_scopes'] += ['data.write', 'spreadsheets']
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
    with service.store.transaction(write=False) as db:
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
    def __init__(self, model, allowed_recipients, client, direct_send=False, sheet_targets=None, direct_write=False, planner_timeout=180,
                 sheet_discoverer=None, manager_email=None):
        from planner.provider import OpenAIStructuredOutputProvider
        self.provider = OpenAIStructuredOutputProvider(client=client, model=model, timeout_seconds=planner_timeout)
        self.context = {'runtime_model': {'provider': 'openai', 'model_id': model},
                        'available_tools': ['google_sheets_read_rows', 'smtp_send_email'],
                        'available_capabilities': ['read_spreadsheet', 'send_email', 'classify_text', 'generate_report'],
                        'allowed_agent_permissions': ['workflow.read_input', 'data.read', 'communication.send'],
                        'allowed_email_recipients': allowed_recipients}
        self.context['email_action_approval_required'] = not direct_send
        self.sheet_discoverer = sheet_discoverer
        self.direct_send = direct_send
        self.context['customer_automation_defaults'] = {'enabled': direct_send,
            'manager_email': manager_email or allowed_recipients[0]}
        self.sheet_targets = sheet_targets or []
        definition = json.loads((ROOT / 'shared/contracts/examples/tools/google-sheets-upsert-record.json').read_text())
        definition['availability'] = 'enabled'
        definition['approval_required'] = not direct_write
        self.context['available_tools'].append(definition['tool_id'])
        self.context['available_capabilities'].append('update_spreadsheet')
        self.context['allowed_agent_permissions'].append('data.write')
        self.context['sheet_write_targets'] = self.sheet_targets
        self.context['sheet_record_tool'] = definition
        self.context['sheet_action_approval_required'] = not direct_write
        self.context['sheet_target_mode'] = 'workflow_metadata'
        self.context['tool_output_schemas'] = {tool: json.loads((ROOT / 'shared/contracts/examples/tools' / filename).read_text())['output_schema']
            for tool,filename in [('smtp_send_email','smtp-send-email.json'),('google_sheets_read_rows','google-sheets-read.json')]}
        self.context['tool_output_schemas']['google_sheets_upsert_record'] = definition['output_schema']

    def generate(self, objective, context):
        from .service import WorkflowService
        from planner.errors import PlannerFailure
        from planner.validation import mark_automatic_inputs
        from runtime.expressions import validate_expression
        from registry.safety import reject_secrets
        from registry.contracts import RegistryError
        import ast
        supplied = {**context, **self.context}
        database_tools = [*context.get('database_workflow_tools', []), *context.get('workflow_google_tools', [])]
        if database_tools:
            supplied['available_tools'] = [*supplied['available_tools'], *(t['tool_id'] for t in database_tools)]
            supplied['available_capabilities'] = [*supplied['available_capabilities'], *(t['capability'] for t in database_tools)]
            supplied['tool_output_schemas'] = {**supplied['tool_output_schemas'], **{t['tool_id']: t['output_schema'] for t in database_tools}}
            supplied['allowed_agent_permissions'] = sorted(set(supplied['allowed_agent_permissions']) | {p for t in database_tools for p in t['permission_scopes']})
        from .sheet_discovery import spreadsheet_references, planning_spreadsheet_references, validate_discovered_setup, catalog_snapshot
        catalogs = []
        references = planning_spreadsheet_references(objective, supplied)
        if self.sheet_discoverer is not None:
            try:
                explicit = set(spreadsheet_references(objective))
                unavailable = []
                for reference in references:
                    try:
                        catalogs.append(self.sheet_discoverer(reference))
                    except Exception:
                        if reference in explicit:
                            raise
                        unavailable.append(reference)
                if unavailable:
                    supplied['unavailable_source_ids'] = unavailable
            except Exception as exc:
                raise PlannerFailure(getattr(exc, 'code', 'SHEETS_DISCOVERY_FAILED'),
                    'Could not inspect the spreadsheet. Check its link, headers, and Google account access.') from None
        if catalogs:
            supplied['discovered_spreadsheets'] = catalog_snapshot(catalogs)
        explicit_review = bool(re.search(r'\b(?:human|manual)\s+approval\b|\brequire\s+approval\b', objective, re.I))
        wants_automatic = bool(re.search(r'\bautomatic(?:ally)?\b|\bwithout\s+(?:manual\s+)?approval\b', objective, re.I)) and not explicit_review
        supplied['customer_automation_requested'] = wants_automatic and self.direct_send
        if supplied.get('procurement_planning_mode') == 'requirements_first':
            # Automatic planning does not authorize customer-email handling.
            supplied['customer_automation_requested'] = False
            supplied.pop('customer_automation_defaults', None)
        # At most two bounded planning calls. A correction edits the draft;
        # neither call registers grants, publishes, executes or approves it.
        from .inventory_report_planner import seed_inventory_report
        seed = seed_inventory_report(objective, supplied)
        for attempt in range(2):
            from shared.llm_feedback import feedback
            try:
                workflow = deepcopy(seed) if seed is not None else self.provider.generate(objective, supplied)
            except PlannerFailure as exc:
                if attempt == 0 and exc.code in {'PLANNER_OUTPUT_INVALID', 'PLANNER_OUTPUT_INVALID_JSON'}:
                    supplied['validation_feedback'] = [feedback(exc.code, exc.field)]
                    continue
                raise
            if catalogs:
                workflow.setdefault('metadata', {})['sheet_catalog'] = catalog_snapshot(catalogs)
            automation = workflow.get('metadata', {}).get('customer_automation')
            if isinstance(automation, dict):
                automation['instructions'] = objective[:12000]
            mark_automatic_inputs(workflow, supplied)
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
            from planner.validation import normalize_generated_inputs, normalize_tool_agent_capabilities, validate_output_mappings
            from runtime.sheet_records import normalize_generated_record_schemas
            from .inventory_report_planner import compile_inventory_report
            try:
                if seed is None:
                    workflow = compile_inventory_report(workflow, objective, supplied)
            except PlannerFailure as exc:
                if not exc.retryable:
                    raise
                if attempt == 0:
                    supplied['validation_feedback'] = [{'code': exc.code, 'hint': str(exc)}]
                    continue
                raise
            normalize_generated_inputs(workflow)
            normalize_tool_agent_capabilities(workflow)
            normalize_generated_record_schemas(workflow)
            from runtime.email_recipients import normalize_generated_email_approvals
            normalize_generated_email_approvals(workflow)
            try:
                WorkflowService.validate_document(workflow)
                validate_output_mappings(workflow, supplied['tool_output_schemas'])
                from runtime.sheet_records import validate_record_workflow
                validate_record_workflow(workflow, self.sheet_targets)
                from runtime.email_recipients import validate_email_workflow
                validate_email_workflow(workflow, allow_automatic=supplied['customer_automation_requested'],
                                        managers=self.context['allowed_email_recipients'])
                validate_discovered_setup(workflow, catalogs)
                if supplied.get('database_catalog'):
                    from .database_workflows import bind_generated
                    try:
                        bind_generated(deepcopy(workflow), supplied)
                    except (ValueError, TypeError, KeyError):
                        raise PlannerFailure('KG_SOURCE_BINDING_INVALID',
                            'Use exact catalog dataset IDs and explicit specialist source assignments within the selected scope.',
                            field='metadata.database_source_ids') from None
            except PlannerFailure as exc:
                if exc.code == 'SHEETS_SOURCE_AMBIGUOUS':
                    raise
                hints = {
                    'EMAIL_SOURCE_MAPPING_REQUIRED': 'The initial graph sends only to the source-row customer. Remove manager email nodes and reply-loop branches; the inbox worker handles those using customer_automation metadata.',
                    'WORKFLOW_VALIDATION_FAILED': 'Include a kind=trigger node and a kind=output node, and connect every graph node to a path from the trigger. Use canonical schema fields and restricted expressions only. No len(), methods, function calls, dict literals or JavaScript. Required source columns are enforced by poll_input.required_fields.',
                    'OUTPUT_FIELD_NOT_DECLARED': 'Map only fields declared in each source output schema using the graph node ID, with no result/output wrapper. Profile returns email_address, report creation spreadsheet_url, mail message_id and calendar event_id.',
                }
                errors.append({'code': exc.code, 'field': exc.field, **({'hint':hints[exc.code]} if exc.code in hints else {})})
            agents_by_id = {agent['agent_id']: agent for agent in workflow.get('agents', [])}
            reserved_cost = sum(agents_by_id.get(node.get('agent_id'), {}).get('limits', {}).get('max_estimated_cost_usd', 0)
                                for node in workflow.get('nodes', []) if node.get('kind') == 'agent')
            dynamic_master_ids = {node.get('agent_id') for node in workflow.get('nodes', [])
                                  if node['node_id'] in workflow.get('metadata', {}).get('dynamic_delegation', {})}
            reserved_cost += sum(agent['limits'].get('max_estimated_cost_usd', 0)
                                 for agent in workflow.get('agents', []) if agent.get('parent_agent_id') in dynamic_master_ids)
            workflow_cost = workflow.get('execution_policy', {}).get('limits', {}).get('max_estimated_cost_usd', 0)
            if round(reserved_cost, 12) > round(workflow_cost, 12):
                errors.append({'code': 'WORKFLOW_COST_BUDGET_REQUIRED',
                               'field': 'execution_policy.limits.max_estimated_cost_usd'})
            node_ids = {node['node_id'] for node in workflow.get('nodes', [])}
            for agent in workflow.get('agents', []):
                if any(agent.get('model', {}).get(key) != value for key, value in self.context['runtime_model'].items()):
                    errors.append({'code': 'USE_CONFIGURED_RUNTIME_MODEL', 'field': agent['agent_id']})
                if set(agent.get('permissions', [])) - set(supplied['allowed_agent_permissions']):
                    errors.append({'code': 'USE_ALLOWED_PERMISSIONS', 'field': agent['agent_id']})
                if set(agent.get('capabilities', [])) - set(supplied['available_capabilities']):
                    errors.append({'code': 'USE_AVAILABLE_CAPABILITIES', 'field': agent['agent_id']})
            for tool in workflow.get('tools', []):
                if 'configuration_reference' in tool:
                    errors.append({'code': 'REMOVE_CLIENT_TOOL_ASSIGNMENT', 'field': tool['tool_id']})
            for node in workflow.get('nodes', []):
                if node.get('tool_id') == 'smtp_send_email':
                    configuration = node.get('configuration', {})
                    recipient = configuration.get('input', {}).get('to')
                    if 'to' in configuration.get('input_mapping', {}):
                        try:
                            recipient = ast.literal_eval(configuration['input_mapping']['to'])
                        except (ValueError, SyntaxError, TypeError):
                            recipient = None
                    from runtime.customer_automation import source_email_policy
                    source_mode = source_email_policy(workflow)
                    if not source_mode and recipient not in self.context['allowed_email_recipients']:
                        errors.append({'code': 'USE_LITERAL_ALLOWED_EMAIL_RECIPIENT', 'field': node['node_id']})
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
                supplied['validation_feedback'] = [{**feedback(e['code'], e.get('field')), **e} for e in errors]
                supplied['previous_draft'] = deepcopy(workflow)
        raise PlannerFailure('PLANNER_OUTPUT_INVALID', 'The generated workflow failed execution validation.',
                             retryable=True, details={'requirements': sorted({item['code'] for item in errors})})


def create_configured_app(env=None, database=None, client=None, model_factory=None):
    env = environment() if env is None else env
    usage_budgets = env.get('BUILDER_ENFORCE_USAGE_BUDGETS', '1')
    if usage_budgets not in {'0', '1'}:
        raise ValueError('BUILDER_ENFORCE_USAGE_BUDGETS must be 0 or 1.')
    enforce_usage_budgets = usage_budgets == '1'
    mode = deployment_mode(env.get('BUILDER_ENVIRONMENT', 'production'))
    process_role=env.get('BUILDER_PROCESS_ROLE','combined')
    if process_role not in {'api','worker','combined'}:raise ValueError('Use api, worker or combined process role.')
    if env.get('BUILDER_DEV_AUTH') != '1':
        raise ValueError('Explicitly enable development authentication for the local live launcher.')
    allowed_origins = origins(env.get('BUILDER_UI_ORIGINS'))
    config = registry_configuration(env)
    from .procurement import configuration as procurement_configuration, extend_registry
    procurement_settings = procurement_configuration(env)
    if procurement_settings:
        extend_registry(config, procurement_settings)
    model, rates, tokenizers = model_configuration(env)
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    private_write(REGISTRY, json.dumps(config, indent=2) + '\n')
    app = create_app(dev_auth=True, roles=['admin', 'approver'], runtime_enabled=True,
                     registry_config=REGISTRY, database=database or env.get('BUILDER_DATABASE_URL'), start_workers=False, planning_available=True,
                     environment_name=mode, ui_origins=allowed_origins,
                     planner_timeout_seconds=int(env.get('BUILDER_PLANNER_TIMEOUT_SECONDS', '180')),planning_worker_enabled=False, google_oauth_config=env)
    service = app.state.workflow_service
    service.background_execution=process_role=='api'
    from .integration_checks import smtp_probe
    service.integration_probes={'smtp':smtp_probe(env)}
    service.auxiliary_database_url=env.get('BUILDER_AUXILIARY_DATABASE_URL')
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
    from runtime.sheet_records import GoogleSheetsRecordConnector, write_targets, validate_record_workflow
    targets = write_targets(env['BUILDER_SHEETS_WRITE_TARGETS']) if env.get('BUILDER_SHEETS_WRITE_TARGETS') else []
    direct_write = env.get('BUILDER_SHEETS_DIRECT_WRITE') == '1'
    def validate_configuration(workflow):
        from runtime.email_recipients import validate_email_workflow
        validate_record_workflow(workflow, targets)
        validate_email_workflow(workflow, allow_automatic=direct_send, managers=recipients(env))
        from planner.validation import validate_output_mappings
        validate_output_mappings(workflow, {item['definition']['tool_id']: item['definition']['output_schema'] for item in config['tools']})
        from .sheet_discovery import validate_discovered_setup
        validate_discovered_setup(workflow, workflow.get('metadata', {}).get('sheet_catalog', []))
    service.configuration_validator = validate_configuration
    planner_timeout = int(env.get('BUILDER_PLANNER_TIMEOUT_SECONDS', '180'))
    def resolve(reference):
        if reference == 'cred_google_sheets':
            return {'provider_id': 'google_sheets'}
        if reference == 'cred_gmail_smtp':
            return dict(host='smtp.gmail.com', port=587, username=env['GMAIL_SMTP_USER'], password=env['GMAIL_SMTP_PASSWORD'], sender=env['GMAIL_SMTP_USER'])
        raise ValueError('Unknown provider credential reference.')
    runner = service.runtime_runner
    runner.runtime.enforce_usage_budgets = enforce_usage_budgets
    runner.connectors = {'google_sheets_read_rows': GoogleSheetsConnector(resolve, ROOT / env['GOOGLE_TOKEN_FILE'], timeout=15),
                         'smtp_send_email': SMTPConnector(resolve, recipients(env), ['smtp.gmail.com'], timeout=15, require_approval=not direct_send)}
    runner.direct_write_tools = frozenset({'smtp_send_email'} if direct_send else ())
    runner.connectors['google_sheets_upsert_record'] = GoogleSheetsRecordConnector(
        resolve, ROOT / env['GOOGLE_TOKEN_FILE'], targets, timeout=15, require_approval=not direct_write)
    runner.connectors.update(app.state.database_workflows.connectors())
    if direct_write:
        runner.direct_write_tools |= {'google_sheets_upsert_record'}
    from .source_context import knowledge_documents
    runner.agents = CrewExecutor(service.registry_adapter, model_factory or OpenAIModelFactory(
                                    rates, client, tokenizers, enforce_usage_budgets=enforce_usage_budgets),
                                knowledge_loader=lambda workspace: knowledge_documents(service.store, workspace))
    source = ProviderTriggerSource(service, runner.connectors)
    service.trigger_poller = source.poll
    service.trigger_configuration_validator = source.validate_configuration
    service.planner = PlannerService(provider=LivePlannerProvider(model, recipients(env), client, direct_send,
        targets, direct_write, planner_timeout, lambda resource: service.google_tools.discover(runner.connectors['google_sheets_read_rows'], resource),
        env.get('BUILDER_CASE_BOSS_EMAIL', env['GMAIL_SMTP_USER'])))
    from threading import Event, Thread
    auth = operator_auth(config)
    if procurement_settings:
        from .procurement import install
        procurement_worker = install(app, procurement_settings, env, client, model, auth)
    else:
        procurement_worker = None
    def read_case_evidence(case, requests):
        from runtime.service import RuntimeFailure
        from runtime.connectors import google_spreadsheet_id
        with service.store.transaction(write=False) as db:
            stored = db.execute('SELECT document FROM runtime_runs WHERE workspace=? AND run_id=?',
                                (auth['subject']['workspace_id'], case['run_id'])).fetchone()
            original_run = json.loads(stored[0]) if stored else None
        if original_run is None:
            raise RuntimeFailure('CASE_RUN_NOT_FOUND', 'The original case run was not found.')
        authority = authenticate(service, auth, auth['subject']['workspace_id'], original_run['subject_id'])
        if authority is None:
            raise RuntimeFailure('EXECUTION_AUTHORITY_REVOKED', 'The case workflow is no longer active.')
        with service.store.transaction(write=False) as db:
            workflow, grants = runner.runtime.revision(db, case['workflow_id'], case['workflow_version'], authority, True)
        permitted = {(google_spreadsheet_id(t['spreadsheet_id']), t['range']) for t in workflow['metadata'].get('sheet_read_targets', [])}
        read_grant = next((g for g in grants if g['tool_id'] == 'google_sheets_read_rows'), None)
        if read_grant is None:
            raise RuntimeFailure('CASE_READ_NOT_AUTHORIZED', 'No authorized case read tool is available.')
        results = []
        for request in requests:
            if not isinstance(request, dict) or set(request) != {'spreadsheet_id','range','match_column','source_column'}:
                raise RuntimeFailure('CASE_READ_NOT_AUTHORIZED', 'Use a configured table and matching source column.')
            target = (google_spreadsheet_id(request['spreadsheet_id']), request['range'])
            if target not in permitted or request['source_column'] not in case['source_row']:
                raise RuntimeFailure('CASE_READ_NOT_AUTHORIZED', 'The requested table or source column was not published for this case.')
            output = runner.connectors['google_sheets_read_rows'].invoke(read_grant,
                {'spreadsheet_id': target[0], 'range': target[1]}, 'case-read:' + case['case_id'])
            rows = output['rows']
            headers = rows[0] if rows else []
            if request['match_column'] not in headers or len(set(headers)) != len(headers):
                raise RuntimeFailure('CASE_MATCH_COLUMN_INVALID', 'The matching column is missing or ambiguous.')
            index = headers.index(request['match_column'])
            identity = str(case['source_row'][request['source_column']])
            matches = [r for r in rows[1:] if len(r) > index and str(r[index]) == identity]
            results.append({'request': request, 'matching_record_count': len(matches),
                            'rows': [headers, *matches[:20]], 'truncated': len(matches) > 20})
        return results
    if env.get('BUILDER_REPLY_MONITOR') == '1':
        from .reply_cases import ReplyCases
        boss = env.get('BUILDER_CASE_BOSS_EMAIL', env['GMAIL_SMTP_USER'])
        if boss not in recipients(env):
            raise ValueError('The case boss address must be in BUILDER_EMAIL_RECIPIENTS.')
        service.reply_cases = ReplyCases(service.store, env['GMAIL_SMTP_USER'], env['GMAIL_SMTP_PASSWORD'],
                                        boss, client, model, automatic_enabled=direct_send, evidence_reader=read_case_evidence,
                                        allowed_managers=recipients(env), model_rates=rates[model])
        service.reply_monitor_health = {'state': 'starting'}
    lookup = lambda workspace, subject: authenticate(service, auth, workspace, subject)
    service.worker_authenticate=lookup
    workers = [TriggerScheduler(service, lookup, interval=1), RuntimeWorker(runner, lookup)]
    if procurement_worker:
        workers.append(procurement_worker)
    reply_stop = Event()
    reply_thread = None
    def poll_replies():
        while not reply_stop.is_set():
            try:
                actions = service.reply_cases.process_pending(auth['subject']['workspace_id'])
                accepted = service.reply_cases.poll(auth['subject']['workspace_id'])
                actions += service.reply_cases.process_pending(auth['subject']['workspace_id'])
                service.reply_monitor_health = {'state': 'ready', 'new_replies': accepted, 'processed_jobs': actions}
            except Exception:
                service.reply_monitor_health = {'state': 'error', 'error_code': 'IMAP_POLL_FAILED'}
            reply_stop.wait(15)
    app.state.live_operator_auth = auth
    app.state.live_workers = workers

    class ReplyWorker:
        def __init__(self):self.stop_event=reply_stop;self.thread=None
        @property
        def health(self):
            state=service.reply_monitor_health
            return {'state':state.get('state','starting'),'last_success':state.get('last_success'),'last_error':state.get('error_code')}
        def start(self):
            nonlocal reply_thread
            if reply_thread and reply_thread.is_alive():return
            reply_stop.clear()
            reply_thread=Thread(target=poll_replies,name='builder-reply-monitor',daemon=True)
            self.thread=reply_thread
            reply_thread.start()
        def stop(self):
            reply_stop.set()
            if reply_thread:reply_thread.join(timeout=5)
    from .worker_control import WorkerSupervisor
    components=[*workers,app.state.planning_jobs,app.state.data_source_worker,app.state.data_query_jobs]
    if hasattr(service,'reply_cases'):components.append(ReplyWorker())
    supervisor=WorkerSupervisor(service.store,components,role=process_role)
    app.state.worker_supervisor=supervisor
    app.state.process_role=process_role

    @app.on_event('startup')
    def start():supervisor.start()

    @app.on_event('shutdown')
    def stop():supervisor.stop()

    return app
