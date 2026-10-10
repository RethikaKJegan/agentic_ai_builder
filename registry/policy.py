"""Trusted registry policy. Construct only from authenticated server configuration."""
from dataclasses import dataclass, field
from .contracts import RegistryError, validate
from .safety import reject_secrets


@dataclass
class WorkspacePolicy:
    workspace_id: str
    version: int = 1
    agent_permissions: set = field(default_factory=lambda: {'workflow.read_input'})
    agent_limits: dict = field(default_factory=lambda: dict(max_llm_calls=10, max_tool_calls=20,
        max_tokens=20000, max_retries=3, timeout_seconds=300, max_estimated_cost_usd=10))
    approved_providers: set = field(default_factory=set)
    allowed_destinations: set = field(default_factory=set)
    credential_references: dict = field(default_factory=dict)
    # Each opaque credential reference maps to provider_id and granted scopes.
    remaining_quota: dict = field(default_factory=dict)
    max_risk: str = 'medium'
    max_tool_cost_usd: float = 1
    max_tool_timeout_seconds: int = 120
    max_tool_retries: int = 3
    approval_grants: dict = field(default_factory=dict)
    # Binding fingerprints map to expiring approval references and trusted approver auth.
    approval_roles: set = field(default_factory=lambda: {'approver'})


def authorize_subject(auth, policy, permission):
    reject_secrets(auth)
    validate(auth, 'auth')
    if not auth['subject']['subject_id'] or not auth['subject']['workspace_id']:
        raise RegistryError('AUTHENTICATION_REQUIRED', 'An authenticated subject is required.', status=401)
    if auth['decision'] != 'allow' or auth['subject']['workspace_id'] != policy.workspace_id:
        raise RegistryError('WORKSPACE_NOT_AUTHORIZED', 'The workspace is not authorized.', status=403)
    roles = set(auth['roles'])
    needed_roles = {'admin'} if permission == 'tools.manage' else {'admin', 'builder', 'viewer', 'approver'}
    if permission == 'tools.assign':
        needed_roles = {'admin', 'builder'}
    if not roles & needed_roles or permission not in auth['permissions']:
        raise RegistryError('OPERATION_NOT_AUTHORIZED', 'The subject cannot perform this registry operation.', status=403)


def authorize_tool(tool, agent, auth, policy, credential_reference, destination):
    if tool['availability'] != 'enabled':
        raise RegistryError('TOOL_UNAVAILABLE', 'The tool is not enabled.', status=403)
    if tool['provider_id'] not in policy.approved_providers:
        raise RegistryError('PROVIDER_NOT_AUTHORIZED', 'The provider is not approved.', status=403)
    permissions = set(tool['permission_scopes'])
    if permissions - set(agent['permissions']) or permissions - set(auth['permissions']):
        raise RegistryError('MISSING_PERMISSION', 'Tool permissions are not granted to subject and agent.', status=403)
    scopes = set(tool['authentication'].get('scopes', [])) | permissions
    missing = scopes - set(auth['scopes'])
    if missing:
        raise RegistryError('MISSING_SCOPE', 'Required tool scopes are missing.', details={'missing_scopes': sorted(missing)}, status=403)
    if tool['authentication']['mode'] != 'none' or tool['authentication']['credential_reference_required']:
        credential = policy.credential_references.get(credential_reference)
        if not credential or credential['provider_id'] != tool['provider_id'] or scopes - set(credential['scopes']):
            raise RegistryError('CREDENTIAL_NOT_CONFIGURED', 'An authorized credential reference is required.', status=403)
    if policy.remaining_quota.get(tool['tool_id'], 0) <= 0:
        raise RegistryError('QUOTA_EXCEEDED', 'The tool has no remaining quota.', status=403)
    risks = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
    if risks[tool['risk_level']] > risks[policy.max_risk]:
        raise RegistryError('RISK_NOT_AUTHORIZED', 'Tool risk exceeds workspace policy.', status=403)
    if (tool['estimated_cost']['per_call'] > policy.max_tool_cost_usd or
        tool['timeout_seconds'] > policy.max_tool_timeout_seconds or
        tool['retry_policy']['max_retries'] > policy.max_tool_retries or
        tool['estimated_cost']['per_call'] * agent['limits']['max_tool_calls'] > agent['limits'].get('max_estimated_cost_usd', policy.agent_limits['max_estimated_cost_usd']) or
        tool['timeout_seconds'] > agent['limits']['timeout_seconds'] or
        tool['retry_policy']['max_retries'] > agent['limits']['max_retries'] or
        agent['limits']['max_tool_calls'] < 1):
        raise RegistryError('TOOL_LIMIT_EXCEEDED', 'Tool execution policy exceeds authorized limits.', status=403)
    destinations = set(tool.get('allowed_destinations', []))
    needs_destination = tool['provider_id'] in {'http', 'webhook'} or bool(destinations)
    if needs_destination and (not destination or destination not in destinations or destination not in policy.allowed_destinations):
        raise RegistryError('DESTINATION_NOT_AUTHORIZED', 'The destination is outside the approved allowlist.', status=403)
