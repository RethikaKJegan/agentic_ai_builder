"""Additional final-release chaos checks; controlled effects on one Linux host."""
import json
import multiprocessing
import sqlite3
import time

import pytest

from connector_extension.common import EffectJournal
from runtime import RuntimeService
from runtime.graph import GraphRunner
from tests.test_distributed_execution import f, approved
from tests.test_distributed_postgres import pg


@pytest.mark.parametrize('fixture_name', ['f', 'pg'])
def test_two_killed_workers_preserve_unknown_effects_and_budgets(request, fixture_name, tmp_path, monkeypatch):
    fixture = request.getfixturevalue(fixture_name)
    monkeypatch.setenv('BUILDER_RUNTIME_LEASE_SECONDS', '30')
    run_ids = [approved(fixture, index) for index in range(2)]
    ledger = tmp_path / 'provider.sqlite3'
    with sqlite3.connect(ledger) as db:
        db.execute('CREATE TABLE effects (reference TEXT PRIMARY KEY)')
    journal = EffectJournal(tmp_path)
    context = multiprocessing.get_context('fork')
    entered = [context.Event() for _ in run_ids]
    hold = context.Event()

    def consume(run_id, reached):
        runtime = RuntimeService(fixture.workflows, clock=lambda: fixture.now)

        def invoke(grant, inputs, reference):
            def effect():
                with sqlite3.connect(ledger) as db:
                    db.execute('INSERT INTO effects VALUES (?)', (reference,))
                reached.set()
                hold.wait(60)
                return {'message_id': 'controlled_message'}
            return journal.perform(grant['tool_id'], reference, inputs, effect)

        fixture.connector.invoke = invoke
        GraphRunner(runtime, connectors={'smtp_send_email': fixture.connector}).advance(run_id, fixture.auth)

    children = [context.Process(target=consume, args=(run_id, reached)) for run_id, reached in zip(run_ids, entered)]
    try:
        for child in children:
            child.start()
        assert all(reached.wait(20) for reached in entered), 'Both workers must reach provider acceptance before termination.'
        for child in children:
            child.kill()
        for child in children:
            child.join(5)
            assert child.exitcode == -9
    finally:
        for child in children:
            if child.is_alive():
                child.kill()
                child.join(5)

    with fixture.store.transaction(write=False) as db:
        before = {run_id: fixture.runtime.load(db, run_id, fixture.auth) for run_id in run_ids}
    fixture.now += 31
    runtime = RuntimeService(fixture.workflows, clock=lambda: fixture.now)
    unexpected_dispatches = []

    def forbidden_replay(*args):
        unexpected_dispatches.append(args)
        raise AssertionError('An uncertain provider effect must not be dispatched again.')

    fixture.connector.invoke = forbidden_replay
    runner = GraphRunner(runtime, connectors={'smtp_send_email': fixture.connector})
    began = time.monotonic()
    for run_id in run_ids:
        assert runner.advance(run_id, fixture.auth)['status'] == 'blocked'
        assert runner.advance(run_id, fixture.auth)['status'] == 'blocked'
        with fixture.store.transaction(write=False) as db:
            after = runtime.load(db, run_id, fixture.auth)
        assert after['error_code'] == 'UNKNOWN_INVOCATION_RESULT'
        assert after['workflow_digest'] == before[run_id]['workflow_digest']
        assert after['usage'] == before[run_id]['usage']
        for node_id, status in before[run_id]['node_states'].items():
            if status == 'completed':
                assert after['node_states'][node_id] == status
    assert not unexpected_dispatches
    with sqlite3.connect(ledger) as db:
        assert db.execute('SELECT COUNT(*) FROM effects').fetchone()[0] == 2
    (tmp_path / 'two-worker-recovery.json').write_text(json.dumps({
        'store': fixture_name, 'terminated_processes': 2, 'signal_exit_code': -9,
        'accepted_effects': 2, 'replayed_dispatches': 0, 'outcome': 'blocked',
        'lease_advance_seconds': 31, 'reconstruction_and_block_wall_seconds': time.monotonic() - began,
        'qualification': 'One host; controlled providers; fake lease advance; not a production RTO.',
    }, indent=2))


def test_sqlite_write_permission_loss_after_provider_effect_blocks_replay(f, tmp_path, monkeypatch):
    """Actual OS permission denial on this fixture's DB, not physical disk loss."""
    from pathlib import Path
    import stat

    monkeypatch.setenv('BUILDER_RUNTIME_LEASE_SECONDS', '30')
    run_id = approved(f)
    path = Path(f.store.path).resolve()
    assert path.is_relative_to(Path(f.temp.name).resolve())
    original_mode = stat.S_IMODE(path.stat().st_mode)
    accepted = []
    saved = []

    def lose_write_access(grant, inputs, reference):
        accepted.append(reference)
        with f.store.transaction(write=False) as db:
            saved.append(f.runtime.load(db, run_id, f.auth))
        path.chmod(0o400)
        return {'message_id': 'controlled_accepted_effect'}

    f.connector.invoke = lose_write_access
    try:
        with pytest.raises(sqlite3.OperationalError) as error:
            f.graph.advance(run_id, f.auth)
    finally:
        # SQLite can create WAL/SHM files using the temporarily read-only DB
        # permissions. Restore this fixture-owned store as a complete set.
        for owned in path.parent.glob(path.name + "*"):
            owned.chmod(original_mode)
    assert error.value.sqlite_errorcode & 255 == sqlite3.SQLITE_READONLY
    assert len(accepted) == 1
    f.now += 31
    runtime = RuntimeService(f.workflows, clock=lambda: f.now)
    runner = GraphRunner(runtime, connectors={'smtp_send_email': f.connector})
    assert runner.advance(run_id, f.auth)['status'] == 'blocked'
    assert len(accepted) == 1
    with f.store.transaction(write=False) as db:
        after = runtime.load(db, run_id, f.auth)
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    assert after['error_code'] == 'UNKNOWN_INVOCATION_RESULT'
    assert after['workflow_digest'] == saved[0]['workflow_digest']
    assert after['usage'] == saved[0]['usage']


def test_pytest_bootstrap_and_fresh_api_import_use_private_stores(tmp_path):
    import os
    from pathlib import Path
    import subprocess
    import sys

    configured = Path(os.environ['BUILDER_DATABASE_URL'])
    assert configured.parent.name.startswith('builder-pytest-bootstrap-')
    target = tmp_path / 'fresh-default.sqlite3'
    env = {**os.environ, 'BUILDER_DATABASE_URL': str(target), 'PYTHONDONTWRITEBYTECODE': '1'}
    env.pop('BUILDER_CLIENT_ID', None)
    result = subprocess.run([sys.executable, '-B', '-c',
        'from workflow_api.main import app; print(app.state.workflow_service.store.path)'],
        env=env, capture_output=True, text=True, check=True)
    assert result.stdout.strip() == str(target)
    assert target.is_file()


@pytest.mark.parametrize('script', ['serve_ui_test_api.py', 'serve_lifecycle_ui_test_api.py', 'serve_orchestration_ui_test_api.py'])
def test_browser_fixture_bootstrap_never_opens_shared_default_database(script):
    import os
    from pathlib import Path
    import subprocess
    import sys
    from tempfile import TemporaryDirectory

    root = Path(__file__).resolve().parents[1]
    code = '''
import os, runpy, sys
from pathlib import Path
from urllib.parse import urlsplit, unquote
import uvicorn
shared = (Path(sys.argv[1]) / '.local/workflows.sqlite3').resolve()
def audit(event, args):
    if event == 'sqlite3.connect':
        value = os.fspath(args[0])
        if isinstance(value, bytes): value = os.fsdecode(value)
        if value.startswith('file:'): value = unquote(urlsplit(value).path)
        if Path(value).resolve() == shared:
            raise AssertionError('Browser fixture attempted to open the shared default store.')
sys.addaudithook(audit)
uvicorn.run = lambda *args, **kwargs: None
sys.path.insert(0, str(Path(sys.argv[1]) / 'scripts'))
runpy.run_path(str(Path(sys.argv[1]) / 'scripts' / sys.argv[2]), run_name='__main__')
print('Isolated browser fixture bootstrap passed')
'''
    with TemporaryDirectory(prefix='builder-bootstrap-audit-', dir=root / '.local') as directory:
        env = {**os.environ, 'BUILDER_TEST_DATABASE_DIR': str(Path(directory) / 'browser'),
            'BUILDER_TEST_FRESH_DATABASE': '1', 'BUILDER_REAL_CONNECTORS': '0',
            'CREWAI_TESTING': 'true', 'CREWAI_TRACING_ENABLED': 'false',
            'CREWAI_DISABLE_TELEMETRY': 'true', 'PYTHONDONTWRITEBYTECODE': '1'}
        env.pop('BUILDER_DATABASE_URL', None)
        env.pop('BUILDER_CLIENT_ID', None)
        result = subprocess.run([sys.executable, '-B', '-c', code, str(root), script],
            cwd=root, env=env, capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, result.stderr
        assert 'Isolated browser fixture bootstrap passed' in result.stdout


def test_importing_api_factory_does_not_initialize_any_database(tmp_path):
    import os
    import subprocess
    import sys
    target=tmp_path/'must-not-exist.sqlite3'
    env={**os.environ,'BUILDER_DATABASE_URL':str(target),'PYTHONDONTWRITEBYTECODE':'1'}
    env.pop('BUILDER_CLIENT_ID',None)
    code="""
import sys
def audit(event,args):
    if event == 'sqlite3.connect': raise AssertionError('Factory import opened SQLite')
sys.addaudithook(audit)
from workflow_api.main import create_app
from workflow_api.live_providers import create_configured_app
assert callable(create_app) and callable(create_configured_app)
"""
    result=subprocess.run([sys.executable,'-B','-c',code],env=env,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert not target.exists()
