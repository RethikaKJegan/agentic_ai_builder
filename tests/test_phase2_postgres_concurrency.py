"""Concurrent real PostgreSQL editing, activation and worker recovery checks."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Barrier
import pytest
from tests import test_postgres_backend as fixtures
from tests import test_phase2_reliability as reliability
from tests import test_phase2_workers as workers


@pytest.fixture
def pg_context():
    fixture=fixtures.LifecyclePostgresTests('test_literal_event_paths_support_published_priority_mapping')
    fixture.setUp()
    try:yield fixture
    finally:fixture.tearDown();fixture.doCleanups()


@pytest.mark.parametrize('check',[
    reliability.test_revision_change_during_provider_preparation_aborts_and_compensates,
    reliability.test_two_preparations_cannot_activate_conflicting_releases,
    reliability.test_same_key_retry_during_preparation_does_not_repeat_provider_setup,
    reliability.test_crashed_preparation_is_lease_aware_and_recoverable,
    workers.test_only_one_worker_group_starts_and_expired_owner_is_reclaimed,
    workers.test_stale_dispatch_claim_cannot_execute_or_overwrite_new_owner,
    workers.test_dispatch_failure_after_run_creation_is_not_automatically_replayed,
    workers.test_dispatch_finish_cannot_undo_cancellation,
    workers.test_expired_runtime_intent_blocks_instead_of_repeating,
    workers.test_health_reports_redacted_component_failures,
    workers.test_api_execute_only_enqueues_and_worker_completes,
    workers.test_waiting_approvals_cannot_starve_new_queued_runs,
    workers.test_scheduler_claims_each_job_when_ready_to_execute,
])
def test_postgres_race_and_recovery_boundaries(pg_context,check):check(pg_context)


def test_two_editors_cannot_overwrite_same_base_revision():
    fixture=fixtures.WorkflowApiPostgresTests('test_same_prompt_after_deletion_gets_stable_fresh_identity_and_agents')
    fixture.setUp()
    try:
        assert fixture.save().status_code==200
        workflow=deepcopy(fixture.workflow);workflow['version']=2
        barrier=Barrier(2)
        def edit(index):
            candidate=deepcopy(workflow);candidate['name']='Editor '+str(index)
            barrier.wait(timeout=5)
            return fixture.save(candidate,base=1,key='parallel_editor_'+str(index))
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(edit,[1,2]))
        assert sorted(result.status_code for result in results)==[200,409]
        rejected=next(result for result in results if result.status_code==409)
        assert rejected.json()['data']['error']['error_code']=='REVISION_CONFLICT'
        with fixture.service.store.transaction(write=False) as db:
            assert db.execute('SELECT COUNT(*) FROM revisions WHERE version=2').fetchone()[0]==1
    finally:fixture.tearDown();fixture.doCleanups()
