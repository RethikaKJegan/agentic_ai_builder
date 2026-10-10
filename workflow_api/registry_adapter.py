"""Harihar's transport adapter for Aravind's existing registry service.

Configuration is operator-owned, never a browser payload. No connector calls,
permission inference, or credential retrieval happen here.
"""
from copy import deepcopy
from dataclasses import fields
import json
from pathlib import Path
from threading import RLock
import time

from registry import RegistryService, WorkspacePolicy
from registry.contracts import RegistryError, validate_json_schema
from registry.safety import reject_secrets

ROOT = Path(__file__).resolve().parents[1]
MODEL_ONLY_CAPABILITIES = frozenset({'classify_text', 'generate_report'})


class RegistryAdapter:
    def __init__(self, service, agents=None, bindings=None, auto_resolve_planner=False):
        self.service = service
        self.agents = deepcopy(agents or {})
        self.bindings = deepcopy(bindings or [])
        self._grants = {}
        self._lock = RLock()
        self.auto_resolve_planner = bool(auto_resolve_planner)

    def _management_auth(self, auth):
        """Return server-owned registration authority, never supplied by the draft."""
        return {**deepcopy(auth), 'roles': ['admin'],
                'permissions': sorted(set(auth.get('permissions', [])) | {'tools.manage'}),
                'subject': {'subject_id': 'planner-registry', 'workspace_id': auth['subject']['workspace_id']}}

    @staticmethod
    def _assignment_auth(auth):
        """Use the server-pinned publisher identity for Registry revalidation.

        Automation runs retain their own subject in run records, but a release's
        approved grants are exact to the publisher of that revision.  The
        lifecycle service adds this marker only to its server-owned identity;
        no browser request can supply it.
        """
        origin = auth.get('_registry_assignment_subject')
        subject = auth.get('subject', {})
        if (not isinstance(origin, dict) or
                not isinstance(origin.get('subject_id'), str) or
                origin.get('workspace_id') != subject.get('workspace_id') or
                not isinstance(subject.get('subject_id'), str) or
                not subject['subject_id'].startswith('automation:')):
            return auth
        resolved = deepcopy(auth)
        resolved['subject'] = deepcopy(origin)
        resolved.pop('_registry_assignment_subject', None)
        return resolved

    def _tool_candidates(self, capability, auth):
        response = self.service.list_tools(auth)
        if response['status'] >= 400:
            return []
        candidates = [item for item in response['data'].get('items', [])
                      if item['definition']['capability'] == capability and item['definition']['availability'] == 'enabled']
        risk = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
        return sorted(candidates, key=lambda item: (risk.get(item['definition']['risk_level'], 99),
                                                     bool(item['definition']['approval_required']), item['tool_id']))

    def _ensure_planner_agent(self, workflow_agent, candidates, auth):
        record = self.agents.get(workflow_agent['agent_id'])
        if record and record['workspace_id'] == auth['subject']['workspace_id']:
            return record
        definition = deepcopy(workflow_agent)
        definition['name'] = definition['agent_id'].replace('_', ' ').title()
        definition['retry_policy'] = {'max_retries': definition['limits']['max_retries'], 'backoff_seconds': 1}
        definition['guardrails'] = {'pii_redaction': True, 'prompt_injection_detection': True, 'output_validation': True}
        permission_scopes = {scope for item in candidates for scope in item['definition']['permission_scopes']}
        definition['permissions'] = sorted(set(definition.get('permissions', [])) | permission_scopes)
        # Planner drafts never self-assign executable tools.  The subsequent
        # Registry assignment operation issues the exact, reviewed grants.
        # Reset a persisted projection here so restart reconstruction follows
        # the same registration sequence as first publication.
        definition['allowed_tool_ids'] = []
        if definition['capabilities'] and candidates:
            definition['limits']['max_tool_calls'] = max(1, definition['limits'].get('max_tool_calls', 0))
            candidate_retries = max(item['definition']['retry_policy']['max_retries'] for item in candidates)
            definition['limits']['max_retries'] = max(definition['limits'].get('max_retries', 0), candidate_retries)
            definition['retry_policy']['max_retries'] = definition['limits']['max_retries']
        response = self.service.register_agent(definition, self._management_auth(auth))
        if response['status'] >= 400:
            return None
        record = response['data']['agent']
        self.agents[definition['agent_id']] = deepcopy(record)
        return record

    def resolve_draft(self, workflow, auth):
        """Resolve planner capabilities into a server-owned executable draft."""
        if not self.auto_resolve_planner:
            return deepcopy(workflow), self._review(workflow, auth)
        resolved = deepcopy(workflow)
        unresolved = list(resolved.get('metadata', {}).get('unresolved_requirements', []))
        unresolved_capabilities = {item.get('requirement') for item in unresolved if isinstance(item, dict)}
        selected_tools = {}
        for agent in resolved['agents']:
            candidates = []
            for capability in agent['capabilities']:
                candidates.extend(self._tool_candidates(capability, auth))
            record = self._ensure_planner_agent(agent, candidates, auth)
            if record:
                agent['permissions'] = deepcopy(record['definition']['permissions'])
                agent['limits'] = deepcopy(record['definition']['limits'])
            for tool in resolved['tools']:
                if tool['capability'] not in agent['capabilities']:
                    continue
                candidates = self._tool_candidates(tool['capability'], auth)
                if not candidates:
                    continue
                selected = next((item['definition'] for item in candidates if item['tool_id'] == tool['tool_id']), candidates[0]['definition'])
                old_id = tool['tool_id']
                tool['tool_id'] = selected['tool_id']
                selected_tools[selected['tool_id']] = deepcopy(selected)
                for node in resolved['nodes']:
                    if node.get('kind') == 'tool' and node.get('tool_id') == old_id:
                        node['tool_id'] = selected['tool_id']
                unresolved_capabilities.discard(tool['capability'])
            # These capabilities execute within the registered model agent and
            # intentionally have no connector/tool reference to authorize.
            for capability in agent['capabilities']:
                if capability in MODEL_ONLY_CAPABILITIES:
                    unresolved_capabilities.discard(capability)
        unresolved_mappings = self._materialize_tool_nodes(resolved, selected_tools)
        resolved['metadata']['unresolved_requirements'] = [item for item in unresolved
            if not (isinstance(item, dict) and item.get('requirement') not in unresolved_capabilities)] + unresolved_mappings
        return resolved, self._review(resolved, auth)

    @staticmethod
    def _materialize_tool_nodes(workflow, tool_definitions=None):
        """Add missing executable nodes to provider-generated graphs without changing graph authority."""
        tool_definitions = tool_definitions or {}
        unresolved = []
        workflow_inputs = {field['name'] for field in workflow['inputs']}
        output = next((node for node in workflow['nodes'] if node.get('kind') == 'output' and node['node_id'] == 'workflow_output'), None)
        if output is None:
            output = next((node for node in workflow['nodes'] if node.get('kind') == 'output'), None)
        for index, tool in enumerate(workflow['tools']):
            tool_node = next((node for node in workflow['nodes']
                              if node.get('kind') == 'tool' and node.get('tool_id') == tool['tool_id']), None)
            agent = next((item for item in workflow['agents'] if tool['capability'] in item['capabilities']), None)
            if agent is None:
                continue
            node_id = tool_node['node_id'] if tool_node else f"{tool['capability']}_action"
            if not tool_node and any(node['node_id'] == node_id for node in workflow['nodes']):
                continue
            mapping = {}
            if tool['capability'] == 'read_spreadsheet':
                mapping = {'spreadsheet_id': 'inputs.spreadsheet_id', 'range': 'inputs.range'}
            elif tool['capability'] == 'send_email':
                mapping = {'to': 'inputs.email_to', 'subject': 'inputs.email_subject', 'body': 'inputs.email_body'}
            elif tool['capability'] == 'retrieve_records':
                mapping = {'path': 'inputs.path', 'query': 'inputs.query'}
            elif tool['capability'] == 'send_notification':
                mapping = {'text': 'inputs.notification_text'} if tool['tool_id'] == 'slack_send_notification' else {'path': 'inputs.path', 'body': 'inputs.body'}
            elif tool['capability'] == 'update_spreadsheet':
                mapping = {'spreadsheet_id': 'inputs.spreadsheet_id', 'range': 'inputs.range', 'values': 'inputs.values'}
            definition = tool_definitions.get(tool['tool_id'], {})
            input_schema = definition.get('input_schema', {})
            properties = input_schema.get('properties', {})
            for property_name in properties:
                if property_name not in mapping and property_name in workflow_inputs:
                    mapping[property_name] = f'inputs.{property_name}'
            for property_name in input_schema.get('required', []):
                source = mapping.get(property_name)
                valid_input = isinstance(source, str) and source.startswith('inputs.') and source.split('.', 2)[1] in workflow_inputs
                valid_output = isinstance(source, str) and source.startswith('outputs.') and source.split('.', 2)[1] in {node['node_id'] for node in workflow['nodes']}
                if not (valid_input or valid_output):
                    unresolved.append({'requirement': f'tool_input:{tool["tool_id"]}.{property_name}',
                                       'reason': 'workflow_input_mapping_required'})
            if tool_node:
                tool_node.setdefault('configuration', {})['input_mapping'] = {
                    **mapping, **tool_node.get('configuration', {}).get('input_mapping', {})}
                continue
            node = {'node_id': node_id, 'kind': 'tool', 'label': tool['capability'].replace('_', ' ').title(),
                    'agent_id': agent['agent_id'], 'tool_id': tool['tool_id'], 'configuration': {'input_mapping': mapping}}
            inserted = False
            if agent and any(n.get('kind') == 'approval' for n in workflow['nodes']) and tool['capability'] == 'send_email':
                approval = next(n for n in workflow['nodes'] if n.get('kind') == 'approval')
                edge = next((e for e in workflow['edges'] if e['source'] == approval['node_id'] and e.get('outcome') == 'approved'), None)
                if edge:
                    old_target = edge['target']; edge['target'] = node_id
                    workflow['edges'].append({'edge_id': f'{approval["node_id"]}_to_{node_id}', 'source': node_id, 'target': old_target})
                    inserted = True
            if not inserted and output:
                incoming = next((e for e in workflow['edges'] if e['target'] == output['node_id']), None)
                if incoming:
                    old_source = incoming['source']; incoming['target'] = node_id
                    workflow['edges'].append({'edge_id': f'{node_id}_to_{output["node_id"]}', 'source': node_id, 'target': output['node_id']})
                    inserted = True
            if inserted:
                workflow['nodes'].insert(workflow['nodes'].index(output), node)
        return unresolved

    def approve_pending(self, workflow, auth):
        """Install server-side evidence for a revision approver's exact assignments."""
        if not self.auto_resolve_planner:
            return self._review(workflow, auth)
        pending = {}
        for agent in workflow['agents']:
            for tool in workflow['tools']:
                if tool['capability'] not in agent['capabilities']:
                    continue
                candidates = self._tool_candidates(tool['capability'], auth)
                if not candidates:
                    continue
                definition = candidates[0]['definition']
                destination = next(iter(definition.get('allowed_destinations', [])), None)
                response = self.service.assign(agent['agent_id'], tool['capability'], definition['input_schema'], definition['output_schema'],
                                               auth, workflow['workflow_id'], workflow['version'], destination=destination, tool_id=definition['tool_id'])
                assignment = response['data'].get('assignment')
                if assignment and assignment.get('approval_fingerprint') and assignment['authorization_state'] == 'pending_approval':
                    pending[assignment['approval_fingerprint']] = {
                        'reference': 'approval_' + workflow['workflow_id'] + '_' + str(workflow['version']),
                        'expires_at': time.time() + 86400,
                        'approver': deepcopy(auth),
                    }
        if pending:
            self.service.update_approval_evidence(pending, auth)
        return self._review(workflow, auth)

    def review(self, workflow, auth):
        """Return a secret-free projection; keep executable references server-side."""
        with self._lock:
            return self._review(workflow, self._assignment_auth(auth))

    def _review(self, workflow, auth):
        results, issues = [], []
        refs = {tool['tool_id']: tool for tool in workflow['tools']}
        covered = set()
        if workflow['metadata'].get('unresolved_requirements'):
            issues.append('UNRESOLVED_REQUIREMENTS')
        for agent in workflow['agents']:
            dynamic_bindings = []
            if self.auto_resolve_planner:
                candidates = []
                for capability in agent['capabilities']:
                    candidates.extend(self._tool_candidates(capability, auth))
                record = self._ensure_planner_agent(agent, candidates, auth)
                for capability in agent['capabilities']:
                    ref = next((item for item in workflow['tools'] if item['capability'] == capability), None)
                    candidate = next((item for item in self._tool_candidates(capability, auth)
                                      if ref is None or item['tool_id'] == ref['tool_id']), None)
                    if candidate:
                        definition = candidate['definition']
                        dynamic_bindings.append(dict(workflow_id=workflow['workflow_id'], workflow_version=workflow['version'],
                            agent_id=agent['agent_id'], capability=capability, tool_id=definition['tool_id'],
                            input_schema=deepcopy(definition['input_schema']), output_schema=deepcopy(definition['output_schema']),
                            destination=next(iter(definition.get('allowed_destinations', [])), None)))
            else:
                record = self.agents.get(agent['agent_id'])
            if not record:
                issues.append('AGENT_REGISTRATION_REQUIRED')
                results.append(dict(agent_id=agent['agent_id'], capability=None, tool_id=None,
                                    authorization_state='denied', reason_codes=['AGENT_REGISTRATION_REQUIRED']))
                continue
            definition = record['definition']
            # Embedded workflow definitions must match the accepted registered definition.
            # Only server-issued allowed_tool_ids are excluded from this comparison.
            if record['workspace_id'] != auth['subject']['workspace_id'] or any(
                    definition.get(key) != value for key, value in agent.items() if key != 'allowed_tool_ids'):
                issues.append('AGENT_CONFIGURATION_MISMATCH')
                results.append(dict(agent_id=agent['agent_id'], capability=None, tool_id=None,
                                    authorization_state='denied', reason_codes=['AGENT_CONFIGURATION_MISMATCH']))
                continue
            for capability in agent['capabilities']:
                # Some capabilities are performed by the agent's model alone
                # (for example classify_text or generate_report). Only a
                # capability represented by a workflow tool needs a Registry
                # connector assignment. Treating every model capability as a
                # missing connector made otherwise executable multi-agent
                # workflows impossible to approve.
                ref = next((item for item in workflow['tools'] if item['capability'] == capability), None)
                if ref is None:
                    continue
                bindings = ([b for b in dynamic_bindings if b['capability'] == capability] if self.auto_resolve_planner else [b for b in self.bindings if b['workflow_id'] == workflow['workflow_id']
                            and b['workflow_version'] == workflow['version']
                            and b['agent_id'] == agent['agent_id'] and b['capability'] == capability])
                if not bindings:
                    issues.append('ASSIGNMENT_CONFIGURATION_REQUIRED')
                    results.append(dict(agent_id=agent['agent_id'], capability=capability, tool_id=None,
                                        authorization_state='denied', reason_codes=['ASSIGNMENT_CONFIGURATION_REQUIRED']))
                for binding in bindings:
                    tool_id = binding['tool_id']
                    if tool_id not in refs or refs[tool_id]['capability'] != capability:
                        issues.append('TOOL_REFERENCE_MISMATCH')
                        results.append(dict(agent_id=agent['agent_id'], capability=capability, tool_id=tool_id,
                                            authorization_state='denied', reason_codes=['TOOL_REFERENCE_MISMATCH']))
                        continue
                    cache_key = (auth['subject']['workspace_id'], auth['subject']['subject_id'],
                                 workflow['workflow_id'], workflow['version'], agent['agent_id'], tool_id)
                    grant = self._grants.get(cache_key)
                    if grant:
                        response = self.service.revalidate_assignment(grant['authorization_reference'], agent['agent_id'],
                            tool_id, workflow['workflow_id'], workflow['version'], auth)
                    else:
                        response = self.service.assign(agent['agent_id'], capability, binding['input_schema'],
                            binding['output_schema'], auth, workflow['workflow_id'], workflow['version'],
                            destination=binding.get('destination'), tool_id=tool_id)
                    data = response['data']
                    assignment = data.get('assignment')
                    state = assignment['authorization_state'] if assignment else 'denied'
                    reasons = []
                    if assignment and assignment['agent_version'] != record['version']:
                        state = 'denied'
                        reasons.append('STALE_AGENT_REGISTRATION')
                    if response['status'] >= 400:
                        error = data['error']
                        reasons.append(error['error_code'])
                        reasons.extend(c['reason_code'] for c in error.get('details', {}).get('excluded_candidates', []))
                    if state == 'pending_approval':
                        reasons.append('APPROVAL_REQUIRED')
                    if state == 'authorized':
                        self._grants[cache_key] = deepcopy(assignment)
                        covered.add(tool_id)
                    else:
                        issues.extend(reasons or ['TOOL_ASSIGNMENT_REQUIRED'])
                    results.append(dict(agent_id=agent['agent_id'], agent_version=record['version'], capability=capability,
                        tool_id=tool_id, authorization_state=state, reason_codes=sorted(set(reasons)),
                        tool_version=assignment.get('tool_version') if assignment else None,
                        policy_version=assignment.get('policy_version') if assignment else None,
                        approval_required=assignment.get('approval_required', False) if assignment else False))
        if set(refs) - covered:
            issues.append('TOOL_ASSIGNMENT_REQUIRED')
        review = dict(workflow_id=workflow['workflow_id'], workflow_version=workflow['version'],
                      ready=not issues, items=results, reason_codes=sorted(set(issues)))
        reject_secrets(review)
        return review

    def execution_assignments(self, workflow, auth):
        """Trusted downstream-only boundary; never serialized into UI responses."""
        with self._lock:
            assignment_auth = self._assignment_auth(auth)
            review = self._review(workflow, assignment_auth)
            # Registry authorization records are process-local.  An immutable
            # published release carries server-verified workflow approval, so
            # a restarted process may reconstruct its pending assignment
            # evidence through the same Registry approval path before running
            # an automation.  Ordinary browser/manual execution never has the
            # lifecycle-only marker and cannot take this branch.
            approved_by = workflow.get('metadata', {}).get('approved_by')
            if (not review['ready'] and auth.get('_registry_assignment_subject') and
                    workflow.get('status') == 'published' and
                    workflow.get('metadata', {}).get('validation_state') == 'validated' and
                    isinstance(approved_by, str) and
                    approved_by == assignment_auth.get('subject', {}).get('subject_id')):
                approval_auth = auth.get('_registry_approval_auth')
                if not isinstance(approval_auth, dict) or approval_auth.get('subject') != assignment_auth.get('subject'):
                    # Older releases were created before the full approving
                    # authority was persisted.  Recover it only when this is
                    # the exact publisher named in an already-approved,
                    # immutable release and that authority still has the
                    # approval permission.  This restores Registry's
                    # in-memory evidence after a restart; it does not grant a
                    # new workflow approval or bypass a runtime approval gate.
                    if 'workflow.approve' in assignment_auth.get('permissions', []):
                        approval_auth = deepcopy(assignment_auth)
                        approval_auth['roles'] = sorted(set(approval_auth.get('roles', [])) | {'approver'})
                if isinstance(approval_auth, dict) and approval_auth.get('subject') == assignment_auth.get('subject'):
                    self.approve_pending(workflow, approval_auth)
                    review = self._review(workflow, assignment_auth)
            if not review['ready']:
                raise RegistryError('TOOL_ASSIGNMENT_REQUIRED', 'Assignments are not currently authorized.', status=403)
            prefix = (assignment_auth['subject']['workspace_id'], assignment_auth['subject']['subject_id'], workflow['workflow_id'], workflow['version'])
            return [deepcopy(grant) for key, grant in self._grants.items() if key[:4] == prefix]


def load_registry_config(path):
    """Bootstrap through public registry methods from explicit repository-local JSON.

    A malformed configuration fails startup without reflecting file contents.
    No fixture or example is loaded by default.
    """
    try:
        source = Path(path)
        source = (source if source.is_absolute() else ROOT / source).resolve()
        if not source.is_relative_to(ROOT):
            raise ValueError()
        config = json.loads(source.read_text())
        reject_secrets(config)
        if set(config) - {'policy', 'agents', 'tools', 'bindings', 'subject_permissions', 'subject_scopes', 'operator_permissions', 'auto_resolve_planner'}:
            raise ValueError()
        policy_data = deepcopy(config['policy'])
        if set(policy_data) - {f.name for f in fields(WorkspacePolicy)} or policy_data.get('workspace_id') != 'local-workspace':
            raise ValueError()
        # Workflow approvals belong to Rethika, never operator-created JSON grants.
        if policy_data.get('approval_grants'):
            raise ValueError()
        for field in fields(WorkspacePolicy):
            if field.name not in policy_data:
                continue
            value = policy_data[field.name]
            if field.type is set and (not isinstance(value, list) or any(not isinstance(item, str) for item in value)):
                raise ValueError()
            if field.type is dict and not isinstance(value, dict):
                raise ValueError()
            if field.type is int and (type(value) is not int or value < (1 if field.name in {'version', 'max_tool_timeout_seconds'} else 0)):
                raise ValueError()
            if field.type is float and (type(value) not in (int, float) or value < 0):
                raise ValueError()
            if field.type is str and not isinstance(value, str):
                raise ValueError()
        if policy_data.get('max_risk', 'medium') not in {'low', 'medium', 'high', 'critical'}:
            raise ValueError()
        if any(type(value) is not int or value < 0 for value in policy_data.get('remaining_quota', {}).values()):
            raise ValueError()
        for key in ('agent_permissions', 'approved_providers', 'allowed_destinations', 'approval_roles'):
            if key in policy_data:
                policy_data[key] = set(policy_data[key])
        policy = WorkspacePolicy(**policy_data)
        service = RegistryService(policy)
        server_auth = dict(subject=dict(subject_id='registry-configuration', workspace_id=policy.workspace_id),
                           roles=['admin'], permissions=['tools.manage'], scopes=[], decision='allow')
        def accepted(result, name):
            if result['status'] != 200:
                raise ValueError()
            return result['data'][name]
        for entry in config.get('tools', []):
            if set(entry) - {'definition', 'credential_reference'}:
                raise ValueError()
            accepted(service.register_tool(entry['definition'], server_auth, entry.get('credential_reference')), 'tool')
        agents = {}
        for definition in config.get('agents', []):
            record = accepted(service.register_agent(definition, server_auth), 'agent')
            if definition['agent_id'] in agents:
                raise ValueError()
            agents[definition['agent_id']] = record
        bindings = config.get('bindings', [])
        required = {'workflow_id', 'workflow_version', 'agent_id', 'capability', 'tool_id', 'input_schema', 'output_schema'}
        seen = set()
        for binding in bindings:
            if not required <= set(binding) or set(binding) - (required | {'destination'}):
                raise ValueError()
            if type(binding['workflow_version']) is not int or binding['workflow_version'] < 1:
                raise ValueError()
            validate_json_schema(binding['input_schema'])
            validate_json_schema(binding['output_schema'])
            if any(not isinstance(binding[k], str) or not binding[k] for k in ('workflow_id', 'agent_id', 'capability', 'tool_id')):
                raise ValueError()
            if 'destination' in binding and not isinstance(binding['destination'], str):
                raise ValueError()
            key = tuple(binding[k] for k in ('workflow_id', 'workflow_version', 'agent_id', 'capability', 'tool_id'))
            if key in seen:
                raise ValueError()
            seen.add(key)
        permissions, scopes = config.get('subject_permissions', []), config.get('subject_scopes', [])
        operator_permissions = config.get('operator_permissions', [])
        if not isinstance(permissions, list) or not isinstance(scopes, list):
            raise ValueError()
        if not isinstance(operator_permissions, list) or set(operator_permissions) - {'tools.manage'}:
            raise ValueError()
        if any(not isinstance(v, str) or '*' in v for v in permissions + scopes + operator_permissions):
            raise ValueError()
        # Config may grant connector scopes, never arbitrary lifecycle/management powers.
        if set(permissions) - policy.agent_permissions:
            raise ValueError()
        return RegistryAdapter(service, agents, bindings, auto_resolve_planner=config.get('auto_resolve_planner', False)), permissions + operator_permissions, scopes
    except Exception:
        raise ValueError('Invalid trusted registry configuration. Check its schema, workspace and registrations.') from None
