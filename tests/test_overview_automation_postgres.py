"""Overview mutation ledger and recurring execution on disposable PostgreSQL."""
import pytest
from tests.test_overview_automation_integration import (automation,google_setup,connected,composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release,queries)
from tests.test_durable_automation_postgres import disposable_postgres
from tests import test_overview_automation_integration as checks


@pytest.mark.parametrize('check',[
    checks.test_overview_prepares_scoped_query_and_consent_without_provider_effects,
    checks.test_overview_review_activation_two_occurrences_and_duplicate_retry,
    checks.test_relative_query_changes_only_approved_dates_at_delayed_occurrence,
    checks.test_existing_queue_reattaches_prepared_overview_without_model_or_provider_replay,
])
def test_overview_postgres(automation,queries,check):
    check(automation,queries)
