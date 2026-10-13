"""Extension-only approval composition for independently reviewed workflows."""
from copy import deepcopy
import time
from registry import RegistryService
from workflow_api.registry_adapter import RegistryAdapter


class ExtensionRegistry(RegistryService):
    def merge_approval_evidence(self, grants, auth, request_id=None):
        # Workflow review adds exact grants without discarding unrelated approvals.
        # The original update_approval_evidence method retains its replacement
        # semantics, including explicit operator revocation with an empty snapshot.
        if not isinstance(grants, dict):
            return self.update_approval_evidence(grants, auth, request_id)
        with self._lock:
            retained = {fingerprint: deepcopy(grant) for fingerprint, grant in self._policy.approval_grants.items()
                        if grant.get('expires_at', 0) > time.time()}
            retained.update(deepcopy(grants))
            return self.update_approval_evidence(retained, auth, request_id)


class ExtensionRegistryAdapter(RegistryAdapter):
    def approve_pending(self, workflow, auth):
        if not self.auto_resolve_planner:
            return self._review(workflow, auth)
        pending = {}
        for agent in workflow['agents']:
            for reference in workflow['tools']:
                if reference['capability'] not in agent['capabilities']: continue
                candidates = self._tool_candidates(reference['capability'], auth)
                record = next((candidate for candidate in candidates if candidate['tool_id'] == reference['tool_id']), None)
                if record is None: continue
                definition = record['definition']
                response = self.service.assign(agent['agent_id'], reference['capability'], definition['input_schema'],
                    definition['output_schema'], auth, workflow['workflow_id'], workflow['version'],
                    destination=next(iter(definition.get('allowed_destinations', [])), None), tool_id=definition['tool_id'])
                assignment = response['data'].get('assignment')
                if assignment and assignment.get('approval_fingerprint') and assignment['authorization_state'] == 'pending_approval':
                    pending[assignment['approval_fingerprint']] = {
                        'reference': 'approval_' + workflow['workflow_id'] + '_' + str(workflow['version']),
                        'expires_at': time.time() + 86400, 'approver': deepcopy(auth)}
        if pending: self.service.merge_approval_evidence(pending, auth)
        return self._review(workflow, auth)
