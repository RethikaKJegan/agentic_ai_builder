"""Optional composition root; original startup/configuration is never invoked."""
from contextlib import asynccontextmanager
from copy import deepcopy
import json
import math
import os
import re
from pathlib import Path
from planner import PlannerService
from planner.errors import PlannerFailure
from planner.provider import OpenAIStructuredOutputProvider
from registry import WorkspacePolicy
from .registry import ExtensionRegistry, ExtensionRegistryAdapter
from workflow_api.service import WorkflowService
from workflow_api.storage import WorkflowStore
from runtime.graph import GraphRunner
from runtime.service import RuntimeService
from .catalog import CATALOG
from .common import ArtifactStore, EffectJournal, JSONTransport
from .google import GoogleAPI, GoogleToken
from .sheet_creation import SheetsSetup, SheetResourceStore, setup_inputs
from .sheet_report import ReportSheetsSetup
from .calendar import CalendarConnector
from .mail import MailConnector, address
from .search import SearchConnector
from .sheets import SheetsRead, SheetsWrite, SheetsDiscover, normalized_write_workflow, normalized_write_targets, read_location
from .transport import create_transport, PERMISSIONS

ROOT = Path(__file__).resolve().parents[1]
STATE_ROOT = ROOT / '.local/connector-extension'
PROVIDERS = {'google_sheets', 'google_calendar', 'gmail', 'brave_search'}
CONFIG_KEYS = {'procurement_enabled', 'procurement_currency_precision', 'sheet_creation_enabled', 'enabled_providers', 'sheet_reads', 'sheet_writes', 'calendars', 'mail_account', 'mail_recipients', 'search_cost_per_call_usd'}


def state_directory(path=None):
    target = Path(path or STATE_ROOT).absolute()
    # Never permit the default application's DB, credential files or a symlinked state path.
    if target != STATE_ROOT and not target.is_relative_to(STATE_ROOT):
        raise ValueError('Extension state must stay under .local/connector-extension.')
    if any(parent.is_symlink() for parent in [target, *target.parents]):
        raise ValueError('Extension state cannot use symlink directories.')
    target.mkdir(mode=0o700, parents=True, exist_ok=True)
    return target


def configuration(path):
    from registry.safety import reject_secrets
    from runtime.connectors import google_spreadsheet_id
    from runtime.sheet_records import write_targets
    config = json.loads(Path(path).read_text()) if isinstance(path, (str, Path)) else deepcopy(path)
    if not isinstance(config, dict) or set(config) - CONFIG_KEYS:
        raise ValueError('Use only documented extension configuration fields.')
    reject_secrets(config)
    if type(config.get('sheet_creation_enabled', False)) is not bool:
        raise ValueError('sheet_creation_enabled must be a boolean opt-in.')
    if type(config.get('procurement_enabled',False)) is not bool:raise ValueError('procurement_enabled must be boolean.')
    precision=config.get('procurement_currency_precision',{})
    if not isinstance(precision,dict) or any(not re.fullmatch('[A-Z]{3}',k) or type(v) is not int or not 0<=v<=6 for k,v in precision.items()):
        raise ValueError('Use explicit currency rounding precision.')
    if config.get('procurement_enabled') and (not precision or not config.get('sheet_creation_enabled') or
            not {'google_sheets','gmail'}<=set(config.get('enabled_providers',[]))):
        raise ValueError('Procurement requires Sheets, Gmail, creation opt-in and explicit currency precision.')
    enabled = config.get('enabled_providers', [])
    if not isinstance(enabled, list) or any(provider not in PROVIDERS for provider in enabled):
        raise ValueError('Select known extension providers.')
    for name in ['sheet_reads', 'sheet_writes', 'calendars', 'mail_recipients']:
        if not isinstance(config.get(name, []), list): raise ValueError('Extension resource settings must be lists.')
    for item in config.get('sheet_reads', []):
        if not isinstance(item, dict) or set(item) != {'spreadsheet_id', 'range'}:
            raise ValueError('Sheet reads require spreadsheet_id and bounded range.')
        item['spreadsheet_id'] = google_spreadsheet_id(item['spreadsheet_id']); read_location(item['range'])
    if config.get('sheet_writes'): config['sheet_writes'] = write_targets(config['sheet_writes'])
    for item in config.get('calendars', []):
        if not isinstance(item, str) or not item.strip() or any(c in item for c in '\r\n'):
            raise ValueError('Use exact approved calendar IDs.')
    if config.get('mail_account'): config['mail_account'] = address(config['mail_account'])
    config['mail_recipients'] = [address(item) for item in config.get('mail_recipients', [])]
    cost = config.get('search_cost_per_call_usd', 0)
    if type(cost) not in (int, float) or not math.isfinite(cost) or cost < 0:
        raise ValueError('Configure a finite nonnegative search cost.')
    return config


class CatalogPlanner:
    def __init__(self, definitions, config, provider=None, sheet_discoverer=None, calendar_discoverer=None):
        self.definitions, self.config, self.provider = definitions, config, provider
        self.sheet_discoverer = sheet_discoverer
        self.calendar_discoverer = calendar_discoverer

    def generate(self, objective, context):
        if self.provider is None:
            raise PlannerFailure('PLANNER_NOT_CONFIGURED', 'Configure an optional model for extension workflow generation.')
        catalogs = []
        if self.sheet_discoverer is not None:
            from workflow_api.sheet_discovery import spreadsheet_references
            for identifier in spreadsheet_references(objective):
                try: catalogs.append(self.sheet_discoverer(identifier))
                except Exception as exc:
                    raise PlannerFailure('SHEETS_DISCOVERY_FAILED', 'Could not inspect the supplied spreadsheet. Confirm the connected account has access.') from None
        calendar_catalog = None
        if self.calendar_discoverer is not None and re.search(r'\b(calendar|calendars|reminder|reminders|meeting|meetings|appointment|appointments|deadline|deadlines)\b', objective, re.I):
            try: calendar_catalog = self.calendar_discoverer()
            except Exception:
                raise PlannerFailure('CALENDAR_DISCOVERY_FAILED', 'Could not inspect connected calendars. Confirm extension calendar-list consent.') from None
        enabled = [definition for definition in self.definitions if definition['availability'] == 'enabled']
        supplied = {**context, 'available_tools': [d['tool_id'] for d in enabled],
            'available_capabilities': [d['capability'] for d in enabled],
            'extension_tool_definitions': enabled,
            'tool_output_schemas': {d['tool_id']: d['output_schema'] for d in enabled},
            'extension_resource_policy': self.config, 'discovered_spreadsheets': catalogs,
            'discovered_calendars': calendar_catalog, 'mail_sender_mode': 'connected_account' if not self.config.get('mail_account') else 'operator_override',
            'sheet_target_mode': 'workflow_metadata', 'sheet_write_targets': self.config.get('sheet_writes', []),
            'allowed_agent_permissions': sorted({p for d in enabled for p in d['permission_scopes']} | {'workflow.read_input'}),
            'extension_guidance': 'Use only these enabled tool IDs and exact schemas. Author complete tool inputs or mappings. '
                'Writes require allow_external_writes=true and an approval gate immediately before each write. '
                'Connector availability does not imply business decisions or receipt confirmation. '
                'Spreadsheet links are selected per workflow, not preconfigured. Extract IDs from the user links internally. '
                'Use discovered tab titles, headers and bounded ranges; never invent missing headers. '
                'If a tab/identity is ambiguous, report an unresolved setup requirement. '
                'Reads accept spreadsheet_url or spreadsheet_id plus a bounded range. '
                'Sheets writes require reviewed metadata.sheet_write_targets from the setup prompt; '
                'a nonempty configured sheet_writes list is only an optional additional ceiling. '
                'Select calendars from discovered names/IDs and access roles, or use the connected primary calendar. '
                'If a named calendar is missing or ambiguous, report an unresolved requirement rather than guessing. '
                'Mail sender is discovered from the authenticated account; recipients, messages, threads and attachments '
                'come from workflow inputs and reviewed source records, not fixed server lists. '
                'Nonempty calendars or mail_recipients lists are optional additional restrictions. '
                'Provisioning is separately enabled; use a stable project_id/creation_key and literal reviewed tab/header inputs. '
                'Returned proposed_write_targets require a separately saved and reviewed row-write workflow. '
                'For a NEW populated report use extension_sheets_create_report instead: it creates the file with '
                'bounded scalar report rows in the same approved request, with no existing write target. '
                'Use workflow-selected search queries, country, language, freshness and page values; no topic is hardcoded.'}
        return self.provider.generate(objective, supplied)


def create_extension_app(config, state_dir=None, transport=None, token_supplier=None, planner_provider=None,
                         model_factory=None, start_workers=False, search_key=None):
    config = configuration(config)
    state = state_directory(state_dir)
    for name in ['workflows.sqlite3', 'effects.sqlite3', 'google-token.json']:
        if (state / name).is_symlink(): raise ValueError('Extension state files cannot be symlinks.')
    token_file = state / 'google-token.json'
    transport = transport or JSONTransport()
    api = GoogleAPI(token_supplier or GoogleToken(token_file), transport)
    journal, artifacts = EffectJournal(state), ArtifactStore(state)
    secret = search_key if search_key is not None else os.getenv('BUILDER_EXTENSION_BRAVE_API_KEY', '')
    definitions = []
    catalog=dict(CATALOG)
    providers=set(PROVIDERS)
    if config.get('procurement_enabled'):
        from .procurement.runtime_tools import TOOLS
        catalog.update(TOOLS);providers.add('procurement')
    for original in catalog.values():
        tool = deepcopy(original); provider = tool['provider_id']
        enabled = provider=='procurement' or provider in config.get('enabled_providers', [])
        if tool['tool_id'] in {'extension_sheets_create', 'extension_sheets_add_tabs', 'extension_sheets_create_report'}:
            enabled = enabled and config.get('sheet_creation_enabled', False)
        connected = True if provider=='procurement' else bool(token_supplier or token_file.is_file()) if provider != 'brave_search' else bool(secret)
        tool['availability'] = 'enabled' if enabled and connected else 'needs_configuration' if enabled else 'disabled'
        if provider == 'brave_search': tool['estimated_cost']['per_call'] = config.get('search_cost_per_call_usd', 0)
        definitions.append(tool)
    permissions = {p for tool in definitions for p in tool['permission_scopes']}
    scopes = permissions | {s for tool in definitions for s in tool['authentication']['scopes']}
    references = {'cred_extension_' + provider: {'provider_id': provider, 'scopes': sorted({
        s for tool in definitions if tool['provider_id'] == provider for s in tool['authentication']['scopes'] + tool['permission_scopes']})}
        for provider in providers}
    policy = WorkspacePolicy('local-workspace', approved_providers=providers,
        agent_permissions=permissions | {'workflow.read_input'}, credential_references=references,
        allowed_destinations={'configured_spreadsheet', 'extension_calendars', 'extension_recipients', 'extension_sheet_setup'},
        remaining_quota={tool['tool_id']: 10000 for tool in definitions})
    registry = ExtensionRegistry(policy)
    auth = {'subject': {'subject_id': 'local-builder', 'workspace_id': 'local-workspace'}, 'roles': ['admin', 'approver'],
            'permissions': sorted(set(PERMISSIONS) | permissions), 'scopes': sorted(scopes | {'workspace:read', 'workspace:write'}), 'decision': 'allow'}
    for tool in definitions:
        result = registry.register_tool(tool, auth, 'cred_extension_' + tool['provider_id'])
        if result['status'] != 200: raise ValueError('The extension tool catalog failed Registry validation.')
    adapter = ExtensionRegistryAdapter(registry, auto_resolve_planner=True)
    if planner_provider is None and os.getenv('OPENAI_API_KEY') and os.getenv('OPENAI_MODEL'):
        planner_provider = OpenAIStructuredOutputProvider(model=os.environ['OPENAI_MODEL'])
    service = WorkflowService(WorkflowStore(state / 'workflows.sqlite3'),
        planner=PlannerService(CatalogPlanner(definitions, config, planner_provider)), registry_adapter=adapter)
    os.chmod(state / 'workflows.sqlite3', 0o600)
    procurement=None
    if config.get('procurement_enabled'):
        from .procurement.service import ProcurementService
        procurement=ProcurementService(service,state,config['procurement_currency_precision'],
            lambda workspace:deepcopy(auth) if workspace==auth['subject']['workspace_id'] else None)
    connectors = {}
    sheet_resources = SheetResourceStore(state) if config.get('sheet_creation_enabled', False) else None
    for tool in definitions:
        if tool['availability'] != 'enabled': continue
        provider = tool['provider_id']
        if provider=='procurement':
            from .procurement.runtime_tools import ProcurementConnector
            connector=ProcurementConnector(tool,procurement)
        elif tool['tool_id'] in {'extension_sheets_create', 'extension_sheets_add_tabs', 'extension_sheets_create_report'}:
            connector_type = ReportSheetsSetup if tool['tool_id'] == 'extension_sheets_create_report' else SheetsSetup
            connector = connector_type(tool, api, journal, sheet_resources, config.get('sheet_reads', []), config.get('sheet_writes', []))
        elif tool['tool_id'] == 'extension_sheets_discover':
            connector = SheetsDiscover(tool, api, config.get('sheet_reads', []))
        elif tool['tool_id'] == 'google_sheets_read_rows':
            connector = SheetsRead(tool, api, config.get('sheet_reads', []))
        elif tool['tool_id'] == 'google_sheets_upsert_record':
            connector = SheetsWrite(tool, api, journal, config.get('sheet_writes', []), token_file, state / 'sheet-locks')
        elif provider == 'google_calendar': connector = CalendarConnector(tool, api, journal, config.get('calendars', []))
        elif provider == 'gmail': connector = MailConnector(tool, api, journal, artifacts, config.get('mail_account'), config.get('mail_recipients', []))
        else:
            connector = SearchConnector(tool, transport, lambda reference: secret if reference == 'cred_extension_brave_search' else None)
        connectors[tool['tool_id']] = connector
    if model_factory is None and os.getenv('BUILDER_EXTENSION_MODEL_RATES') and os.getenv('OPENAI_MODEL'):
        from runtime.model import OpenAIModelFactory
        rates = json.loads(os.environ['BUILDER_EXTENSION_MODEL_RATES'])
        tokenizers = {os.environ['OPENAI_MODEL']: os.environ['BUILDER_EXTENSION_MODEL_TOKENIZER']} if os.getenv('BUILDER_EXTENSION_MODEL_TOKENIZER') else None
        model_factory = OpenAIModelFactory(rates, tokenizers=tokenizers)
    agents = None
    if model_factory is not None:
        from runtime.crew import CrewExecutor
        agents = CrewExecutor(adapter, model_factory)
    service.runtime_runner = GraphRunner(RuntimeService(service), agents=agents, connectors=connectors)
    def validate_configuration(workflow):
        from runtime.sheet_records import validate_record_workflow
        if procurement is not None and any(t['tool_id']=='extension_procurement_ingest' for t in workflow['tools']):
            from .procurement.runtime_tools import ingestion_workflow
            from .procurement.store import ProcurementError
            try:
                project=workflow.get('metadata',{}).get('procurement_project_id')
                job=procurement.job(auth['subject']['workspace_id'],project)
                expected=ingestion_workflow(job['plan'],job['ingestion_workflow_id'])
                if (workflow['workflow_id']!=expected['workflow_id'] or workflow['version']!=1 or
                    workflow['nodes']!=expected['nodes'] or workflow['edges']!=expected['edges'] or
                    workflow['tools']!=expected['tools']):
                    raise PlannerFailure('PROCUREMENT_SOURCE_WORKFLOW_REQUIRED','Use the exact registered source-read and mapped-ingestion graph.')
            except (ProcurementError,TypeError):
                raise PlannerFailure('PROCUREMENT_SOURCE_WORKFLOW_REQUIRED','Register the reviewed project/source plan first.') from None
        # New writes need an exact graph action behind its own gate. Model-selected
        # writes without concrete reviewed inputs remain outside this extension.
        nodes = {node['node_id']: node for node in workflow['nodes']}
        for reference in workflow['tools']:
            definition = catalog.get(reference['tool_id'])
            if not definition or not definition['approval_required']: continue
            actions = [node for node in workflow['nodes'] if node.get('tool_id') == reference['tool_id'] and node['kind'] == 'tool']
            if not actions:
                raise PlannerFailure('APPROVAL_REQUIRED', 'Extension writes require explicit tool nodes with action approval gates.')
            for node in actions:
                if reference['tool_id'] in {'extension_sheets_create', 'extension_sheets_add_tabs'}:
                    from jsonschema import Draft202012Validator
                    config_node = node.get('configuration', {})
                    literal = config_node.get('input')
                    if config_node.get('input_mapping') or not isinstance(literal, dict) or list(Draft202012Validator(definition['input_schema']).iter_errors(literal)):
                        raise PlannerFailure('SHEETS_SETUP_REQUIRED', 'Provisioning requires complete literal reviewed setup inputs.')
                    try: setup_inputs(literal)
                    except Exception as exc:
                        from runtime.service import RuntimeFailure
                        if not isinstance(exc, RuntimeFailure): raise
                        raise PlannerFailure('SHEETS_SETUP_REQUIRED', 'Correct the bounded tab/header setup before review.') from None
                incoming = [edge for edge in workflow['edges'] if edge['target'] == node['node_id']]
                if (len(incoming) != 1 or incoming[0].get('outcome') != 'approved' or
                        nodes[incoming[0]['source']]['kind'] != 'approval'):
                    raise PlannerFailure('APPROVAL_REQUIRED', 'Place a dedicated approval immediately before each extension write.')
        if any(tool['tool_id'] == 'google_sheets_upsert_record' for tool in workflow['tools']):
            validate_record_workflow(normalized_write_workflow(workflow), normalized_write_targets(config.get('sheet_writes', [])))
    discover = connectors.get('extension_sheets_discover')
    if discover is not None:
        # Setup discovery is server-owned, read-only, and limited to prompt links.
        # Runtime tool discovery still requires its exact Registry assignment.
        import time
        service.planner.provider.sheet_discoverer = lambda identifier: discover.execute(None,
            {'spreadsheet_id': identifier}, 'setup-discovery', time.monotonic() + discover.timeout)
    calendar_discover = connectors.get('extension_calendar_discover')
    if calendar_discover is not None:
        import time
        service.planner.provider.calendar_discoverer = lambda: calendar_discover.execute(None,
            {'limit': 100}, 'setup-calendar-discovery', time.monotonic() + calendar_discover.timeout)
    service.configuration_validator = validate_configuration
    app = create_transport(service, auth, planning_available=planner_provider is not None)
    app.state.extension_auth = auth
    app.state.extension_state_directory = state
    app.state.extension_artifacts = artifacts
    if procurement is not None:
        from .procurement.routes import register_routes
        register_routes(app,procurement,auth);app.state.procurement_service=procurement
    workers = []
    @asynccontextmanager
    async def lifespan(_app):
        if start_workers:
            from runtime.worker import RuntimeWorker
            # Manual extension runs resume using only the current operator identity.
            worker = RuntimeWorker(service.runtime_runner, lambda workspace, subject: deepcopy(auth) if
                workspace == auth['subject']['workspace_id'] and subject == auth['subject']['subject_id'] else None)
            worker.start(); workers.append(worker)
            if procurement is not None:
                from .procurement.routes import ProcurementWorker
                procurement_worker=ProcurementWorker(procurement);procurement_worker.start();workers.append(procurement_worker)
        try: yield
        finally:
            for worker in workers: worker.stop()
    app.router.lifespan_context = lifespan
    return app
