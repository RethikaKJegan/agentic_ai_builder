"""Automatic discovery fixtures; no real cloud credentials or provider writes."""
import json

import pytest
from jsonschema import Draft202012Validator
from pathlib import Path
from tests.test_data_sources import manager, auth, config
from workflow_api.service import ApiFailure


def due(manager,cid):
    with manager.store.transaction() as db:
        db.execute('UPDATE data_source_refresh SET next_check=0 WHERE connection_id=?',(cid,))


def test_unchanged_automatic_check_preserves_graph_and_plan_identity(manager):
    cid=manager.connect(auth(),config())['connection_id'];manager.tick();manager.relationships.tick()
    before=manager.relationships.get(auth());connection=manager.metadata(auth(),cid)['connection']
    due(manager,cid);manager.tick()
    after=manager.metadata(auth(),cid)['connection']
    assert (after['generation'],after['metadata_revision'])==(connection['generation'],connection['metadata_revision'])
    assert manager.relationships.get(auth())==before
    view=manager.refresh.get(auth())
    assert view['items'][0]['last_success_at'] and view['items'][0]['next_check_at']>0
    schema=json.loads((Path(__file__).resolve().parents[1]/'shared/contracts/data-sources/refresh-v1.schema.json').read_text())
    Draft202012Validator(schema).validate(view)


def test_changed_automatic_check_queues_graph_without_manual_refresh(manager):
    cid=manager.connect(auth(),config())['connection_id'];manager.tick();manager.relationships.tick()
    manager.adapter.field='order_id';due(manager,cid);manager.tick()
    assert manager.metadata(auth(),cid)['snapshot']['revision']==2
    assert manager.relationships.get(auth())['build_status']=='queued'
    assert manager.refresh.get(auth())['items'][0]['last_change_at']
    manager.relationships.tick()
    assert any(n['label']=='order_id' for n in manager.relationships.get(auth())['graph']['nodes'])


def test_failure_preserves_snapshot_and_backoff_then_recovery(manager):
    cid=manager.connect(auth(),config())['connection_id'];manager.tick()
    manager.adapter.failure=RuntimeError('password=private-value');due(manager,cid);manager.tick()
    state=manager.refresh.get(auth())['items'][0]
    assert state['consecutive_failures']==1 and state['next_check_at']>manager.refresh.clock()+590
    assert manager.metadata(auth(),cid)['snapshot']['revision']==1
    assert 'private-value' not in json.dumps(state)
    manager.adapter.failure=None;due(manager,cid);manager.tick()
    assert manager.refresh.get(auth())['items'][0]['consecutive_failures']==0
    assert manager.metadata(auth(),cid)['snapshot']['revision']==1


def test_disabled_disconnected_and_active_jobs_are_not_scheduled(manager):
    cid=manager.connect(auth(),config())['connection_id'];due(manager,cid)
    assert not manager.refresh.schedule() # initial profile is already queued
    manager.tick()
    manager.refresh.edit(auth(),cid,dict(enabled=False,interval_seconds=60));due(manager,cid)
    assert not manager.tick()
    manager.refresh.edit(auth(),cid,dict(enabled=True,interval_seconds=60));due(manager,cid)
    assert manager.refresh.schedule() and not manager.refresh.schedule()
    manager.action(auth(),cid,'disconnect')
    assert not manager.refresh.schedule()


def test_settings_isolation_permissions_and_validation(manager):
    cid=manager.connect(auth(),config())['connection_id']
    assert not manager.refresh.get(auth('other'))['items']
    for actor in (auth('other'),auth(write=False)):
        with pytest.raises(ApiFailure):manager.refresh.edit(actor,cid,dict(enabled=True,interval_seconds=60))
    for body in (dict(enabled=True,interval_seconds=1),dict(enabled=1,interval_seconds=60),dict(enabled=True,interval_seconds=True)):
        with pytest.raises(ApiFailure):manager.refresh.edit(auth(),cid,body)


def test_disconnect_during_automatic_profile_cannot_reactivate(manager):
    cid=manager.connect(auth(),config())['connection_id'];manager.tick();due(manager,cid)
    manager.adapter.hook=lambda:manager.action(auth(),cid,'disconnect')
    manager.tick()
    assert manager.metadata(auth(),cid)['connection']['connection_status']=='disconnected'
    assert manager.metadata(auth(),cid)['snapshot']['revision']==1
