"""Phase 5 authoritative state/conflict invariants on real PostgreSQL."""
import pytest
from tests import test_postgres_backend as fixtures
from tests import test_phase5_state as checks
@pytest.fixture
def pg_context():
    fixture=fixtures.WorkflowApiPostgresTests('test_same_prompt_after_deletion_gets_stable_fresh_identity_and_agents');fixture.setUp()
    try:yield fixture
    finally:fixture.tearDown();fixture.doCleanups()
@pytest.mark.parametrize('check',[
 checks.test_two_editors_cannot_lose_updates_or_advance_an_unconfirmed_base,
 checks.test_new_draft_preserves_layout_metadata_branches_and_the_active_release,
 checks.test_client_draft_cannot_supply_executable_assignments_or_old_approval,
])
def test_postgres_state_boundaries(pg_context,check):check(pg_context)
