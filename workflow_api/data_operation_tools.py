"""Real Registry bindings for direct, reviewed point database operations."""
import hashlib
import json
import time

from registry.policy import WorkspacePolicy
from registry.service import RegistryService
from .service import ApiFailure


def tool_definition(engine, action, operation_id=None, index=0):
    reference = {'type': 'string'} if operation_id is None else {'const': operation_id}
    return dict(
        tool_id=f'{engine}_{action}_record', provider_id=engine, capability=f'database.{action}',
        description=f'{action.title()} one explicitly authorized, stable-key record; writes require a reviewed immutable operation.',
        input_schema=dict(type='object', additionalProperties=False, required=['operation_id', 'step_index'],
                          properties=dict(operation_id=reference, step_index={'const': index})),
        output_schema=dict(type='object', additionalProperties=False, required=['matched_records', 'affected_records'],
                           properties={name: dict(type='integer', minimum=0, maximum=1)
                                       for name in ('matched_records', 'affected_records')}),
        authentication=dict(mode='secret_reference', credential_reference_required=True,
                            scopes=['workspace:read' if action == 'read' else 'workspace:write']),
        # Direct console permission, exact owner/target/field policy and human
        # approval are additionally checked by DataOperations, not model input.
        permission_scopes=[], availability='enabled', risk_level='low' if action == 'read' else 'high',
        rate_limits=dict(requests_per_minute=20), estimated_cost=dict(currency='USD', per_call=0),
        retry_policy=dict(max_retries=0, retryable_errors=[]), timeout_seconds=30,
        approval_required=action != 'read', allowed_destinations=[])


def registered_grant(auth, engine, action, cid, did, operation_id, index):
    definition = tool_definition(engine, action, operation_id, index)
    definition['allowed_destinations'] = [did]
    scopes = set(definition['authentication']['scopes'])
    reference = 'cred_database_' + hashlib.sha256(cid.encode()).hexdigest()[:24]
    policy = WorkspacePolicy(workspace_id=auth['subject']['workspace_id'], approved_providers={engine},
                             agent_permissions=set(), max_risk='high', allowed_destinations={did},
                             credential_references={reference: dict(provider_id=engine, scopes=list(scopes))},
                             remaining_quota={definition['tool_id']: 1}, approval_roles={'admin', 'approver'})
    registry = RegistryService(policy)
    bootstrap = dict(subject=dict(subject_id='database_registry', workspace_id=policy.workspace_id),
                     decision='allow', roles=['admin'], permissions=['tools.manage'], scopes=[])

    def checked(result):
        if result['status'] != 200:
            raise ApiFailure('DATA_WRITE_GRANT_DENIED', 'The exact registered database tool is not authorized.', 403)
        return result['data']

    checked(registry.register_tool(definition, bootstrap, credential_reference=reference))
    agent = dict(agent_id='database_operator', name='Database operator', role='Reviewed point operations',
                 goal='Execute only the exact prepared operation.', instructions='No model invocation; use only the reviewed reference.',
                 model=dict(provider='none', model_id='deterministic'),
                 input_schema=definition['input_schema'], output_schema=definition['output_schema'],
                 capabilities=[definition['capability']], allowed_tool_ids=[], permissions=[],
                 limits=dict(max_llm_calls=0, max_tool_calls=1, max_tokens=1, max_retries=0,
                             timeout_seconds=30, max_estimated_cost_usd=0),
                 retry_policy=dict(max_retries=0, backoff_seconds=0), approval_requirements=[],
                 guardrails=dict(pii_redaction=True, prompt_injection_detection=True, output_validation=True))
    checked(registry.register_agent(agent, bootstrap))

    def assign():
        return checked(registry.assign(agent['agent_id'], definition['capability'],
                                       definition['input_schema'], definition['output_schema'], auth,
                                       operation_id, 1, destination=did, tool_id=definition['tool_id']))['assignment']

    grant = assign()
    if action != 'read':
        # The caller's explicit execute request is the human approval. Rebind
        # that real authority to the next policy revision's exact fingerprint.
        keys = ('subject_id', 'workspace_id', 'agent_id', 'agent_version', 'tool_id', 'tool_version',
                'workflow_id', 'workflow_version', 'policy_version', 'credential_reference',
                'destination', 'input_schema', 'output_schema')
        binding = {key: grant[key] for key in keys}
        policy.version = binding['policy_version'] = 2
        digest = hashlib.sha256(json.dumps(binding, sort_keys=True).encode()).hexdigest()
        policy.approval_grants[digest] = dict(reference=operation_id, expires_at=time.time()+60, approver=auth)
        checked(registry.update_policy(policy, bootstrap))
        grant = assign()
    if grant['authorization_state'] != 'authorized':
        raise ApiFailure('DATA_WRITE_APPROVAL_REQUIRED', 'This operation requires current authorized human approval.', 403)
    checked(registry.revalidate_assignment(grant['authorization_reference'], agent['agent_id'],
                                          definition['tool_id'], operation_id, 1, auth))
    return grant
