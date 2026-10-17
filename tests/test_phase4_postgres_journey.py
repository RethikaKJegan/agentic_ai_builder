"""Exact release and event-sequence reads against an isolated real PostgreSQL schema."""
import pytest
from tests import test_postgres_backend as fixtures
from tests import test_phase4_journey as checks

@pytest.fixture
def pg_context():
    fixture=fixtures.WorkflowApiPostgresTests('test_same_prompt_after_deletion_gets_stable_fresh_identity_and_agents');fixture.setUp()
    try:yield fixture
    finally:fixture.tearDown();fixture.doCleanups()

@pytest.mark.parametrize('check',[
 checks.test_release_read_does_not_confuse_current_draft_with_active_revision,
 checks.test_release_read_workspace_isolation_and_no_release,
 checks.test_release_read_prefers_active_identity_over_newer_failed_preparation,
 checks.test_release_read_reports_disabled_state_without_inventing_activation,
 checks.test_release_read_rejects_anonymous_and_unprivileged_requests,
])
def test_postgres_release_state(pg_context,check):check(pg_context)

def test_postgres_recorded_sequence():
    fixture=fixtures.RuntimePostgresTests('test_approved_revision_creates_canonical_events');fixture.setUp()
    try:checks.test_events_expose_database_sequence_without_rewriting_stored_evidence(fixture)
    finally:fixture.doCleanups()
