"""Phase 6 history queries executed against real PostgreSQL."""
import pytest
from tests import test_postgres_backend as fixtures
from tests import test_phase6_runtime as checks
@pytest.fixture
def context():
    f=fixtures.RuntimePostgresTests('test_approved_revision_creates_canonical_events');f.setUp()
    try:yield f
    finally:f.doCleanups()
@pytest.mark.parametrize('check',[
 checks.test_run_keyset_filter_before_limit_and_workspace_isolation,
 checks.test_sequence_pages_resume_deduplicate_and_do_not_modify_evidence,
 checks.test_monitoring_aggregates_and_pages_without_loading_all_workflows,
 checks.test_http_history_preserves_envelope_auth_and_validates_filters,
])
def test_postgres_history(context,check):check(context)
