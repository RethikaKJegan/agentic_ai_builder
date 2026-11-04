"""Disposable-schema PostgreSQL checks; never migrate the configured application schema."""
from types import SimpleNamespace
from urllib.parse import urlencode
from uuid import uuid4
import pytest
from workflow_api.storage import WorkflowStore
from workflow_api.business_cases import BusinessCases
from tests.test_postgres_backend import test_dsn
from tests.test_generic_lifecycle_phase6 import (
    test_late_evidence_reassesses_only_dependencies_preserves_history as check_late,
    test_concurrent_reassessment_revision_cas_and_idempotency as check_cas,
    test_old_case_without_phase6_fields_and_feedback_replay as check_old)


@pytest.fixture
def cases():
    psycopg=pytest.importorskip('psycopg');from psycopg import sql
    base=test_dsn();schema='check_lifecycle6_'+uuid4().hex
    with psycopg.connect(base,autocommit=True) as connection:
        connection.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    try:
        dsn=base+('&' if '?' in base else '?')+urlencode({'options':'-csearch_path='+schema})
        yield BusinessCases(SimpleNamespace(store=WorkflowStore(dsn),runtime_runner=None),clock=lambda:1793808000)
    finally:
        with psycopg.connect(base,autocommit=True) as connection:
            connection.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))


@pytest.mark.parametrize('check',['late','concurrent','old'])
def test_disposable_postgres_transactions_history_feedback_and_compatibility(cases,check):
    if check=='late':check_late(cases,'inspection_findings',False)
    elif check=='concurrent':check_cas(cases)
    else:check_old(cases)
