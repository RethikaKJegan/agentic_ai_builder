"""Persisted DAG execution with fail-closed branch and approval control.

Provider calls happen outside SQLite transactions. An intent is committed first;
interrupted calls block recovery instead of silently repeating an unknown effect.
"""
from copy import deepcopy
import json
import time
from uuid import uuid4
from jsonschema import Draft202012Validator
from registry.safety import reject_secrets
from registry.contracts import RegistryError
from .service import RuntimeFailure, digest
from .expressions import evaluate
from .trace import snapshot
from .handoffs import record_handoffs
from .delegation import DelegationSession


class RetryableInvocation(RuntimeFailure):
    """An adapter-confirmed failure before any external effect was attempted."""



class GraphRunner:
    def __init__(self, runtime, agents=None, connectors=None, direct_write_tools=()):
        self.runtime = runtime
        self.agents, self.connectors = agents, connectors or {}
        self.direct_write_tools = frozenset(direct_write_tools)

    @staticmethod
    def outgoing(workflow, node_id):
        return [edge for edge in workflow['edges'] if edge['source'] == node_id]

    def finish_node(self, db, run, workflow, node, output=None, outcome=None, evidence=None):
        node_id = node['node_id']
        run['node_states'][node_id] = 'completed'
        if output is not None:
            reject_secrets(output)
            run['outputs'][node_id] = output
        edges = self.outgoing(workflow, node_id)
        if outcome is not None and not any(edge.get('outcome') == outcome for edge in edges):
            raise RuntimeFailure('UNMATCHED_BRANCH', 'No declared successor matches the selected outcome.')
        error_outcome = node.get('configuration', {}).get('error_outcome')
        for edge in edges:
            selected = (edge.get('outcome') != error_outcome or error_outcome is None) if outcome is None else edge.get('outcome') == outcome
            run['edge_states'][edge['edge_id']] = 'selected' if selected else 'skipped'
        self.runtime.event(db, run, 'node.completed', {'node_id': node_id, 'invocation_id': run.get('node_invocations', {}).get(node_id), 'output': snapshot(output), 'selected_edges': [e['edge_id'] for e in edges if run['edge_states'][e['edge_id']] == 'selected'], 'next_nodes': [e['target'] for e in edges if run['edge_states'][e['edge_id']] == 'selected'], **({'outcome': outcome} if outcome is not None else {}), **(evidence or {})})
        run.pop('current_node_id', None)
        self.runtime.save(db, run)

    def next_node(self, db, run, workflow):
        while True:
            skipped = False
            for node in workflow['nodes']:
                if node['node_id'] in run['node_states']:
                    continue
                incoming = [edge for edge in workflow['edges'] if edge['target'] == node['node_id']]
                if any(edge['edge_id'] not in run['edge_states'] for edge in incoming):
                    continue
                if not incoming:
                    if node['kind'] != 'trigger':
                        raise RuntimeFailure('UNREACHABLE_EXECUTION_NODE', 'Only trigger nodes may start a graph.')
                    return node
                if any(run['edge_states'][edge['edge_id']] == 'selected' for edge in incoming):
                    return node
                run['node_states'][node['node_id']] = 'skipped'
                for edge in self.outgoing(workflow, node['node_id']):
                    run['edge_states'][edge['edge_id']] = 'skipped'
                self.runtime.event(db, run, 'node.skipped', {'node_id': node['node_id'], 'explanation': 'All incoming paths were skipped in this run.'})
                self.runtime.save(db, run)
                skipped = True
            if not skipped:
                return None

    def fail(self, db, run, code, blocked=False):
        run['error_code'] = code
        node_id = run.get('current_node_id')
        if node_id:
            run['node_states'][node_id] = 'blocked' if blocked else 'failed'
            self.runtime.event(db, run, 'node.failed', {'node_id': node_id, 'invocation_id': run.get('node_invocations', {}).get(node_id), 'error_code': code, 'status': 'blocked' if blocked else 'failed'})
        self.runtime.event(db, run, 'runtime.denied', {'error_code': code})
        self.runtime.transition(db, run, 'blocked' if blocked else 'failed')

    @staticmethod
    def params(node, run):
        configuration = node.get('configuration', {})
        if 'input' in configuration:
            result = deepcopy(configuration['input'])
        elif 'input_mapping' in configuration:
            result = {key: evaluate(path, run['inputs'], run['outputs']) for key, path in configuration['input_mapping'].items()}
        else:
            result = deepcopy(run['inputs'])
        if not isinstance(result, dict):
            raise RuntimeFailure('INVALID_NODE_INPUT', 'Node inputs must be a mapped object.', 400)
        reject_secrets(result)
        return result

    def action_digest(self, node, run):
        """Hash the exact approved action without persisting its input values."""
        return digest({'node_id': node['node_id'], 'kind': node['kind'], 'tool_id': node.get('tool_id'),
                       'agent_id': node.get('agent_id'), 'params': self.params(node, run)})

    def reserve(self, db, run, workflow, agent, amount):
        if set(amount) - {'llm_calls', 'tool_calls', 'tokens', 'retries', 'estimated_cost_usd'}:
            raise RuntimeFailure('INVALID_USAGE', 'The provider reservation contains unsupported usage counters.')
        for key, value in amount.items():
            if type(value) not in (int, float) or value < 0 or value != value or value == float('inf'):
                raise RuntimeFailure('INVALID_USAGE', 'Provider usage must contain finite nonnegative counters.')
        counters = {'llm_calls': 'max_llm_calls', 'tool_calls': 'max_tool_calls', 'tokens': 'max_tokens',
                    'retries': 'max_retries', 'estimated_cost_usd': 'max_estimated_cost_usd'}
        groups = [('workflow', workflow['execution_policy']['limits'])]
        if agent:
            groups.append((agent['agent_id'], agent['limits']))
        for name, limits in groups:
            if name != 'workflow':
                started = run.get('agent_started_at', {}).get(name, self.runtime.clock())
                if self.runtime.clock() - started >= limits['timeout_seconds']:
                    raise RuntimeFailure('AGENT_TIMEOUT', 'The agent execution duration budget is exhausted.')
            usage = run['usage'].get(name, {})
            for key, value in amount.items():
                if usage.get(key, 0) + value > limits.get(counters[key], 0):
                    raise RuntimeFailure('BUDGET_EXHAUSTED', 'The next invocation exceeds an execution budget.')
        for name, _ in groups:
            if name != 'workflow':
                run.setdefault('agent_started_at', {}).setdefault(name, self.runtime.clock())
            usage = run['usage'].setdefault(name, {})
            for key, value in amount.items():
                usage[key] = usage.get(key, 0) + value
        self.runtime.event(db, run, 'budget.reserved', {'counters': amount, 'agent_id': agent['agent_id'] if agent else None})

    def prepare_tool(self, run, workflow, grants, node, auth):
        """Shared exact-binding boundary for graph and delegated connector calls."""
        runtime = self.runtime
        eligible = [g for g in grants if g['tool_id'] == node['tool_id'] and (not node.get('agent_id') or g['agent_id'] == node['agent_id'])]
        if len(eligible) != 1:
            raise RuntimeFailure('TOOL_ISOLATION_DENIED', 'Tool execution requires one exact authorized agent binding.', 403)
        grant = eligible[0]
        agent = next(a for a in workflow['agents'] if a['agent_id'] == grant['agent_id'])
        if grant['tool_id'] not in agent['allowed_tool_ids']:
            raise RuntimeFailure('TOOL_ISOLATION_DENIED', 'The tool is not assigned to this agent.', 403)
        if any(required not in {a['approval_gate_id'] for a in workflow['approval_gates']} for required in agent['approval_requirements']):
            raise RuntimeFailure('APPROVAL_REQUIRED', 'Agent approval requirements are not represented by gates.', 403)
        passed = {a['gate_id'] for a in run.get('approval_evidence', [])}
        if set(agent['approval_requirements']) - passed:
            raise RuntimeFailure('APPROVAL_REQUIRED', 'The assigned agent requires an approved gate.', 403)
        connector = self.connectors.get(grant['tool_id'])
        if connector is None:
            raise RuntimeFailure('CONNECTOR_NOT_CONFIGURED', 'No authorized connector adapter is configured.', 503)
        bind_workflow = getattr(connector, 'bind_workflow', None)
        if callable(bind_workflow):
            connector = bind_workflow(workflow)
        bind_run = getattr(connector, 'bind_run', None)
        if callable(bind_run):
            connector = bind_run(workflow, run)
        direct = grant['tool_id'] in self.direct_write_tools and grant.get('approval_required') is False
        if connector.external_write and (not workflow['execution_policy'].get('allow_external_writes') or (not passed and not direct)):
            raise RuntimeFailure('APPROVAL_REQUIRED', 'External writes require workflow policy and run approval.', 403)
        expected_action = run.get('approval_context', {}).get('action_digest')
        if connector.external_write and expected_action and expected_action != self.action_digest(node, run):
            raise RuntimeFailure('APPROVAL_ACTION_MISMATCH', 'The approved external action no longer matches the requested action.', 403)
        discovery_auth = {k: v for k, v in auth.items() if k not in
                          {'_registry_assignment_subject', '_registry_approval_auth'}}
        discovery = runtime.workflows.registry.list_tools(discovery_auth)
        tools = discovery['data'].get('items', []) if discovery['status'] == 200 else []
        record = next((t for t in tools if t['tool_id'] == grant['tool_id'] and t['version'] == grant['tool_version']), None)
        if record is None:
            raise RuntimeFailure('TOOL_METADATA_REQUIRED', 'Current authorized tool metadata is required.', 403)
        remaining_run = workflow['execution_policy']['limits']['timeout_seconds'] - (runtime.clock() - run['created_at'])
        remaining_agent = agent['limits']['timeout_seconds'] - (runtime.clock() - run.get('agent_started_at', {}).get(agent['agent_id'], runtime.clock()))
        if getattr(connector, 'timeout', float('inf')) > min(record['definition']['timeout_seconds'], remaining_agent, remaining_run):
            raise RuntimeFailure('TOOL_TIMEOUT_EXCEEDED', 'The connector timeout exceeds its accepted policy.', 403)
        params = self.params(node, run)
        if list(Draft202012Validator(grant['input_schema']).iter_errors(params)):
            raise RuntimeFailure('CONNECTOR_INPUT_INVALID', 'Connector inputs do not meet the assignment schema.', 400)
        reservation = connector.reservation(grant)
        reservation['tool_calls'] = max(1, reservation.get('tool_calls', 0))
        reservation['estimated_cost_usd'] = max(record['definition']['estimated_cost']['per_call'], reservation.get('estimated_cost_usd', 0))
        return connector, grant, agent, params, reservation

    def advance(self, run_id, auth):
        runtime = self.runtime
        worker = 'worker_' + uuid4().hex
        with runtime.store.transaction() as db:
            run = runtime.load(db, run_id, auth, 'workflow.execute')
            if run['subject_id'] != auth['subject']['subject_id']:
                raise RuntimeFailure('SUBJECT_MISMATCH', 'The worker subject must match the execution subject.', 403)
            if run['status'] == 'paused_for_approval' and self.runtime.clock() >= run['approval_context']['expires_at']:
                self.expire(db, run)
            if run['status'] not in {'queued', 'running'}:
                return runtime.public(run)
            if run.get('lease_until', 0) > runtime.clock():
                return runtime.public(run)
            if any(state == 'executing' for state in run['node_states'].values()):
                if run['status'] == 'queued':
                    runtime.transition(db, run, 'running')
                self.fail(db, run, 'UNKNOWN_INVOCATION_RESULT', blocked=True)
                return runtime.public(run)
            run['worker'] = worker
            run['lease_until'] = runtime.clock() + 3600
            if run['status'] == 'queued':
                runtime.transition(db, run, 'running')
            runtime.save(db, run)
        while True:
            invocation = None
            with runtime.store.transaction() as db:
                run = runtime.load(db, run_id, auth, 'workflow.execute')
                if run.get('worker') != worker or run['status'] != 'running':
                    return runtime.public(run)
                try:
                    workflow, grants = runtime.revision(db, run['workflow_id'], run['workflow_version'], auth, run.get('release_bound', False))
                    if digest(workflow) != run['workflow_digest']:
                        raise RuntimeFailure('REVISION_CHANGED', 'The approved revision changed after execution was queued.')
                    if runtime.clock() - run['created_at'] >= workflow['execution_policy']['limits']['timeout_seconds']:
                        raise RuntimeFailure('RUN_TIMEOUT', 'The execution duration budget is exhausted.')
                    node = self.next_node(db, run, workflow)
                    if node is None:
                        run.pop('current_node_id', None)
                        if len(run['node_states']) != len(workflow['nodes']):
                            raise RuntimeFailure('UNMATCHED_BRANCH', 'Graph dependencies cannot advance.')
                        runtime.transition(db, run, 'completed')
                        return runtime.public(run)
                    run['current_node_id'] = node['node_id']
                    kind = node['kind']
                    config = node.get('configuration', {})
                    if set(config) - {'ui', 'description', 'input', 'input_mapping', 'on_timeout', 'timeout_outcome', 'error_outcome'}:
                        raise RuntimeFailure('UNSUPPORTED_EXECUTION_CONFIGURATION', 'The node contains execution configuration requiring review.')
                    params = self.params(node, run)
                    invocation_id = str(uuid4())
                    run.setdefault('node_invocations', {})[node['node_id']] = invocation_id
                    runtime.event(db, run, 'node.observed', {'node_id': node['node_id'], 'invocation_id': invocation_id, 'observation': snapshot({'inputs': run['inputs'], 'upstream_outputs': run['outputs']}) if kind == 'condition' else snapshot(params), 'kind': kind, 'agent_id': node.get('agent_id'), 'tool_id': node.get('tool_id'), 'policy': snapshot(next(({key: a[key] for key in ('role', 'goal', 'instructions', 'model')} for a in workflow['agents'] if a['agent_id'] == node.get('agent_id')), None))})
                    record_handoffs(runtime, db, run, workflow, node, params, invocation_id)
                    if kind == 'condition':
                        condition = next(c for c in workflow['conditions'] if c['condition_id'] == node['condition_id'])
                        value = evaluate(condition['expression'], run['inputs'], run['outputs'])
                        outcome = ('yes' if value else 'no') if type(value) is bool and set(condition['outcomes']) == {'yes', 'no'} else value
                        if not isinstance(outcome, str) or outcome not in condition['outcomes']:
                            raise RuntimeFailure('UNMATCHED_BRANCH', 'The condition did not produce a declared outcome.')
                        self.finish_node(db, run, workflow, node, outcome=outcome, evidence={'expression': condition['expression'], 'evaluated_value': snapshot(value), 'explanation': 'The recorded expression produced the declared outcome; matching outgoing edges were selected.'})
                    elif kind == 'approval':
                        gate = next(g for g in workflow['approval_gates'] if g['approval_gate_id'] == node['approval_gate_id'])
                        approved_edge = next((edge for edge in self.outgoing(workflow, node['node_id']) if edge.get('outcome') == 'approved'), None)
                        approved_node = next((candidate for candidate in workflow['nodes'] if approved_edge and candidate['node_id'] == approved_edge['target']), None)
                        action_hash = self.action_digest(approved_node, run) if approved_node and approved_node.get('kind') == 'tool' else None
                        email_preview = None
                        if approved_node and approved_node.get('tool_id') == 'smtp_send_email':
                            from .email_recipients import source_recipient
                            recipient = source_recipient(workflow, run['inputs'])
                            email_preview = self.params(approved_node, run)
                            if recipient is not None and email_preview.get('to') != recipient:
                                raise RuntimeFailure('DESTINATION_NOT_AUTHORIZED', 'Recipient must match the original review row.', 403)
                        approval = dict(approval_id='approval_' + uuid4().hex, workflow_id=run['workflow_id'], workflow_version=run['workflow_version'],
                                        status='pending', allowed_decisions=['approved', 'rejected'], action_digest=action_hash)
                        run['approvals'].append(approval)
                        run['approval_context'] = dict(node_id=node['node_id'], gate_id=gate['approval_gate_id'],
                                                       action_digest=action_hash,
                                                       expires_at=runtime.clock() + gate.get('timeout_seconds', workflow['execution_policy']['limits']['timeout_seconds']))
                        run['node_states'][node['node_id']] = 'paused'
                        run['lease_until'] = 0
                        runtime.event(db, run, 'approval.pending', {'approval_id': approval['approval_id'], 'node_id': node['node_id'],
                                      **({'email_preview': email_preview} if email_preview is not None else {})})
                        runtime.transition(db, run, 'paused_for_approval')
                        return runtime.public(run)
                    elif kind in {'trigger', 'transform', 'output'}:
                        if kind == 'trigger':
                            from .email_recipients import source_recipient
                            source_recipient(workflow, run['inputs'])
                        output = self.params(node, run)
                        if kind == 'output':
                            fields = workflow['outputs']
                            contract = {'type': 'object', 'properties': {f['name']: {'type': f['type']} for f in fields},
                                        'required': [f['name'] for f in fields if f['required']]}
                            if list(Draft202012Validator(contract).iter_errors(output)):
                                raise RuntimeFailure('WORKFLOW_OUTPUT_INVALID', 'Output does not satisfy the declared workflow fields.')
                        self.finish_node(db, run, workflow, node, output=output)
                    else:
                        agent = next((a for a in workflow['agents'] if a['agent_id'] == node.get('agent_id')), None)
                        if kind == 'agent':
                            passed = {a['gate_id'] for a in run.get('approval_evidence', [])}
                            if set(agent['approval_requirements']) - passed:
                                raise RuntimeFailure('APPROVAL_REQUIRED', 'The agent requires an approved gate before model execution.', 403)
                            if self.agents is None:
                                raise RuntimeFailure('MODEL_NOT_CONFIGURED', 'A bounded model adapter must be configured.', 503)
                            invocation = (self.agents, agent, self.params(node, run))
                            reservation = self.agents.reservation(agent)
                            reservation['llm_calls'] = max(1, reservation.get('llm_calls', 0))
                        else:
                            connector, grant, agent, params, reservation = self.prepare_tool(run, workflow, grants, node, auth)
                            invocation = (connector, grant, params)
                        dynamic = kind == 'agent' and node['node_id'] in workflow['metadata'].get('dynamic_delegation', {})
                        if not dynamic:
                            self.reserve(db, run, workflow, agent, reservation)
                        run['node_states'][node['node_id']] = 'executing'
                        runtime.event(db, run, 'node.started', {'node_id': node['node_id'], 'invocation_id': invocation_id})
                        runtime.save(db, run)
                except (RuntimeFailure, RegistryError) as failure:
                    self.fail(db, run, failure.code, blocked=True)
                    return runtime.public(run)
                except Exception:
                    self.fail(db, run, 'INVALID_EXECUTION_DATA', blocked=True)
                    return runtime.public(run)
            if invocation:
                adapter, binding, params = invocation
                try:
                    if kind == 'agent' and node['node_id'] in workflow['metadata'].get('dynamic_delegation', {}):
                        output = DelegationSession(self, run_id, auth, worker, workflow, node, agent, params).execute()
                    else:
                        output = adapter.invoke(binding, params, run['run_id'] + ':' + node['node_id'])
                    if kind == 'agent' and list(Draft202012Validator(agent['output_schema']).iter_errors(output)):
                        raise RuntimeFailure('AGENT_OUTPUT_INVALID', 'Agent output failed validation.')
                    if kind == 'tool' and list(Draft202012Validator(binding['output_schema']).iter_errors(output)):
                        raise RuntimeFailure('CONNECTOR_OUTPUT_INVALID', 'Tool output failed validation.')
                    reject_secrets(output)
                    code = None
                except RetryableInvocation:
                    output, code = None, 'RETRYABLE_INVOCATION_FAILED'
                except RuntimeFailure as failure:
                    output, code = None, failure.code
                except Exception:
                    output, code = None, 'UNKNOWN_INVOCATION_RESULT' if getattr(adapter, 'external_write', False) else 'INVOCATION_FAILED'
                with runtime.store.transaction() as db:
                    run = runtime.load(db, run_id, auth, 'workflow.execute')
                    if run.get('worker') != worker or run['status'] != 'running':
                        return runtime.public(run)
                    if (code == 'RETRYABLE_INVOCATION_FAILED' and
                            node['node_id'] not in workflow['metadata'].get('dynamic_delegation', {}) and
                            getattr(adapter, 'retry_safe', False) and not getattr(adapter, 'external_write', False) and
                            workflow['error_policy']['on_runtime_error'] == 'retry'):
                        attempts = run.setdefault('retry_attempts', {}).get(node['node_id'], 0)
                        ceiling = min(workflow['error_policy'].get('max_retries', 0), agent['limits']['max_retries'])
                        if attempts < ceiling:
                            try:
                                self.reserve(db, run, workflow, agent, {'retries': 1})
                                run['retry_attempts'][node['node_id']] = attempts + 1
                                run['node_states'].pop(node['node_id'])
                                runtime.event(db, run, 'node.retry', {'node_id': node['node_id'], 'attempt': attempts + 1})
                                runtime.save(db, run)
                                continue
                            except RuntimeFailure:
                                code = 'BUDGET_EXHAUSTED'
                        else:
                            code = 'RETRY_EXHAUSTED'
                    if code and workflow['error_policy']['on_runtime_error'] == 'branch' and code not in {'SMTP_DELIVERY_UNCERTAIN', 'MODEL_INVOCATION_FAILED', 'UNKNOWN_INVOCATION_RESULT'}:
                        outcome = node.get('configuration', {}).get('error_outcome')
                        if outcome and any(edge.get('outcome') == outcome for edge in self.outgoing(workflow, node['node_id'])):
                            self.finish_node(db, run, workflow, node, outcome=outcome)
                            run['node_states'][node['node_id']] = 'failed'
                            runtime.event(db, run, 'node.failed', {'node_id': node['node_id'], 'invocation_id': run.get('node_invocations', {}).get(node['node_id']), 'error_code': code})
                            runtime.save(db, run)
                            continue
                    if code:
                        self.fail(db, run, code, blocked=code in {'SMTP_DELIVERY_UNCERTAIN', 'MODEL_INVOCATION_FAILED', 'UNKNOWN_INVOCATION_RESULT'})
                        return runtime.public(run)
                    try:
                        workflow, _ = runtime.revision(db, run['workflow_id'], run['workflow_version'], auth, run.get('release_bound', False))
                        if digest(workflow) != run['workflow_digest']:
                            raise RuntimeFailure('REVISION_CHANGED', 'The approved revision changed.')
                        self.finish_node(db, run, workflow, node, output)
                    except Exception:
                        self.fail(db, run, 'POST_INVOCATION_REVALIDATION_FAILED', blocked=True)
                        return runtime.public(run)

    def decide(self, request, approver):
        runtime = self.runtime
        runtime.authorize(approver, 'runs.view', {'admin', 'builder', 'viewer', 'approver'})
        if not {'workspace:read', 'workspace:write'} & set(approver['scopes']):
            raise RuntimeFailure('APPROVAL_SCOPE_REQUIRED', 'Approval requires trusted workspace membership.', 403)
        payload = request['payload']
        if set(payload) - {'approval_id', 'workflow_id', 'workflow_version', 'decision'}:
            raise RuntimeFailure('INVALID_REQUEST', 'Approval contains unsupported fields.', 400)
        key = request.get('idempotency_key')
        if not isinstance(key, str) or not 8 <= len(key) <= 128:
            raise RuntimeFailure('INVALID_IDEMPOTENCY_KEY', 'An approval retry key is required.', 400)
        with runtime.store.transaction() as db:
            rows = db.execute('SELECT document FROM runtime_runs WHERE workspace=?', (approver['subject']['workspace_id'],)).fetchall()
            run = next((json.loads(row[0]) for row in rows if any(a['approval_id'] == payload.get('approval_id') for a in json.loads(row[0])['approvals'])), None)
            if run is None:
                raise RuntimeFailure('APPROVAL_NOT_FOUND', 'The approval was not found in this workspace.', 404)
            if payload.get('workflow_id') != run['workflow_id'] or payload.get('workflow_version') != run['workflow_version']:
                raise RuntimeFailure('APPROVAL_REFERENCE_MISMATCH', 'Approval must reference the exact workflow revision.')
            workflow = runtime.store.get(db, run['workspace_id'], run['workflow_id'], run['workflow_version'])
            if not workflow or digest(workflow) != run['workflow_digest'] or workflow['status'] not in {'approved', 'published'}:
                raise RuntimeFailure('REVISION_CHANGED', 'The reviewed approval revision is no longer current.')
            gate = next(g for g in workflow['approval_gates'] if g['approval_gate_id'] == run['approval_context']['gate_id'])
            # Run actions can be approved by any authenticated member of this
            # workspace. Publication and execution keep their own permissions.
            approval = next(a for a in run['approvals'] if a['approval_id'] == payload['approval_id'])
            decision = payload.get('decision')
            if decision not in {'approved', 'rejected'}:
                raise RuntimeFailure('INVALID_APPROVAL_DECISION', 'Choose approved or rejected.', 400)
            old = run.get('approval_decisions', {}).get(approval['approval_id'])
            if old:
                if old != dict(key=digest(key), decision=decision, subject=approver['subject']['subject_id']):
                    raise RuntimeFailure('APPROVAL_ALREADY_DECIDED', 'This gate already has a decision.')
                return runtime.public(run)
            if run['status'] != 'paused_for_approval' or approval['status'] != 'pending':
                raise RuntimeFailure('APPROVAL_NOT_PENDING', 'The approval is no longer pending.')
            if runtime.clock() >= run['approval_context']['expires_at']:
                self.expire(db, run)
                return runtime.public(run)
            approval.update(status=decision, allowed_decisions=[])
            run.setdefault('approval_decisions', {})[approval['approval_id']] = dict(key=digest(key), decision=decision, subject=approver['subject']['subject_id'])
            runtime.event(db, run, 'approval.' + decision, {'approval_id': approval['approval_id'], 'node_id': run['approval_context']['node_id']})
            node = next(n for n in workflow['nodes'] if n['node_id'] == run['approval_context']['node_id'])
            if decision == 'rejected' and gate['on_reject'] == 'stop':
                runtime.transition(db, run, 'rejected')
            elif decision == 'rejected' and gate['on_reject'] == 'retry':
                runtime.transition(db, run, 'running')
                try:
                    self.reserve(db, run, workflow, None, {'retries': 1})
                    run['node_states'].pop(node['node_id'])
                    runtime.save(db, run)
                except RuntimeFailure:
                    self.fail(db, run, 'BUDGET_EXHAUSTED', blocked=True)
            else:
                runtime.transition(db, run, 'running')
                try:
                    self.finish_node(db, run, workflow, node, outcome=decision)
                    if decision == 'approved':
                        run.setdefault('approval_evidence', []).append(dict(gate_id=gate['approval_gate_id'], approval_id=approval['approval_id']))
                    runtime.save(db, run)
                except RuntimeFailure as failure:
                    self.fail(db, run, failure.code, blocked=True)
            return runtime.public(run)

    def expire(self, db, run):
        runtime = self.runtime
        workflow = runtime.store.get(db, run['workspace_id'], run['workflow_id'], run['workflow_version'])
        approval = next(a for a in run['approvals'] if a['status'] == 'pending')
        approval.update(status='timed_out', allowed_decisions=[])
        runtime.event(db, run, 'approval.timed_out', {'approval_id': approval['approval_id'], 'node_id': run['approval_context']['node_id']})
        if not workflow or digest(workflow) != run['workflow_digest']:
            runtime.transition(db, run, 'blocked')
            return
        node = next(n for n in workflow['nodes'] if n['node_id'] == run['approval_context']['node_id'])
        mode = node.get('configuration', {}).get('on_timeout', 'stop')
        if mode == 'stop':
            runtime.transition(db, run, 'failed')
        else:
            runtime.transition(db, run, 'running')
            try:
                if mode == 'retry':
                    self.reserve(db, run, workflow, None, {'retries': 1})
                    run['node_states'].pop(node['node_id'])
                elif mode == 'branch' and node.get('configuration', {}).get('timeout_outcome'):
                    self.finish_node(db, run, workflow, node, outcome=node['configuration']['timeout_outcome'])
                else:
                    raise RuntimeFailure('INVALID_TIMEOUT_POLICY', 'An explicit safe timeout policy/path is required.')
                runtime.save(db, run)
            except RuntimeFailure as failure:
                self.fail(db, run, failure.code, blocked=True)
