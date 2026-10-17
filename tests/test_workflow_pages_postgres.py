import pytest
from tests import test_postgres_backend as postgres_fixtures
from tests import test_workflow_pages as checks

@pytest.mark.parametrize('check',[checks.test_pages_preserve_totals_latest_revisions_and_workspace,checks.test_page_cursor_validation_and_anonymous_denial])
def test_postgres_workflow_pages(check):
 fixture=postgres_fixtures.WorkflowApiPostgresTests('test_same_prompt_after_deletion_gets_stable_fresh_identity_and_agents');fixture.setUp()
 try:check(fixture)
 finally:fixture.tearDown();fixture.doCleanups()
