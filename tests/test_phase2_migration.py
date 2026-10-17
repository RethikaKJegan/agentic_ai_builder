"""Real PostgreSQL migration validation, sequence preservation and rollback."""
import json
from pathlib import Path
import sqlite3
from urllib.parse import urlencode
from uuid import uuid4

import pytest
from tests.test_postgres_backend import test_dsn as postgres_dsn
from tests.test_phase2_reliability import context
from scripts.migrate_builder_database import snapshot,migrate
from workflow_api.postgres import PostgresDatabase


@pytest.fixture
def pg_target():
    psycopg=pytest.importorskip('psycopg');from psycopg import sql
    base=postgres_dsn();schema='migrate_'+uuid4().hex
    with psycopg.connect(base,autocommit=True) as db:db.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    try:yield base+('&' if '?' in base else '?')+urlencode({'options':'-csearch_path='+schema})
    finally:
        with psycopg.connect(base,autocommit=True) as db:db.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))


def test_snapshot_and_migration_preserve_releases_jobs_history_and_highwater(context,tmp_path,pg_target):
    context.activate()
    job=context.service.lifecycle.ingest('binding_main',{'event_id':'migration','body':'Preserve'},context.auth)['job']
    context.service.lifecycle.lease('local-workspace');context.service.lifecycle.execute_job(job['job_id'],context.runner)
    with context.service.store.transaction() as db:
        db.execute('INSERT INTO runtime_events(sequence,workspace,run_id,document) VALUES (10000,?,?,?)',('local-workspace','deleted_probe','{}'))
        db.execute('DELETE FROM runtime_events WHERE sequence=10000')
    backup=snapshot(context.path,tmp_path/'private-snapshot.sqlite3')
    assert backup.stat().st_mode&0o777==0o600
    preparation=migrate(backup)
    assert preparation['applied'] is False
    completed=migrate(backup,target_dsn=pg_target,apply=True)
    assert completed['validated'] is True
    assert {table['name'] for table in completed['tables']} >= {'revisions','lifecycle_releases','lifecycle_jobs','runtime_runs','runtime_events','mutations'}
    with PostgresDatabase(pg_target,3000).transaction() as db:
        next_id=db.execute('INSERT INTO runtime_events(workspace,run_id,document) VALUES (?,?,?)',('local-workspace','new_probe','{}')).lastrowid
        assert next_id>10000
        assert db.execute('SELECT COUNT(*) FROM lifecycle_active').fetchone()[0]==1


def test_nonempty_target_is_never_overwritten(context,tmp_path,pg_target):
    backup=snapshot(context.path,tmp_path/'snapshot.sqlite3')
    database=PostgresDatabase(pg_target,3000)
    with database.transaction() as db:
        db.execute('CREATE TABLE existing_data (id TEXT PRIMARY KEY, payload TEXT)')
        db.execute('INSERT INTO existing_data VALUES (?,?)',('preserved','original'))
    with pytest.raises(ValueError,match='empty'):migrate(backup,target_dsn=pg_target,apply=True)
    with database.transaction(write=False) as db:assert db.execute('SELECT payload FROM existing_data').fetchone()[0]=='original'


def test_failed_integrity_import_rolls_back_all_target_data(tmp_path,pg_target):
    source=tmp_path/'invalid.sqlite3'
    with sqlite3.connect(source) as db:
        db.execute('CREATE TABLE records (id TEXT PRIMARY KEY, document TEXT)')
        db.execute('INSERT INTO records VALUES (NULL,?)',('legacy-null-primary-key',))
    with pytest.raises(Exception):migrate(source,target_dsn=pg_target,apply=True)
    with PostgresDatabase(pg_target,3000).transaction(write=False) as db:
        assert not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='records'").fetchone()


def test_bound_parameters_do_not_rewrite_question_marks_or_percent_literals(pg_target):
    with PostgresDatabase(pg_target,3000).transaction(write=False) as db:
        assert db.execute("SELECT ?, 'literal? 100%'",("why? 50% 'safe'",)).fetchone()==("why? 50% 'safe'",'literal? 100%')


@pytest.mark.parametrize('kind',['procurement','effect-journal','sheet-resources'])
def test_auxiliary_databases_migrate_with_constraints_and_exact_rows(kind,tmp_path,pg_target):
    from connector_extension.tests.test_procurement_store import StoreTests
    from connector_extension.tests.test_sheet_creation import CreationTests
    fixture=StoreTests() if kind=='procurement' else CreationTests()
    fixture.setUp()
    try:
        if kind=='procurement':
            fixture.quote_ready();source=fixture.store.path
        else:
            fixture.invoke();source=fixture.journal.path if kind=='effect-journal' else fixture.resources.path
        backup=snapshot(source,tmp_path/'auxiliary.sqlite3')
        result=migrate(backup,target_dsn=pg_target,apply=True)
        assert result['validated'] is True
        assert sum(table['rows'] for table in result['tables'])>0
    finally:fixture.tearDown();fixture.doCleanups()
