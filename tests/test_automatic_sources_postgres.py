"""Automatic source context against an isolated real PostgreSQL schema."""
from urllib.parse import urlencode
from uuid import uuid4
import pytest
from tests.test_postgres_backend import test_dsn
from tests import test_automatic_sources as checks
from workflow_api.storage import WorkflowStore

@pytest.fixture
def postgres_store():
 import psycopg
 from psycopg import sql
 dsn=test_dsn();schema='source_check_'+uuid4().hex
 with psycopg.connect(dsn,autocommit=True) as db:db.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
 try:yield WorkflowStore(dsn+('&' if '?' in dsn else '?')+urlencode({'options':'-csearch_path='+schema}))
 finally:
  with psycopg.connect(dsn,autocommit=True) as db:db.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))

@pytest.mark.parametrize('check',[
 checks.test_workspace_context_overrides_client_evidence_and_excludes_other_workspace,
 checks.test_context_is_bounded_and_secret_documents_are_not_model_input,
 checks.test_published_source_candidates_do_not_include_other_workspace_or_drafts,
 checks.test_real_planning_boundary_uses_knowledge_and_retry_survives_knowledge_change,
 checks.test_runtime_loads_fresh_knowledge_from_registry_workspace_with_data_read_only,
])
def test_postgres_automatic_sources(postgres_store,check):check(postgres_store)
