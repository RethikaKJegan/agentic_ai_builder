"""Durable business state around the existing workflow runtime, not an agent engine."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import secrets
import time
from jsonschema import Draft202012Validator
from registry.safety import reject_secrets
from runtime.service import RuntimeService, RuntimeFailure
from runtime.recovery import classify
from .business_knowledge_model import canonical, digest
from .evidence_completion import EvidenceCompletion, MISSING, artifact, at, conforms
from .service import ApiFailure

CONTRACT = json.loads((Path(__file__).resolve().parents[1] / 'shared/contracts/business-lifecycle-v1.json').read_text())
CASE_CONTRACT = json.loads((Path(__file__).resolve().parents[1] / 'shared/contracts/business-case-v1.json').read_text())
CASE_VALIDATOR = Draft202012Validator(CASE_CONTRACT)
DONE = {'COMPLETED', 'COMPLETED_PROVISIONALLY'}
TERMINAL = DONE | {'CANCELLED'}
WAITING = {'WAITING_FOR_INPUT', 'WAITING_FOR_EVENT', 'WAITING_FOR_AUTHORIZATION'}
TRANSITIONS = {
    'CREATED': {'READY', 'CANCELLED'},
    'READY': {'RUNNING', 'BLOCKED', 'CANCELLED'},
    'RUNNING': DONE | WAITING | {'READY', 'FAILED', 'BLOCKED', 'CANCELLED'},
    'WAITING_FOR_INPUT': {'READY', 'BLOCKED', 'FAILED', 'CANCELLED'},
    'WAITING_FOR_EVENT': {'READY', 'BLOCKED', 'FAILED', 'CANCELLED'},
    'WAITING_FOR_AUTHORIZATION': {'READY', 'BLOCKED', 'FAILED', 'CANCELLED'},
    'BLOCKED': {'READY', 'CANCELLED'}, 'FAILED': {'READY', 'CANCELLED'},
    'COMPLETED': set(), 'COMPLETED_PROVISIONALLY': set(), 'CANCELLED': set()
}


def fail(message, code='CASE_INVALID', status=422):
    raise ApiFailure(code, message, status)


def validate_schema(schema):
    try:
        Draft202012Validator.check_schema(schema)
    except Exception:
        fail('Invalid stage JSON schema.')
    def visit(value, depth=0):
        if depth > 20:
            fail('Stage schema exceeds its nesting bound.')
        if isinstance(value, dict):
            if any(k in value for k in ('$ref', '$dynamicRef', '$recursiveRef')):
                fail('Stage value schemas must be self-contained.')
            for item in value.values():visit(item, depth+1)
        elif isinstance(value, list):
            for item in value:visit(item, depth+1)
    visit(schema)


class BusinessCases:
    def __init__(self, service, clock=time.time, configuration=None):
        self.service, self.store, self.clock = service, service.store, clock
        # Trusted server configuration, never caller/model supplied authority.
        self.configuration = configuration or {}
        with self.store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS business_case_migrations (version INTEGER PRIMARY KEY)')
            db.execute('CREATE TABLE IF NOT EXISTS business_process_definitions (workspace TEXT NOT NULL, owner TEXT NOT NULL, process_id TEXT NOT NULL, version INTEGER NOT NULL, fingerprint TEXT NOT NULL, document TEXT NOT NULL, PRIMARY KEY(workspace,owner,process_id,version))')
            db.execute('CREATE TABLE IF NOT EXISTS business_cases (workspace TEXT NOT NULL, owner TEXT NOT NULL, case_id TEXT NOT NULL, revision INTEGER NOT NULL, document TEXT NOT NULL, PRIMARY KEY(workspace,owner,case_id))')
            db.execute('CREATE TABLE IF NOT EXISTS business_case_commands (workspace TEXT NOT NULL, owner TEXT NOT NULL, request_key TEXT NOT NULL, fingerprint TEXT NOT NULL, document TEXT NOT NULL, PRIMARY KEY(workspace,owner,request_key))')
            db.execute('INSERT INTO business_case_migrations VALUES (1) ON CONFLICT DO NOTHING')
            db.execute('CREATE TABLE IF NOT EXISTS business_case_revisions (workspace TEXT NOT NULL, owner TEXT NOT NULL, case_id TEXT NOT NULL, revision INTEGER NOT NULL, document TEXT NOT NULL, PRIMARY KEY(workspace,owner,case_id,revision))')
            db.execute('CREATE TABLE IF NOT EXISTS business_lifecycle_feedback (workspace TEXT NOT NULL, owner TEXT NOT NULL, case_id TEXT NOT NULL, feedback_id TEXT NOT NULL, document TEXT NOT NULL, PRIMARY KEY(workspace,owner,feedback_id))')
            db.execute('INSERT INTO business_case_migrations VALUES (2) ON CONFLICT DO NOTHING')

    def timestamp(self):
        return datetime.fromtimestamp(self.clock(), timezone.utc).isoformat()

    @staticmethod
    def scope(auth, write=False, execute=False):
        from .business_ontology import identity
        scope = identity(auth, write)
        RuntimeService.authorize(auth, 'workflow.execute' if execute else 'workflow.edit' if write else 'workflow.view', {'admin', 'builder'})
        return scope

    @staticmethod
    def body(body, required, optional=()):
        if not isinstance(body, dict) or not set(required) <= set(body) or set(body) - (set(required) | set(optional)):
            fail('Missing or unsupported business case fields.')
        if len(canonical(body).encode()) > 100000:
            fail('Business case request exceeds its bound.')
        reject_secrets(body)

    @staticmethod
    def key(body):
        key = body.get('request_key')
        if not isinstance(key, str) or not 8 <= len(key) <= 128:
            fail('Use an explicit request_key of 8 to 128 characters.')
        return key

    @staticmethod
    def validate_definition(body):
        if len(canonical(body).encode()) > 100000 or list(Draft202012Validator(CONTRACT).iter_errors(body)):
            fail('Process definition does not satisfy business-lifecycle-v1.')
        reject_secrets(body)
        stages = {s['stage_instance_id']: s for s in body['stages']}
        if len(stages) != len(body['stages']):
            fail('Stage instance IDs must be unique; definition IDs may repeat.')
        visited = set()
        def visit(sid, pending):
            if sid in pending:fail('Process dependencies must be acyclic.')
            if sid in visited:return
            for dep in stages[sid]['dependency_definitions']:
                if dep not in stages:fail('Unknown stage dependency.')
                visit(dep, pending | {sid})
            visited.add(sid)
        for sid, stage in stages.items():
            visit(sid, set())
            if stage['domain'] != body['domain_id']:fail('Stage domain must match process domain.')
            if set(stage['required_inputs']) & set(stage['optional_inputs']):fail('Input names must be distinct.')
            validate_schema(stage['output_schema'])
            if stage['output_schema'].get('type') != 'object':fail('Stage outputs must be objects.')
            for spec in list(stage['required_inputs'].values()) + list(stage['optional_inputs'].values()):validate_schema(spec['schema'])
            for wait in stage['external_event_requirements']:
                validate_schema(wait['schema'])
                if not wait.get('blocking', True) and (not stage['provisional_continuation_policy']['allowed'] or stage['side_effect_classification'] in ('draft','write')):
                    fail('Nonblocking event waits require a provisional analytical/read stage.')
            if stage['side_effect_classification'] in ('draft', 'write') and not stage['required_capabilities']:
                fail('External actions require registered capabilities through the existing runtime.')
            dependencies = set(stage['dependency_definitions'])
            def ancestors(node):
                for dep in stages[node]['dependency_definitions']:
                    if dep not in dependencies:
                        dependencies.add(dep);ancestors(dep)
            for dep in list(dependencies):ancestors(dep)
            def check_bindings(value):
                if isinstance(value, dict):
                    source = value.get('source')
                    if source and 'path' in value:
                        if source.startswith('stage:'):
                            if source[6:] not in dependencies:fail('Output bindings require a declared upstream dependency.')
                        elif source not in ('user', 'config', 'event', 'input', 'output', 'runtime', 'receipt'):
                            fail('Unknown typed binding source.')
                    for item in value.values():check_bindings(item)
                elif isinstance(value, list):
                    for item in value:check_bindings(item)
            check_bindings(stage)
    def publish(self, auth, body):
        scope = self.scope(auth, True)
        self.validate_definition(body)
        fingerprint = digest(body)
        with self.store.transaction() as db:
            db.execute('INSERT INTO business_process_definitions VALUES (?,?,?,?,?,?) ON CONFLICT DO NOTHING', (*scope, body['process_definition_id'], body['version'], fingerprint, canonical(body)))
            row = db.execute('SELECT fingerprint FROM business_process_definitions WHERE workspace=? AND owner=? AND process_id=? AND version=?', (*scope, body['process_definition_id'], body['version'])).fetchone()
            if row[0] != fingerprint:fail('Published process versions are immutable.', 'CASE_PROCESS_CONFLICT', 409)
        return deepcopy(body)

    def process(self, auth, process_id, version):
        scope = self.scope(auth)
        with self.store.transaction(write=False) as db:
            row = db.execute('SELECT document FROM business_process_definitions WHERE workspace=? AND owner=? AND process_id=? AND version=?', (*scope, process_id, version)).fetchone()
        if not row:fail('Process version not found.', 'CASE_NOT_FOUND', 404)
        return json.loads(row[0])

    def process_listing(self,auth):
        scope=self.scope(auth)
        with self.store.transaction(write=False) as db:
            rows=db.execute('SELECT document FROM business_process_definitions WHERE workspace=? AND owner=? ORDER BY process_id,version DESC LIMIT 100',scope).fetchall()
        return {'items':[{k:p[k] for k in ('process_definition_id','version','client_id','domain_id')} for p in (json.loads(r[0]) for r in rows)]}

    def listing(self,auth,before=None):
        scope=self.scope(auth)
        if before is not None and (type(before) is not int or before<1):fail('Use a positive case page cursor.')
        clause=' AND rowid<?' if before is not None else ''
        with self.store.transaction(write=False) as db:
            rows=db.execute('SELECT rowid,document FROM business_cases WHERE workspace=? AND owner=?'+clause+' ORDER BY rowid DESC LIMIT 51',(*scope,*([before] if before is not None else []))).fetchall()
        keys=('case_id','client_id','process_definition_id','process_definition_version','original_user_goal','case_status','execution_status','business_outcome_status','revision','updated_at')
        return dict(items=[{k:c[k] for k in keys} for c in (json.loads(r[1]) for r in rows[:50])],next_cursor=rows[49][0] if len(rows)>50 else None)

    def _load(self, db, scope, case_id):
        row = db.execute('SELECT document FROM business_cases WHERE workspace=? AND owner=? AND case_id=?', (*scope, case_id)).fetchone()
        if not row:fail('Business case not found.', 'CASE_NOT_FOUND', 404)
        return json.loads(row[0])

    def get(self, auth, case_id):
        scope = self.scope(auth)
        with self.store.transaction(write=False) as db:return self._load(db, scope, case_id)

    def section(self, auth, case_id, name):
        case = self.get(auth, case_id)
        if name in ('history','reassessments'):
            from .lifecycle_reassessment import LifecycleReassessment
            return LifecycleReassessment(self).history(auth,case_id) if name=='history' else {'items':case.get('reassessments',[])}
        if name=='learning':
            from .lifecycle_learning import LifecycleLearning
            return LifecycleLearning(self).metrics(auth,case_id)
        if name=='memory':
            from runtime.memory import WorkingMemory
            return dict(working=WorkingMemory.case_view(case),recommendations={sid:s.get('memory_recommendations',[]) for sid,s in case['stages'].items()})
        if name=='recovery':return {'stages':{sid:dict(errors=s['errors'],attempts=s['retry_history']) for sid,s in case['stages'].items()}}
        if name == 'report':
            from .lifecycle_driver import analytical_report
            return analytical_report(case)
        if name == 'outcomes':
            return {k:case[k] for k in ('execution_status','business_outcome_status','case_status','completed_at')} | {'stages':{sid:{k:s[k] for k in ('execution_status','business_outcome_status','real_world_status','outputs')} for sid,s in case['stages'].items()}}
        if name in ('agents','tools'):
            key = 'agent_configurations' if name == 'agents' else 'tool_execution_records'
            return {sid:s[key] for sid,s in case['stages'].items()}
        key = {'timeline':'execution_history','evidence':'source_evidence','assumptions':'assumptions','waits':'waits','stages':'stages','conflicts':'conflicts'}.get(name)
        if key is None:fail('Unknown case inspection section.')
        return {'items':case[key]} if isinstance(case[key], list) else case[key]

    def record(self, case, kind, **details):
        case['execution_history'].append(dict(sequence=len(case['execution_history'])+1, timestamp=self.timestamp(), event_type=kind, **details))

    def transition(self, case, stage, target, reason=None):
        before = stage['execution_status']
        if before == target:return
        if target not in TRANSITIONS[before]:fail('Invalid stage state transition.', 'CASE_TRANSITION_INVALID', 409)
        stage['execution_status'] = target
        stage['updated_at'] = self.timestamp()
        if target in DONE:stage['completed_at'] = self.timestamp()
        self.record(case, 'stage.transition', stage_instance_id=stage['stage_instance_id'], previous=before, target=target, reason=reason)

    def aggregate(self, case):
        stages = list(case['stages'].values())
        for field, statuses in [('active_stage_ids', {'RUNNING'}), ('completed_stage_ids', DONE),
                                ('pending_stage_ids', {'CREATED', 'READY'} | WAITING), ('blocked_stage_ids', {'BLOCKED', 'FAILED'})]:
            case[field] = [s['stage_instance_id'] for s in stages if s['execution_status'] in statuses]
        if case['case_status'] == 'CANCELLED':return
        statuses = {s['execution_status'] for s in stages}
        case['business_outcome_status'] = 'PROVISIONAL' if any(s['business_outcome_status'] == 'PROVISIONAL' for s in stages) else 'PENDING'
        if statuses <= DONE:
            provisional = case['business_outcome_status'] == 'PROVISIONAL'
            case['case_status'] = 'COMPLETED_PROVISIONALLY' if provisional else 'COMPLETED'
            case['execution_status'] = 'COMPLETED'
            case['business_outcome_status'] = 'PROVISIONAL' if provisional else 'EVIDENCE_COMPLETE'
            case['completed_at'] = case['completed_at'] or self.timestamp()
        else:
            priority = ['RUNNING', 'READY', 'WAITING_FOR_AUTHORIZATION', 'WAITING_FOR_EVENT', 'WAITING_FOR_INPUT', 'BLOCKED', 'FAILED', 'CREATED']
            case['case_status'] = next(s for s in priority if s in statuses)
            case['execution_status'] = case['case_status']
        case['generated_assumption_references'] = list(case['assumptions'])
        for item in case.get('reassessments',[]):
            if item['status']=='PENDING' and all(case['stages'][sid]['execution_status'] in DONE for sid in item['reexecute_stage_ids']):item['status']='COMPLETED'

    def _save(self, db, scope, case):
        revision = case['revision']
        case['revision'] += 1
        case['updated_at'] = self.timestamp()
        self.aggregate(case)
        if list(CASE_VALIDATOR.iter_errors(case)):fail('Case state violates its persistence contract.', 'CASE_STATE_INVALID', 409)
        reject_secrets(case)
        if len(canonical(case).encode()) > 8000000:fail('Case history exceeds its storage bound.', 'CASE_STORAGE_LIMIT')
        result = db.execute('UPDATE business_cases SET revision=?,document=? WHERE workspace=? AND owner=? AND case_id=? AND revision=?',
                            (case['revision'], canonical(case), *scope, case['case_id'], revision))
        if result.rowcount != 1:fail('Case changed; reload its revision.', 'CASE_CONFLICT', 409)

    def _receipt(self, db, scope, body, fingerprint):
        row = db.execute('SELECT fingerprint,document FROM business_case_commands WHERE workspace=? AND owner=? AND request_key=?', (*scope, self.key(body))).fetchone()
        if row:
            if row[0] != fingerprint:fail('Command key was reused with different inputs.', 'CASE_COMMAND_CONFLICT', 409)
            return json.loads(row[1])

    def _remember(self, db, scope, body, fingerprint, result):
        db.execute('INSERT INTO business_case_commands VALUES (?,?,?,?,?)', (*scope, self.key(body), fingerprint, canonical(result)))

    def create(self, auth, body):
        scope = self.scope(auth, True)
        self.body(body, ('request_key', 'process_definition_id', 'process_definition_version', 'original_user_goal'),
                  ('inputs', 'business_request', 'resources', 'client_package_id', 'client_package_revision', 'google_connection_id'))
        if type(body['process_definition_version']) is not int or body['process_definition_version'] < 1 or not isinstance(body['process_definition_id'], str):
            fail('Supply an exact process identifier and positive integer version.')
        if not isinstance(body['original_user_goal'], str) or not 1 <= len(body['original_user_goal'].strip()) <= 4000:fail('Supply a bounded business goal.')
        for key in ('inputs', 'business_request', 'resources'):
            if not isinstance(body.get(key, {}), dict):fail('Case inputs and resources must be objects.')
        package=None
        if body.get('client_package_id'):
            packages=self.service.business_composition.packages
            package=packages.get(auth,body['client_package_id'],body.get('client_package_revision'))
            packages.install_processes(auth,body['client_package_id'],body['client_package_revision'],self)
        process = self.process(auth, body['process_definition_id'], body['process_definition_version'])
        if package and (process['client_id']!=package['client_id'] or process['domain_id']!=package['domain']):fail('Process is outside the client package.','CLIENT_PACKAGE_INVALID')
        if package and package.get('process_definitions') and process not in package['process_definitions']:fail('Process is not pinned by this package.','CLIENT_PACKAGE_INVALID')
        fingerprint = digest(['create', body]);timestamp = self.timestamp()
        with self.store.transaction() as db:
            old = self._receipt(db, scope, body, fingerprint)
            if old:return old
            cid = 'case_' + secrets.token_hex(12)
            case = dict(schema_version='business-case-v1', case_id=cid, tenant_id=scope[0], workspace_id=scope[0], owner_id=scope[1],
                        client_id=process['client_id'], domain_id=process['domain_id'], process_definition_id=process['process_definition_id'],
                        process_definition_version=process['version'], process_definition=process, process_sha256=digest(process),
                        original_user_goal=body['original_user_goal'], normalized_goal=' '.join(body['original_user_goal'].split()),
                        case_status='CREATED', execution_status='CREATED', business_outcome_status='PENDING', revision=1,
                        created_at=timestamp, updated_at=timestamp, started_at=None, completed_at=None,
                        ontology_version=None, mapping_version=None, capability_registry_version=None,
                        active_stage_ids=[], completed_stage_ids=[], pending_stage_ids=[], blocked_stage_ids=[],
                        evidence_references=[], generated_assumption_references=[], execution_history=[], external_action_references=[],
                        assumptions={}, conflicts=[], waits={}, source_evidence={}, preparation_id=None,
                        inputs=deepcopy(body.get('inputs', {})), resources=deepcopy(body.get('resources', {})),
                        business_request=deepcopy(body.get('business_request', {})), stages={},
                        configuration_snapshot=deepcopy(self.configuration.get(scope, {})),configuration_version=digest(self.configuration.get(scope, {})))
            for key in ('client_package_id', 'client_package_revision', 'google_connection_id'):
                if key in body:case[key] = body[key]
            if package:case['memory_policy']=deepcopy(package.get('memory_policy',{'enabled':True,'max_recommendations':8,'retention_seconds':2592000}))
            for definition in process['stages']:
                sid = definition['stage_instance_id']
                case['stages'][sid] = dict(stage_instance_id=sid, definition=deepcopy(definition), execution_status='CREATED',
                    business_outcome_status='PENDING', real_world_status='UNVERIFIED' if definition['external_event_requirements'] or definition['side_effect_classification'] in ('draft', 'write') else 'NOT_APPLICABLE',
                    inputs={}, resolved_inputs={}, outputs={}, attempts=0, errors=[], retry_history=[], run_id=None,
                    composition_id=None, agent_configurations=[], tool_execution_records=[], created_at=timestamp, updated_at=timestamp)
            self.record(case, 'case.created');self.aggregate(case)
            CASE_VALIDATOR.validate(case)
            reject_secrets(case)
            db.execute('INSERT INTO business_cases VALUES (?,?,?,?,?)', (*scope, cid, 1, canonical(case)))
            self._remember(db, scope, body, fingerprint, case)
        return case

    def command(self, auth, case_id, operation, body):
        scope = self.scope(auth, True, execute=operation in ('start', 'advance', 'resume', 'cancel'))
        self.body(body, ('request_key', 'expected_revision'), ('inputs',) if operation == 'input' else ('max_stage_executions',) if operation in ('start','advance','resume') else ())
        stage_limit = body.get('max_stage_executions', 64)
        if type(stage_limit) is not int or not 1 <= stage_limit <= 64:fail('Stage dispatch limit must be between one and 64.')
        if type(body['expected_revision']) is not int:fail('An integer expected_revision is required.')
        if operation not in ('prepare', 'start', 'advance', 'resume', 'cancel', 'input'):fail('Unknown case command.')
        if operation == 'prepare':return self.prepare(auth, case_id, body)
        fingerprint = digest([case_id, operation, body]);claimed = []
        with self.store.transaction() as db:
            old = self._receipt(db, scope, body, fingerprint)
            if old:
                return self._load(db, scope, case_id) if operation in ('start','advance','resume','cancel') else old
            case = self._load(db, scope, case_id)
            if case['revision'] != body['expected_revision']:fail('Case changed; reload its revision.', 'CASE_CONFLICT', 409)
            if case['case_status'] in TERMINAL:fail('Case is terminal.', 'CASE_TERMINAL', 409)
            if operation == 'cancel':
                case.update(case_status='CANCELLED', execution_status='CANCELLED', completed_at=self.timestamp())
                for stage in case['stages'].values():
                    if stage['execution_status'] not in TERMINAL:self.transition(case, stage, 'CANCELLED')
                for wait in case['waits'].values():
                    if wait['current_status'] == 'PENDING':wait['current_status'] = 'CANCELLED'
                self.cancel_runs(db, auth, case)
            else:
                if operation == 'input':
                    if not isinstance(body.get('inputs'), dict):fail('Supply a typed inputs object.')
                    if any(s.get('composition_id') and s['execution_status'] not in TERMINAL for s in case['stages'].values()):
                        fail('An existing composition pins its input context; create a new case to change those inputs.', 'CASE_BINDING_CHANGED', 409)
                    case['inputs'].update(deepcopy(body['inputs']))
                if not case.get('prepared_at'):fail('Prepare case evidence before execution.', 'CASE_NOT_PREPARED', 409)
                if operation in ('start', 'advance', 'resume'):
                    case['started_at'] = case['started_at'] or self.timestamp()
                self.refresh(case, scope, wake_authorization=True)
                for stage in case['stages'].values():
                    if operation == 'resume' and stage['execution_status'] in ('RUNNING', 'FAILED', 'BLOCKED'):
                        self.recoverable(case, stage)
                    if operation != 'input' and stage['execution_status'] == 'READY':
                        if len(claimed) >= stage_limit:break
                        self.transition(case, stage, 'RUNNING')
                        token = secrets.token_hex(16);stage['claim'] = token
                        stage['deadline'] = self.clock() + stage['definition']['timeout_policy']['seconds']
                        stage['lease_until'] = self.clock() + min(300, stage['definition']['timeout_policy']['seconds'])
                        claimed.append((stage['stage_instance_id'], token))
            self.record(case, 'case.' + operation)
            self._save(db, scope, case)
            self._remember(db, scope, body, fingerprint, case)
        if claimed:
            with ThreadPoolExecutor(max_workers=min(4, len(claimed))) as executor:
                futures = [executor.submit(self.execute_stage, auth, case_id, sid, token, operation == 'resume') for sid, token in claimed]
                for future in futures:future.result()
            return self.get(auth, case_id)
        return case

    def prepare(self, auth, case_id, body):
        scope = self.scope(auth, True);fingerprint = digest([case_id, 'prepare', body])
        with self.store.transaction(write=False) as db:
            old = self._receipt(db, scope, body, fingerprint)
            if old:return old
            case = self._load(db, scope, case_id)
        if case['revision'] != body['expected_revision']:fail('Case changed; reload its revision.', 'CASE_CONFLICT', 409)
        if case.get('prepared_at') or case['case_status'] in TERMINAL:fail('Case preparation is immutable; create a new case for different pins.', 'CASE_ALREADY_PREPARED', 409)
        composition = getattr(self.service, 'business_composition', None)
        preparation = getattr(self.service, 'business_preparation', None)
        package = None;prepared = None
        if case.get('client_package_id'):
            if composition is None:fail('Client package preparation is unavailable.', 'CASE_UNAVAILABLE', 503)
            package = composition.packages.get(auth, case['client_package_id'], case['client_package_revision'])
            case['ontology_version'] = package['ontology_version'];case['mapping_version'] = digest(package['source_mappings'])
            from .capability_contracts import catalogue
            contracts = deepcopy(package['capability_contracts'])
            contracts['business.report'] = catalogue(None, [])['business.report']
            needed = {cid for stage in case['stages'].values() for cid in stage['definition']['required_capabilities']}
            def dependencies(cid):
                for dep in contracts.get(cid, {}).get('preconditions', []):
                    if dep not in needed:needed.add(dep);dependencies(dep)
            for cid in list(needed):dependencies(cid)
            for cid in sorted(needed):
                c = contracts.get(cid, {})
                if c.get('kind') == 'tool' and c.get('verification_method') == 'mapped_evidence_and_coverage':
                    case['source_evidence'][cid] = composition.packages.read(auth, dict(package_id=case['client_package_id'],revision=case['client_package_revision'],capability_id=cid))
            case['evidence_references'] = [dict(record_id=r['record_id'], task=t) for t,e in case['source_evidence'].items() for r in e.get('records', [])]
        else:
            from .capability_contracts import catalogue
            tools = composition.tools(auth) if composition else []
            base_contracts = catalogue(None, tools)
            needed = {cid for stage in case['stages'].values() for cid in stage['definition']['required_capabilities']}
            def capability_dependencies(cid):
                for dep in base_contracts.get(cid, {}).get('preconditions', []):
                    if dep not in needed:needed.add(dep);capability_dependencies(dep)
            for cid in list(needed):capability_dependencies(cid)
            retrieval_tasks = {base_contracts[cid]['retrieval_task'] for cid in needed if cid in base_contracts and base_contracts[cid]['retrieval_task']}
            view = preparation.general_context(auth, case['original_user_goal'], case['business_request']) if preparation else {}
            if view.get('preflight_id'):
                prepared = preparation.checked(auth, view['preflight_id'])
                if retrieval_tasks - set(prepared['tasks']):
                    from .business_investigations import QUESTIONS
                    request = deepcopy(case['business_request'])
                    request.update(objective=case['original_user_goal']+'. '+'; '.join(QUESTIONS[t] for t in sorted(retrieval_tasks)),
                                   version_id=prepared['version_id'],inputs=deepcopy(prepared['inputs']))
                    prepared = preparation.prepare(auth, request)
                case['preparation_id'] = prepared['preflight_id'];case['ontology_version'] = prepared['pins']['ontology_version']
                case['mapping_version'] = prepared['pins']['mapping_sha256']
                case['source_evidence'] = deepcopy(prepared['available_evidence'])
                # Existing scenario fixtures never become ACTUAL case source evidence.
                if prepared.get('evidence_context'):fail('Business cases require company evidence or case-local assumptions; scenario evidence cannot be verified.', 'CASE_SCENARIO_DENIED')
                case['evidence_references'] = [dict(record_id=r['record_id'], task=t) for t,e in case['source_evidence'].items() for r in e.get('records', [])]
            contracts = catalogue(prepared, tools)
        case['capability_registry_version'] = digest(contracts)
        case['capability_contracts'] = deepcopy(contracts)
        concepts = {c['id'] for c in package['concepts']} if package else {c['id'] for t in (prepared or {}).get('tasks', {}).values() for c in t['concepts']}
        for stage in case['stages'].values():
            definition = stage['definition']
            if set(definition['required_capabilities']) - set(contracts):fail('Process requires unregistered capabilities.', 'CASE_CAPABILITY_UNSUPPORTED')
            if set(definition['required_ontology_concepts']) - concepts:fail('Required ontology concepts are unavailable.', 'CASE_ONTOLOGY_UNSUPPORTED')
        case['prepared_at'] = self.timestamp()
        with self.store.transaction() as db:
            current = self._load(db, scope, case_id)
            if current['revision'] != case['revision']:fail('Case changed during preparation.', 'CASE_CONFLICT', 409)
            old = self._receipt(db, scope, body, fingerprint)
            if old:return old
            self.refresh(case, scope);self.record(case, 'case.prepared');self._save(db, scope, case)
            self._remember(db, scope, body, fingerprint, case)
        return case

    def predicate(self, predicate, resolver, outputs=None, runtime=None):
        source = predicate['source']
        if source in ('output', 'runtime'):
            value = at(outputs if source == 'output' else runtime, predicate['path'])
        else:
            entry = resolver.binding(predicate);value = entry['value'] if entry else MISSING
        if predicate['operator'] == 'exists':return value is not MISSING
        if value is MISSING:return None
        other = predicate.get('value');op = predicate['operator']
        try:
            return value == other if op == 'eq' else value != other if op == 'ne' else value > other if op == 'gt' else value < other if op == 'lt' else value in other
        except TypeError:return None

    def refresh(self, case, scope, wake_authorization=False):
        # Persisted canonical JSON sorts keys. Evaluate dependencies before children
        # so a skipped branch can settle without a redundant execution command.
        ordered=[];seen=set()
        def visit(sid):
            if sid in seen:return
            for dependency in case['stages'][sid]['definition']['dependency_definitions']:visit(dependency)
            seen.add(sid);ordered.append(case['stages'][sid])
        for sid in case['stages']:visit(sid)
        for stage in ordered:
            status = stage['execution_status'];definition = stage['definition']
            if status in TERMINAL | {'RUNNING', 'FAILED', 'BLOCKED'}:continue
            if status == 'WAITING_FOR_AUTHORIZATION' and stage.get('composition_id') and not wake_authorization:continue
            if not all(case['stages'][dep]['execution_status'] in DONE for dep in definition['dependency_definitions']):continue
            if status == 'CREATED':self.transition(case, stage, 'READY')
            resolver = EvidenceCompletion(case, stage, self.timestamp(), case.get('configuration_snapshot', self.configuration.get(scope, {})))
            resolved = {};missing = [];specs = {**definition['required_inputs'], **definition['optional_inputs']}
            stage['resolved_inputs'] = resolved
            attempted = set()
            def resolve_input(name, stack):
                if name in attempted:return
                if name in stack:fail('Input derivation bindings contain a cycle.')
                def dependencies(value):
                    if isinstance(value, dict):
                        if value.get('source') == 'input' and 'path' in value:
                            dep = value['path'].split('.')[0]
                            if dep not in specs:fail('Input binding references an unknown field.')
                            resolve_input(dep, stack | {name})
                        for child in value.values():dependencies(child)
                    elif isinstance(value, list):
                        for child in value:dependencies(child)
                dependencies(specs[name])
                entry = resolver.resolve(name, specs[name]);attempted.add(name)
                if entry:resolved[name] = entry
                elif name in definition['required_inputs']:missing.append(name)
            for name in specs:resolve_input(name, set())
            stage['resolved_inputs'] = resolved;stage['inputs'] = {k:e['value'] for k,e in resolved.items()};stage['missing_inputs'] = missing
            branches = [self.predicate(p, resolver) for p in definition['transition_rules']]
            if branches and not all(branches):
                if stage['execution_status'] != 'READY':self.transition(case, stage, 'READY')
                self.transition(case, stage, 'RUNNING')
                if not any(b is False for b in branches):
                    self.transition(case, stage, 'WAITING_FOR_INPUT', 'conditional_input_unavailable')
                else:
                    stage['business_outcome_status'] = 'SKIPPED'
                    self.transition(case, stage, 'COMPLETED', 'conditional_branch_not_selected')
                continue
            event_missing = {name for name in missing if definition['required_inputs'][name].get('binding', {}).get('source') == 'event'} if definition['external_event_requirements'] and not stage.get('event') else set()
            missing_evidence = [mid for mid in definition['evidence_requirements'] if not resolver.evidence(mid)]
            stage['missing_evidence'] = missing_evidence
            if missing_evidence and definition['provisional_continuation_policy']['allowed']:
                stage['business_outcome_status'] = 'PROVISIONAL'
            if set(missing)-event_missing or (missing_evidence and not definition['provisional_continuation_policy']['allowed']) or not all(self.predicate(p, resolver) for p in definition['preconditions']):
                if stage['execution_status'] != 'WAITING_FOR_INPUT':
                    if stage['execution_status'] != 'READY':self.transition(case, stage, 'READY')
                    self.transition(case, stage, 'RUNNING');self.transition(case, stage, 'WAITING_FOR_INPUT')
                continue
            if stage['execution_status'] in WAITING:self.transition(case, stage, 'READY')
            if definition['external_event_requirements'] and not stage.get('event') and not stage.get('event_timeout_provisional'):
                requirement = definition['external_event_requirements'][0]
                keys = {k:resolver.binding(b) for k,b in requirement['correlation_keys'].items()}
                if not all(keys.values()) or any(e['provenance_type'] != 'ACTUAL' for e in keys.values()):
                    self.transition(case, stage, 'RUNNING');self.transition(case, stage, 'WAITING_FOR_INPUT');continue
                wid = 'wait_' + digest([case['case_id'], stage['stage_instance_id']])[:24]
                if wid not in case['waits']:
                    case['waits'][wid] = dict(wait_id=wid, case_id=case['case_id'], stage_instance_id=stage['stage_instance_id'],
                        event_type=requirement['event_type'], expected_source=requirement['expected_source'],
                        correlation_keys={k:e['value'] for k,e in keys.items()}, created_at=self.timestamp(),
                        deadline=self.clock()+definition['timeout_policy']['seconds'], current_status='PENDING',
                        continuation_target=stage['stage_instance_id'], retry_or_escalation_policy=deepcopy(definition['timeout_policy']),blocking=requirement.get('blocking', True))
                wait = case['waits'][wid]
                if not requirement.get('blocking', True):
                    stage['pending_real_world_event'] = wait['current_status'] in ('PENDING','TIMED_OUT')
                    if stage['pending_real_world_event']:stage['business_outcome_status'] = 'PROVISIONAL'
                    if event_missing:
                        self.transition(case, stage, 'RUNNING');self.transition(case, stage, 'WAITING_FOR_INPUT', 'protected_event_input_required')
                    continue
                if wait['current_status'] == 'PENDING' and wait['deadline'] <= self.clock():
                    wait['current_status'] = 'TIMED_OUT'
                    policy = definition['provisional_continuation_policy']
                    if definition['timeout_policy']['action'] == 'continue_provisionally' and policy['allowed'] and policy.get('allow_event_timeout') and not requirement['requires_authorization']:
                        stage['event_timeout_provisional'] = True
                        stage['business_outcome_status'] = 'PROVISIONAL'
                        self.record(case, 'wait.provisional_timeout', wait_id=wid)
                        continue
                    self.transition(case, stage, 'RUNNING')
                    self.transition(case, stage, 'FAILED' if definition['timeout_policy']['action'] == 'fail' else 'BLOCKED', 'event_deadline')
                    self.record(case, 'stage.escalated', stage_instance_id=stage['stage_instance_id'], wait_id=wid);continue
                self.transition(case, stage, 'RUNNING')
                self.transition(case, stage, 'WAITING_FOR_AUTHORIZATION' if requirement['requires_authorization'] else 'WAITING_FOR_EVENT')

    def recoverable(self, case, stage):
        status = stage['execution_status']
        if status == 'RUNNING' and stage.get('lease_until', stage.get('deadline', float('inf'))) > self.clock():return
        if status in ('FAILED', 'BLOCKED'):
            max_retries = stage['definition']['retry_policy']['max_retries']
            if len(stage['retry_history']) >= max_retries:return
            if stage.get('error') and not stage['error']['retry_eligible']:return
            if self.clock() < stage.get('retry_after', 0):return
            stage['retry_history'].append(dict(timestamp=self.timestamp(), previous=deepcopy(stage.get('error'))))
        if status in ('FAILED', 'BLOCKED', 'RUNNING'):
            # Saved run is authoritative; never create a replacement write invocation.
            stage.pop('claim', None);self.transition(case, stage, 'READY', 'explicit_resume')

    def execute_stage(self, auth, case_id, sid, token, resume=False):
        scope = self.scope(auth, True, True)
        case = self.get(auth, case_id);stage = deepcopy(case['stages'][sid]);definition = stage['definition']
        if stage.get('claim') != token or stage['execution_status'] != 'RUNNING':return
        try:
            if definition['required_capabilities']:
                self.execute_capabilities(auth, case, stage, resume)
                if stage['execution_status'] == 'WAITING_FOR_AUTHORIZATION':
                    self.finish(auth, case_id, sid, token, stage);return
            if self.clock() >= stage['deadline']:
                policy = definition['timeout_policy']
                if policy['action'] == 'continue_provisionally' and definition['provisional_continuation_policy']['allowed'] and not definition_write(stage):
                    stage['deadline_exceeded'] = True
                else:
                    fail('The pinned stage execution deadline expired.', 'CASE_STAGE_TIMEOUT', 409)
            resolver = EvidenceCompletion(case, stage, self.timestamp(), case.get('configuration_snapshot', self.configuration.get(scope, {})))
            outputs = {}
            for name, binding in definition['output_bindings'].items():
                if binding['source'] in ('runtime', 'receipt'):
                    value = at(stage.get('runtime_result', {}), binding['path'])
                    if value is MISSING:fail('Required runtime output was not returned.', 'CASE_OUTPUT_INVALID')
                    receipt = binding['source'] == 'receipt'
                    if receipt and binding['path'].split('.')[0] not in stage.get('workflow', {}).get('metadata', {}).get('composition_action_verifiers', {}):
                        fail('Receipt bindings require a verified deterministic action node.', 'CASE_OUTPUT_INVALID')
                    # Model narrative is never actual evidence. Provider receipts remain separate.
                    outputs[name] = artifact(value, 'ACTUAL' if receipt else 'INFERRED', [{'run_id': stage['run_id']}], 'connector_receipt' if receipt else 'verified_runtime_result', self.timestamp(), case_id)
                else:
                    entry = resolver.binding(binding)
                    if not entry:fail('Required output binding was not resolved.', 'CASE_OUTPUT_INVALID')
                    outputs[name] = entry
            raw = {k:e['value'] for k,e in outputs.items()}
            if not conforms(raw, definition['output_schema']):fail('Stage output does not satisfy its pinned schema.', 'CASE_OUTPUT_INVALID')
            if not all(self.predicate(p, resolver, raw, stage.get('runtime_result', {})) for p in definition['completion_criteria']):
                fail('Stage completion criteria are not satisfied.', 'CASE_COMPLETION_UNVERIFIED')
            provisional = (stage.get('pending_real_world_event') or stage.get('event_timeout_provisional') or stage.get('deadline_exceeded') or bool(stage.get('missing_evidence')) or stage.get('analytical_runtime_result', False) or any(e['provenance_type'] in ('INFERRED', 'SYNTHETIC') for e in list(outputs.values())+list(stage['resolved_inputs'].values())))
            if provisional and not definition['provisional_continuation_policy']['allowed']:fail('This stage requires verified evidence.', 'CASE_EVIDENCE_REQUIRED')
            stage['outputs'] = outputs;stage['business_outcome_status'] = 'PROVISIONAL' if provisional else 'EVIDENCE_COMPLETE'
            stage['execution_status'] = 'COMPLETED_PROVISIONALLY' if provisional else 'COMPLETED'
        except Exception as exc:
            code = getattr(exc, 'code', 'CASE_EXECUTION_FAILED')
            stage['error'] = classify(code, task=sid, external_write=definition['side_effect_classification'] in ('draft', 'write'))
            # Invalid bindings, schemas and permissions require correction, not blind retries.
            if code.startswith('CASE_'):stage['error']['retry_eligible'] = False
            stage['errors'].append(dict(timestamp=self.timestamp(), **stage['error']))
            stage['execution_status'] = 'BLOCKED' if code == 'CASE_STAGE_TIMEOUT' and definition['timeout_policy']['action'] != 'fail' else 'FAILED'
            stage['retry_after'] = self.clock()+definition['retry_policy']['backoff_seconds']
        self.finish(auth, case_id, sid, token, stage)

    def checkpoint(self, auth, case_id, sid, token, updates):
        scope = self.scope(auth, True, True)
        with self.store.transaction() as db:
            case = self._load(db, scope, case_id);stage = case['stages'][sid]
            if stage.get('claim') != token or stage['execution_status'] != 'RUNNING':fail('Stage claim expired.', 'CASE_CLAIM_LOST', 409)
            stage.update(deepcopy(updates));self._save(db, scope, case)

    def execute_capabilities(self, auth, case, stage, resume):
        definition = stage['definition'];sid = stage['stage_instance_id'];token = stage['claim']
        composition = getattr(self.service, 'business_composition', None)
        runner = self.service.runtime_runner
        if composition is None or runner is None:fail('Configure the existing composition and runtime.', 'CASE_RUNTIME_UNAVAILABLE', 503)
        if definition['side_effect_classification'] in ('draft', 'write') and any(e['provenance_type'] != 'ACTUAL' for e in stage['resolved_inputs'].values()):
            fail('Generated inputs cannot authorize an external action.', 'CASE_PROVISIONAL_ACTION_DENIED', 403)
        if not stage['composition_id']:
            execution_identity=[case['case_id'],sid]+([stage['reassessment_generation']] if stage.get('reassessment_generation') else [])
            operations = [dict(capability_id=cid, inputs=deepcopy(stage['inputs'])) for cid in definition['required_capabilities']]
            request = dict(objective=case['original_user_goal'], request_key='lifecycle_'+digest(execution_identity)[:32],
                           operations=operations, resources=deepcopy(case['resources']),recovery_max_retries=definition['retry_policy']['max_retries'])
            if case.get('preparation_id'):request['preparation_id'] = case['preparation_id']
            elif case.get('client_package_id'):
                request.update(client_package_id=case['client_package_id'], client_package_revision=case['client_package_revision'])
            elif case['business_request']:request['business_request'] = case['business_request']
            if case.get('google_connection_id'):request['google_connection_id'] = case['google_connection_id']
            from runtime.memory import WorkingMemory
            context = dict(case_id=case['case_id'], stage_instance_id=sid, inputs=deepcopy(stage['resolved_inputs']),working_memory=WorkingMemory.case_view(case,stage),
                           qualification='Generated assumptions are analytical only; source citations and real activities require actual evidence.')
            doc = composition.prepare(auth, request, lifecycle_context=context)
            stage['memory_recommendations']=deepcopy(doc.get('memory_recommendations',[]))
            stage['capability_plan_reference'] = doc['composition_id']
            stage['capability_gaps'] = deepcopy(doc['gaps'])
            if doc['state'] != 'ready':fail('Resolve registered capability and resource gaps.', 'CASE_CAPABILITY_NOT_READY')
            if any(doc['contracts'].get(cid) != case['capability_contracts'].get(cid) for cid in definition['required_capabilities']):
                fail('Pinned capability contracts changed; prepare a new case.', 'CASE_CAPABILITY_STALE', 409)
            selected = {v['tool_id'] for v in doc['selected_tools'].values()}
            if not selected <= set(definition['allowed_tools']):fail('Planner selected a tool outside the pinned stage allowlist.', 'CASE_TOOL_DENIED', 403)
            if any(t['side_effect'] in ('draft','write') for t in doc['tasks']) and definition['side_effect_classification'] not in ('draft','write'):
                fail('Planner selected an external action for a read-only stage.', 'CASE_TOOL_DENIED', 403)
            if set(definition['required_capabilities']) - {t['capability_id'] for t in doc['tasks']}:fail('Planner omitted a required stage capability.', 'CASE_CAPABILITY_NOT_READY')
            stage.update(composition_id=doc['composition_id'], agent_configurations=deepcopy(doc['configurations']), workflow=composition.workflow(auth, doc['composition_id']))
            self.checkpoint(auth, case['case_id'], sid, token, {k:stage[k] for k in ('composition_id','agent_configurations','workflow')})
        # Save a normal draft; stable commands also cover interruption before saving.
        workflow = stage['workflow']
        execution_identity=[case['case_id'],sid]+([stage['reassessment_generation']] if stage.get('reassessment_generation') else [])
        pinned_inputs = workflow['metadata'].get('lifecycle_context', {}).get('inputs', {})
        def stable_inputs(values):
            return {name:{k:v for k,v in entry.items() if k != 'generated_at'} for name,entry in values.items()}
        if stable_inputs(pinned_inputs) != stable_inputs(stage['resolved_inputs']):
            fail('Stage inputs changed after composition; create a case with fresh reviewed pins.', 'CASE_BINDING_CHANGED', 409)
        with self.store.transaction(write=False) as db:
            existing = self.store.get(db, scope_workspace(auth), workflow['workflow_id'], workflow['version'])
        if not existing:
            response = self.service.handle(dict(request_id='lifecycle_save', operation='save_workflow_version',
                idempotency_key='lifecycle_save_'+digest(execution_identity)[:32], payload=dict(workflow_id=workflow['workflow_id'],workflow_version=1,base_version=0,workflow=workflow)), auth)
            if response['status'] >= 400:
                error = response['data']['error'];fail(error['message'], error['error_code'], response['status'])
        rt = runner.runtime
        if not stage.get('run_id'):
            try:
                def attach(db, created):
                    # Atomically attach the run and validate cancellation/claim before it can be leased.
                    current = self._load(db, self.scope(auth, True, True), case['case_id'])
                    target = current['stages'][sid]
                    if target.get('claim') != token or target['execution_status'] != 'RUNNING':
                        fail('Case was cancelled or its stage claim changed.', 'CASE_CLAIM_LOST', 409)
                    target['run_id'] = created['run_id']
                    self._save(db, self.scope(auth, True, True), current)
                run = rt.create_run(dict(request_id='lifecycle_run', idempotency_key='lifecycle_run_'+digest(execution_identity)[:32],
                    payload=dict(workflow_id=workflow['workflow_id'],workflow_version=workflow['version'],inputs={})), auth, on_created=attach)
            except RuntimeFailure as exc:
                if exc.code in ('REVISION_NOT_APPROVED', 'WORKFLOW_NOT_FOUND'):
                    stage['execution_status'] = 'WAITING_FOR_AUTHORIZATION';return
                raise
            stage['run_id'] = run['run_id']
        with self.store.transaction(write=False) as db:
            run = deepcopy(rt.load(db, stage['run_id'], auth))
        if run['status'] in ('failed','blocked'):
            if not resume:fail('Saved runtime failure requires explicit guarded recovery.', 'CASE_RECOVERY_REQUIRED', 409)
            rt.recovery.resume(run['run_id'], auth)
        result = runner.advance(stage['run_id'], auth)
        with self.store.transaction(write=False) as db:
            saved = deepcopy(rt.load(db, stage['run_id'], auth))
        stage['runtime_result'] = deepcopy(saved.get('outputs', {}))
        stage['tool_execution_records'] = [deepcopy(t) for c in saved.get('task_checkpoints', {}).values() for t in c.get('result', {}).get('tool_results', [])]
        stage['tool_execution_records'] += [dict(node_id=node, output=deepcopy(saved.get('outputs', {}).get(node)), run_id=stage['run_id']) for node in workflow['metadata'].get('composition_action_verifiers', {}) if node in saved.get('outputs', {})]
        stage['runtime_checkpoints'] = deepcopy(saved.get('task_checkpoints', {}))
        stage['runtime_source_evidence'] = {task:deepcopy(checkpoint['result']['source_evidence']) for task,checkpoint in saved.get('task_checkpoints', {}).items() if checkpoint.get('result', {}).get('source_evidence')}
        stage['analytical_runtime_result'] = any(c.get('kind') == 'model' for c in case['capability_contracts'].values() if c['capability_id'] in definition['required_capabilities'])
        stage['runtime_error_code'] = saved.get('error_code')
        if result['status'] == 'paused_for_approval':
            stage['execution_status'] = 'WAITING_FOR_AUTHORIZATION';return
        if result['status'] != 'completed':
            raise RuntimeFailure(saved.get('error_code') or 'CASE_RUNTIME_INCOMPLETE', 'Inspect the existing runtime run and recovery details.')
        if definition['side_effect_classification'] in ('draft','write'):
            stage['real_world_status'] = 'CONNECTOR_CONFIRMED'

    def finish(self, auth, case_id, sid, token, result):
        scope = self.scope(auth, True, True)
        with self.store.transaction() as db:
            case = self._load(db, scope, case_id);stage = case['stages'][sid]
            if case['case_status'] == 'CANCELLED' or stage.get('claim') != token:return
            target = result.pop('execution_status')
            result.pop('claim', None)
            stage.update(result);stage['attempts'] += 1;stage.pop('claim', None)
            if target in DONE:stage.pop('error', None)
            for task, packets in stage.get('runtime_source_evidence', {}).items():
                for index, packet in enumerate(packets):
                    case['source_evidence'][stage['run_id']+':'+task+':'+str(index)] = deepcopy(packet)
                    for record in packet.get('records', []):
                        reference = dict(record_id=record['record_id'], task=task, run_id=stage['run_id'])
                        if reference not in case['evidence_references']:case['evidence_references'].append(reference)
            self.transition(case, stage, target)
            if stage.get('error', {}).get('error_code') == 'CASE_STAGE_TIMEOUT' or stage.get('deadline_exceeded'):
                self.record(case, 'stage.deadline_exceeded', stage_instance_id=sid, action=stage['definition']['timeout_policy']['action'])
            if stage.get('run_id') and definition_write(stage) and stage['run_id'] not in case['external_action_references']:
                case['external_action_references'].append(stage['run_id'])
            # Refresh only eligibility; execution requires another bounded command.
            self.refresh(case, scope);self._save(db, scope, case)

    def event(self, auth, case_id, body):
        scope = self.scope(auth, True)
        RuntimeService.authorize(auth, 'events.ingest', {'admin','builder'})
        self.body(body, ('request_key','event_id','event_type','source','correlation_keys','payload'))
        if not isinstance(body['correlation_keys'], dict) or not isinstance(body['payload'], dict) or not all(isinstance(body[k],str) and 1<=len(body[k])<=128 for k in ('event_id','event_type','source')):fail('Invalid external event envelope.')
        fingerprint = digest([case_id,'event',body])
        with self.store.transaction() as db:
            old = self._receipt(db, scope, body, fingerprint)
            if old:return old
            case = self._load(db, scope, case_id)
            if case['case_status'] == 'CANCELLED':fail('Cancelled cases cannot consume events.', 'CASE_TERMINAL', 409)
            seen = case.setdefault('external_events', {})
            identity = body['source']+':'+body['event_id']
            content = {k:v for k,v in body.items() if k != 'request_key'}
            if identity in seen:
                if seen[identity] != content:fail('Event identity reused with different content.', 'CASE_EVENT_CONFLICT', 409)
                self._remember(db, scope, body, fingerprint, case);return case
            matches = [w for w in case['waits'].values() if w['current_status'] in ('PENDING','TIMED_OUT')
                       and w['event_type'] == body['event_type'] and w['expected_source'] == body['source'] and w['correlation_keys'] == body['correlation_keys']]
            if len(matches) != 1:fail('Event must correlate to exactly one case stage wait.', 'CASE_EVENT_UNMATCHED', 409)
            wait = matches[0];stage = case['stages'][wait['stage_instance_id']];requirement = stage['definition']['external_event_requirements'][0]
            timed_out = wait['current_status'] == 'TIMED_OUT'
            if requirement['requires_authorization']:
                RuntimeService.authorize(auth, 'workflow.approve', {'admin','approver'})
                # This records an asserted business authorization event; it never approves runtime writes.
            if not conforms(body['payload'], requirement['schema']):fail('Event payload does not satisfy the pinned event contract.')
            seen[identity] = content;stage['event'] = deepcopy(content)
            stage['event']['submitted_by'] = deepcopy(auth['subject'])
            stage['real_world_status'] = 'REPORTED_BY_AUTHENTICATED_SOURCE'
            wait.update(current_status='RECEIVED', event_id=body['event_id'], received_at=self.timestamp())
            if stage['execution_status'] in DONE:
                case['conflicts'].append(dict(stage=stage['stage_instance_id'], reason='late_event_requires_downstream_reassessment', event=content))
            else:
                # Re-evaluate inputs on the next command, retaining prior assumptions/conflicts.
                if stage['execution_status'] in WAITING or (timed_out and stage['execution_status'] in ('BLOCKED','FAILED') and not stage.get('error')):
                    self.transition(case, stage, 'READY', 'external_event_received')
                self.refresh(case, scope)
            self.record(case, 'event.received', wait_id=wait['wait_id'], event_id=body['event_id'])
            self._save(db, scope, case);self._remember(db, scope, body, fingerprint, case)
        return case

    def cancel_runs(self, db, auth, case):
        # Same scoped transition as CompositionPresentation.cancel, in the case transaction.
        # A crash cannot commit case cancellation while leaving its queued runtime run active.
        runner = self.service.runtime_runner
        for stage in case['stages'].values():
            if stage.get('run_id'):
                if runner is None:fail('Configure the existing runtime to cancel attached runs atomically.', 'CASE_RUNTIME_UNAVAILABLE', 503)
                rt = runner.runtime;run = rt.load(db,stage['run_id'],auth,'workflow.execute')
                if run['subject_id'] != case['owner_id'] or run['workflow_id'] != stage['workflow']['workflow_id']:
                    fail('Run is outside this case binding.', 'CASE_RUN_MISMATCH', 403)
                if run['status'] in ('queued','running','paused_for_approval'):rt.transition(db,run,'cancelled')


def definition_write(stage):
    return stage['definition']['side_effect_classification'] in ('draft', 'write')


def scope_workspace(auth):
    return auth['subject']['workspace_id']
