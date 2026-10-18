"""Phase 5 native source/Registry/runtime tests; no cloud or paid providers."""
from copy import deepcopy
import json
from pathlib import Path
from uuid import uuid4

import pytest
from registry import RegistryService, WorkspacePolicy
from runtime import RuntimeService
from runtime.graph import GraphRunner
from workflow_api.registry_adapter import RegistryAdapter
from workflow_api.service import WorkflowService, ApiFailure
from workflow_api.data_queries import DataQueries
from workflow_api.database_workflows import DatabaseWorkflows, bind_generated, definitions, schema
from tests.test_data_operations import engines, operations, auth, request, read

ROOT = Path(__file__).resolve().parents[1]


def agent(agent_id, capabilities, role=None, parent=None):
    value = json.loads((ROOT/'shared/contracts/examples/agents/valid-classifier.json').read_text())
    value.update(agent_id=agent_id, capabilities=capabilities, input_schema={'type': 'object'}, output_schema={'type': 'object'})
    value['limits'].update(max_tool_calls=10, max_llm_calls=4, timeout_seconds=240, max_tokens=12000)
    if role:
        value['hierarchy_role'] = role
    if parent:
        value['parent_agent_id'] = parent
    return {k: v for k, v in value.items() if k not in {'name', 'retry_policy', 'guardrails'}}


@pytest.fixture
def harness(operations):
    a = auth()
    a['permissions'] += ['workflow.view', 'workflow.edit', 'workflow.plan', 'workflow.validate', 'workflow.execute', 'workflow.publish', 'runs.view', 'tools.manage', 'data.write']
    a['scopes'] += ['data.write', 'spreadsheets']
    policy = WorkspacePolicy('one', max_risk='high', agent_permissions={'workflow.read_input', 'data.write'}, approval_roles={'admin', 'approver'})
    registry = RegistryService(policy)
    adapter = RegistryAdapter(registry, auto_resolve_planner=True)
    service = WorkflowService(operations.store, registry_adapter=adapter)
    coordinator = DatabaseWorkflows(service, operations, DataQueries(operations.manager),
                                   lambda workspace, owner: a if (workspace, owner) == ('one', 'alice') else None)
    service.database_workflows = coordinator
    coordinator.register(a)
    runtime = RuntimeService(service)
    runner = service.runtime_runner = GraphRunner(runtime, connectors=coordinator.connectors())
    return dict(auth=a, coordinator=coordinator, service=service, runner=runner, runtime=runtime, operations=operations)


def workflow(h, steps=None, nodes=None, tools=None):
    w = json.loads((ROOT/'shared/contracts/examples/workflows/support-triage.json').read_text())
    tools = tools or ['database_read_record', 'database_prepare_operation', 'database_execute_operation']
    defs = {t['tool_id']: t for t in definitions()}
    w.update(workflow_id='db_workflow_'+uuid4().hex, inputs=[], outputs=[], conditions=[],
             agents=[agent('database_agent', [defs[t]['capability'] for t in tools])],
             tools=[dict(tool_id=t, capability=defs[t]['capability']) for t in tools])
    w['execution_policy']['limits'].update(max_tool_calls=20, max_llm_calls=20, max_tokens=48000, timeout_seconds=600)
    w['execution_policy']['allow_external_writes'] = True
    if nodes is None:
        target = h['operations'].testing['targets'][0]
        point = dict(connection_id=target['connection_id'], dataset_id=target['dataset_id'], identity={'id': 'seed'})
        nodes = [dict(node_id='read', kind='tool', tool_id='database_read_record', configuration={'input': point}),
                 dict(node_id='prepare', kind='tool', tool_id='database_prepare_operation',
                      configuration={'input': {'steps': steps or [request(h['operations'], action='update', identity='seed', name='Workflow updated')]}}),
                 dict(node_id='review', kind='approval', approval_gate_id='database_review'),
                 dict(node_id='execute', kind='tool', tool_id='database_execute_operation', configuration={'input_mapping': {'operation_id': 'outputs.prepare.operation_id'}})]
    w['nodes'] = [dict(node_id='start', kind='trigger', label='Start'),
                  *[{**n, 'label': n.get('label', n['node_id']), **({'agent_id': n.get('agent_id', 'database_agent')} if n['kind'] == 'tool' else {})} for n in nodes],
                  dict(node_id='finish', kind='output', label='Finish', configuration={'input': {}})]
    w['edges'] = [dict(edge_id='e'+str(i), source=a['node_id'], target=b['node_id'], **({'outcome': 'approved'} if a['kind'] == 'approval' else {})) for i, (a, b) in enumerate(zip(w['nodes'], w['nodes'][1:]))]
    w['approval_gates'] = [dict(approval_gate_id=n['approval_gate_id'], approver_roles=['admin'], timeout_seconds=300, on_reject='stop') for n in nodes if n['kind'] == 'approval']
    catalog = h['coordinator'].catalog(h['auth'])
    w['metadata'].update(database_source_ids=[s['dataset_id'] for s in catalog['sources']], unresolved_requirements=[])
    bind_generated(w, {'database_catalog': catalog})
    return w


def publish(h, w):
    def call(operation, **payload):
        result = h['service'].handle(dict(request_id='req_'+uuid4().hex, operation=operation, idempotency_key=uuid4().hex,
                                        payload=dict(workflow_id=w['workflow_id'], workflow_version=1, **payload)), h['auth'])
        assert result['status'] == 200, json.dumps(result, indent=2)
        return result
    call('save_workflow_version', workflow=w, base_version=0)
    call('validate_workflow')
    call('approve_workflow', action='approve')
    call('approve_workflow', action='publish')
    run = h['runtime'].create_run(dict(request_id='req_run', operation='execute_workflow', idempotency_key=uuid4().hex,
                                     payload=dict(workflow_id=w['workflow_id'], workflow_version=1, inputs={})), h['auth'])
    return run


def decide(h, run, decision='approved'):
    approval = run['approvals'][-1]
    return h['runner'].decide(dict(idempotency_key=uuid4().hex, payload=dict(approval_id=approval['approval_id'],
                                    workflow_id=run['workflow_id'], workflow_version=1, decision=decision)), h['auth'])


def events(h, run):
    return h['runtime'].events(run['run_id'], h['auth'], limit=500)['items']


@pytest.mark.parametrize('engine', ['pg', 'mongo'])
def test_native_read_prepare_approve_update_and_no_replay(harness, engine):
    h = harness
    w = workflow(h, [request(h['operations'], engine, 'update', 'seed', name='Workflow updated')])
    run = publish(h, w)
    run = h['runner'].advance(run['run_id'], h['auth'])
    assert run['status'] == 'paused_for_approval', events(h, run)
    assert read(h['operations'], engine, 'seed')['name'] == 'Seed'
    pending = next(e for e in events(h, run) if e['event_type'] == 'approval.pending')
    operation_id = pending['details']['database_operation_id']
    assert h['operations'].get(h['auth'], operation_id)['preview_available']
    with pytest.raises(ApiFailure, match='originating workflow'):
        h['operations'].execute(h['auth'], operation_id, {'confirm': True})
    decide(h, run)
    run = h['runner'].advance(run['run_id'], h['auth'])
    assert run['status'] == 'completed', events(h, run)
    assert read(h['operations'], engine, 'seed')['name'] == 'Workflow updated'
    assert h['runner'].advance(run['run_id'], h['auth'])['status'] == 'completed'
    outcome = next(e for e in events(h, run) if e['event_type'] == 'node.completed' and e['details']['node_id'] == 'execute')
    assert outcome['details']['output']['steps'][0]['affected_records'] == 1
    assert any(e['event_type'] == 'node.handoff' for e in events(h, run))


def test_conflict_after_runtime_approval_preserves_newer_record(harness):
    import psycopg
    from psycopg import sql
    h = harness
    run = h['runner'].advance(publish(h, workflow(h))['run_id'], h['auth'])
    decide(h, run)
    with psycopg.connect(h['operations'].testing['engines']['dsn'], autocommit=True) as conn:
        conn.execute(sql.SQL("UPDATE {}.records SET name='Newer external value' WHERE id='seed'").format(sql.Identifier(h['operations'].testing['schema'])))
    run = h['runner'].advance(run['run_id'], h['auth'])
    assert run['status'] == 'failed', events(h, run)
    assert read(h['operations'], identity='seed')['name'] == 'Newer external value'


def test_missing_adjacent_gate_and_unscoped_dataset_are_rejected(harness):
    h = harness
    w = workflow(h)
    w['edges'] = [e for e in w['edges'] if e['target'] != 'execute']
    with pytest.raises(ApiFailure, match='immediate'):
        h['coordinator'].validate_workflow(w, h['auth'])
    with pytest.raises(ApiFailure, match='outside'):
        h['coordinator'].scope(h['auth'], workflow(h), ['unselected_dataset'])


def test_catalog_ownership_and_context_spoofing(harness):
    h = harness
    context = h['coordinator'].enrich(h['auth'], {'database_catalog': {'sources': ['invented']}, 'database_workflow_tools': ['invented']})
    assert len(context['database_catalog']['sources']) == 2
    assert context['database_workflow_tools'][0]['tool_id'] == 'database_read_record'
    other = deepcopy(h['auth']); other['subject']['subject_id'] = 'other'
    with pytest.raises(ApiFailure):
        h['coordinator'].catalog(other)


def test_policy_revocation_before_commit_blocks_write(harness):
    h = harness
    run = h['runner'].advance(publish(h, workflow(h))['run_id'], h['auth'])
    decide(h, run)
    h['operations'].testing['policyfile'].write_text(json.dumps({'targets': []}))
    run = h['runner'].advance(run['run_id'], h['auth'])
    assert run['status'] in {'blocked', 'failed'}, events(h, run)
    with h['operations'].store.transaction(write=False) as db:
        summary = json.loads(db.execute('SELECT summary FROM data_write_operations').fetchone()[0])
    assert summary['state'] == 'prepared'  # Denied before claiming or attempting a write.


def test_prepare_expiry_and_explicit_rejection_do_not_write(harness):
    h = harness
    run = h['runner'].advance(publish(h, workflow(h))['run_id'], h['auth'])
    decide(h, run, 'rejected')
    assert h['runner'].advance(run['run_id'], h['auth'])['status'] == 'rejected'
    assert read(h['operations'], identity='seed')['name'] == 'Seed'


@pytest.mark.parametrize('engine', ['pg', 'mongo'])
@pytest.mark.parametrize('action', ['create', 'delete'])
def test_native_create_and_delete_through_workflow(harness, engine, action):
    h = harness
    identity = 'new_record' if action == 'create' else 'seed'
    values = {'name': 'Created by workflow'} if action == 'create' else {}
    run = h['runner'].advance(publish(h, workflow(h, [request(h['operations'], engine, action, identity, **values)]))['run_id'], h['auth'])
    assert run['status'] == 'paused_for_approval', events(h, run)
    decide(h, run)
    run = h['runner'].advance(run['run_id'], h['auth'])
    assert run['status'] == 'completed', events(h, run)
    record = read(h['operations'], engine, identity)
    assert (record is None) == (action == 'delete')


def test_lost_commit_acknowledgement_blocks_runtime_replay(harness):
    from workflow_api.data_write_adapter import UncertainWrite
    h = harness
    run = h['runner'].advance(publish(h, workflow(h))['run_id'], h['auth'])
    decide(h, run)
    mutate, calls = h['operations'].adapter.mutate, []
    def lost(*args):
        calls.append(1)
        mutate(*args)
        raise UncertainWrite()
    h['operations'].adapter.mutate = lost
    run = h['runner'].advance(run['run_id'], h['auth'])
    assert run['status'] == 'blocked', events(h, run)
    assert h['runner'].advance(run['run_id'], h['auth'])['status'] == 'blocked'
    assert len(calls) == 1 and read(h['operations'], identity='seed')['name'] == 'Workflow updated'


def test_current_execution_authority_revocation_blocks_prepared_write(harness):
    h = harness
    run = h['runner'].advance(publish(h, workflow(h))['run_id'], h['auth'])
    decide(h, run)
    worker_auth = deepcopy(h['auth'])
    h['auth']['permissions'].remove('workflow.execute')
    run = h['runner'].advance(run['run_id'], worker_auth)
    assert run['status'] == 'failed', events(h, run)
    assert read(h['operations'], identity='seed')['name'] == 'Seed'


def test_other_run_cannot_execute_prepared_operation(harness):
    h = harness
    original = h['runner'].advance(publish(h, workflow(h))['run_id'], h['auth'])
    operation_id = next(e['details']['database_operation_id'] for e in events(h, original) if e['event_type'] == 'approval.pending')
    w = workflow(h)
    node = next(n for n in w['nodes'] if n['node_id'] == 'execute')
    node['configuration'] = {'input': {'operation_id': operation_id}}
    run = h['runner'].advance(publish(h, w)['run_id'], h['auth'])
    decide(h, run)
    run = h['runner'].advance(run['run_id'], h['auth'])
    assert run['status'] == 'failed', events(h, run)
    assert read(h['operations'], identity='seed')['name'] == 'Seed'


def build_test_graph(h):
    manager = h['operations'].manager
    with manager.store.transaction() as db:
        for cid, revision, raw in db.execute('SELECT connection_id,revision,document FROM data_source_snapshots').fetchall():
            snapshot = json.loads(raw)
            snapshot.update(revision=revision, coverage='sampled' if cid == 'mongo' else 'declared', warnings=[])
            db.execute('UPDATE data_source_snapshots SET document=? WHERE connection_id=? AND revision=?', (json.dumps(snapshot), cid, revision))
    manager.relationships.request(h['auth'])
    manager.relationships.tick()
    view = manager.relationships.get(h['auth'])
    assert view['graph'], view
    return view['graph']


def test_validated_cross_database_query_uses_reviewed_relationship_and_real_rows(harness):
    from workflow_api.data_relationships import fingerprint
    h = harness
    graph = build_test_graph(h)
    context = h['coordinator'].queries.context(h['auth'])
    pg = next(d for d in context[1].values() if d['connection']['engine'] == 'postgresql')
    mongo = next(d for d in context[1].values() if d['connection']['engine'] == 'mongodb')
    field = lambda d, name: next(f['field_id'] for f in d['fields'] if f['name'] == name)
    # Explicit test-only relationship fixture; never pretend generic id matching
    # was inferred or review alone proved cardinality. Execution verifies values.
    edge = dict(relationship_id='rel_workflow_test', kind='suggested', status='proposed',
                source_dataset_id=pg['dataset_id'], target_dataset_id=mongo['dataset_id'],
                field_pairs=[dict(source_field_id=field(pg, 'id'), target_field_id=field(mongo, '_id'))],
                evidence=['Explicit dedicated-test link'], evidence_hash=fingerprint(['Explicit dedicated-test link']))
    with h['operations'].store.transaction() as db:
        raw = db.execute('SELECT document FROM data_relationship_graphs').fetchone()[0]
        stored = json.loads(raw); stored['relationships'].append(edge)
        db.execute('UPDATE data_relationship_graphs SET document=?', (json.dumps(stored),))
    h['operations'].manager.relationships.edit(h['auth'], 'review', edge['relationship_id'], dict(revision=graph['revision'], status='accepted'))
    plan = dict(base_dataset_id=pg['dataset_id'], joins=[dict(relationship_id=edge['relationship_id'], target_dataset_id=mongo['dataset_id'])],
                fields=[field(pg, 'name'), field(mongo, 'name')], filters=[], group_by=[], metrics=[], order_by=[], limit=10,
                explanation='Read linked dedicated test records.', clarification='')
    w = workflow(h, nodes=[dict(node_id='query', kind='tool', tool_id='database_read_query', configuration={'input': {'plan': plan}})], tools=['database_read_query'])
    run = h['runner'].advance(publish(h, w)['run_id'], h['auth'])
    assert run['status'] == 'completed', events(h, run)
    output = next(e['details']['output'] for e in events(h, run) if e['event_type'] == 'node.completed' and e['details']['node_id'] == 'query')
    assert output['rows'] == [{field(pg, 'name'): 'Seed', field(mongo, 'name'): 'Seed'}]
    assert len(output['sources']) == 2 and output['join_checks']


def test_master_specialist_prepares_then_fixed_graph_gate_commits(harness):
    h = harness
    nodes = [dict(node_id='master', kind='agent', agent_id='master_agent'),
             dict(node_id='review', kind='approval', approval_gate_id='database_review'),
             dict(node_id='execute', kind='tool', agent_id='commit_agent', tool_id='database_execute_operation', configuration={'input_mapping': {'operation_id': 'outputs.master.operation_id'}})]
    w = workflow(h, nodes=nodes)
    w['agents'] = [agent('master_agent', [], 'master'),
                   agent('specialist_agent', ['database.read_record', 'database.prepare'], 'sub_agent', 'master_agent'),
                   agent('commit_agent', ['database.execute'])]
    w['metadata']['dynamic_delegation'] = {'master': {'max_rounds': 3, 'max_tasks': 2}}
    target = h['operations'].testing['targets'][1]
    class Offline:
        external_write = retry_safe = False
        @staticmethod
        def reservation(agent): return {'llm_calls': 1, 'tokens': 10}
        def invoke_decision(self, agent, inputs, invocation_id, output_schema):
            if inputs['results']:
                return dict(action='finish', reason='Use the actual prepared operation.', output=inputs['results'][0]['result'])
            return dict(action='delegate', reason='Inspect and prepare the test record.', tasks=[dict(agent_id='specialist_agent', inputs={'task': 'check'}, reason='Database specialist.')])
        def invoke_tool_decision(self, agent, inputs, invocation_id, output_schema):
            results = inputs['tool_results']
            if not results:
                return dict(action='tool', reason='Read the exact test record.', tool_id='database_read_record', inputs=dict(connection_id='mongo', dataset_id=target['dataset_id'], identity={'_id': 'seed'}))
            if len(results) == 1:
                return dict(action='tool', reason='Prepare without committing.', tool_id='database_prepare_operation', inputs={'steps': [request(h['operations'], 'mongo', 'update', 'seed', name='Delegated preparation')]})
            return dict(action='finish', reason='Return the actual operation reference.', output={'operation_id': results[1]['output']['operation_id']})
    h['runner'].agents = Offline()
    run = h['runner'].advance(publish(h, w)['run_id'], h['auth'])
    assert run['status'] == 'paused_for_approval', events(h, run)
    assert read(h['operations'], 'mongo', 'seed')['name'] == 'Seed'
    decide(h, run)
    run = h['runner'].advance(run['run_id'], h['auth'])
    assert run['status'] == 'completed', events(h, run)
    assert read(h['operations'], 'mongo', 'seed')['name'] == 'Delegated preparation'
    assert any(e['event_type'] == 'agent.spawned' for e in events(h, run))


def test_planning_uses_trusted_catalog_and_database_tool_schemas(harness):
    from planner import PlannerService
    from workflow_api.live_providers import LivePlannerProvider
    h = harness
    proposed = workflow(h)
    proposed['metadata'].pop('database_scope')
    proposed['metadata']['database_source_ids'] = [t['dataset_id'] for t in h['operations'].testing['targets']]
    proposed['metadata']['agent_database_source_ids'] = {a['agent_id']: proposed['metadata']['database_source_ids'] for a in proposed['agents']}
    for a in proposed['agents']:
        a['model'] = {'provider': 'openai', 'model_id': 'test-model'}
    class OfflineProvider:
        def generate(self, objective, context):
            assert 'database.execute' in context['available_capabilities']
            assert 'database_execute_operation' in context['tool_output_schemas']
            assert all(isinstance(s, dict) for s in context['database_catalog']['sources'])
            return deepcopy(proposed)
    provider = LivePlannerProvider('test-model', ['owner@example.test'], object())
    provider.provider = OfflineProvider()
    h['service'].planner = PlannerService(provider=provider)
    preview = h['coordinator'].preview(h['auth'], {'objective':'Read test records'})
    selection = dict(revision=preview['revision'], source_ids=[t['dataset_id'] for t in h['operations'].testing['targets']])
    result = h['service'].handle(dict(request_id='req_plan', operation='plan_workflow', idempotency_key=uuid4().hex,
        payload=dict(objective='Read the selected test records and prepare the explicit reviewed update.',
                     context={'database_catalog': {'sources': ['invented']}, 'database_workflow_tools': ['invented'], 'knowledge_graph_selection':selection})), h['auth'])
    assert result['status'] == 200, json.dumps(result)
    generated = result['data']['workflow']
    assert len(generated['metadata']['database_scope']['sources']) == 2
    assert 'database_source_ids' not in generated['metadata']
    assert 'Database reference metadata' in generated['agents'][0]['instructions']


def test_database_workflow_composes_with_separately_approved_google_action(harness):
    import os
    h = harness
    registry = h['service'].registry_adapter.service
    policy = registry.trusted_policy_snapshot(h['auth'])
    policy.version += 1
    policy.approved_providers.add('google_sheets')
    policy.allowed_destinations.add('configured_spreadsheet')
    policy.credential_references['cred_google_test'] = dict(provider_id='google_sheets', scopes=['data.write', 'spreadsheets'])
    policy.remaining_quota['google_sheets_upsert_record'] = 10
    assert registry.update_policy(policy, h['auth'])['status'] == 200
    definition = json.loads((ROOT/'shared/contracts/examples/tools/google-sheets-upsert-record.json').read_text())
    definition['availability'] = 'enabled'
    assert registry.register_tool(definition, h['auth'], 'cred_google_test')['status'] == 200
    calls = []
    class OfflineSheets:
        external_write = True
        retry_safe = False
        timeout = 15
        @staticmethod
        def reservation(grant): return {'tool_calls': 1}
        def invoke(self, grant, params, invocation):
            calls.append(deepcopy(params))
            return dict(identity=params['identity'], row_index=2, created=True, updated_cells=2)
    h['runner'].connectors['google_sheets_upsert_record'] = OfflineSheets()
    w = workflow(h)
    w['agents'].append(agent('google_agent', ['update_spreadsheet']))
    w['agents'][-1]['permissions'].append('data.write')
    w['tools'].append(dict(tool_id='google_sheets_upsert_record', capability='update_spreadsheet'))
    w['nodes'][-1:-1] = [dict(node_id='google_review', kind='approval', label='Review Google action', approval_gate_id='google_review'),
                          dict(node_id='google_action', kind='tool', label='Save reviewed result to Sheets', agent_id='google_agent', tool_id='google_sheets_upsert_record',
                               configuration={'input': dict(spreadsheet_id='dedicated-test-sheet', range='Records!A:B', identity_column='id', identity='seed', fields={'name': 'Workflow updated'})})]
    w['edges'] = [dict(edge_id='e'+str(i), source=a['node_id'], target=b['node_id'], **({'outcome': 'approved'} if a['kind'] == 'approval' else {})) for i, (a, b) in enumerate(zip(w['nodes'], w['nodes'][1:]))]
    w['approval_gates'].append(dict(approval_gate_id='google_review', approver_roles=['admin'], timeout_seconds=300, on_reject='stop'))
    run = h['runner'].advance(publish(h, w)['run_id'], h['auth'])
    pending_run = deepcopy(run)
    pending_events = events(h, run)
    operation_id = next(e['details']['database_operation_id'] for e in pending_events if e['event_type'] == 'approval.pending')
    preview = h['operations'].get(h['auth'], operation_id)
    decide(h, run)
    run = h['runner'].advance(run['run_id'], h['auth'])
    assert run['status'] == 'paused_for_approval' and not calls, events(h, run)
    assert read(h['operations'], identity='seed')['name'] == 'Workflow updated'
    decide(h, run)
    run = h['runner'].advance(run['run_id'], h['auth'])
    assert run['status'] == 'completed' and len(calls) == 1, events(h, run)
    if output := os.getenv('BUILDER_PHASE5_FIXTURE_OUTPUT'):
        with h['operations'].store.transaction(write=False) as db:
            canonical = h['operations'].store.get(db, 'one', w['workflow_id'], 1)
        Path(output).write_text(json.dumps(dict(workflow=canonical, pending_run=pending_run, pending_events=pending_events,
                                              operation=preview, completed_run=run, completed_events=events(h, run)), indent=2)+'\n')


def test_metadata_change_after_approval_blocks_write(harness):
    h = harness
    run = h['runner'].advance(publish(h, workflow(h))['run_id'], h['auth'])
    decide(h, run)
    with h['operations'].store.transaction() as db:
        raw = db.execute("SELECT document FROM data_source_connections WHERE connection_id='pg'").fetchone()[0]
        connection = json.loads(raw); connection['generation'] += 1
        db.execute("UPDATE data_source_connections SET document=? WHERE connection_id='pg'", (json.dumps(connection),))
    run = h['runner'].advance(run['run_id'], h['auth'])
    assert run['status'] == 'failed', events(h, run)
    assert read(h['operations'], identity='seed')['name'] == 'Seed'


def test_expired_preparation_cannot_be_committed(harness):
    import time
    h = harness
    run = h['runner'].advance(publish(h, workflow(h))['run_id'], h['auth'])
    decide(h, run)
    with h['operations'].store.transaction() as db:
        raw = db.execute('SELECT summary FROM data_write_operations').fetchone()[0]
        summary = json.loads(raw); summary['expires_at'] = time.time()-1
        db.execute('UPDATE data_write_operations SET expires=?,summary=?', (summary['expires_at'], json.dumps(summary)))
    run = h['runner'].advance(run['run_id'], h['auth'])
    assert run['status'] == 'failed', events(h, run)
    assert read(h['operations'], identity='seed')['name'] == 'Seed'


def test_only_registered_and_configured_google_tools_enter_planning_context(harness):
    from connector_extension.catalog import CATALOG
    h = harness
    registry = h['service'].registry_adapter.service
    policy = registry.trusted_policy_snapshot(h['auth'])
    policy.version += 1
    policy.approved_providers.add('google_calendar')
    policy.credential_references['cred_calendar_test'] = dict(provider_id='google_calendar', scopes=['calendar.events.readonly', 'calendar.read'])
    policy.remaining_quota['extension_calendar_list'] = 10
    assert registry.update_policy(policy, h['auth'])['status'] == 200
    tool = deepcopy(CATALOG['extension_calendar_list']); tool['availability'] = 'enabled'
    assert registry.register_tool(tool, h['auth'], 'cred_calendar_test')['status'] == 200
    context = h['coordinator'].enrich(h['auth'], {'workflow_google_tools': ['invented']})
    assert context['workflow_google_tools'] == []
    h['runner'].connectors['extension_calendar_list'] = object()
    h['auth']['permissions'].append('calendar.read')
    h['auth']['scopes'] += ['calendar.read', 'calendar.events.readonly']
    context = h['coordinator'].enrich(h['auth'], {})
    assert context['workflow_google_tools'][0]['tool_id'] == 'extension_calendar_list'
