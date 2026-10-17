"""Workflow transport/revision lifecycle and delegation to an explicit runtime."""
from copy import deepcopy
from datetime import datetime, timezone
from .security import request_correlation
import hashlib
import json
import logging
import sqlite3
import re
import time
from uuid import uuid4

from jsonschema import Draft202012Validator
from planner.service import PlannerService
from planner.errors import PlannerFailure
from planner.validation import validate_workflow
from registry import RegistryService, WorkspacePolicy
from registry.contracts import RegistryError, VERSIONS, schema, validate
from registry.safety import reject_secrets
from .storage import WorkflowStore, sqlite_category
from .postgres import DatabaseFailure
from .registry_adapter import RegistryAdapter
from runtime.service import RuntimeFailure
from .lifecycle import LifecycleService, LifecycleFailure


class ApiFailure(Exception):
    def __init__(self, code, message, status=400, field=None, retryable=False, details=None):
        super().__init__(message)
        self.code, self.status, self.field, self.retryable = code, status, field, retryable
        self.details = details


PERMISSIONS = {
    'plan_workflow': ('workflow.plan', {'admin', 'builder'}),
    'list_workflows': ('workflow.view', {'admin', 'builder', 'viewer', 'approver'}),
    'get_workflow': ('workflow.view', {'admin', 'builder', 'viewer', 'approver'}),
    'save_workflow_version': ('workflow.edit', {'admin', 'builder'}),
    'validate_workflow': ('workflow.validate', {'admin', 'builder'}),
    'approve_workflow': ('workflow.approve', {'admin', 'approver'}),
    'list_tools': ('tools.read', {'admin', 'builder', 'viewer', 'approver'}),
    'list_capabilities': ('tools.read', {'admin', 'builder', 'viewer', 'approver'}),
    'execute_workflow': ('workflow.execute', {'admin', 'builder'}),
    'get_run': ('runs.view', {'admin', 'builder', 'viewer', 'approver'}),
    'list_run_events': ('runs.view', {'admin', 'builder', 'viewer', 'approver'}),
    'decide_approval': ('runs.view', {'admin', 'builder', 'viewer', 'approver'}),
    'list_runs': ('runs.view', {'admin', 'builder', 'viewer', 'approver'}),
    'list_approvals': ('runs.view', {'admin', 'builder', 'viewer', 'approver'}),
}


class WorkflowService:
    def __init__(self, store, planner=None, registry=None, registry_adapter=None, runtime_runner=None,
                 lifecycle_adapter=None, trigger_secrets=None, clock=time.time):
        self.runtime_runner = runtime_runner
        self.store = store
        self.planner = planner or PlannerService()
        self.registry = registry_adapter.service if registry_adapter else registry or RegistryService(WorkspacePolicy('local-workspace'))
        self.registry_adapter = registry_adapter or RegistryAdapter(self.registry)
        self.lifecycle = LifecycleService(self, clock, lifecycle_adapter, trigger_secrets)

    def handle_lifecycle(self, operation, request, auth, **context):
        """Additive v2 boundary; accepted v1 request operations remain unchanged."""
        request_id = request.get('request_id', f'req_{uuid4().hex}') if isinstance(request, dict) else f'req_{uuid4().hex}'
        try:
            if not isinstance(request, dict) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,128}', request_id):
                raise LifecycleFailure('INVALID_REQUEST', 'Use a valid lifecycle request envelope.', 400)
            if any(key in request.get('payload', {}) for key in ('auth_context', 'roles', 'permissions', 'subject', 'authorization_reference')):
                raise LifecycleFailure('UNTRUSTED_AUTHORITY', 'Authority must come from the server session.', 400)
            if operation == 'activate_release':
                data = self.lifecycle.activate(request, auth)
            elif operation == 'disable_release':
                data = self.lifecycle.disable(request, auth)
            elif operation == 'delete_workflow':
                data = self.lifecycle.delete(request, auth)
            elif operation == 'list_workflow_overview':
                data = self.lifecycle.overview(auth, cursor=context.get("workflow_cursor"))
            elif operation == 'subscribe_workflow_overview':
                data = self.lifecycle.overview(auth, context.get('after_sequence', 0))
            elif operation == 'get_lifecycle_operation':
                data = self.lifecycle.get_operation(context.get('operation_id'), auth)
            elif operation == 'ingest_trigger_event':
                data = self.lifecycle.ingest(context.get('binding_id'), request.get('payload', {}).get('event'), auth,
                                             context.get('signature'), context.get('timestamp'),
                                             request.get('payload', {}).get('checkpoint'))
            elif operation == 'poll_trigger':
                data = self.lifecycle.poll(context.get('binding_id'), request.get('payload', {}).get('changes', []),
                                           request.get('payload', {}).get('cursor'), auth)
            elif operation == 'replay_dispatch_job':
                data = {'job': self.lifecycle.replay(context.get('job_id'), auth)}
            else:
                raise LifecycleFailure('INVALID_OPERATION', 'The lifecycle operation is not supported.', 400)
            return self.envelope(request_id, 200, data)
        except DatabaseFailure as exc:
            codes={'contention':'API_DATABASE_BUSY','serialization':'API_DATABASE_SERIALIZATION_RETRY','deadlock':'API_DATABASE_DEADLOCK','transaction_state':'API_DATABASE_TRANSACTION_INVALID','unavailable':'API_DATABASE_UNAVAILABLE'}
            return self.failure(request_id,ApiFailure(codes.get(exc.category,'INVALID_API_DATA'),
                'The database transaction could not complete. Check the current state before retrying.',503 if exc.retryable else 500,retryable=exc.retryable))
        except sqlite3.OperationalError as exc:
            if sqlite_category(exc)=='contention':
                return self.failure(request_id, ApiFailure('API_DATABASE_BUSY',
                    'The workflow database is busy. Retry shortly.', 503, retryable=True))
            if sqlite_category(exc)=='transaction_state':
                return self.failure(request_id,ApiFailure('API_DATABASE_TRANSACTION_INVALID','The database transaction is invalid.',500))
            logging.warning("Workflow database error request_id=%s category=%s",request_id,sqlite_category(exc))
            return self.failure(request_id, ApiFailure('INVALID_API_DATA', 'The workflow database could not process the request.', 500))
        except ApiFailure as exc:
            return self.failure(request_id, exc)
        except LifecycleFailure as exc:
            if operation in {'activate_release', 'disable_release', 'delete_workflow'}:
                try:
                    self.lifecycle.record_failure(request, auth, operation, exc)
                except Exception:
                    pass
            return self.failure(request_id, ApiFailure(exc.code, str(exc), exc.status, retryable=exc.retryable))

    @staticmethod
    def envelope(request_id, status, data):
        result = dict(request_id=request_id, status=status, data={
            'correlation_id': request_correlation.get() or f'corr_{uuid4().hex}', 'contract_versions': deepcopy(VERSIONS), **data})
        Draft202012Validator(schema('api')['properties']['response_envelope']).validate(result)
        reject_secrets(result)
        return result

    @classmethod
    def failure(cls, request_id, failure):
        # Never reflect provider messages, validation values or user-controlled paths.
        field = failure.field if failure.field and re.fullmatch(r'[a-zA-Z0-9_.\[\]-]{1,200}', failure.field) else None
        error = dict(
            error_code=failure.code, message=str(failure), request_id=request_id,
            retryable=failure.retryable, field=field)
        if failure.details is not None:
            reject_secrets(failure.details)
            error['details'] = deepcopy(failure.details)
        return cls.envelope(request_id, failure.status, {'error': error})

    @staticmethod
    def authorize(auth, operation):
        validate(auth, 'auth')
        permission, roles = PERMISSIONS[operation]
        if (auth['decision'] != 'allow' or not auth['subject']['subject_id'] or
                not auth['subject']['workspace_id'] or not roles.intersection(auth['roles']) or
                permission not in auth['permissions']):
            raise ApiFailure('OPERATION_NOT_AUTHORIZED', 'Your session cannot perform this operation.', 403)

    def handle(self, request, auth, read_cursor=None):
        request_id = f'req_{uuid4().hex}'
        try:
            reject_secrets(request)
            Draft202012Validator(schema('api')['properties']['request_envelope']).validate(request)
            candidate = request['request_id']
            if not re.fullmatch(r'[a-zA-Z0-9_-]{1,128}', candidate):
                raise ApiFailure('INVALID_REQUEST', 'Use a safe request identifier.', field='request_id')
            request_id = candidate
            operation = request['operation']
            if operation not in PERMISSIONS:
                raise ApiFailure('INVALID_OPERATION', 'The API operation is not supported.', field='operation')
            self.authorize(auth, operation)
            payload = request['payload']
            if any(key in payload for key in ('auth_context', 'roles', 'scopes', 'permissions', 'subject', 'credential_reference', 'authorization_reference')):
                raise ApiFailure('UNTRUSTED_AUTHORITY', 'Authority must come from the server session.')
            if operation in {'execute_workflow', 'get_run', 'list_run_events', 'decide_approval'}:
                if self.runtime_runner is None:
                    raise ApiFailure('SERVICE_UNAVAILABLE', 'The runtime and approval service is not connected.', 503, retryable=True)
                runtime = self.runtime_runner.runtime
                if operation == 'execute_workflow':
                    run = runtime.create_run(request, auth)
                    if not getattr(self,'background_execution',False):
                        run = self.runtime_runner.advance(run['run_id'], auth)
                    data = {'run': run}
                elif operation == 'get_run':
                    data = {'run': runtime.get_run(payload.get('run_id'), auth)}
                elif operation == 'list_run_events':
                    data = runtime.events(payload.get('run_id'), auth)
                else:
                    run = self.runtime_runner.decide(request, auth)
                    if run['status'] == 'running' and not getattr(self,'background_execution',False):
                        with self.store.transaction(write=False) as db:
                            execution_subject = db.execute(
                                'SELECT subject FROM runtime_runs WHERE workspace=? AND run_id=?',
                                (auth['subject']['workspace_id'], run['run_id'])).fetchone()
                        # Approval authority is not execution authority. Automation
                        # resumes through the worker's fresh identity resolver.
                        if (execution_subject and execution_subject[0] == auth['subject']['subject_id'] and
                                'workflow.execute' in auth['permissions'] and {'admin', 'builder'} & set(auth['roles'])):
                            run = self.runtime_runner.advance(run['run_id'], auth)
                    data = next(a for a in run['approvals'] if a['approval_id'] == payload['approval_id'])
                return self.envelope(request_id, 200, data)
            if operation == 'list_runs':
                if self.runtime_runner is None:
                    raise ApiFailure('SERVICE_UNAVAILABLE', 'The runtime and approval service is not connected.', 503, retryable=True)
                return self.envelope(request_id, 200, self.runtime_runner.runtime.list_runs(auth, payload.get('limit', 100), payload.get('status')))
            if operation == 'list_approvals':
                if self.runtime_runner is None:
                    raise ApiFailure('SERVICE_UNAVAILABLE', 'The runtime and approval service is not connected.', 503, retryable=True)
                return self.envelope(request_id, 200, self.runtime_runner.runtime.list_approvals(auth, payload.get('pending_only', False), payload.get('limit', 100)))
            if operation in {'list_tools', 'list_capabilities'}:
                return self.registry.handle(request, auth)
            if operation == 'plan_workflow':
                trusted = deepcopy(request)
                trusted['payload']['auth_context'] = {
                    **auth['subject'], 'roles': auth['roles'], 'permissions': auth['permissions']}
                from .source_context import planning_context
                result = self.planner.plan(trusted, context_resolver=lambda context: planning_context(self.store, auth, context))
                if result['status'] >= 400:
                    error = result.get('error') or (result.get('data') or {}).get('error') or {}
                    code = error.get('error_code', 'PLANNER_PROVIDER_FAILED')
                    safe = {'VALIDATION_FAILED': 'Enter a non-empty process description.',
                            'IDEMPOTENCY_KEY_REUSED': 'This retry key belongs to a different planning request.',
                            'SENSITIVE_DATA_DETECTED': 'Remove secret material from the planning request.',
                            'PLANNER_OUTPUT_UNSAFE': 'The planner generated unsafe metadata. No draft was saved. Try generating again.'}
                    safe['PROCUREMENT_SOURCE_REQUIRED'] = 'No accessible requirements spreadsheet was identified. Include its link or save it as a workspace source. To start from an idea, ask to generate a new BOQ first.'
                    safe.update(PLANNER_PROVIDER_TIMEOUT='Workflow generation timed out. Retry generation.',
                                PLANNER_PROVIDER_UNAVAILABLE='The model connection is unavailable. Retry generation.',
                                PLANNER_RATE_LIMITED='The model provider rate limit was reached. Retry later.',
                                PLANNER_OUTPUT_INVALID='The generated workflow needs corrections before it can be saved. Retry generation.')
                    return self.failure(request_id, ApiFailure(code, safe.get(code, 'The planner could not produce a valid draft.'),
                        result['status'], error.get('field'), bool(error.get('retryable')),
                        {'requirements': error['details']['requirements']} if code == 'PLANNER_OUTPUT_INVALID' and isinstance(error.get('details', {}).get('requirements'), list) else {}))
                result = deepcopy(result)
                self.replace_deleted_plan(result['data']['workflow'], auth['subject']['workspace_id'])
                validate_workflow(result['data']['workflow'])
                reject_secrets(result)
                return self.envelope(result['request_id'], 200, result['data'])
            workspace = auth['subject']['workspace_id']
            if operation in {'get_workflow', 'list_workflows'}:
                with self.store.transaction(write=False) as db:
                    if operation == 'list_workflows':
                        from .workflow_pages import read_page
                        return self.envelope(request_id, 200, read_page(self.store, workspace, read_cursor, connection=db))
                    deleted = db.execute('SELECT 1 FROM lifecycle_tombstones WHERE workspace=? AND workflow_id=?',
                                         (workspace, payload.get('workflow_id'))).fetchone()
                    workflow = (None if deleted and payload.get('workflow_version') is None else
                                self.store.get(db, workspace, payload.get('workflow_id'), payload.get('workflow_version')))
                    if not workflow:
                        raise ApiFailure('WORKFLOW_NOT_FOUND', 'This workflow revision was not found.', 404)
                    return self.envelope(request_id, 200, self.document_data(workflow, auth))
            key = request.get('idempotency_key', '')
            if not isinstance(key, str) or len(key) < 8 or len(key) > 128:
                raise ApiFailure('INVALID_IDEMPOTENCY_KEY', 'A retry key of 8–128 characters is required.', field='idempotency_key')
            fingerprint = hashlib.sha256(json.dumps({'operation': operation, 'payload': payload}, sort_keys=True).encode()).hexdigest()
            subject = auth['subject']['subject_id']
            with self.store.transaction() as db:
                old = db.execute('SELECT fingerprint, response FROM mutations WHERE workspace=? AND subject=? AND key=?', (workspace, subject, key)).fetchone()
                if old:
                    if old[0] != fingerprint:
                        raise ApiFailure('IDEMPOTENCY_KEY_REUSED', 'This retry key belongs to a different mutation.', 409)
                    return json.loads(old[1])
                result = self.mutate(db, workspace, operation, payload, auth, request_id)
                db.execute('INSERT INTO mutations VALUES (?, ?, ?, ?, ?)', (workspace, subject, key, fingerprint, json.dumps(result)))
                return result
        except RuntimeFailure as exc:
            return self.failure(request_id, ApiFailure(exc.code, str(exc), exc.status))
        except ApiFailure as exc:
            return self.failure(request_id, exc)
        except RegistryError as exc:
            return self.failure(request_id, ApiFailure(exc.code, 'The request does not meet the authorization or data contract.', exc.status, exc.field))
        except PlannerFailure as exc:
            return self.failure(request_id, ApiFailure(exc.code, 'Correct the workflow fields before continuing.', 400, exc.field))
        except DatabaseFailure as exc:
            codes={'contention':'API_DATABASE_BUSY','serialization':'API_DATABASE_SERIALIZATION_RETRY','deadlock':'API_DATABASE_DEADLOCK','transaction_state':'API_DATABASE_TRANSACTION_INVALID','unavailable':'API_DATABASE_UNAVAILABLE'}
            return self.failure(request_id,ApiFailure(codes.get(exc.category,'INVALID_API_DATA'),
                'The database transaction could not complete. Check the current state before retrying.',503 if exc.retryable else 500,retryable=exc.retryable))
        except sqlite3.OperationalError as exc:
            if sqlite_category(exc)=='contention':
                return self.failure(request_id, ApiFailure('API_DATABASE_BUSY',
                    'The workflow database is busy. Retry shortly.', 503, retryable=True))
            if sqlite_category(exc)=='transaction_state':
                return self.failure(request_id,ApiFailure('API_DATABASE_TRANSACTION_INVALID','The database transaction is invalid.',500))
            logging.warning("Workflow database error request_id=%s category=%s",request_id,sqlite_category(exc))
            return self.failure(request_id, ApiFailure('INVALID_API_DATA', 'The workflow database could not process the request.', 500))
        except Exception:
            logging.exception("Unhandled workflow API error request_id=%s", request_id)
            return self.failure(request_id, ApiFailure('INVALID_API_DATA', 'The API could not process valid, safe data.', 400))

    def document_data(self, workflow, auth=None):
        data = {'workflow': workflow, 'workflow_id': workflow['workflow_id'],
                'workflow_version': workflow['version'], 'status': workflow['status'],
                'validation_state': workflow.get('metadata', {}).get('validation_state', 'not_validated')}
        if auth is not None:
            data['registry_review'] = self.registry_adapter.review(workflow, auth)
        return data

    @staticmethod
    def validate_document(workflow):
        validate_workflow(workflow)
        for node in workflow['nodes']:
            configuration = node.get('configuration', {})
            if set(configuration) - {'ui', 'description', 'input', 'input_mapping', 'on_timeout', 'timeout_outcome', 'error_outcome'}:
                raise PlannerFailure('UNSUPPORTED_EXECUTION_CONFIGURATION', 'Use the supported node input mappings.', field='nodes.configuration')
            if node['kind'] == 'tool' and not node.get('agent_id'):
                raise PlannerFailure('AGENT_REGISTRATION_REQUIRED', 'Tool nodes require a registered execution agent.', field='nodes.agent_id')
            if node['kind'] == 'agent':
                agent = next(item for item in workflow['agents'] if item['agent_id'] == node['agent_id'])
                if agent['limits']['max_llm_calls'] < 1:
                    raise PlannerFailure('BUDGET_EXHAUSTED', 'Model agent nodes require a model-call budget.', field='agents.limits.max_llm_calls')
            if 'input_mapping' in configuration:
                from runtime.expressions import validate_expression
                for expression in configuration['input_mapping'].values():
                    try:
                        validate_expression(expression)
                    except RuntimeFailure:
                        raise PlannerFailure('UNSUPPORTED_EXECUTION_CONFIGURATION', 'Use restricted expressions in node input mappings.', field='nodes.configuration.input_mapping') from None
            ui = node.get('configuration', {}).get('ui', {})
            if isinstance(ui, dict) and any(ui.get(key) for key in ('role', 'parentNodeId', 'combine')):
                raise PlannerFailure('UNSUPPORTED_EXECUTION_CONFIGURATION', 'Hierarchy execution mapping requires downstream review.', field='nodes.configuration.ui')
        required_inputs = {item['name'] for item in workflow['inputs'] if item['required']}
        for trigger in workflow.get('metadata', {}).get('trigger_templates', []):
            from .lifecycle import LifecycleService, LifecycleFailure
            for mapping in trigger.get('input_mapping', {}).values():
                try:
                    if isinstance(mapping, str):
                        LifecycleService.event_path(mapping)
                    elif not (isinstance(mapping, dict) and set(mapping) == {'constant'}):
                        raise LifecycleFailure('EVENT_MAPPING_FAILED', 'Unsupported event mapping.', 400)
                except LifecycleFailure:
                    raise PlannerFailure('EVENT_MAPPING_FAILED', 'Use event data paths or explicit constants.', field='metadata.trigger_templates.input_mapping') from None
            if required_inputs - set(trigger.get('input_mapping', {})):
                raise PlannerFailure('TRIGGER_INPUT_MAPPING_REQUIRED', 'Map every required workflow input from the trigger event.', field='metadata.trigger_templates.input_mapping')
            if trigger.get('provider_id') == 'google_sheets' and trigger.get('event_type') == 'row.created':
                poll_input = trigger.get('poll_input', {})
                if not poll_input.get('identity_field') or not poll_input.get('range'):
                    raise PlannerFailure('TRIGGER_ROW_IDENTITY_REQUIRED', 'Configure the stable row identity column and Sheet range.', field='metadata.trigger_templates.poll_input')

    def replace_deleted_plan(self, workflow, workspace):
        """Keep tombstoned history immutable; the same prompt can start a new draft."""
        previous = workflow['workflow_id']
        with self.store.transaction(write=False) as db:
            while True:
                deleted = db.execute('SELECT deleted_at FROM lifecycle_tombstones WHERE workspace=? AND workflow_id=?',
                    (workspace, workflow['workflow_id'])).fetchone()
                if not deleted:
                    break
                identity = f"{workspace}:{workflow['workflow_id']}:{deleted[0]}"
                workflow['workflow_id'] = 'planned_' + hashlib.sha256(identity.encode()).hexdigest()[:16]
        if workflow['workflow_id'] != previous:
            PlannerService._scope_planned_agents(workflow, previous_workflow_id=previous)

    def mutate(self, db, workspace, operation, payload, auth, request_id):
        workflow_id = payload.get('workflow_id')
        current = self.store.get(db, workspace, workflow_id)
        if operation == 'save_workflow_version':
            workflow = deepcopy(payload.get('workflow'))
            validate(workflow, 'workflow')
            # Canonical fields survive saving. Executable authority never comes from edits.
            if workflow['workflow_id'] != workflow_id or workflow['status'] != 'draft' or payload.get('workflow_version') != workflow['version']:
                raise ApiFailure('INVALID_REVISION', 'Save an editable draft with the matching workflow ID.', field='workflow.status')
            base = payload.get('base_version')
            expected = current['version'] if current else 0
            if type(base) is not int or base != expected or workflow['version'] != expected + 1:
                raise ApiFailure('REVISION_CONFLICT', 'A newer revision exists. Reload it before saving.', 409, 'workflow.version')
            workflow, _ = self.registry_adapter.resolve_draft(workflow, auth)
            if any(agent['allowed_tool_ids'] for agent in workflow['agents']) or any('configuration_reference' in tool for tool in workflow['tools']):
                raise ApiFailure('UNTRUSTED_ASSIGNMENT', 'Executable assignments must be supplied by the trusted registry.', 403)
            workflow['metadata'].pop('validation_state', None)
            workflow['metadata'].pop('approved_by', None)
            workflow['metadata'].pop('approval_submission', None)
            workflow['metadata']['updated_at'] = datetime.fromtimestamp(self.lifecycle.clock(),timezone.utc).isoformat()
            workflow['metadata'].pop('registry_review', None)
            workflow['metadata']['workspace_id'] = workspace
            workflow['metadata']['validation_state'] = 'not_validated'
            self.store.put(db, workspace, workflow)
            return self.envelope(request_id, 200, self.document_data(workflow, auth))
        if not current or payload.get('workflow_version') != current['version']:
            raise ApiFailure('REVISION_CONFLICT', 'Use the current saved revision.', 409, 'workflow_version')
        workflow = deepcopy(current)
        if operation == 'validate_workflow':
            if workflow['status'] not in {'draft', 'validated'}:
                raise ApiFailure('INVALID_TRANSITION', 'This revision cannot be validated again.', 409)
            try:
                self.validate_document(workflow)
                if getattr(self, 'configuration_validator', None):
                    self.configuration_validator(workflow)
                # A structurally valid draft may still lack executable tool assignments.
                workflow['status'] = 'validated'
                workflow['metadata']['validation_state'] = 'validated'
            except PlannerFailure as exc:
                # Lifecycle failure is metadata because workflow-schema-v1 excludes validation_failed.
                workflow['status'] = 'draft'
                workflow['metadata']['validation_state'] = 'validation_failed'
                self.store.put(db, workspace, workflow)
                return self.failure(request_id, ApiFailure(exc.code, 'Correct the workflow graph before continuing.', 400, exc.field))
        elif operation == 'approve_workflow':
            action = payload.get('action', 'approve')
            if action not in {'approve', 'publish'}:
                raise ApiFailure('INVALID_REQUEST', 'Choose approve or publish.', field='action')
            if action == 'publish' and 'workflow.publish' not in auth['permissions']:
                raise ApiFailure('OPERATION_NOT_AUTHORIZED', 'Your session cannot publish workflows.', 403)
            expected = 'validated' if action == 'approve' else 'approved'
            if workflow['status'] != expected:
                raise ApiFailure('INVALID_TRANSITION', f'The revision must be {expected} first.', 409)
            self.validate_document(workflow)
            if getattr(self, 'configuration_validator', None):
                self.configuration_validator(workflow)
            if action == 'approve':
                # Reconcile older validated drafts with the current trusted
                # registry before reviewing them. This lets an existing draft
                # recover after a configured planner capability becomes
                # resolvable, without accepting browser-supplied grants.
                workflow, _ = self.registry_adapter.resolve_draft(workflow, auth)
                self.validate_document(workflow)
                self.registry_adapter.approve_pending(workflow, auth)
            review = self.registry_adapter.review(workflow, auth)
            if not review['ready']:
                code = 'AGENT_REGISTRATION_REQUIRED' if not workflow['tools'] and 'AGENT_REGISTRATION_REQUIRED' in review['reason_codes'] else 'TOOL_ASSIGNMENT_REQUIRED'
                requirements = []
                for item in workflow['metadata'].get('unresolved_requirements', [])[:30]:
                    if isinstance(item, str):
                        requirements.append(item[:500])
                    elif isinstance(item, dict):
                        if item.get('reason') == 'condition_mapping_required':
                            requirements.append('Configure a reviewed condition/event mapping before publication.')
                        elif isinstance(item.get('requirement'), str):
                            requirements.append('Resolve requirement: ' + item['requirement'][:200])
                if not self.registry_adapter.auto_resolve_planner and (workflow['agents'] or workflow['tools']):
                    requirements.append('Load trusted agent/tool registrations with BUILDER_REGISTRY_CONFIG before publication.')
                raise ApiFailure(code, 'Publication needs the setup requirements listed below.', 409,
                    details={'requirements': list(dict.fromkeys(requirements)), 'reason_codes': review['reason_codes']})
            workflow['status'] = 'approved' if action == 'approve' else 'published'
            assignments = self.registry_adapter.execution_assignments(workflow, auth)
            for agent in workflow['agents']:
                agent['allowed_tool_ids'] = sorted({grant['tool_id'] for grant in assignments if grant['agent_id'] == agent['agent_id']})
            if action == 'approve':
                workflow['metadata']['approved_by'] = auth['subject']['subject_id']
        self.store.put(db, workspace, workflow)
        return self.envelope(request_id, 200, self.document_data(workflow, auth))
