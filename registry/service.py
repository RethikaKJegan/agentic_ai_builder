"""Workspace-scoped registry service boundaries and auditable assignments.

Authentication, policies, credentials and approval evidence are supplied by the
trusted server adapter, never copied from planner/request payloads. No external
connector or model calls are made here.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import re
from threading import RLock
import time
from uuid import uuid4

from jsonschema import Draft202012Validator
from .agents import PLANNER_CAPABILITIES, planner_requirements, validate_agent
from .contracts import RegistryError, VERSIONS, schema, validate, validate_json_schema
from .matching import compatible
from .policy import authorize_subject, authorize_tool
from .safety import reject_secrets


def timestamp():
    return datetime.now(timezone.utc).isoformat()


class RegistryService:
    def __init__(self, policy):
        self._policy = deepcopy(policy)
        self._agents, self._tools, self._assignments = {}, {}, {}
        self._decisions = []
        self._lock = RLock()

    def _catalog(self):
        return PLANNER_CAPABILITIES | {record['definition']['capability'] for record in self._tools.values()}

    def _respond(self, auth, permission, operation, request_id=None):
        request_id = request_id or f'req_{uuid4().hex}'
        correlation_id = f'corr_{uuid4().hex}'
        with self._lock:
            try:
                reject_secrets(request_id)
                if not isinstance(request_id, str) or not request_id:
                    raise RegistryError('INVALID_REQUEST', 'A request ID must be a nonempty string.')
                authorize_subject(auth, self._policy, permission)
                data = operation()
                result = {'request_id': request_id, 'status': 200,
                          'data': {**data, 'correlation_id': correlation_id, 'contract_versions': deepcopy(VERSIONS)}}
                reason = data.get('authorization_state', 'allow')
            except RegistryError as exc:
                # Untrusted request identifiers cannot be reflected into errors.
                try:
                    reject_secrets(request_id)
                    if not isinstance(request_id, str) or not request_id:
                        request_id = f'req_{uuid4().hex}'
                except RegistryError:
                    request_id = f'req_{uuid4().hex}'
                result = {'request_id': request_id, 'status': exc.status,
                          'data': {'error': exc.envelope(request_id), 'correlation_id': correlation_id,
                                   'contract_versions': deepcopy(VERSIONS)}}
                reason = exc.code
            self._decisions.append({
                'request_id': request_id, 'correlation_id': correlation_id,
                'workspace_id': self._policy.workspace_id, 'policy_version': self._policy.version,
                'subject_id': auth.get('subject', {}).get('subject_id') if isinstance(auth, dict) and isinstance(auth.get('subject'), dict) else None,
                'reason_code': reason, 'status': result['status'], 'timestamp': timestamp(),
                'contract_versions': deepcopy(VERSIONS),
                'agent_versions': {key: records[-1]['version'] for key, records in self._agents.items()},
                'tool_versions': {key: record['version'] for key, record in self._tools.items()},
                'policy_inputs': {'roles': auth.get('roles', []) if isinstance(auth, dict) else [],
                                  'permissions': auth.get('permissions', []) if isinstance(auth, dict) else [],
                                  'scopes': auth.get('scopes', []) if isinstance(auth, dict) else []},
                'assignment': deepcopy(result['data'].get('assignment')),
                'error_details': deepcopy(result['data'].get('error', {}).get('details', {})),
            })
            # A denied subject may contain a secret in its identity; do not log it.
            try:
                reject_secrets(self._decisions[-1])
            except RegistryError:
                self._decisions[-1]['subject_id'] = None
                self._decisions[-1]['policy_inputs'] = {}
            Draft202012Validator(schema('api')['properties']['response_envelope']).validate(result)
            return deepcopy(result)

    def register_agent(self, definition, auth, request_id=None):
        def operation():
            agent = validate_agent(definition, self._policy, self._catalog())
            records = self._agents.setdefault(agent['agent_id'], [])
            record = dict(definition=agent, version=len(records) + 1,
                          workspace_id=self._policy.workspace_id, owner_subject_id=auth['subject']['subject_id'],
                          updated_at=timestamp(), policy_version=self._policy.version)
            records.append(record)
            return {'agent': deepcopy(record)}
        return self._respond(auth, 'tools.manage', operation, request_id)

    def register_tool(self, definition, auth, credential_reference=None, request_id=None):
        def operation():
            reject_secrets(definition)
            reject_secrets(credential_reference)
            validate(definition, 'tool')
            for name in ('input_schema', 'output_schema'):
                validate_json_schema(definition[name])
            if any('*' in scope for scope in definition['permission_scopes'] + definition['authentication'].get('scopes', [])):
                raise RegistryError('TOOL_NOT_AUTHORIZED', 'Wildcard tool permissions and scopes are not accepted.', status=403)
            if definition['provider_id'] not in self._policy.approved_providers:
                raise RegistryError('PROVIDER_NOT_AUTHORIZED', 'The provider is not approved.', status=403)
            if credential_reference is not None and (not isinstance(credential_reference, str) or not re.fullmatch(r'cred_[a-zA-Z0-9_-]{3,128}', credential_reference)):
                raise RegistryError('INVALID_CREDENTIAL_REFERENCE', 'Only opaque credential IDs are accepted.')
            if credential_reference:
                credential = self._policy.credential_references.get(credential_reference)
                scopes = set(definition['permission_scopes']) | set(definition['authentication'].get('scopes', []))
                if not credential or credential['provider_id'] != definition['provider_id'] or scopes - set(credential['scopes']):
                    raise RegistryError('CREDENTIAL_NOT_CONFIGURED', 'Credential provider or scopes do not match.', status=403)
            tool_id = definition['tool_id']
            old = self._tools.get(tool_id)
            record = dict(definition=deepcopy(definition), version=old['version'] + 1 if old else 1,
                          workspace_id=self._policy.workspace_id, credential_reference=credential_reference,
                          updated_at=timestamp(), policy_version=self._policy.version)
            self._tools[tool_id] = record
            return {'tool': deepcopy(record)}
        return self._respond(auth, 'tools.manage', operation, request_id)

    def consume_planner(self, response, auth, request_id=None):
        return self._respond(auth, 'tools.assign', lambda: {'requirements': planner_requirements(
            response, {key: record['definition'] for key, record in self._tools.items()})}, request_id)

    def list_capabilities(self, auth, request_id=None):
        def operation():
            items = [{'capability': capability, 'registered_tool_ids': sorted(
                tool_id for tool_id, record in self._tools.items()
                if record['definition']['capability'] == capability and self._can_view(record, auth))}
                for capability in sorted(self._catalog())]
            return dict(items=items, has_more=False, next_cursor=None, total=len(items))
        return self._respond(auth, 'tools.read', operation, request_id)

    def _can_view(self, record, auth):
        tool = record['definition']
        required = set(tool['permission_scopes'])
        scopes = required | set(tool['authentication'].get('scopes', []))
        return not (required - set(auth['permissions']) or scopes - set(auth['scopes']))

    def list_tools(self, auth, request_id=None):
        def operation():
            items = []
            for tool_id, record in sorted(self._tools.items()):
                if self._can_view(record, auth):
                    items.append(dict(tool_id=tool_id, definition=deepcopy(record['definition']),
                        version=record['version'], updated_at=record['updated_at'],
                        workspace_id=record['workspace_id'],
                        credential_configured=record['credential_reference'] in self._policy.credential_references,
                        authorization_state='requires_assignment'))
            return dict(items=items, has_more=False, next_cursor=None, total=len(items))
        return self._respond(auth, 'tools.read', operation, request_id)

    def assign(self, agent_id, capability, input_schema, output_schema, auth,
               workflow_id, workflow_version, destination=None, tool_id=None, request_id=None):
        def operation():
            reject_secrets([agent_id, capability, input_schema, output_schema, workflow_id, destination, tool_id])
            if (not isinstance(agent_id, str) or not isinstance(capability, str) or
                (tool_id is not None and not isinstance(tool_id, str)) or
                (destination is not None and not isinstance(destination, str))):
                raise RegistryError('INVALID_REQUEST', 'Assignment identifiers and destination must be strings.')
            validate_json_schema(input_schema)
            validate_json_schema(output_schema)
            if not isinstance(workflow_id, str) or not re.fullmatch(r'[a-z][a-z0-9_-]{2,127}', workflow_id) or type(workflow_version) is not int or workflow_version < 1:
                raise RegistryError('INVALID_WORKFLOW_REFERENCE', 'A valid workflow ID and revision are required.')
            records = self._agents.get(agent_id)
            if not records:
                raise RegistryError('AGENT_NOT_FOUND', 'The agent is not registered in this workspace.', status=404)
            agent_record = records[-1]
            agent = validate_agent(agent_record['definition'], self._policy, self._catalog())
            if capability not in agent['capabilities']:
                raise RegistryError('UNASSIGNED_CAPABILITY', 'The capability is outside the agent responsibility.', status=403)
            eligible, excluded = [], []
            for candidate_id, record in sorted(self._tools.items()):
                tool = record['definition']
                if tool['capability'] != capability or (tool_id is not None and tool_id != candidate_id):
                    continue
                try:
                    if not compatible(tool, input_schema, output_schema):
                        raise RegistryError('SCHEMA_INCOMPATIBLE', 'Tool input/output schemas do not satisfy the requested assignment.')
                    authorize_tool(tool, agent, auth, self._policy, record['credential_reference'], destination)
                    eligible.append(record)
                except RegistryError as exc:
                    excluded.append({'tool_id': candidate_id, 'reason_code': exc.code, 'details': exc.details})
            if not eligible:
                raise RegistryError('NO_ELIGIBLE_TOOL', 'No authorized tool satisfies the requested capability.',
                                    details={'excluded_candidates': excluded}, status=403)
            record = eligible[0]
            tool = record['definition']
            binding = dict(subject_id=auth['subject']['subject_id'], workspace_id=self._policy.workspace_id,
                agent_id=agent_id, agent_version=agent_record['version'], tool_id=tool['tool_id'], tool_version=record['version'],
                workflow_id=workflow_id, workflow_version=workflow_version, policy_version=self._policy.version,
                credential_reference=record['credential_reference'], destination=destination,
                input_schema=deepcopy(input_schema), output_schema=deepcopy(output_schema))
            fingerprint = hashlib.sha256(json.dumps(binding, sort_keys=True).encode()).hexdigest()
            approval_required = tool['approval_required'] or bool(agent['approval_requirements'])
            grant = self._policy.approval_grants.get(fingerprint)
            approved = False
            if grant and grant.get('expires_at', 0) > time.time() and grant.get('reference'):
                approver = grant.get('approver')
                try:
                    authorize_subject(approver, self._policy, 'workflow.approve')
                    approved = bool(set(approver['roles']) & self._policy.approval_roles) and not (
                        (set(tool['permission_scopes']) | set(tool['authentication'].get('scopes', []))) - set(approver['scopes']))
                except RegistryError:
                    approved = False
            state = 'pending_approval' if approval_required and not approved else 'authorized'
            assignment = {**binding, 'authorization_state': state, 'approval_required': approval_required,
                'approval_requirements': deepcopy(agent['approval_requirements']),
                'approval_fingerprint': fingerprint, 'approval_reference': grant['reference'] if approved else None,
                'authorization_reference': f'authz_{uuid4().hex}' if state == 'authorized' else None,
                'assigned_tool_ids': [tool['tool_id']] if state == 'authorized' else [],
                'required_scopes': sorted(set(tool['permission_scopes']) | set(tool['authentication'].get('scopes', []))),
                'created_at': timestamp()}
            if state == 'authorized':
                self._assignments[assignment['authorization_reference']] = deepcopy(assignment)
            return dict(assignment=assignment, authorization_state=state, excluded_candidates=excluded)
        return self._respond(auth, 'tools.assign', operation, request_id)

    def revalidate_assignment(self, reference, agent_id, tool_id, workflow_id, workflow_version, auth, request_id=None):
        """Registry-only authorization check; consumers call this before tool use."""
        def operation():
            reject_secrets([reference, agent_id, tool_id, workflow_id])
            if not all(isinstance(value, str) for value in (reference, agent_id, tool_id, workflow_id)) or type(workflow_version) is not int:
                raise RegistryError('INVALID_REQUEST', 'Assignment references are invalid.')
            grant = self._assignments.get(reference)
            if not grant or any(grant[name] != value for name, value in (
                ('agent_id', agent_id), ('tool_id', tool_id), ('workflow_id', workflow_id),
                ('workflow_version', workflow_version), ('subject_id', auth['subject']['subject_id']))):
                raise RegistryError('UNASSIGNED_TOOL', 'This tool is not assigned to this agent, subject, and workflow.', status=403)
            records = self._agents.get(agent_id)
            record = self._tools.get(tool_id)
            if (not records or not record or records[-1]['version'] != grant['agent_version'] or
                record['version'] != grant['tool_version'] or self._policy.version != grant['policy_version']):
                raise RegistryError('STALE_ASSIGNMENT', 'Registry or policy revision changed; request a new assignment.', status=403)
            agent = validate_agent(records[-1]['definition'], self._policy, self._catalog())
            authorize_tool(record['definition'], agent, auth, self._policy, record['credential_reference'], grant['destination'])
            if grant['approval_required']:
                approval = self._policy.approval_grants.get(grant['approval_fingerprint'])
                if not approval or approval.get('expires_at', 0) <= time.time() or approval.get('reference') != grant['approval_reference']:
                    raise RegistryError('APPROVAL_REQUIRED', 'The assignment approval expired or was revoked.', status=403)
                authorize_subject(approval.get('approver'), self._policy, 'workflow.approve')
                if (not set(approval['approver']['roles']) & self._policy.approval_roles or
                    set(grant['required_scopes']) - set(approval['approver']['scopes'])):
                    raise RegistryError('APPROVAL_REQUIRED', 'The approval role is no longer authorized.', status=403)
            return dict(assignment=deepcopy(grant), authorization_state='authorized')
        return self._respond(auth, 'tools.assign', operation, request_id)

    def update_policy(self, policy, auth, request_id=None):
        def operation():
            if policy.workspace_id != self._policy.workspace_id or policy.version <= self._policy.version:
                raise RegistryError('INVALID_POLICY_REVISION', 'Policy revisions must advance within the same workspace.')
            self._policy = deepcopy(policy)
            return {'policy_version': policy.version}
        return self._respond(auth, 'tools.manage', operation, request_id)

    def decision_records(self, auth, request_id=None):
        return self._respond(auth, 'tools.manage', lambda: {'items': deepcopy(self._decisions)}, request_id)

    def handle(self, request, auth):
        """Accepted discovery request envelope; auth is a separate trusted input."""
        def operation():
            reject_secrets(request)
            errors = list(Draft202012Validator(schema('api')['properties']['request_envelope']).iter_errors(request))
            if errors:
                raise RegistryError('INVALID_REQUEST', 'The registry request envelope is invalid.')
            if request['operation'] not in {'list_tools', 'list_capabilities'}:
                raise RegistryError('INVALID_OPERATION', 'Only registry discovery operations are supported here.')
            result = self.list_tools(auth) if request['operation'] == 'list_tools' else self.list_capabilities(auth)
            return {key: value for key, value in result['data'].items() if key not in {'correlation_id', 'contract_versions'}}
        request_id = request.get('request_id') if isinstance(request, dict) else None
        return self._respond(auth, 'tools.read', operation, request_id)

    def merge_approval_evidence(self, grants, auth, request_id=None):
        """Add exact reviewed bindings while preserving unrelated unexpired reviews."""
        with self._lock:
            retained = {key: deepcopy(value) for key, value in self._policy.approval_grants.items()
                        if value.get('expires_at', 0) > time.time()}
            if not isinstance(grants, dict):
                return self.update_approval_evidence(grants, auth, request_id)
            retained.update(deepcopy(grants))
            return self.update_approval_evidence(retained, auth, request_id)

    def update_approval_evidence(self, grants, auth, request_id=None):
        """Trusted adapter installs references to approvals decided upstream.

        This does not decide approvals: the upstream approval service supplies
        authenticated approver context, an expiry and the exact binding hash.
        """
        def operation():
            reject_secrets(grants)
            if not isinstance(grants, dict):
                raise RegistryError('INVALID_APPROVAL_EVIDENCE', 'Approval evidence must be a mapping.')
            for fingerprint, grant in grants.items():
                if (not re.fullmatch(r'[a-f0-9]{64}', fingerprint) or not isinstance(grant, dict) or
                    not isinstance(grant.get('reference'), str) or
                    not re.fullmatch(r'approval_[a-zA-Z0-9_-]{3,128}', grant['reference']) or
                    type(grant.get('expires_at')) not in (int, float) or
                    not 0 < grant['expires_at'] < 1e12):
                    raise RegistryError('INVALID_APPROVAL_EVIDENCE', 'Approval evidence is invalid.')
                authorize_subject(grant.get('approver'), self._policy, 'workflow.approve')
                if not set(grant['approver']['roles']) & self._policy.approval_roles:
                    raise RegistryError('APPROVAL_NOT_AUTHORIZED', 'Approval role does not match policy.', status=403)
            self._policy.approval_grants = deepcopy(grants)
            return {'approval_count': len(grants), 'policy_version': self._policy.version}
        return self._respond(auth, 'tools.manage', operation, request_id)
