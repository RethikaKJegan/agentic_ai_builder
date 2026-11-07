"""The real app factory gates the opt-in worker arrangement without network I/O."""
import pytest
from runtime.worker import RuntimeWorker
from workflow_api.scheduler import LifecycleDispatchWorker,TriggerScheduler
from tests import test_live_providers as live_fixtures


def test_configured_multi_active_keeps_pollers_singleton_and_limits_server_owned():
    fixture=live_fixtures.LiveProviderTests();fixture.setUp()
    try:
        fixture.env.update(BUILDER_WORKER_MODE='multi-active',BUILDER_WORKER_CONCURRENCY='2',BUILDER_ACCOUNT_CONCURRENCY='3',BUILDER_PROVIDER_RATE_LIMITS='{"smtp":5}')
        app=fixture.make_app(database=fixture.path/'multi.sqlite')
        service=app.state.workflow_service;supervisor=app.state.worker_supervisor
        assert {type(w) for w in supervisor.parallel_workers}=={RuntimeWorker,LifecycleDispatchWorker}
        poller=next(w for w in supervisor.workers if isinstance(w,TriggerScheduler))
        assert not poller.dispatch
        assert service.runtime_runner.runtime.resource_controls.policy.running_per_account==3
        assert service.runtime_runner.runtime.resource_controls.policy.provider_per_minute=={'smtp':5}
        assert service.business_composition.packages.account_graph is service.account_graph
        assert all(w.thread is None for w in supervisor.parallel_workers)
        fixture.env['BUILDER_WORKER_MODE']='unknown'
        with pytest.raises(ValueError):fixture.make_app(database=fixture.path/'invalid.sqlite')
    finally:fixture.doCleanups()
