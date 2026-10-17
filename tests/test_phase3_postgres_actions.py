"""Real PostgreSQL checks for additive Phase 3 actions and publication overview."""
import pytest
from tests import test_postgres_backend as fixtures
from tests import test_phase3_actions as actions


@pytest.fixture
def pg_context():
    fixture=fixtures.WorkflowApiPostgresTests('test_same_prompt_after_deletion_gets_stable_fresh_identity_and_agents')
    fixture.setUp()
    try:yield fixture
    finally:fixture.tearDown();fixture.doCleanups()


@pytest.mark.parametrize('check',[
    actions.test_submission_is_explicit_durable_and_does_not_approve_publish_or_activate,
    actions.test_submission_rejects_unvalidated_stale_and_unauthorized_requests,
    actions.test_save_timestamp_is_server_confirmed_and_submission_does_not_leak_to_new_draft,
    actions.test_settings_need_admin_validate_input_and_return_confirmed_value,
    actions.test_configuration_is_not_verification_and_unsupported_probes_stay_unverified,
    actions.test_real_probe_runs_outside_database_and_failure_is_redacted,
    actions.test_published_revision_is_visible_before_activation_and_under_newer_draft,
])
def test_real_postgres_phase3_actions(pg_context,check):check(pg_context)
