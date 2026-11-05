"""Same controlled acceptance on disposable PostgreSQL schemas when configured."""
from urllib.parse import urlencode
from uuid import uuid4
import pytest
from workflow_api.storage import WorkflowStore
from tests.test_postgres_backend import test_dsn
from tests import test_business_ontology as ontology_fixture
from tests import test_durable_automation as checks
from tests.test_durable_automation import (automation,connected,composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release,google_setup)


@pytest.fixture(autouse=True)
def disposable_postgres(monkeypatch):
    psycopg=pytest.importorskip('psycopg');from psycopg import sql
    base=test_dsn();name='automation_'+uuid4().hex
    with psycopg.connect(base,autocommit=True) as db:db.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(name)))
    dsn=base+('&' if '?' in base else '?')+urlencode({'options':'-csearch_path='+name})
    monkeypatch.setattr(ontology_fixture,'WorkflowStore',lambda _path,*a,**kw:WorkflowStore(dsn,**kw))
    try:yield
    finally:
        with psycopg.connect(base,autocommit=True) as db:db.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(name)))


@pytest.mark.parametrize('check',[
    checks.test_reply_resumes_same_case_after_days_once,
    checks.test_daily_report_distinct_occurrences_fresh_reads_and_restart,
    checks.test_concurrent_due_ticks_and_workers_do_not_duplicate_occurrence,
    checks.test_restart_after_completed_send_before_job_commit_never_resends,
])
def test_postgres_automation(automation,tmp_path,check):
    import inspect
    if 'tmp_path' in inspect.signature(check).parameters:check(automation,tmp_path)
    else:check(automation)
