"""Run an isolated, read-only GitHub delegation example with real model calls."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import tempfile
from threading import Event, Lock
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from registry import RegistryService, WorkspacePolicy
from registry.safety import reject_secrets
from runtime import RuntimeService
from runtime.connectors import HTTPJSONConnector
from runtime.crew import CrewExecutor
from runtime.graph import GraphRunner
from runtime.model import OpenAIModelFactory
from workflow_api.live_providers import environment, model_configuration
from workflow_api.registry_adapter import RegistryAdapter
from workflow_api.service import WorkflowService
from workflow_api.storage import WorkflowStore


def run_example(repository, notes, claim, evidence_path):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
        raise ValueError('Use an owner/repository identifier.')
    env = environment()
    model, rates, tokenizers = model_configuration(env)
    from openai import OpenAI
    client = OpenAI(api_key=env['OPENAI_API_KEY'], base_url=env.get('OPENAI_BASE_URL'), max_retries=0, timeout=60)
    factory = OpenAIModelFactory(rates, client=client, tokenizers=tokenizers)
    auth = {'subject': {'subject_id': 'example-operator', 'workspace_id': 'local-workspace'},
            'roles': ['admin'], 'permissions': ['workflow.execute', 'runs.view', 'tools.assign', 'tools.read', 'tools.manage', 'data.read'],
            'scopes': ['data.read', 'github.access'], 'decision': 'allow'}
    policy = WorkspacePolicy('local-workspace', agent_permissions={'workflow.read_input', 'data.read'},
        approved_providers={'github'}, credential_references={'cred_example_github': {'provider_id': 'github', 'scopes': auth['scopes']}},
        remaining_quota={'github_rest_request': 2})
    registry = RegistryService(policy)
    tool = json.loads((ROOT / 'shared/contracts/examples/tools/github-rest.json').read_text())
    tool.update(availability='enabled', timeout_seconds=15, retry_policy={'max_retries': 0, 'retryable_errors': []})
    response = registry.register_tool(tool, auth, 'cred_example_github')
    if response['status'] != 200:
        raise ValueError('Example tool registration failed.')
    findings_schema = {'type': 'object', 'additionalProperties': False,
        'required': ['repository', 'archived', 'default_branch', 'claim_status', 'assessment', 'source_url'],
        'properties': {'repository': {'type': 'string'}, 'archived': {'type': 'boolean'}, 'default_branch': {'type': 'string'},
            'claim_status': {'enum': ['confirmed', 'contradicted', 'partially_confirmed']},
            'assessment': {'type': 'string'}, 'source_url': {'type': 'string'}}}
    base = json.loads((ROOT / 'shared/contracts/examples/agents/valid-classifier.json').read_text())
    master = deepcopy(base)
    master.update(agent_id='project_update_master', name='Project update coordinator', role='Project update coordinator',
        goal='Draft a project update and incorporate checked repository facts.', capabilities=[], hierarchy_role='master',
        input_schema={'type': 'object'},
        output_schema={'type': 'object', 'additionalProperties': False, 'required': ['project_update', 'repository_check'],
            'properties': {'project_update': {'type': 'string'}, 'repository_check': findings_schema}},
        instructions='The request contains project notes and a repository claim. Delegate the repository check to the available specialist. '
            'Include continuation holding the notes and remaining drafting work, so you keep working while the check runs. '
            'On the next turn with a pending specialist and undrafted notes, draft the independent project update and return continue '
            'with that draft in continuation; do not wait before drafting. Preserve the draft, then collect the check and finish '
            'with a project update and repository_check from the specialist. Treat contradictory claims as unverified until checked.')
    master['limits'].update(max_llm_calls=6, max_tokens=20000, timeout_seconds=300, max_estimated_cost_usd=.2, max_retries=0)
    child = deepcopy(base)
    child.update(agent_id='repository_specialist', name='Repository facts specialist', role='Repository facts specialist',
        goal='Check repository metadata and assess whether the supplied claim is supported.',
        hierarchy_role='sub_agent', parent_agent_id=master['agent_id'], capabilities=['retrieve_records'], permissions=['data.read'],
        input_schema={'type': 'object', 'additionalProperties': False, 'required': ['repository', 'claim'],
            'properties': {'repository': {'type': 'string'}, 'claim': {'type': 'string'}}}, output_schema=findings_schema,
        instructions='Use your assigned GitHub tool to GET /repos/{repository} for the supplied owner/repository. '
            'Examine actual archived and default_branch fields, compare them to the claim, and explain the findings. '
            'Use html_url for source_url and full_name for repository. Do not infer maintenance quality merely from archived=false. '
            'Return finish only after you have actual tool evidence. Never invent repository facts.')
    child['limits'].update(max_llm_calls=3, max_tool_calls=2, max_tokens=18000, timeout_seconds=300, max_estimated_cost_usd=.15, max_retries=0)
    records, agents = {}, []
    for definition in [master, child]:
        definition['model'].update(model_id=model)
        definition['retry_policy']['max_retries'] = 0
        response = registry.register_agent(definition, auth)
        if response['status'] != 200:
            raise ValueError('Example agent registration failed.')
        records[definition['agent_id']] = response['data']['agent']
        agent = {key: deepcopy(value) for key, value in definition.items() if key not in {'name', 'retry_policy', 'guardrails'}}
        if definition is child:
            agent['allowed_tool_ids'] = [tool['tool_id']]
        agents.append(agent)
    workflow = json.loads((ROOT / 'shared/contracts/examples/workflows/support-triage.json').read_text())
    workflow.update(workflow_id='live_repository_delegation_example', name='Project update with repository fact check',
        description='An isolated read-only example with real model and GitHub calls.', status='approved', agents=agents,
        conditions=[], approval_gates=[], outputs=[], tools=[{'tool_id': tool['tool_id'], 'capability': 'retrieve_records'}],
        nodes=[{'node_id': 'start', 'kind': 'trigger', 'label': 'Project update requested'},
               {'node_id': 'master', 'kind': 'agent', 'label': 'Draft project update', 'agent_id': master['agent_id']},
               {'node_id': 'finish', 'kind': 'output', 'label': 'Combined checked update', 'configuration': {'input_mapping': {'result': 'outputs.master'}}}],
        edges=[{'edge_id': 'start_master', 'source': 'start', 'target': 'master'}, {'edge_id': 'master_finish', 'source': 'master', 'target': 'finish'}])
    workflow['metadata'] = {'workspace_id': 'local-workspace', 'approved_by': auth['subject']['subject_id'],
        'validation_state': 'validated', 'example_only': True, 'dynamic_delegation': {'master': {'max_rounds': 6, 'max_tasks': 2}}}
    workflow['execution_policy']['limits'].update(max_llm_calls=9, max_tool_calls=2, max_tokens=38000, timeout_seconds=300, max_estimated_cost_usd=.35)
    bindings = [{'workflow_id': workflow['workflow_id'], 'workflow_version': 1, 'agent_id': child['agent_id'],
                 'capability': 'retrieve_records', 'tool_id': tool['tool_id'], 'input_schema': tool['input_schema'], 'output_schema': tool['output_schema']}]
    adapter = RegistryAdapter(registry, records, bindings)
    reading, independent_work_done = Event(), Event()
    lock = Lock()
    observed = {'model_calls': 0, 'tool_calls': 0, 'master_turns': 0, 'calls': []}

    class ObservedConnector(HTTPJSONConnector):
        def invoke(self, grant, inputs, effect_id):
            started = time.monotonic()
            observed['tool_calls'] += 1
            reading.set()
            try:
                output = super().invoke(grant, inputs, effect_id)
                data = output['result']
                observed['source_facts'] = {key: data[key] for key in ['full_name', 'archived', 'default_branch', 'html_url']}
                # Test synchronization keeps the result outstanding until the
                # independent master turn completes; model outputs stay live.
                if not independent_work_done.wait(60):
                    raise ValueError('Independent master turn did not complete.')
                return output
            finally:
                observed['tool_interval'] = [started, time.monotonic()]

    class ObservedExecutor(CrewExecutor):
        def record_call(self, agent, operation):
            started = time.monotonic()
            with lock:
                observed['model_calls'] += 1
            output = operation()
            with lock:
                observed['calls'].append({'agent_id': agent['agent_id'], 'action': output['action'], 'interval': [started, time.monotonic()]})
            return output

        def invoke_decision(self, agent, inputs, invocation_id, schema):
            observed['master_turns'] += 1
            turn = observed['master_turns']
            if turn == 2 and not reading.wait(60):
                independent_work_done.set()
                raise ValueError('Specialist did not request its tool.')
            try:
                return self.record_call(agent, lambda: super(ObservedExecutor, self).invoke_decision(agent, inputs, invocation_id, schema))
            finally:
                if turn == 2:
                    independent_work_done.set()

        def invoke_tool_decision(self, agent, inputs, invocation_id, schema):
            return self.record_call(agent, lambda: super(ObservedExecutor, self).invoke_tool_decision(agent, inputs, invocation_id, schema))

    def resolve(reference):
        if reference != 'cred_example_github':
            raise ValueError('Unknown example credential reference.')
        return {'provider_id': 'github', 'token': env.get('GITHUB_TOKEN', '')}
    connector = ObservedConnector(resolve, 'github', 'https://api.github.com', timeout=15,
        required_tool_id=tool['tool_id'], headers={'User-Agent': 'AgenticAIBuilder-DelegationExample/1.0'})
    evidence_path = Path(evidence_path)
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='delegation-example-', dir=ROOT / '.local') as directory:
        store = WorkflowStore(Path(directory) / 'runtime.sqlite3')
        service = WorkflowService(store, registry_adapter=adapter)
        runtime = RuntimeService(service)
        with store.transaction() as db:
            store.put(db, auth['subject']['workspace_id'], workflow)
        text = f'Project notes: {notes}\nRepository: {repository}\nClaim to check: {claim}'
        request = {'request_id': 'req_live_repository_example', 'operation': 'execute_workflow', 'idempotency_key': 'live_repository_example',
                   'payload': {'workflow_id': workflow['workflow_id'], 'workflow_version': 1, 'inputs': {'request_text': text}}}
        run_id = runtime.create_run(request, auth)['run_id']
        result = GraphRunner(runtime, agents=ObservedExecutor(adapter, factory), connectors={tool['tool_id']: connector}).advance(run_id, auth)
        with store.transaction() as db:
            stored = runtime.load(db, run_id, auth)
        events = runtime.events(run_id, auth)['items']
        output = stored['outputs'].get('master')
        interval = observed.get('tool_interval', [0, 0])
        overlap = any(call['agent_id'] == master['agent_id'] and call['action'] == 'continue' and
            interval[0] <= call['interval'][0] < call['interval'][1] <= interval[1] for call in observed['calls'])
        facts = observed.get('source_facts', {})
        checked = (output or {}).get('repository_check', {})
        facts_match = bool(facts) and all(checked.get(target) == facts.get(source) for target, source in
            [('repository', 'full_name'), ('archived', 'archived'), ('default_branch', 'default_branch'), ('source_url', 'html_url')])
        evidence = {'captured_at': datetime.now(timezone.utc).isoformat(), 'transport': 'live model and live read-only GitHub REST',
            'synchronization': 'The tool result is held until master turn two completes to verify independent work overlap.',
            'model': model, 'repository': repository, 'input': {'notes': notes, 'claim': claim},
            'run': result, 'output': output, 'observed': observed, 'overlap_verified': overlap, 'source_facts_match': facts_match,
            'workflow': workflow, 'events': events}
        reject_secrets(evidence)
        evidence_path.write_text(json.dumps(evidence, indent=2) + '\n')
        if result['status'] != 'completed' or not overlap or not facts_match:
            raise ValueError('Live example did not pass all checks; inspect the saved evidence.')
        return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', default='octocat/Hello-World')
    parser.add_argument('--notes', default='Design mockups are finished. The test plan is being prepared.')
    parser.add_argument('--claim', default='The repository is archived and its default branch is main.')
    parser.add_argument('--evidence', default=str(ROOT / '.local/live-delegation-example/evidence.json'))
    args = parser.parse_args()
    try:
        evidence = run_example(args.repository, args.notes, args.claim, args.evidence)
    except Exception as exc:
        print('Live example failed:', getattr(exc, 'code', type(exc).__name__), file=sys.stderr)
        return 1
    print(json.dumps({'status': evidence['run']['status'], 'run_id': evidence['run']['run_id'],
        'model_calls': evidence['observed']['model_calls'], 'tool_calls': evidence['observed']['tool_calls'],
        'overlap_verified': evidence['overlap_verified'], 'source_facts_match': evidence['source_facts_match'],
        'output': evidence['output'], 'evidence': args.evidence}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
