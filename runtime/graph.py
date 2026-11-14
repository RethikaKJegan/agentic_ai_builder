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


def ready_frontier(nodes, edges, node_states, edge_states):
    """Pure DAG frontier shared by approved workflows and read-only investigations.

    Incoming edges must all resolve. One selected incoming path activates a join;
    wholly skipped branches propagate skips without blocking later joins.
    """
    ready, skipped = [], []
    for node in nodes:
        nid = node['node_id']
        if nid in node_states:
            continue
        incoming = [edge for edge in edges if edge['target'] == nid]
        if any(edge['edge_id'] not in edge_states for edge in incoming):
            continue
        if not incoming or any(edge_states[e['edge_id']] == 'selected' for e in incoming):
            ready.append(node)
        else:
            skipped.append(node)
    return ready, skipped



class GraphRunner:
    @staticmethod
    def model_pass_binding(binding,action,workflow=None,run=None,*,enforce_usage_budgets=True):
        agent=deepcopy(binding)
        if (workflow or {}).get('metadata',{}).get('adaptive_control',{}).get('kind')=='workflow-investigation':
            usage=(run or {}).get('usage',{}).get(agent['agent_id'],{})
            if enforce_usage_budgets:
                agent['limits']['max_tokens']=max(0,agent['limits']['max_tokens']-usage.get('tokens',0))
                agent['limits']['max_estimated_cost_usd']=max(0,agent['limits'].get('max_estimated_cost_usd',0)-usage.get('estimated_cost_usd',0))
            agent['limits']['max_llm_calls']=1
        if action and action['capability_id'] in {'content.prepare','data.plan_query'}:
            agent['limits']['max_llm_calls']=min(1,agent['limits']['max_llm_calls'])
        if action and action['capability_id']=='data.plan_query' and binding['limits']['max_llm_calls']>=2:
            # Two pure-model attempts share the already reviewed token/cost cap.
            agent['limits']['max_tokens']=binding['limits']['max_tokens']//2
            agent['limits']['max_estimated_cost_usd']=binding['limits'].get('max_estimated_cost_usd',0)/2
        return agent

    def invoke_agent_with_feedback(self, adapter, binding, params, run_id, auth, worker, workflow, node, reference):
        from shared.llm_feedback import correct_once
        attempt_binding=binding
        def invoke(item):
            agent = deepcopy(attempt_binding)
            with self.runtime.store.transaction(write=False) as policy_db:
                policy_run=self.runtime.load(policy_db,run_id,auth,'workflow.execute')
                agent['_execution_preferences']=deepcopy(policy_run.get('execution_preferences',{}).get('agents',{}).get(agent['agent_id'],{}))
            graph=getattr(self.runtime.workflows,'account_graph',None)
            pin=workflow.get('metadata',{}).get('account_graph_pin')
            if graph and pin:agent['_account_knowledge']=graph.context(auth,pin,node.get('label',''))
            if item:
                agent['_validation_feedback'] = item
            from .action_plans import action_for
            action=action_for(workflow,node['node_id'])
            agent=self.model_pass_binding(agent,action,workflow,enforce_usage_budgets=self.runtime.enforce_usage_budgets)
            accounted=getattr(adapter,'invoke_accounted',None)
            if workflow.get('metadata',{}).get('adaptive_control',{}).get('kind')=='workflow-investigation' and callable(accounted):
                reservation=adapter.reservation(agent)
                output,actual=accounted(agent,params,reference)
                from .model_usage import validate_confirmed
                validate_confirmed(actual,reservation,enforce_usage_budgets=self.runtime.enforce_usage_budgets)
                with self.runtime.store.transaction() as db:
                    saved=self.runtime.load(db,run_id,auth,'workflow.execute')
                    if not self.runtime.owns_execution(saved,worker):raise RuntimeFailure('DELEGATION_INTERRUPTED','Execution ownership changed.')
                    for group in ('workflow',agent['agent_id']):
                        for key,value in actual.items():saved['usage'][group][key]=max(0,saved['usage'][group][key]-(reservation[key]-value))
                    self.runtime.event(db,saved,'budget.settled',dict(agent_id=agent['agent_id'],counters=actual))
                    self.runtime.save(db,saved)
            else:output = adapter.invoke(agent, params, reference)
            if list(Draft202012Validator(binding['output_schema']).iter_errors(output)):
                raise RuntimeFailure('AGENT_OUTPUT_INVALID', 'Agent output failed validation.')
            from .action_plans import validate_content
            try:validate_content(workflow,node,output,params)
            except RuntimeFailure as error:
                if action and action['capability_id'] in {'data.plan_query','subway.plan_query'} and getattr(error,'invalid_model_output',False):
                    with self.runtime.store.transaction() as db:
                        run=self.runtime.load(db,run_id,auth,'workflow.execute')
                        if self.runtime.owns_execution(run,worker):
                            self.runtime.event(db,run,'agent.output_rejected',dict(node_id=node['node_id'],
                                error_code=error.code,field=getattr(error,'validation_field','query'),
                                validation_rule=getattr(error,'validation_hint','')[:400]))
                raise
            return output
        def prepare(item):
            nonlocal attempt_binding
            if getattr(adapter, 'external_write', False):
                return False
            with self.runtime.store.transaction() as db:
                run = self.runtime.load(db, run_id, auth, 'workflow.execute')
                if not self.runtime.owns_execution(run, worker):
                    raise RuntimeFailure('DELEGATION_INTERRUPTED', 'The run no longer owns model execution.')
                self.runtime.revision(db, run['workflow_id'], run['workflow_version'], auth, run.get('release_bound', False))
                if self.runtime.clock()-run['created_at'] >= workflow['execution_policy']['limits']['timeout_seconds']:
                    raise RuntimeFailure('RUN_TIMEOUT', 'The run duration is exhausted.')
                if any(run['usage'].get(group, {}).get('llm_calls', 0) >= limits['max_llm_calls']
                       for group, limits in ((binding['agent_id'], binding['limits']),
                                             ('workflow', workflow['execution_policy']['limits']))):
                    return False
                from .action_plans import action_for
                root=next(a for a in workflow['agents'] if a['agent_id']==binding['agent_id'])
                attempt_binding=self.model_pass_binding(root,action_for(workflow,node['node_id']),workflow,run,enforce_usage_budgets=self.runtime.enforce_usage_budgets)
                amount = adapter.reservation(attempt_binding)
                amount['llm_calls'] = 1
                self.reserve(db, run, workflow, binding, amount)
                self.runtime.event(db, run, 'agent.correction', {'node_id': node['node_id'],
                    'agent_id': binding['agent_id'], 'attempt': 1, 'validation_feedback': [item]})
                self.runtime.save(db, run)
        return correct_once(invoke, prepare)

    def __init__(self, runtime, agents=None, connectors=None, direct_write_tools=()):
        self.runtime = runtime
        self.agents, self.connectors = agents, connectors or {}
        self.direct_write_tools = frozenset(direct_write_tools)

    @staticmethod
    def outgoing(workflow, node_id):
        return [edge for edge in workflow['edges'] if edge['source'] == node_id]

    def finish_node(self, db, run, workflow, node, output=None, outcome=None, evidence=None):
        node_id = node['node_id']
        run.get('query_waits',{}).pop(node_id,None)
        from .action_plans import completed as action_completed
        action_completed(workflow,node,run,output)
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
        if node['kind']=='agent':
            settings=run.get('execution_preferences',{}).get('agents',{}).get(node.get('agent_id'),{})
            if settings.get('packs') or any(v is True or (k=='preferredLanguage' and v!='Auto') for k,v in settings.get('behaviours',{}).items()):
                self.runtime.event(db,run,'agent.preferences_checked',dict(node_id=node_id,agent_id=node.get('agent_id'),settings_revision=settings.get('revision',0),pack_pins=[dict(id=p['id'],version=p['version'],controls=p.get('effective_controls',[])) for p in settings.get('packs',[])],scope='supported model boundaries; direct tools unchanged'))
        run.pop('current_node_id', None)
        self.runtime.save(db, run)

    def next_node(self, db, run, workflow, excluded=()):
        while True:
            ready, skipped = ready_frontier(workflow['nodes'], workflow['edges'], run['node_states'], run['edge_states'])
            from .query_parallel import eligible
            ready=eligible(self,run,ready,excluded)
            # Adaptive ordering is a hint only; the case-owned guard revalidates authority.
            preferred=run.get('adaptive_next_action') if workflow.get('metadata',{}).get('adaptive_control') else None
            if preferred:
                selected=next((n for n in ready if n['node_id'] in (preferred,'approve_'+preferred,'condition_'+preferred,'skip_'+preferred)),None)
                if selected:return selected
            # Preserve original graph-order choice between ready and skipped nodes.
            eligible = {n['node_id'] for n in [*ready, *skipped]}
            ordered=sorted(workflow['nodes'],key=lambda n:0 if n in skipped else 1) if preferred else workflow['nodes']
            for node in ordered:
                if node['node_id'] not in eligible:
                    continue
                if node in ready:
                    if not any(e['target'] == node['node_id'] for e in workflow['edges']) and node['kind'] != 'trigger':
                        raise RuntimeFailure('UNREACHABLE_EXECUTION_NODE', 'Only trigger nodes may start a graph.')
                    return node
                run['node_states'][node['node_id']] = 'skipped'
                if node['node_id'] in run.get('action_instances',{}):run['action_instances'][node['node_id']]['state']='skipped'
                for edge in self.outgoing(workflow, node['node_id']):
                    run['edge_states'][edge['edge_id']] = 'skipped'
                self.runtime.event(db, run, 'node.skipped', {'node_id': node['node_id'], 'explanation': 'All incoming paths were skipped in this run.'})
                self.runtime.save(db, run)
            if not skipped:
                return None

    def fail(self, db, run, code, blocked=False):
        if code in {'TOOL_RESTRICTED', 'SOURCE_RESTRICTED', 'READ_ONLY_VIOLATION', 'OPERATION_NOT_AUTHORIZED', 'GOVERNANCE_BUDGET_EXHAUSTED', 'RUN_TIMEOUT', 'AGENT_TIMEOUT', 'MODEL_TIMEOUT', 'TOOL_TIMEOUT', 'DELEGATION_TIMEOUT', 'ACTION_OUTCOME_UNKNOWN', 'ACTION_RECEIPT_INVALID'}:
            blocked = True
        run['error_code'] = code
        node_id = run.get('current_node_id')
        from .recovery import classify,node_external_write
        workflow = self.runtime.store.get(db, run['workspace_id'], run['workflow_id'], run['workflow_version']) or {'nodes': []}
        node = next((n for n in workflow['nodes'] if n['node_id'] == node_id), {})
        run.setdefault('classified_failures', []).append(classify(code, task=node_id, source=node.get('tool_id'), external_write=node_external_write(workflow,node)))
        if node_id:
            entry=run.get('action_instances',{}).get(node_id)
            if entry is not None:entry.update(state='blocked' if blocked else 'failed',error_code=code,external_effect_status='requires_reconciliation' if code in {'UNKNOWN_INVOCATION_RESULT','SMTP_DELIVERY_UNCERTAIN','POST_INVOCATION_REVALIDATION_FAILED','ACTION_EFFECT_UNVERIFIED'} else 'failed',retry_decision='explicit_review_required')
            run['node_states'][node_id] = 'blocked' if blocked else 'failed'
            self.runtime.event(db, run, 'node.failed', {'node_id': node_id, 'invocation_id': run.get('node_invocations', {}).get(node_id), 'error_code': code, 'status': 'blocked' if blocked else 'failed'})
        self.runtime.event(db, run, 'runtime.denied', {'error_code': code})
        if run.get('adaptive',{}).get('kind')=='workflow-investigation':
            # Known validation failures have no uncertain external effect. Let
            # the existing evaluator revise unfinished read/reasoning work.
            if code in {'AGENT_OUTPUT_INVALID','CONNECTOR_INPUT_INVALID','SUBWAY_QUERY_INVALID','SUBWAY_QUERY_TYPE','SUBWAY_QUERY_LIMIT'}:
                adaptive=run['adaptive']
                adaptive['recoverable_failures']=adaptive.get('recoverable_failures',0)+1
                if adaptive['recoverable_failures']<=2:
                    adaptive.pop('execution_permission',None)
                    run['lease_until']=0
                    self.runtime.event(db,run,'adaptive.action_rejected',dict(node_id=node_id,code=code))
                    self.runtime.save(db,run)
                    return
            run['adaptive'].update(status='blocked' if blocked else 'failed',blocker=code)
        self.runtime.transition(db, run, 'blocked' if blocked else 'failed')

    @staticmethod
    def params(node, run, workflow=None, *, now=None):
        if workflow is not None:
            from .action_plans import params as connected_params
            resolved=connected_params(workflow,node,run,now=now)
            if resolved is not None:return resolved
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

    def action_digest(self, node, run, workflow=None):
        """Hash the exact approved action without persisting its input values."""
        return digest({'node_id': node['node_id'], 'kind': node['kind'], 'tool_id': node.get('tool_id'),
                       'agent_id': node.get('agent_id'), 'params': self.params(node, run, workflow,now=self.runtime.clock())})

    def reserve(self, db, run, workflow, agent, amount, provider_id=None, credential_reference=None):
        self.runtime.check_deadlines(run, workflow, agent)
        self.runtime.governance.reserve(db, run, workflow, amount)
        if set(amount) - {'llm_calls', 'tool_calls', 'tokens', 'retries', 'estimated_cost_usd', 'delegation_calls'}:
            raise RuntimeFailure('INVALID_USAGE', 'The provider reservation contains unsupported usage counters.')
        for key, value in amount.items():
            if type(value) not in (int, float) or value < 0 or value != value or value == float('inf'):
                raise RuntimeFailure('INVALID_USAGE', 'Provider usage must contain finite nonnegative counters.')
        from .adaptive_control import reserve as adaptive_reserve
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
                if key in {'tokens', 'estimated_cost_usd'} and not self.runtime.enforce_usage_budgets:
                    continue
                if key == 'delegation_calls':
                    continue
                if usage.get(key, 0) + value > limits.get(counters[key], 0):
                    raise RuntimeFailure('BUDGET_EXHAUSTED', 'The next invocation exceeds an execution budget.')
        if controls:=getattr(self.runtime,'resource_controls',None):
            if amount.get('llm_calls',0):
                controls.reserve_provider(db,run['workspace_id'],agent['model']['provider'],self.runtime.clock())
            if amount.get('tool_calls',0):
                node=next((n for n in workflow['nodes'] if n['node_id']==run.get('current_node_id')), {})
                provider=provider_id or controls.tool_provider(self.runtime,node.get('tool_id'))
                controls.reserve_provider(db,run['workspace_id'],provider,self.runtime.clock(),credential_reference or controls.tool_credential(self.runtime,node.get('tool_id')))
        adaptive_reserve(run,workflow,amount)
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
        if node['tool_id'] in runtime.governance.effective(run)['restricted_tools']:
            raise RuntimeFailure('TOOL_RESTRICTED', 'This tool is restricted by workspace policy.', 403)
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
        bind_context = getattr(connector, 'bind_context', None)
        if callable(bind_context):
            connector = bind_context(workflow, run, auth, node)
        bind_workflow = getattr(connector, 'bind_workflow', None)
        if callable(bind_workflow):
            connector = bind_workflow(workflow)
        bind_run = getattr(connector, 'bind_run', None)
        if callable(bind_run):
            connector = bind_run(workflow, run)
        if binder := getattr(runtime.workflows, 'bind_google_connector', None):
            connector = binder(connector, workflow, run, auth, grant)
        direct = grant['tool_id'] in self.direct_write_tools and grant.get('approval_required') is False
        expected_action = run.get('approval_context', {}).get('action_digest')
        context = run.get('approval_context', {})
        same_action = not context.get('policy_review') or context.get('node_id') == node['node_id']
        if connector.external_write and same_action and expected_action and expected_action != self.action_digest(node, run, workflow):
            raise RuntimeFailure('APPROVAL_ACTION_MISMATCH', 'The approved external action no longer matches the requested action.', 403)
        discovery_auth = {k: v for k, v in auth.items() if k not in
                          {'_registry_assignment_subject', '_registry_approval_auth'}}
        discovery = runtime.workflows.registry.list_tools(discovery_auth)
        tools = discovery['data'].get('items', []) if discovery['status'] == 200 else []
        record = next((t for t in tools if t['tool_id'] == grant['tool_id'] and t['version'] == grant['tool_version']), None)
        if record is None:
            raise RuntimeFailure('TOOL_METADATA_REQUIRED', 'Current authorized tool metadata is required.', 403)
        # The Registry bounds the adapter's configured transport timeout. The
        # guarded invocation separately enforces the *remaining* run/agent time;
        # elapsed setup must not make equal configured limits incompatible.
        if getattr(connector, 'timeout', float('inf')) > record['definition']['timeout_seconds']:
            raise RuntimeFailure('TOOL_TIMEOUT_EXCEEDED', 'The connector timeout exceeds its accepted policy.', 403)
        params = self.params(node, run, workflow,now=self.runtime.clock())
        if list(Draft202012Validator(grant['input_schema']).iter_errors(params)):
            raise RuntimeFailure('CONNECTOR_INPUT_INVALID', 'Connector inputs do not meet the assignment schema.', 400)
        runtime.governance.check_tool(run, workflow, node, connector, record['definition'], params)
        if connector.external_write and (not workflow['execution_policy'].get('allow_external_writes') or (not passed and not direct)):
            raise RuntimeFailure('APPROVAL_REQUIRED', 'External writes require workflow policy and run approval.', 403)
        automation=getattr(runtime.workflows,'automation',None)
        if automation and run.get('automation_reference') and (connector.external_write or getattr(connector,'durable_query',False) or node.get('tool_id') in {'subway_query','subway_documents'}):
            with runtime.store.transaction(write=False) as db:automation.check_action(db,auth,run,workflow,node,params)
        if workflow.get('metadata',{}).get('connected_action_plan'):
            from .action_plans import preflight
            preflight(connector,params)
        reservation = connector.reservation(grant)
        reservation['tool_calls'] = max(1, reservation.get('tool_calls', 0))
        reservation['estimated_cost_usd'] = max(record['definition']['estimated_cost']['per_call'], reservation.get('estimated_cost_usd', 0))
        return connector, grant, agent, params, reservation

    def advance(self, run_id, auth, *, _adaptive_dispatch=False):
        from workflow_api.service import ApiFailure
        if not _adaptive_dispatch:
            with self.runtime.store.transaction(write=False) as db:
                run=self.runtime.load(db,run_id,auth,'workflow.execute')
                saved=self.runtime.store.get(db,run['workspace_id'],run['workflow_id'],run['workflow_version']) or {}
            from workflow_api.workflow_adaptive import controlled,drive
            if controlled(saved):
                return drive(self,run_id,auth,lambda:self.advance(run_id,auth,_adaptive_dispatch=True))
        import os
        from workflow_api.worker_control import LeaseHeartbeat
        seconds=int(os.getenv('BUILDER_RUNTIME_LEASE_SECONDS','120'))
        if not 30<=seconds<=3600:raise ValueError('Runtime lease must be 30-3600 seconds.')
        worker='worker_'+uuid4().hex
        def renew():
            with self.runtime.store.transaction() as db:
                run=self.runtime.load(db,run_id,auth,'workflow.execute')
                if not self.runtime.owns_execution(run,worker):return False
                run['lease_until']=self.runtime.clock()+seconds
                self.runtime.save(db,run)
            return True
        with LeaseHeartbeat(renew,interval=max(1,seconds/3)):
            try:
                return self._advance(run_id,auth,worker,seconds)
            except (RuntimeFailure, RegistryError, ApiFailure) as error:
                with self.runtime.store.transaction() as db:
                    run = self.runtime.load(db, run_id, auth, 'workflow.execute')
                    if run['status'] in {'queued', 'running', 'paused_for_approval'} and (run.get('worker') == worker or run.get('lease_until', 0) <= self.runtime.clock()):
                        self.fail(db, run, error.code, blocked=True)
                    return self.runtime.public(run)
            finally:
                # Only the returning owner can relinquish a stopped execution.
                # Keep a still-running/uncertain invocation and all effect state.
                with self.runtime.store.transaction() as db:
                    run=self.runtime.load(db,run_id,auth,'workflow.execute')
                    if run.get('worker')==worker and run['status'] not in {'queued','running'}:
                        run['lease_until']=0
                        self.runtime.save(db,run)

    def _advance(self, run_id, auth, worker, lease_seconds):
        from workflow_api.service import ApiFailure
        runtime = self.runtime
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
            if run.get('available_at',0)>runtime.clock():return runtime.public(run)
            # Durable read-only query submissions can reattach by run/node identity
            # after a worker crash. All other uncertain invocations keep the guard.
            if any(state == 'executing' for state in run['node_states'].values()):
                reviewed,_=runtime.execution_revision(db,run,auth)
                for pending_node in reviewed['nodes']:
                    connector=self.connectors.get(pending_node.get('tool_id'))
                    if (run['node_states'].get(pending_node['node_id'])=='executing' and
                            pending_node['kind']=='tool' and getattr(connector,'durable_query',False) and not connector.external_write):
                        run['node_states'].pop(pending_node['node_id'])
            if any(state == 'executing' for state in run['node_states'].values()):
                if run['status'] == 'queued':
                    runtime.transition(db, run, 'running')
                self.fail(db, run, 'UNKNOWN_INVOCATION_RESULT', blocked=True)
                return runtime.public(run)
            if controls:=getattr(runtime,'resource_controls',None):
                from workflow_api.resource_limits import CapacityDeferred
                try:controls.claim(db,run,runtime.clock())
                except CapacityDeferred as error:
                    try:controls.defer(runtime,db,run,error)
                    except RuntimeFailure as failure:self.fail(db,run,failure.code,blocked=True)
                    return runtime.public(run)
            run['worker'] = worker
            run['lease_until'] = runtime.clock() + lease_seconds
            if run['status'] == 'queued':
                runtime.transition(db, run, 'running')
            runtime.save(db, run)
        query_polled=set()
        while True:
            invocation = None
            with runtime.store.transaction() as db:
                run = runtime.load(db, run_id, auth, 'workflow.execute')
                if not runtime.owns_execution(run, worker):
                    return runtime.public(run)
                try:
                    workflow, grants = runtime.execution_revision(db, run, auth)
                    automation_policy=None
                    automation=getattr(runtime.workflows,'automation',None)
                    if automation and run.get('automation_reference'):
                        if automation.suspended(db,auth,run):return runtime.public(run)
                        automation_policy=automation.guard_run(db,auth,run,workflow)
                    from .adaptive_control import suspended as adaptive_suspended
                    if adaptive_suspended(db,runtime,run,workflow):return runtime.public(run)
                    if runtime.clock() - run['created_at'] >= workflow['execution_policy']['limits']['timeout_seconds']:
                        raise RuntimeFailure('RUN_TIMEOUT', 'The execution duration budget is exhausted.')
                    node = self.next_node(db, run, workflow, query_polled)
                    if node is None:
                        run.pop('current_node_id', None)
                        if run.get('query_waits'):
                            run['lease_until']=0
                            run['available_at']=runtime.clock()+1
                            runtime.save(db,run)
                            return runtime.public(run)
                        if len(run['node_states']) != len(workflow['nodes']):
                            raise RuntimeFailure('UNMATCHED_BRANCH', 'Graph dependencies cannot advance.')
                        runtime.transition(db, run, 'completed')
                        return runtime.public(run)
                    from .adaptive_control import guard as adaptive_guard
                    if not adaptive_guard(db,runtime,run,workflow,node):return runtime.public(run)
                    run['current_node_id'] = node['node_id']
                    kind = node['kind']
                    if automation_policy and run.get('action_instances',{}).get(node['node_id'],{}).get('state','pending')=='pending':
                        from .action_plans import action_for
                        attempted=sum(1 for item in run.get('action_instances',{}).values() if item.get('state')!='pending')
                        if action_for(workflow,node['node_id']) and attempted>=automation_policy['request']['limits']['max_actions_per_occurrence']:
                            raise RuntimeFailure('AUTOMATION_ACTION_LIMIT','The reviewed occurrence action allowance is exhausted.',403)
                    config = node.get('configuration', {})
                    if set(config) - {'ui', 'description', 'input', 'input_mapping', 'on_timeout', 'timeout_outcome', 'error_outcome'}:
                        raise RuntimeFailure('UNSUPPORTED_EXECUTION_CONFIGURATION', 'The node contains execution configuration requiring review.')
                    params = self.params(node, run, workflow,now=self.runtime.clock())
                    from .action_plans import observed as action_observed
                    action_observed(workflow,node,run,params)
                    invocation_id = str(uuid4())
                    run.setdefault('node_invocations', {})[node['node_id']] = invocation_id
                    runtime.event(db, run, 'node.observed', {'node_id': node['node_id'], 'invocation_id': invocation_id, 'observation': snapshot({'inputs': run['inputs'], 'upstream_outputs': run['outputs']}) if kind == 'condition' else snapshot(params), 'kind': kind, 'agent_id': node.get('agent_id'), 'tool_id': node.get('tool_id'), 'policy': snapshot(next(({key: a[key] for key in ('role', 'goal', 'instructions', 'model')} for a in workflow['agents'] if a['agent_id'] == node.get('agent_id')), None))})
                    record_handoffs(runtime, db, run, workflow, node, params, invocation_id)
                    if kind == 'condition':
                        condition = next(c for c in workflow['conditions'] if c['condition_id'] == node['condition_id'])
                        value = params['condition'] if workflow.get('metadata',{}).get('connected_action_plan') else evaluate(condition['expression'], run['inputs'], run['outputs'])
                        outcome = ('yes' if value else 'no') if type(value) is bool and set(condition['outcomes']) == {'yes', 'no'} else value
                        if not isinstance(outcome, str) or outcome not in condition['outcomes']:
                            raise RuntimeFailure('UNMATCHED_BRANCH', 'The condition did not produce a declared outcome.')
                        self.finish_node(db, run, workflow, node, outcome=outcome, evidence={'expression': condition['expression'], 'evaluated_value': snapshot(value), 'explanation': 'The recorded expression produced the declared outcome; matching outgoing edges were selected.'})
                    elif kind == 'approval':
                        gate = next(g for g in workflow['approval_gates'] if g['approval_gate_id'] == node['approval_gate_id'])
                        approved_edge = next((edge for edge in self.outgoing(workflow, node['node_id']) if edge.get('outcome') == 'approved'), None)
                        approved_node = next((candidate for candidate in workflow['nodes'] if approved_edge and candidate['node_id'] == approved_edge['target']), None)
                        action_hash = self.action_digest(approved_node, run, workflow) if approved_node and approved_node.get('kind') == 'tool' else None
                        email_preview = None
                        if approved_node and approved_node.get('tool_id') == 'smtp_send_email':
                            from .email_recipients import source_recipient
                            recipient = source_recipient(workflow, run['inputs'])
                            email_preview = self.params(approved_node, run, workflow,now=self.runtime.clock())
                            if recipient is not None and email_preview.get('to') != recipient:
                                raise RuntimeFailure('DESTINATION_NOT_AUTHORIZED', 'Recipient must match the original review row.', 403)
                        approval = dict(approval_id='approval_' + uuid4().hex, workflow_id=run['workflow_id'], workflow_version=run['workflow_version'],
                                        status='pending', allowed_decisions=['approved', 'rejected'], action_digest=action_hash)
                        if workflow.get('metadata',{}).get('connected_action_plan') and approved_node:
                            approval['resolved_payload']=self.params(approved_node,run,workflow,now=self.runtime.clock())
                            run['action_instances'][approved_node['node_id']].update(state='waiting_for_approval',resolved_inputs=deepcopy(approval['resolved_payload']),input_fingerprint=digest(approval['resolved_payload']))
                        run['approvals'].append(approval)
                        run['approval_context'] = dict(node_id=node['node_id'], gate_id=gate['approval_gate_id'],
                                                       action_digest=action_hash,
                                                       expires_at=runtime.clock() + gate.get('timeout_seconds', workflow['execution_policy']['limits']['timeout_seconds']))
                        run['node_states'][node['node_id']] = 'paused'
                        run['lease_until'] = 0
                        runtime.event(db, run, 'approval.pending', {'approval_id': approval['approval_id'], 'node_id': node['node_id'],
                                      **({'database_operation_id': self.params(approved_node, run, workflow,now=self.runtime.clock()).get('operation_id')} if approved_node and approved_node.get('tool_id') == 'database_execute_operation' else {}),
                                      **({'email_preview': email_preview} if email_preview is not None else {})})
                        runtime.transition(db, run, 'paused_for_approval')
                        return runtime.public(run)
                    elif kind in {'trigger', 'transform', 'output'}:
                        if kind == 'trigger':
                            from .email_recipients import source_recipient
                            source_recipient(workflow, run['inputs'])
                        output = self.params(node, run, workflow,now=self.runtime.clock())
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
                            invocation = (self.agents, agent, self.params(node, run, workflow,now=self.runtime.clock()))
                            reservation_agent=agent
                            from .action_plans import action_for
                            action=action_for(workflow,node['node_id'])
                            reservation_agent=self.model_pass_binding(agent,action,workflow,run,enforce_usage_budgets=self.runtime.enforce_usage_budgets)
                            if workflow.get('metadata',{}).get('adaptive_control',{}).get('kind')=='workflow-investigation':
                                invocation=(self.agents,reservation_agent,self.params(node,run,workflow,now=self.runtime.clock()))
                            reservation = self.agents.reservation(reservation_agent)
                            reservation['llm_calls'] = max(1, reservation.get('llm_calls', 0))
                        else:
                            connector, grant, agent, params, reservation = self.prepare_tool(run, workflow, grants, node, auth)
                            invocation = (connector, grant, params)
                        dynamic = kind == 'agent' and node['node_id'] in workflow['metadata'].get('dynamic_delegation', {})
                        durable_query=kind=='tool' and getattr(invocation[0],'durable_query',False) and not invocation[0].external_write
                        already_reserved=durable_query and node['node_id'] in run.get('durable_query_reservations',[])
                        if not dynamic and not already_reserved:
                            self.reserve(db, run, workflow, agent, reservation)
                            if durable_query:run.setdefault('durable_query_reservations',[]).append(node['node_id'])
                        run.setdefault('node_started_at', {}).setdefault(node['node_id'], runtime.clock())
                        run['node_states'][node['node_id']] = 'executing'
                        runtime.event(db, run, 'node.started', {'node_id': node['node_id'], 'invocation_id': invocation_id,
                            **({'google_connection': invocation[0].google_connection_info} if getattr(invocation[0], 'google_connection_info', None) else {})})
                        runtime.save(db, run)
                except (RuntimeFailure, RegistryError, ApiFailure) as failure:
                    if failure.code == 'POLICY_APPROVAL_REQUIRED' and node['kind'] == 'tool':
                        return self.pause_policy_action(db, run, workflow, node)
                    from workflow_api.resource_limits import CapacityDeferred
                    if isinstance(failure,CapacityDeferred):
                        try:runtime.resource_controls.defer(runtime,db,run,failure)
                        except RuntimeFailure as error:self.fail(db,run,error.code,blocked=True)
                        return runtime.public(run)
                    self.fail(db, run, failure.code, blocked=True)
                    return runtime.public(run)
                except Exception:
                    self.fail(db, run, 'INVALID_EXECUTION_DATA', blocked=True)
                    return runtime.public(run)
            if invocation:
                from workflow_api.workflow_queries import QueryPending,QueryClarification
                adapter, binding, params = invocation
                try:
                    # Intent persistence is not continuing authority. Cancellation,
                    # lease expiry or Registry revocation may occur at that commit.
                    with runtime.store.transaction(write=False) as db:
                        current = runtime.load(db, run_id, auth, 'workflow.execute')
                        if not runtime.owns_execution(current, worker):
                            return runtime.public(current)
                        reviewed, _ = runtime.execution_revision(db, current, auth)
                        if digest(reviewed) != digest(workflow):
                            raise RuntimeFailure('REVISION_CHANGED', 'The approved revision changed before invocation.')
                        runtime.check_deadlines(current, reviewed, agent)
                        if kind == 'tool':
                            self.prepare_tool(current, reviewed, runtime.execution_revision(db, current, auth)[1], node, auth)
                    if kind == 'agent' and node['node_id'] in workflow['metadata'].get('dynamic_delegation', {}):
                        output = runtime.invoke_guarded(run_id, auth, worker,
                            lambda: DelegationSession(self, run_id, auth, worker, workflow, node, agent, params).execute(),
                            agent=agent, kind='delegation')
                    elif kind == 'agent':
                        output = runtime.invoke_guarded(run_id, auth, worker,
                            lambda: self.invoke_agent_with_feedback(adapter, binding, params, run_id, auth, worker, workflow, node, run_id + ':' + node['node_id']),
                            agent=agent, kind='model', adapter=adapter, reference=run_id + ':' + node['node_id'])
                    else:
                        output = runtime.invoke_guarded(run_id, auth, worker,
                            lambda: adapter.invoke(binding, params, run_id + ':' + node['node_id']),
                            agent=agent, kind='tool', adapter=adapter, reference=run_id + ':' + node['node_id'], tool_node=node, effect_schema=binding['output_schema'])
                    if kind == 'agent' and list(Draft202012Validator(agent['output_schema']).iter_errors(output)):
                        raise RuntimeFailure('AGENT_OUTPUT_INVALID', 'Agent output failed validation.')
                    if kind == 'tool' and list(Draft202012Validator(binding['output_schema']).iter_errors(output)):
                        raise RuntimeFailure('CONNECTOR_OUTPUT_INVALID', 'Tool output failed validation.')
                    method=workflow.get('metadata',{}).get('composition_action_verifiers',{}).get(node['node_id'])
                    if method:
                        from .capability_composition import verify_action
                        verify_action(method,output,params)
                    from .action_plans import verify as verify_connected
                    verify_connected(workflow,node,output,params)
                    reject_secrets(output)
                    code = None
                except QueryClarification as clarification:
                    if kind!='tool' or not getattr(adapter,'durable_query',False) or adapter.external_write:
                        raise
                    with runtime.store.transaction() as db:
                        run=runtime.load(db,run_id,auth,'workflow.execute')
                        if not runtime.owns_execution(run,worker):return runtime.public(run)
                        self.fail(db,run,clarification.code,blocked=True)
                        run['action_instances'][node['node_id']].update(state='needs_input',
                            clarification=clarification.question,external_effect_status='not_performed',
                            retry_decision='supply_definition_and_prepare_new_workflow')
                        runtime.event(db,run,'query.clarification_required',dict(node_id=node['node_id'],question=clarification.question,source_read_performed=False))
                        runtime.save(db,run)
                        return runtime.public(run)
                except QueryPending as pending:
                    if kind!='tool' or not getattr(adapter,'durable_query',False) or adapter.external_write:
                        raise
                    with runtime.store.transaction() as db:
                        run=runtime.load(db,run_id,auth,'workflow.execute')
                        if not runtime.owns_execution(run,worker):return runtime.public(run)
                        run['node_states'].pop(node['node_id'],None)
                        if 'query_concurrency' not in run:
                            from .query_parallel import query_limit
                            controls=getattr(runtime,'resource_controls',None)
                            env=getattr(adapter,'manager',None) or getattr(getattr(adapter,'queries',None),'manager',None)
                            run['query_concurrency']=query_limit(getattr(env,'env',{}),controls.policy if controls else None)
                            runtime.event(db,run,'query.concurrency',dict(limit=run['query_concurrency'],eligible_tool=node.get('tool_id')))
                        run.setdefault('query_waits',{})[node['node_id']]=pending.job
                        if node['node_id'] in run.get('action_instances',{}):
                            run['action_instances'][node['node_id']].update(state='waiting_for_query',query_job=dict(job_id=pending.job['job_id'],state=pending.job['state'],progress=pending.job['progress']))
                        runtime.event(db,run,'query.waiting',dict(node_id=node['node_id'],job_id=pending.job['job_id'],state=pending.job['state'],progress=pending.job['progress']))
                        runtime.save(db,run)
                    query_polled.add(node['node_id'])
                    continue
                except RetryableInvocation:
                    output, code = None, 'RETRYABLE_INVOCATION_FAILED'
                except RuntimeFailure as failure:
                    if kind == 'agent' and isinstance(getattr(failure, 'model_diagnostic', None), dict):
                        with runtime.store.transaction() as db:
                            saved = runtime.load(db, run_id, auth, 'workflow.execute')
                            if runtime.owns_execution(saved, worker):
                                runtime.event(db, saved, 'model.invocation_failed', dict(node_id=node['node_id'], error_code=failure.code,
                                    **failure.model_diagnostic))
                    if kind=='agent' and getattr(failure,'invalid_model_output',False) and getattr(failure,'validation_field',None)!='query':
                        with runtime.store.transaction() as db:
                            saved=runtime.load(db,run_id,auth,'workflow.execute')
                            if runtime.owns_execution(saved,worker):
                                runtime.event(db,saved,'agent.output_rejected',dict(node_id=node['node_id'],error_code=failure.code,
                                    field=getattr(failure,'validation_field','output'),validation_rule=getattr(failure,'validation_hint','')[:400]))
                    output, code = None, failure.code
                except Exception:
                    output, code = None, 'UNKNOWN_INVOCATION_RESULT' if getattr(adapter, 'external_write', False) else 'INVOCATION_FAILED'
                if code and kind=='tool' and workflow.get('metadata',{}).get('connected_action_plan') and getattr(adapter,'external_write',False):
                    original_code=code
                    code='ACTION_EFFECT_UNVERIFIED'
                else:original_code=None
                with runtime.store.transaction() as db:
                    run = runtime.load(db, run_id, auth, 'workflow.execute')
                    if not runtime.owns_execution(run, worker):
                        return runtime.public(run)
                    if original_code:
                        run['action_instances'][node['node_id']]['verification_error_code']=original_code
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
                                if getattr(runtime,'resource_controls',None):
                                    run['available_at']=runtime.clock()+min(2**attempts,60)
                                    run['lease_until']=0
                                    runtime.save(db,run)
                                    return runtime.public(run)
                                continue
                            except RuntimeFailure:
                                code = 'BUDGET_EXHAUSTED'
                        else:
                            code = 'RETRY_EXHAUSTED'
                    security_stop = bool(code and (code.endswith(('_DENIED', '_RESTRICTED', '_NOT_AUTHORIZED', '_TIMEOUT')) or code in {'READ_ONLY_VIOLATION', 'APPROVAL_REQUIRED', 'APPROVAL_EXPIRED', 'APPROVER_REVOKED', 'ACTION_OUTCOME_UNKNOWN', 'ACTION_RECEIPT_INVALID', 'ACTION_EFFECT_UNVERIFIED', 'GOVERNANCE_BUDGET_EXHAUSTED', 'BUDGET_EXHAUSTED', 'RETRY_EXHAUSTED'}))
                    if code and not security_stop and workflow['error_policy']['on_runtime_error'] == 'branch' and code not in {'SMTP_DELIVERY_UNCERTAIN', 'MODEL_INVOCATION_FAILED', 'MODEL_PROVIDER_TIMEOUT', 'MODEL_PROVIDER_CONNECTION', 'MODEL_PROVIDER_AUTH', 'MODEL_PROVIDER_RATE_LIMIT', 'MODEL_PROVIDER_UNAVAILABLE', 'MODEL_REQUEST_REJECTED', 'UNKNOWN_INVOCATION_RESULT','ACTION_EFFECT_UNVERIFIED'}:
                        outcome = node.get('configuration', {}).get('error_outcome')
                        if outcome and any(edge.get('outcome') == outcome for edge in self.outgoing(workflow, node['node_id'])):
                            self.finish_node(db, run, workflow, node, outcome=outcome)
                            run['node_states'][node['node_id']] = 'failed'
                            runtime.event(db, run, 'node.failed', {'node_id': node['node_id'], 'invocation_id': run.get('node_invocations', {}).get(node['node_id']), 'error_code': code})
                            runtime.save(db, run)
                            continue
                    if code:
                        self.fail(db, run, code, blocked=code in {'SMTP_DELIVERY_UNCERTAIN', 'MODEL_INVOCATION_FAILED', 'MODEL_PROVIDER_TIMEOUT', 'MODEL_PROVIDER_CONNECTION', 'MODEL_PROVIDER_AUTH', 'MODEL_PROVIDER_RATE_LIMIT', 'MODEL_PROVIDER_UNAVAILABLE', 'MODEL_REQUEST_REJECTED', 'UNKNOWN_INVOCATION_RESULT','ACTION_EFFECT_UNVERIFIED'})
                        return runtime.public(run)
                    try:
                        workflow, _ = runtime.execution_revision(db, run, auth)
                        runtime.check_deadlines(run, workflow, agent)
                        self.finish_node(db, run, workflow, node, output)
                    except Exception as failure:
                        runtime.event(db, run, 'invocation.revalidation_failed', {
                            'node_id': node['node_id'], 'invocation_id': invocation_id,
                            'error_code': failure.code if isinstance(failure, (RuntimeFailure, RegistryError)) else 'INVALID_EXECUTION_DATA'})
                        self.fail(db, run, 'POST_INVOCATION_REVALIDATION_FAILED', blocked=True)
                        return runtime.public(run)

    def pause_policy_action(self, db, run, workflow, node):
        runtime = self.runtime
        action_hash = self.action_digest(node, run, workflow)
        approval = dict(approval_id='approval_' + uuid4().hex, workflow_id=run['workflow_id'],
            workflow_version=run['workflow_version'], status='pending', allowed_decisions=['approved', 'rejected'],
            action_digest=action_hash, resolved_payload=self.params(node, run, workflow, now=runtime.clock()),
            tool_id=node['tool_id'], operation='external_action')
        run['approvals'].append(approval)
        run['approval_context'] = dict(node_id=node['node_id'], gate_id='workspace_action_review', action_digest=action_hash,
            policy_review=True, expires_at=run['created_at'] + min(workflow['execution_policy']['limits']['timeout_seconds'], runtime.governance.effective(run, db)['limits'].get('timeout_seconds', float('inf'))))
        run['lease_until'] = 0
        runtime.event(db, run, 'approval.pending', dict(approval_id=approval['approval_id'], node_id=node['node_id'],
            tool_id=node['tool_id'], policy_review=True, policy_revision=runtime.governance.read(db, run['workspace_id'])['revision']))
        runtime.transition(db, run, 'paused_for_approval')
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
            rows = db.execute("SELECT document FROM runtime_runs WHERE workspace=? AND EXISTS (SELECT 1 FROM json_each(runtime_runs.document,'$.approvals') a WHERE json_extract(a.value,'$.approval_id')=?) LIMIT 1", (approver['subject']['workspace_id'], payload.get('approval_id'))).fetchall()
            run = next((json.loads(row[0]) for row in rows if any(a['approval_id'] == payload.get('approval_id') for a in json.loads(row[0])['approvals'])), None)
            if run is None:
                raise RuntimeFailure('APPROVAL_NOT_FOUND', 'The approval was not found in this workspace.', 404)
            if payload.get('workflow_id') != run['workflow_id'] or payload.get('workflow_version') != run['workflow_version']:
                raise RuntimeFailure('APPROVAL_REFERENCE_MISMATCH', 'Approval must reference the exact workflow revision.')
            workflow = runtime.store.get(db, run['workspace_id'], run['workflow_id'], run['workflow_version'])
            if not workflow or digest(workflow) != run['workflow_digest'] or workflow['status'] not in {'approved', 'published'}:
                raise RuntimeFailure('REVISION_CHANGED', 'The reviewed approval revision is no longer current.')
            evidence = db.execute("SELECT document FROM runtime_events WHERE workspace=? AND run_id=? AND json_extract(document,'$.event_type')='approval.pending' AND json_extract(document,'$.details.approval_id')=? ORDER BY sequence LIMIT 1", (run['workspace_id'], run['run_id'], payload.get('approval_id'))).fetchone()
            node_id = json.loads(evidence[0]).get('details', {}).get('node_id') if evidence else None
            policy_node = next((n for n in workflow['nodes'] if n['node_id'] == node_id), None)
            gate = next((g for g in workflow['approval_gates'] if policy_node and g['approval_gate_id'] == policy_node.get('approval_gate_id')), None)
            policy_review = bool(run.get('approval_context', {}).get('policy_review') and evidence and json.loads(evidence[0]).get('details', {}).get('policy_review'))
            if policy_review:
                gate = dict(approval_gate_id='workspace_action_review', approver_roles=['admin', 'approver'], on_reject='stop')
            if gate is None:
                raise RuntimeFailure('APPROVAL_POLICY_UNAVAILABLE', 'The exact recorded approval policy is unavailable.')
            runtime.authorize(approver, 'workflow.approve', set(gate['approver_roles']))
            # The exact persisted revision gate determines decision authority.
            approval = next(a for a in run['approvals'] if a['approval_id'] == payload['approval_id'])
            decision = payload.get('decision')
            if decision not in {'approved', 'rejected'}:
                raise RuntimeFailure('INVALID_APPROVAL_DECISION', 'Choose approved or rejected.', 400)
            if approval['status'] == 'superseded':
                raise RuntimeFailure('APPROVAL_NOT_PENDING', 'This approval was superseded by a reviewed revision.')
            old = run.get('approval_decisions', {}).get(approval['approval_id'])
            if old:
                # A refreshed browser or scheduler can use a new transport key.
                # Authorization above still applies; replay never changes the
                # original approver, audit trail, run state or external effects.
                if old.get('decision') != decision:
                    raise RuntimeFailure('APPROVAL_ALREADY_DECIDED', 'This gate already has a different decision. Refresh to see its current status.')
                return runtime.public(run)
            if run['status'] != 'paused_for_approval' or approval['status'] != 'pending':
                raise RuntimeFailure('APPROVAL_NOT_PENDING', 'The approval is no longer pending.')
            if runtime.clock() >= run['approval_context']['expires_at']:
                self.expire(db, run)
                return runtime.public(run)
            if policy_review and self.action_digest(policy_node, run, workflow) != approval.get('action_digest'):
                raise RuntimeFailure('APPROVAL_ACTION_MISMATCH', 'The proposed action changed after review was requested.', 403)
            approval.update(status=decision, allowed_decisions=[])
            run.setdefault('approval_decisions', {})[approval['approval_id']] = dict(key=digest(key), decision=decision, subject=approver['subject']['subject_id'], action_digest=run.get('approval_context', {}).get('action_digest'), required_roles=gate['approver_roles'])
            runtime.event(db, run, 'approval.' + decision, {'approval_id': approval['approval_id'], 'node_id': run['approval_context']['node_id'], 'actor_id': approver['subject']['subject_id']})
            node = next(n for n in workflow['nodes'] if n['node_id'] == run['approval_context']['node_id'])
            if policy_review:
                if decision == 'rejected':
                    runtime.transition(db, run, 'rejected')
                else:
                    run.setdefault('approval_evidence', []).append(dict(gate_id=gate['approval_gate_id'], approval_id=approval['approval_id']))
                    runtime.transition(db, run, 'running')
                return runtime.public(run)
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
