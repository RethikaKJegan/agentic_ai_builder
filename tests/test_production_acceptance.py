"""Planner to CrewAI to approved effects, durable event wait and worker restart."""
from copy import deepcopy

from runtime import RuntimeService
from runtime.graph import GraphRunner
from runtime.worker import RuntimeWorker
from workflow_api.business_cases import BusinessCases
from workflow_api.automation import DurableAutomation
from tests.test_durable_automation import (
    automation, connected, composition, investigation, retrieval, knowledge,
    reference, generation, foundation, auth, release, google_setup,
    adaptive_case, subscription, reply, drain, stored, trace,
)


def test_restored_graph_case_preserves_wait_approvals_receipts_and_memory(automation, tmp_path):
    f = automation
    from workflow_api.account_knowledge import AccountKnowledge
    from tests.test_process_recovery import kill_at
    f.general.account_graph=AccountKnowledge(f.general.store,f.general,clock=lambda:f.now)
    f.general.business_composition.packages.account_graph=f.general.account_graph
    case = adaptive_case(f, use_planner=True)
    sub = subscription(f, case)
    rid = case['adaptive']['run_id']
    before = stored(f, rid)
    assert f.planner_contexts
    assert any('account_knowledge' in c for c in f.planner_contexts)
    assert 'tool.extension_mail_send' in f.planner_contexts[0]['capabilities']
    assert before['action_instances']['send']['verified_receipt']
    assert before['action_instances']['send']['approval_references']
    assert before['action_instances']['sheet']['verified_receipt']
    assert f.calls, 'Actual CrewExecutor must have reached the controlled model transport.'
    assert f.http.write_count == 1 and len(f.http.sent) == 1
    prior_actions = deepcopy(before['action_instances'])

    def waiting_process(entered,hold):
        worker=RuntimeWorker(f.runner,f.general.worker_authenticate)
        worker.drain()
        entered.set();hold.wait(60)
    kill_at(waiting_process)
    # Back up and restore only disposable stores through the existing safe SQLite
    # snapshot helper; compare full table dumps before reconstructing services.
    import sqlite3
    from scripts.migrate_builder_database import snapshot
    paths={__import__('pathlib').Path(f.general.store.path)}
    paths.update(p for p in tmp_path.rglob('*') if p.is_file() and p.suffix in ('.sqlite','.sqlite3'))
    for index,path in enumerate(sorted(paths)):
        backup=snapshot(path,tmp_path/('restore-drill-'+str(index)+'.backup'))
        with sqlite3.connect(path) as source,sqlite3.connect(backup) as saved:
            expected=list(saved.iterdump())
            source.execute('CREATE TABLE phase3_restore_probe (id TEXT)');source.commit()
            saved.backup(source)
            assert list(source.iterdump())==expected
            assert source.execute('PRAGMA integrity_check').fetchone()[0]=='ok'

    # Discard service/worker instances after persisted wait and before event receipt.
    # Keep only the disposable store and controlled external provider state.
    agents = f.runner.agents
    f.runtime = RuntimeService(f.general, clock=lambda: f.now)
    f.runner = GraphRunner(f.runtime, agents=agents, connectors=f.connectors)
    f.general.runtime_runner = f.runner
    f.cases = BusinessCases(f.general, clock=lambda: f.now)
    f.general.business_cases = f.cases
    f.auto = DurableAutomation(f.general, clock=lambda: f.now)
    worker = RuntimeWorker(f.runner, f.general.worker_authenticate)
    f.now += 31
    worker.drain()
    assert stored(f, rid)['usage'] == before['usage']
    assert f.cases.get(f.x.a, case['case_id'])['adaptive']['pending_wait']
    assert f.http.write_count == 1 and len(f.http.sent) == 1

    f.messages = [reply(f, sub)]
    f.auto.tick(f.general.worker_authenticate)
    jobs = drain(f)
    assert jobs and jobs[0]['state'] == 'completed', jobs
    final = stored(f, rid)
    completed_case = f.cases.get(f.x.a, case['case_id'])
    assert completed_case['adaptive']['status'] == 'completed'
    assert final['status'] == 'completed'
    assert final['workflow_digest'] == before['workflow_digest']
    for aid in ('read', 'analysis', 'sheet', 'email', 'send'):
        assert final['action_instances'][aid] == prior_actions[aid]
    for group, counters in before['usage'].items():
        for counter, consumed in counters.items():
            assert final['usage'][group].get(counter, 0) >= consumed
    payload = completed_case['automation_evidence'][0]['payload']
    assert f.auto.accept(f.x.a, sub['id'], {'event_id': 'incoming_1', 'payload': payload})['duplicate']
    assert not drain(f)
    assert f.http.write_count == 1 and len(f.http.sent) == 1
    events = f.runtime.events(rid, f.x.a)['items']
    assert any(e['event_type'] == 'approval.approved' for e in events)
    assert any(e['event_type'] == 'run.completed' for e in events)
    trace(f, tmp_path / 'phase3-restored-acceptance-trace.json', completed_case)
