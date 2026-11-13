"""Workspace safety restrictions intersect immutable run policy and reviewed limits.

Policies can only tighten reviewed workflow/Registry authority. No model-provided
metadata grants capabilities. Existing runs retain their original restrictions.
"""
from copy import deepcopy
import json
import math
from uuid import uuid4

from .service import RuntimeFailure, digest

LIMITS = {'timeout_seconds', 'max_llm_calls', 'max_tool_calls', 'max_retries', 'max_tokens', 'max_delegation_calls'}
TIMEOUTS = {'model_timeout_seconds', 'tool_timeout_seconds', 'delegation_timeout_seconds', 'step_timeout_seconds'}
DEFAULT = dict(read_only=False, require_action_approval=False, restricted_tools=[], restricted_sources=[], limits={}, **{k: None for k in TIMEOUTS})


class GovernancePolicy:
    def __init__(self, runtime):
        self.runtime = runtime
        with runtime.store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS runtime_governance (workspace TEXT PRIMARY KEY, revision INTEGER NOT NULL, document TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS runtime_governance_audit (event_id TEXT PRIMARY KEY, workspace TEXT, actor TEXT, timestamp REAL, revision INTEGER, policy_sha256 TEXT)')

    def read(self, db, workspace):
        row = db.execute('SELECT revision,document FROM runtime_governance WHERE workspace=?', (workspace,)).fetchone()
        return dict(revision=row[0], policy=json.loads(row[1])) if row else dict(revision=0, policy=deepcopy(DEFAULT))

    def get(self, auth):
        self.runtime.authorize(auth, 'runs.view', {'admin', 'builder', 'viewer', 'approver'})
        with self.runtime.store.transaction(write=False) as db:
            result = self.read(db, auth['subject']['workspace_id'])
            result['audit'] = [dict(actor_id=row[0], timestamp=row[1], revision=row[2], policy_sha256=row[3]) for row in db.execute('SELECT actor,timestamp,revision,policy_sha256 FROM runtime_governance_audit WHERE workspace=? ORDER BY revision DESC LIMIT 10', (auth['subject']['workspace_id'],)).fetchall()]
        return dict(**result, scope='workspace', enforcement='Restrictions intersect the run snapshot, reviewed workflow/agent limits and Registry grants.', cost_accounting='Estimated costs are not settled charges. Token and call limits remain available.')

    def update(self, auth, body):
        self.runtime.authorize(auth, 'workflow.edit', {'admin'})
        if 'workspace:write' not in auth['scopes']:
            raise RuntimeFailure('OPERATION_NOT_AUTHORIZED', 'Workspace administration scope is required.', 403)
        if not isinstance(body, dict) or set(body) != {'revision', 'policy'} or type(body['revision']) is not int:
            raise RuntimeFailure('INVALID_POLICY', 'Supply the current revision and a complete typed policy.', 422)
        policy = body['policy']
        if not isinstance(policy, dict) or set(policy) != set(DEFAULT):
            raise RuntimeFailure('INVALID_POLICY', 'Supply the supported policy fields.', 422)
        if any(type(policy[k]) is not bool for k in ('read_only', 'require_action_approval')):
            raise RuntimeFailure('INVALID_POLICY', 'Safety flags must be booleans.', 422)
        for key in ('restricted_tools', 'restricted_sources'):
            values = policy[key]
            if not isinstance(values, list) or len(values) > 500 or any(not isinstance(v, str) or not v.strip() or len(v) > 256 for v in values) or len(set(values)) != len(values):
                raise RuntimeFailure('INVALID_POLICY', 'Restrictions must be unique nonempty resource identifiers.', 422)
        if not isinstance(policy['limits'], dict) or set(policy['limits']) - LIMITS:
            raise RuntimeFailure('INVALID_POLICY', 'Use supported execution limits.', 422)
        for key, value in {**policy['limits'], **{k: policy[k] for k in TIMEOUTS if policy[k] is not None}}.items():
            if type(value) is not int or value < (1 if 'seconds' in key else 0) or value > 2147483647:
                raise RuntimeFailure('INVALID_POLICY', 'Limits must be bounded nonnegative integers; durations must be positive.', 422)
        from registry.safety import reject_secrets
        reject_secrets(policy)
        with self.runtime.store.transaction() as db:
            workspace = auth['subject']['workspace_id']
            old = self.read(db, workspace)
            if old['revision'] != body['revision']:
                raise RuntimeFailure('POLICY_CONFLICT', 'The policy changed. Refresh before saving.', 409)
            revision = old['revision'] + 1
            if old['revision']:
                changed = db.execute('UPDATE runtime_governance SET revision=?,document=? WHERE workspace=? AND revision=?', (revision, json.dumps(policy), workspace, old['revision']))
                if changed.rowcount != 1:
                    raise RuntimeFailure('POLICY_CONFLICT', 'The policy changed. Refresh before saving.', 409)
            else:
                db.execute('INSERT INTO runtime_governance VALUES (?,?,?)', (workspace, revision, json.dumps(policy)))
            db.execute('INSERT INTO runtime_governance_audit VALUES (?,?,?,?,?,?)', ('policy_' + uuid4().hex, workspace, auth['subject']['subject_id'], self.runtime.clock(), revision, digest(policy)))
        return self.get(auth)

    @staticmethod
    def intersect(*policies):
        result = deepcopy(DEFAULT)
        for policy in policies:
            result['read_only'] |= policy.get('read_only', False)
            result['require_action_approval'] |= policy.get('require_action_approval', False)
            for key in ('restricted_tools', 'restricted_sources'):
                result[key] = sorted(set(result[key]) | set(policy.get(key, [])))
            for key, value in policy.get('limits', {}).items():
                result['limits'][key] = min(result['limits'].get(key, value), value)
            for key in TIMEOUTS:
                if policy.get(key) is not None:
                    result[key] = min(result[key] or policy[key], policy[key])
        return result

    def effective(self, run, db=None):
        if db is None:
            with self.runtime.store.transaction(write=False) as connection:
                return self.effective(run, connection)
        current = self.read(db, run['workspace_id'])
        return self.intersect(run.get('governance_policy', {}).get('policy', {}), current['policy'])

    @staticmethod
    def usage(run):
        usage = dict(run.get('usage', {}).get('workflow', {}))
        for key, value in run.get('adaptive_reasoning_usage', {}).items():
            usage[key] = usage.get(key, 0) + value
        return usage

    def check_run(self, db, run, workflow):
        policy = self.effective(run, db)
        usage = self.usage(run)
        mapping = dict(max_llm_calls='llm_calls', max_tool_calls='tool_calls', max_tokens='tokens', max_retries='retries', max_delegation_calls='delegation_calls')
        for limit, counter in mapping.items():
            if limit in policy['limits'] and usage.get(counter, 0) > policy['limits'][limit]:
                raise RuntimeFailure('GOVERNANCE_BUDGET_EXHAUSTED', 'The effective workspace execution budget is exhausted.')
        return policy

    def reserve(self, db, run, workflow, amount):
        policy = self.check_run(db, run, workflow)
        mapping = dict(llm_calls='max_llm_calls', tool_calls='max_tool_calls', tokens='max_tokens', retries='max_retries', delegation_calls='max_delegation_calls')
        for counter, value in amount.items():
            limit = policy['limits'].get(mapping.get(counter))
            if limit is not None and self.usage(run).get(counter, 0) + value > limit:
                raise RuntimeFailure('GOVERNANCE_BUDGET_EXHAUSTED', 'The next invocation exceeds the effective workspace budget.')

    def invocation_timeout(self, run, workflow, agent, kind):
        policy = self.effective(run)
        values = [workflow['execution_policy']['limits']['timeout_seconds'] - (self.runtime.clock() - run['created_at'])]
        if 'timeout_seconds' in policy['limits']:
            values.append(policy['limits']['timeout_seconds'] - (self.runtime.clock() - run['created_at']))
        if agent:
            values.append(agent['limits']['timeout_seconds'] - (self.runtime.clock() - run.get('agent_started_at', {}).get(agent['agent_id'], self.runtime.clock())))
        for key in (kind + '_timeout_seconds',):
            if policy.get(key) is not None:
                values.append(policy[key])
        if policy.get('step_timeout_seconds') is not None:
            started = run.get('node_started_at', {}).get(run.get('current_node_id'), self.runtime.clock())
            values.append(policy['step_timeout_seconds'] - (self.runtime.clock() - started))
        result = min(values)
        if not math.isfinite(result):
            raise RuntimeFailure('INVALID_POLICY', 'Invocation duration must be finite.')
        return result

    def check_tool(self, run, workflow, node, connector, definition, params):
        policy = self.effective(run)
        if node['tool_id'] in policy['restricted_tools']:
            raise RuntimeFailure('TOOL_RESTRICTED', 'This tool is restricted by workspace policy.', 403)
        # Both reviewed Registry metadata and the actual bound connector count.
        writes = bool(connector.external_write or workflow.get('metadata', {}).get('connected_contracts', {}).get(definition.get('capability'), {}).get('side_effect') in ('write', 'draft'))
        if policy['read_only'] and writes:
            raise RuntimeFailure('READ_ONLY_VIOLATION', 'Read-only execution cannot perform this action.', 403)
        context = run.get('approval_context', {})
        if writes and context.get('action_digest') and (not context.get('policy_review') or context.get('node_id') == node['node_id']):
            if self.runtime.clock() >= run['approval_context']['expires_at']:
                raise RuntimeFailure('APPROVAL_EXPIRED', 'The action approval expired before execution.', 403)
            decision = next((v for v in run.get('approval_decisions', {}).values() if v.get('decision') == 'approved' and v.get('action_digest') == run['approval_context']['action_digest']), None)
            authenticate = getattr(self.runtime, 'authenticate_current', None)
            if decision and callable(authenticate):
                reviewer = authenticate(run['workspace_id'], decision['subject'])
                if not reviewer or reviewer.get('decision') != 'allow' or 'workflow.approve' not in reviewer.get('permissions', []) or not set(reviewer.get('roles', [])) & set(decision.get('required_roles', [])):
                    raise RuntimeFailure('APPROVER_REVOKED', 'The action reviewer no longer has approval authority.', 403)
        if writes and policy['require_action_approval']:
            approved = run.get('approval_context', {}).get('action_digest')
            from .graph import GraphRunner
            if not approved or approved != GraphRunner(self.runtime).action_digest(node, run, workflow):
                raise RuntimeFailure('POLICY_APPROVAL_REQUIRED', 'This exact action requires human approval.', 403)
        source_keys = {'source_id', 'connection_id', 'data_source_id', 'dataset_id', 'source_ids', 'connection_ids'}
        found = set()
        def visit(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key in source_keys:
                        if isinstance(item, str):found.add(item)
                        elif isinstance(item, list):found.update(v for v in item if isinstance(v, str))
                    visit(item)
            elif isinstance(value, list):
                for item in value:visit(item)
        visit(params)
        visit(workflow.get('metadata', {}))
        if found & set(policy['restricted_sources']):
            raise RuntimeFailure('SOURCE_RESTRICTED', 'A selected source is restricted by workspace policy.', 403)
